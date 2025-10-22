"""
Quality Gate: Main content filtering pipeline.

Orchestrates validation → deduplication → detection → scoring → ranking.
STREAMING: Emits high-quality items IMMEDIATELY as they pass quality gates (no batching).

Pure functions, no mutation, defensive coding, PEP8 compliant.

Module Structure:
- Imports from: quality_config, quality_dedup, quality_detectors, quality_scoring
- Orchestrates: Full pipeline flow (item-by-item streaming)
- Emits: Messages to Azure Storage Queue for processor AS SOON as items qualify

Key Design: Each item emitted individually, allowing processor to start work immediately
rather than waiting for entire batch to be ranked. This minimizes latency between
collection and processing.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from quality.config import get_quality_config
from quality.dedup import apply_all_dedup_layers
from quality.detectors import detect_content_quality
from quality.scoring import calculate_quality_score, rank_items, score_items

logger = logging.getLogger(__name__)


# ============================================================================
# VALIDATION LAYER - Defensive input checking
# ============================================================================


def validate_item(item: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate item has required fields and correct types.

    Required fields: title, content
    Optional but recommended: source, source_url, url

    Args:
        item: Object to validate

    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    if not isinstance(item, dict):
        return (False, f"Item not dict: {type(item).__name__}")

    title = item.get("title")
    content = item.get("content")

    if not title:
        return (False, "Missing required field: title")

    if not isinstance(title, str):
        return (False, f"Field title not str: {type(title).__name__}")

    if not content:
        return (False, "Missing required field: content")

    if not isinstance(content, str):
        return (False, f"Field content not str: {type(content).__name__}")

    # Optional fields - check type if present
    if "source" in item and not isinstance(item["source"], str):
        return (False, f"Field source not str: {type(item['source']).__name__}")

    if "source_url" in item and not isinstance(item["source_url"], str):
        return (False, f"Field source_url not str: {type(item['source_url']).__name__}")

    return (True, None)


def validate_items(items: Any) -> Tuple[List[Dict], List[str]]:
    """
    Validate batch of items, return valid items and error list.

    Args:
        items: List of items to validate

    Returns:
        (valid_items: List[Dict], errors: List[str])
    """
    if not isinstance(items, list):
        return ([], [f"Items not list: {type(items).__name__}"])

    valid_items = []
    errors = []

    for idx, item in enumerate(items):
        is_valid, error_msg = validate_item(item)

        if is_valid:
            valid_items.append(item)
        else:
            errors.append(f"Item {idx}: {error_msg}")

    return (valid_items, errors)


# ============================================================================
# PROCESSING LAYER - Main pipeline orchestration
# ============================================================================


async def process_items(
    items: List[Dict],
    blob_client: Any,
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Process items through complete quality gate pipeline.

    Pipeline stages:
    1. Validate (check required fields and types)
    2. Deduplicate (Layer 1 batch → Layer 2 today → Layer 3 historical)
    3. Detect unsuitable content (paywall, comparison, listicle)
    4. Score quality (apply penalties for detections)
    5. Rank (sort by score, apply source diversity)
    6. Return (metadata, top N items, filtering stats)

    Args:
        items: List of content items to process
        blob_client: Azure ContainerClient for processed-content container.
                     Required for deduplication layers (list_blobs, download_blob).
                     Must be bound to the "processed-content" container.
                     Type: azure.storage.blob.aio.ContainerClient
        config: Configuration dict (optional, uses defaults if not provided)

    Returns:
        {
            "status": "success" | "error",
            "message": str,
            "items": [...ranked items...],
            "stats": {
                "input": int,
                "valid": int,
                "deduplicated": int,
                "scored": int,
                "ranked": int,
                "filtered_by": [list of detection reasons],
            },
            "errors": [list of errors if any],
        }
    """
    try:
        config = config or get_quality_config()

        # Stage 1: Validate
        valid_items, validation_errors = validate_items(items)

        if not valid_items:
            return {
                "status": "error",
                "message": "No valid items after validation",
                "items": [],
                "stats": {
                    "input": len(items) if isinstance(items, list) else 0,
                    "valid": 0,
                    "deduplicated": 0,
                    "scored": 0,
                    "ranked": 0,
                },
                "errors": validation_errors,
            }

        # Stage 2: Deduplicate
        deduped_items = await apply_all_dedup_layers(valid_items, blob_client, config)

        # Stage 3: Detect unsuitable content & Stage 4: Score
        scored_items = score_items(deduped_items, config)

        # Stage 5: Rank and apply diversity
        max_results = config.get("max_results", 20)
        ranked_items = rank_items(scored_items, max_results=max_results)

        # Collect statistics
        detection_reasons = set()
        for item in deduped_items:
            detection = detect_content_quality(
                str(item.get("title", "")),
                str(item.get("content", "")),
                str(item.get("source_url", "")),
            )
            for reason in detection.get("detections", []):
                detection_reasons.add(reason)

        stats = {
            "input": len(items) if isinstance(items, list) else 0,
            "valid": len(valid_items),
            "deduplicated": len(deduped_items),
            "scored": len(scored_items),
            "ranked": len(ranked_items),
            "filtered_by": sorted(list(detection_reasons)),
        }

        return {
            "status": "success",
            "message": f"Processed {stats['input']} items → {stats['ranked']} high-quality results",
            "items": ranked_items,
            "stats": stats,
            "errors": validation_errors if validation_errors else None,
        }

    except Exception as e:
        logger.error(f"Error in process_items: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Processing error: {str(e)}",
            "items": [],
            "stats": {
                "input": len(items) if isinstance(items, list) else 0,
                "valid": 0,
                "deduplicated": 0,
                "scored": 0,
                "ranked": 0,
            },
            "errors": [str(e)],
        }


# ============================================================================
# STREAMING LAYER - Message emission for processor
# ============================================================================


async def emit_to_processor(
    items: List[Dict],
    queue_client: Any,
    message_template: Optional[Dict] = None,
) -> Tuple[bool, str]:
    """
    Emit high-quality items to processor queue.

    Creates message for each item with content, metadata, and score.
    Messages trigger ContentEnricher → ContentPublisher pipeline.

    Args:
        items: High-quality items to emit
        queue_client: Azure Queue async client
        message_template: Template dict for message structure (optional)

    Returns:
        (success: bool, message: str)
    """
    if not queue_client:
        return (False, "No queue client provided")

    if not isinstance(items, list):
        return (False, f"Items not list: {type(items).__name__}")

    template = message_template or {
        "type": "process_article",
        "source": "quality_gate",
    }

    try:
        emitted = 0

        for item in items:
            if not isinstance(item, dict):
                logger.warning(f"Skipping non-dict item: {type(item).__name__}")
                continue

            # Build message
            message = template.copy()
            message.update(
                {
                    "title": item.get("title"),
                    "content": item.get("content"),
                    "source": item.get("source"),
                    "source_url": item.get("source_url"),
                    "url": item.get("url"),
                    "quality_score": item.get("_quality_score", 0.0),
                    "timestamp": datetime.now(timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                }
            )

            # Send message
            try:
                await queue_client.send_message(json.dumps(message))
                emitted += 1
            except Exception as e:
                logger.error(f"Failed to emit message for {item.get('title')}: {e}")
                continue

        return (True, f"Emitted {emitted}/{len(items)} items to processor")

    except Exception as e:
        logger.error(f"Error emitting to processor: {e}", exc_info=True)
        return (False, str(e))


# ============================================================================
# SUMMARY AND MONITORING
# ============================================================================


def get_pipeline_status(
    process_result: Dict, emit_result: Optional[Tuple] = None
) -> Dict[str, Any]:
    """
    Get human-readable pipeline status and results.

    Args:
        process_result: Result from process_items()
        emit_result: Result from emit_to_processor() (optional)

    Returns:
        Status dict with summary information
    """
    if not isinstance(process_result, dict):
        return {"status": "error", "message": "Invalid process result"}

    stats = process_result.get("stats", {})

    summary = {
        "status": process_result.get("status"),
        "total_processed": stats.get("input", 0),
        "valid": stats.get("valid", 0),
        "deduplicated": stats.get("deduplicated", 0),
        "quality_passed": stats.get("scored", 0),
        "top_ranked": stats.get("ranked", 0),
        "filtered_reasons": stats.get("filtered_by", []),
    }

    if emit_result:
        success, message = emit_result
        summary["emitted"] = success
        summary["emit_message"] = message

    return summary

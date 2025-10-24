"""
Streaming pipeline orchestration.

Pure functions: collect → review → dedupe → save → queue
Yields items immediately to processor as they pass quality gates.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


async def stream_collection(
    collector_fn: AsyncIterator[Dict[str, Any]],
    collection_id: str,
    collection_blob: str,
    blob_client: Any,
    queue_client: Any,
    strict_quality_check: bool = True,
) -> Dict[str, int]:
    """
    Stream items through quality pipeline: collect → review → dedupe → save → queue.

    Each item that passes quality gate is immediately:
    1. Saved to blob storage
    2. Marked as seen in dedup
    3. Sent to processor queue

    Args:
        collector_fn: Async generator yielding collected items
        collection_id: Unique collection identifier
        collection_blob: Blob path for storage
        blob_client: Azure Blob Storage client
        queue_client: Azure Storage Queue client
        strict_quality_check: If False, use permissive quality checking (for default sources)

    Returns:
        Stats dict: collected, published, rejected_quality, rejected_dedup
    """
    from pipeline.dedup import hash_content, is_seen, mark_seen
    from quality.review import review_item

    stats = {
        "collected": 0,
        "published": 0,
        "rejected_quality": 0,
        "rejected_dedup": 0,
    }

    seen_hashes = set()

    async for item in collector_fn:
        stats["collected"] += 1

        try:
            # Quality review (pure function) - use strict_mode parameter
            passes_review, rejection_reason = review_item(
                item, strict_mode=strict_quality_check
            )

            if not passes_review:
                stats["rejected_quality"] += 1
                logger.debug(f"Quality rejected: {item.get('id')} - {rejection_reason}")
                continue

            # Deduplication check
            item_hash = hash_content(item.get("title", ""), item.get("content", ""))

            if not item_hash:
                logger.warning(f"Could not hash item {item.get('id')}")
                stats["rejected_dedup"] += 1
                continue

            if item_hash in seen_hashes or await is_seen(item_hash, blob_client):
                stats["rejected_dedup"] += 1
                logger.debug(f"Duplicate: {item.get('id')}")
                continue

            seen_hashes.add(item_hash)
            await mark_seen(item_hash, blob_client)

            # Save to blob (append operation)
            await blob_client.append_item(collection_id, item)

            # Send to processor queue
            message = create_queue_message(item, collection_id, collection_blob)
            await queue_client.send_message(message)

            stats["published"] += 1
            logger.info(f"✅ Published: {item.get('id')}")

        except Exception as e:
            logger.error(f"Error processing item {item.get('id')}: {e}")
            continue

    return stats


def create_queue_message(
    item: Dict[str, Any], collection_id: str, collection_blob: str
) -> Dict[str, Any]:
    """
    Create queue message for content-processor.

    CRITICAL: Must match exact format expected by content-processor.
    See: containers/content-processor/docs/

    Args:
        item: Reviewed item with quality metadata
        collection_id: Collection identifier
        collection_blob: Blob path reference

    Returns:
        Queue message dict (JSON-serializable)
    """
    # Fallback ID: Use deterministic hash instead of random UUID
    # Ensures same item reprocessed after failure won't create duplicate messages
    fallback_id = None
    if not item.get("id"):
        from pipeline.dedup import hash_content

        title = item.get("title", "")
        content = item.get("content", "")
        if title or content:
            # Use hash of content for deterministic ID
            content_hash = hash_content(title, content)
            if content_hash:
                fallback_id = f"topic_{content_hash[:12]}"
        if not fallback_id:
            # Only use random UUID if we can't compute hash (defensive)
            fallback_id = f"topic_{uuid4().hex[:8]}"

    payload = {
        "topic_id": item.get("id", fallback_id),
        "title": item.get("title", "Untitled"),
        "source": item.get("source", "unknown"),
        "collected_at": item.get(
            "collected_at", datetime.now(timezone.utc).isoformat()
        ),
        "priority_score": item.get("priority_score", 0.5),
        "collection_id": collection_id,
        "collection_blob": collection_blob,
    }

    # Add optional metadata fields
    metadata = item.get("metadata", {})
    if metadata.get("subreddit"):
        payload["subreddit"] = metadata["subreddit"]
    if metadata.get("url") or item.get("url"):
        payload["url"] = metadata.get("url") or item.get("url")
    if metadata.get("score") is not None:
        payload["upvotes"] = metadata["score"]
    if metadata.get("num_comments") is not None:
        payload["comments"] = metadata["num_comments"]
    if metadata.get("boosts") is not None:
        payload["boosts"] = metadata["boosts"]
    if metadata.get("author"):
        payload["author"] = metadata["author"]

    # Correlation ID: Use descriptive format for better traceability
    # Format: {collection_id}_{topic_id} to link collection through pipeline stages
    topic_id = payload.get("topic_id", "unknown")
    correlation_id = f"{collection_id}_{topic_id}"

    message = {
        "operation": "process_topic",
        "service_name": "content-collector",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": correlation_id,
        "payload": payload,
    }

    return message

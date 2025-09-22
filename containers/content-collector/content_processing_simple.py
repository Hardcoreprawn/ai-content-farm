"""
Simplified Content Processing Functions - ACTIVE

CURRENT ARCHITECTURE: Simple content processing using simplified collectors
Status: ACTIVE - Replaces complex content_processing.py

Clean, simple content collection using the new simplified collectors.
Provides batch collection and deduplication without complex strategies.

Features:
- Multi-source batch collection using factory pattern
- Simple content deduplication by hash
- Configuration conversion from legacy formats
- Clean error handling and metadata tracking
- Easy integration with existing service logic

Clean, simple content collection using the new simplified collectors.
"""

import hashlib
from typing import Any, Dict, List

from collectors.factory import CollectorFactory


async def collect_content_batch(sources_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Collect content from multiple sources using simplified collectors.

    Args:
        sources_data: List of source configurations with type, subreddits,
                     limit, and criteria

    Returns:
        Dictionary with collected_items and metadata
    """
    all_items = []
    source_metadata = {}
    total_processed = 0

    for source_config in sources_data:
        source_type = source_config.get("type", "")

        try:
            # Convert source config to simplified collector format
            collector_config = _convert_source_config(source_config)

            # Create and use simplified collector
            collector = CollectorFactory.create_collector(source_type, collector_config)

            async with collector:
                items = await collector.collect_with_retry()

            # Add source information to each item
            for item in items:
                item["source_type"] = source_type
                item["source_config"] = source_config

            all_items.extend(items)
            total_processed += 1

            # Track metadata for this source
            source_metadata[f"{source_type}_count"] = len(items)
            source_metadata[f"{source_type}_status"] = "success"

        except Exception as e:
            # Log error but continue with other sources
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to collect from {source_type}: {e}")

            source_metadata[f"{source_type}_count"] = 0
            source_metadata[f"{source_type}_status"] = "failed"
            source_metadata[f"{source_type}_error"] = str(e)

    return {
        "collected_items": all_items,
        "metadata": {
            "total_sources": len(sources_data),
            "sources_processed": total_processed,
            "total_items": len(all_items),
            **source_metadata,
        },
    }


def _convert_source_config(source_config: Dict[str, Any]) -> Dict[str, Any]:
    """Convert old source config format to simplified collector config."""

    config = {}
    source_type = source_config.get("type", "")

    # Convert common parameters
    if "limit" in source_config:
        config["max_items"] = source_config["limit"]

    # Convert Reddit-specific parameters
    if source_type == "reddit":
        if "subreddits" in source_config:
            config["subreddits"] = source_config["subreddits"]

        # Convert criteria to sort/time filter
        criteria = source_config.get("criteria", {})
        if "sort" in criteria:
            config["sort"] = criteria["sort"]
        if "time_filter" in criteria:
            config["time_filter"] = criteria["time_filter"]

    # Convert Mastodon-specific parameters
    elif source_type == "mastodon":
        if "instances" in source_config:
            config["instances"] = source_config["instances"]
        if "hashtags" in source_config:
            config["hashtags"] = source_config["hashtags"]

        criteria = source_config.get("criteria", {})
        if "types" in criteria:
            config["types"] = criteria["types"]

    return config


async def deduplicate_content(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate content based on content hash.

    Args:
        items: List of content items to deduplicate

    Returns:
        List of unique content items
    """
    seen_hashes = set()
    unique_items = []

    for item in items:
        # Create hash from title and content for deduplication
        content_text = f"{item.get('title', '')}{item.get('content', '')}"
        content_hash = hashlib.md5(content_text.encode("utf-8")).hexdigest()

        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            item["content_hash"] = content_hash
            unique_items.append(item)

    return unique_items

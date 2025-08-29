"""
Content Processing Functions

Utility functions for batch content collection and deduplication.
"""

import asyncio
import hashlib
from typing import Any, Dict, List

from source_collectors import SourceCollectorFactory


async def collect_content_batch(sources_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Collect content from multiple sources in batch.

    Args:
        sources_data: List of source configurations with type, subreddits, limit, and criteria

    Returns:
        Dictionary with collected_items and metadata
    """
    all_items = []
    source_metadata = {}
    total_processed = 0

    for source_config in sources_data:
        source_type = source_config.get("type", "")

        try:
            # Create collector for this source type
            collector = SourceCollectorFactory.create_collector(source_type)

            # Collect content from this source
            items = await collector.collect_content(source_config)

            # Add source information to each item
            for item in items:
                item["source_type"] = source_type
                item["source_config"] = source_config

            all_items.extend(items)
            total_processed += 1

            # Track metadata for this source
            source_metadata[f"{source_type}_count"] = len(items)

        except Exception as e:
            source_metadata[f"{source_type}_error"] = str(e)
            continue

    metadata = {
        "total_sources": len(sources_data),
        "sources_processed": total_processed,
        "total_collected": len(all_items),
        "source_breakdown": source_metadata,
    }

    return {"collected_items": all_items, "metadata": metadata}


def deduplicate_content(
    items: List[Dict[str, Any]], similarity_threshold: float = 0.8
) -> List[Dict[str, Any]]:
    """
    Remove duplicate content from a list of items based on content similarity.

    Args:
        items: List of content items to deduplicate
        similarity_threshold: Threshold for considering items similar (0-1)

    Returns:
        List of deduplicated items
    """
    if not items:
        return items

    # Simple deduplication based on content hash and title similarity
    seen_hashes = set()
    seen_titles = set()
    deduplicated_items = []

    for item in items:
        # Create content hash
        content = item.get("content", "") or item.get("text", "") or ""
        title = item.get("title", "") or ""

        # Create hash from content and title
        content_hash = hashlib.md5(f"{title}:{content}".encode()).hexdigest()

        # Simple title-based deduplication (exact match)
        title_lower = title.lower().strip()

        # Skip if we've seen this exact content or title
        if content_hash in seen_hashes or title_lower in seen_titles:
            continue

        # For more sophisticated similarity checking, we could use
        # libraries like difflib or sentence transformers, but for now
        # we'll use exact matching as it's more predictable

        seen_hashes.add(content_hash)
        if title_lower:
            seen_titles.add(title_lower)

        deduplicated_items.append(item)

    return deduplicated_items

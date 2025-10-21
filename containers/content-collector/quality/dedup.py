"""
Deduplication utilities - Three-layer dedup strategy.

Layer 1: In-memory (current batch)
Layer 2: Same-day blob storage (published today)
Layer 3: Historical URLs (never republish same source)

Pure functions, no side effects, defensive coding.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


def hash_content(title: str, content: str) -> str:
    """
    Create stable hash of content for deduplication.

    Uses SHA256(title + first 500 chars of content).
    Returns empty string on invalid input (defensive).

    Args:
        title: Article title
        content: Article body text

    Returns:
        Hex string SHA256 hash (empty string if input invalid)
    """
    if not isinstance(title, str) or not isinstance(content, str):
        return ""

    combined = f"{title.strip()}{content[:500].strip()}".encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


def filter_duplicates_in_batch(items: List[Dict]) -> List[Dict]:
    """
    Remove duplicates from current batch (Layer 1: in-memory).

    Prevents same item appearing twice in single collection cycle.
    Maintains insertion order. Pure function (no mutation of input).

    Args:
        items: List of content items to deduplicate

    Returns:
        List with duplicates removed (by content hash)
    """
    if not isinstance(items, list):
        return []

    seen_hashes: Set[str] = set()
    result = []

    for item in items:
        if not isinstance(item, dict):
            continue

        title = str(item.get("title", "")).strip()
        content = str(item.get("content", "")).strip()

        if not title or not content:
            continue

        item_hash = hash_content(title, content)

        if item_hash and item_hash not in seen_hashes:
            seen_hashes.add(item_hash)
            result.append(item)

    return result


async def filter_duplicates_today(
    items: List[Dict], blob_client: Any, container_name: str = "processed-content"
) -> List[Dict]:
    """
    Filter out articles published today (Layer 2: same-day storage).

    Checks blob storage for articles published in current date.
    Prevents republishing same article multiple times per day.

    Fails open: if blob storage unreachable, returns items unchanged.

    Args:
        items: List of items to check
        blob_client: Azure Blob Storage client (async)
        container_name: Blob container for processed articles

    Returns:
        List with today's published articles removed
    """
    if not isinstance(items, list) or not blob_client:
        return items

    try:
        today_str = datetime.utcnow().strftime("%Y/%m/%d")
        prefix = f"articles/{today_str}/"

        # Collect hashes of all today's published articles
        today_hashes: Set[str] = set()

        try:
            container = blob_client.get_container_client(container_name)
            async for blob in container.list_blobs(name_starts_with=prefix):
                if not blob.name.endswith(".json"):
                    continue

                try:
                    article_json = await container.download_blob(blob.name).readall()
                    article_data = json.loads(article_json)

                    if "title" in article_data and "content" in article_data:
                        pub_hash = hash_content(
                            article_data["title"], article_data["content"]
                        )
                        if pub_hash:
                            today_hashes.add(pub_hash)
                except Exception as e:
                    logger.debug(f"Could not hash article {blob.name}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Could not list today's articles: {e}")
            return items  # Fail open

        # Filter out items matching today's hashes
        result = []
        for item in items:
            if isinstance(item, dict):
                title = str(item.get("title", "")).strip()
                content = str(item.get("content", "")).strip()

                if title and content:
                    item_hash = hash_content(title, content)
                    if item_hash and item_hash not in today_hashes:
                        result.append(item)
                else:
                    result.append(item)
            else:
                result.append(item)

        return result

    except Exception as e:
        logger.error(f"Error in Layer 2 dedup: {e}")
        return items  # Fail open


async def filter_duplicates_historical(
    items: List[Dict],
    blob_client: Any,
    metadata_path: str = "metadata/published-urls.json",
) -> List[Dict]:
    """
    Filter out articles with URLs already published (Layer 3: historical).

    Prevents publishing same external source URL twice, even days apart.
    Uses metadata file tracking all published URLs.

    Fails open: if metadata unreachable, returns items unchanged.

    Args:
        items: List of items to check
        blob_client: Azure Blob Storage client
        metadata_path: Path to published URLs metadata file

    Returns:
        List with historically published URLs removed
    """
    if not isinstance(items, list) or not blob_client:
        return items

    try:
        # Load published URLs from metadata
        published_urls: Set[str] = set()

        try:
            container = blob_client.get_container_client("processed-content")
            metadata_blob = await container.download_blob(metadata_path).readall()
            metadata = json.loads(metadata_blob)
            published_urls = set(metadata.get("urls", []))
        except Exception as e:
            logger.debug(f"Could not load published URLs metadata: {e}")
            # Fail open - don't block on metadata errors

        # Filter out items with published source URLs
        result = []
        for item in items:
            if isinstance(item, dict):
                source_url = str(item.get("source_url", "")).strip()
                url = str(item.get("url", "")).strip()

                check_url = source_url or url

                if check_url and check_url not in published_urls:
                    result.append(item)
                elif not check_url:
                    result.append(item)  # No URL, can't deduplicate
            else:
                result.append(item)

        return result

    except Exception as e:
        logger.error(f"Error in Layer 3 dedup: {e}")
        return items  # Fail open


async def apply_all_dedup_layers(
    items: List[Dict], blob_client: Any, config: Optional[Dict] = None
) -> List[Dict]:
    """
    Apply all three deduplication layers in order.

    Orchestrates: Layer 1 (batch) → Layer 2 (today) → Layer 3 (historical).

    Args:
        items: List of items to deduplicate
        blob_client: Azure Blob Storage client
        config: Configuration dict (optional, for enable/disable flags)

    Returns:
        Deduplicated items from all layers
    """
    if not isinstance(items, list):
        return []

    config = config or {}

    # Layer 1: In-memory batch dedup (always enabled, no blob needed)
    result = filter_duplicates_in_batch(items)

    # Layer 2: Today's published articles
    if config.get("deduplication", {}).get("check_today", True):
        result = await filter_duplicates_today(result, blob_client)

    # Layer 3: Historical URLs
    if config.get("deduplication", {}).get("check_historical", True):
        result = await filter_duplicates_historical(result, blob_client)

    return result

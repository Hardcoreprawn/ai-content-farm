"""
Deduplication: Three-layer strategy with 14-day window.

Layer 1: In-memory (current batch)
Layer 2: Same-day blob storage (published today)
Layer 3: Historical URLs (never republish same source)

Pure functions, no side effects, defensive coding.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Set

logger = logging.getLogger(__name__)


def hash_content(title: str, content: str) -> str:
    """
    Create stable hash of content for deduplication.

    Uses SHA256(title + first 500 chars of content).

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


async def is_seen(item_hash: str, blob_client: Any) -> bool:
    """
    Check if item has been seen in last 14 days.

    Checks blob storage for dedup history from past 14 days.
    Fails open: if blob unreachable, returns False (not seen).

    Args:
        item_hash: Content hash to check
        blob_client: Azure Blob Storage client

    Returns:
        True if seen in past 14 days, False otherwise
    """
    if not blob_client or not item_hash:
        return False

    try:
        # Check last 14 days of dedup files
        today = datetime.now(timezone.utc).date()

        for days_back in range(14):
            check_date = today - timedelta(days=days_back)
            blob_name = f"deduplicated-content/{check_date.isoformat()}.json"

            try:
                content = await blob_client.download_json(blob_name)

                if isinstance(content, dict):
                    hashes = content.get("hashes", [])
                elif isinstance(content, list):
                    hashes = content
                else:
                    continue

                if item_hash in hashes:
                    return True

            except Exception:
                # Blob doesn't exist for this date, continue checking
                continue

        return False

    except Exception as e:
        logger.warning(f"Error checking dedup: {e}, failing open (not seen)")
        return False


async def mark_seen(item_hash: str, blob_client: Any) -> bool:
    """
    Mark item as seen (append to today's dedup file).

    Appends hash to blob: deduplicated-content/YYYY-MM-DD.json

    Args:
        item_hash: Content hash to mark
        blob_client: Azure Blob Storage client

    Returns:
        True if successful, False otherwise
    """
    if not blob_client or not item_hash:
        return False

    try:
        today = datetime.now(timezone.utc).date()
        blob_name = f"deduplicated-content/{today.isoformat()}.json"

        # Read existing hashes
        try:
            existing = await blob_client.download_json(blob_name)
            if isinstance(existing, dict):
                hashes = existing.get("hashes", [])
            elif isinstance(existing, list):
                hashes = existing
            else:
                hashes = []
        except Exception:
            # File doesn't exist or error reading, start fresh
            hashes = []

        # Add new hash if not already present
        if item_hash not in hashes:
            hashes.append(item_hash)

        # Write back to blob
        data = {"hashes": hashes, "updated": datetime.now(timezone.utc).isoformat()}
        await blob_client.upload_json(blob_name, data)

        return True

    except Exception as e:
        logger.error(f"Error marking seen: {e}")
        return False

"""Manual collection trigger endpoint for Container App."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4


def validate_trigger_payload(payload: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate collection trigger payload.

    Args:
        payload: Request JSON payload

    Returns:
        (is_valid, error_message) tuple
    """
    # Type check
    if not isinstance(payload, dict):
        return (False, "Payload must be JSON object")

    # Get sources
    subreddits = payload.get("subreddits", [])
    instances = payload.get("instances", [])

    # At least one source required
    if not subreddits and not instances:
        return (False, "At least one source required (subreddits or instances)")

    # Type checking
    if not isinstance(subreddits, list):
        return (False, "subreddits must be list of strings")
    if not isinstance(instances, list):
        return (False, "instances must be list of strings")

    # Source limits
    if len(subreddits) > 20:
        return (False, "Maximum 20 subreddits allowed")
    if len(instances) > 5:
        return (False, "Maximum 5 Mastodon instances allowed")

    # Validate individual sources (must be non-empty strings)
    for sub in subreddits:
        if not isinstance(sub, str) or not sub.strip():
            return (False, "Invalid subreddit name (must be non-empty string)")

    for instance in instances:
        if not isinstance(instance, str) or not instance.strip():
            return (False, "Invalid instance URL (must be non-empty string)")

    # Optional parameters
    min_score = payload.get("min_score", 25)
    max_items = payload.get("max_items", 50)

    if not isinstance(min_score, int) or min_score < 0:
        return (False, "min_score must be non-negative integer")
    if not isinstance(max_items, int) or max_items <= 0 or max_items > 100:
        return (False, "max_items must be 1-100")

    return (True, None)


def create_trigger_message(
    subreddits: Optional[List[str]] = None,
    instances: Optional[List[str]] = None,
    min_score: int = 25,
    max_items: int = 50,
) -> Dict[str, Any]:
    """
    Create trigger message for manual collection.

    Args:
        subreddits: List of subreddit names
        instances: List of Mastodon instance URLs
        min_score: Minimum score filter for Reddit posts
        max_items: Maximum items to collect

    Returns:
        Trigger message dict
    """
    collection_id = f"manual_{uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    return {
        "operation": "trigger_collection",
        "collection_id": collection_id,
        "collection_blob": f"manual-tests/{now_iso[:10]}/{collection_id}.json",
        "subreddits": subreddits or [],
        "instances": instances or [],
        "min_score": min_score,
        "max_items": max_items,
        "timestamp": now_iso,
        "source": "manual_endpoint",
    }

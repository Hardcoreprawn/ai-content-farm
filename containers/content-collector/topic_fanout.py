"""Pure functions for converting collection items to individual topic messages.

This module supports the architecture pivot to single-topic queue processing,
enabling true horizontal scaling with KEDA.

Architecture:
    OLD: 100 topics → 1 message → 1 processor → 33 minutes
    NEW: 100 topics → 100 messages → 10 processors → 20 seconds (90% faster!)

See: containers/content-processor/ARCHITECTURE_PIVOT_COMPLETE.md
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


def create_topic_message(
    item: Dict[str, Any],
    collection_id: str,
    collection_blob: str,
) -> Dict[str, Any]:
    """Convert a collection item to a topic processing queue message.

    This is a pure function that transforms collection item data into the
    format expected by the content-processor's single-topic handler.

    Args:
        item: Collection item dict with topic data
        collection_id: Unique identifier for the source collection
        collection_blob: Blob path to source collection (for audit trail)

    Returns:
        Queue message dict ready for JSON serialization

    Example:
        >>> item = {
        ...     "id": "reddit_abc123",
        ...     "title": "Cool Tech Article",
        ...     "source": "reddit",
        ...     "url": "https://reddit.com/r/tech/...",
        ...     "metadata": {"subreddit": "technology", "score": 42}
        ... }
        >>> msg = create_topic_message(item, "col123", "collections/...")
        >>> msg["operation"]
        'process_topic'
        >>> msg["payload"]["topic_id"]
        'reddit_abc123'
    """
    # Extract reddit-specific metadata if present
    metadata = item.get("metadata", {})

    # Extract core fields with sensible defaults
    topic_id = item.get("id", f"topic_{uuid4().hex[:8]}")
    title = item.get("title", "Untitled Topic")
    source = item.get("source", "unknown")
    url = item.get("url")

    # Extract Reddit-specific fields
    subreddit = metadata.get("subreddit")
    upvotes = metadata.get("score") or metadata.get("ups") or metadata.get("upvotes")
    comments = (
        metadata.get("num_comments")
        or metadata.get("comments")
        or metadata.get("num_comments")
    )

    # Get collected timestamp (prefer item-level, fall back to now)
    collected_at_str = item.get("created_at") or item.get("collected_at")
    if not collected_at_str:
        collected_at_str = datetime.now(timezone.utc).isoformat()

    # Calculate priority score (0.5 default if not present)
    priority_score = item.get("priority_score", 0.5)

    # Construct message payload
    payload: Dict[str, Any] = {
        "topic_id": topic_id,
        "title": title,
        "source": source,
        "collected_at": collected_at_str,
        "priority_score": priority_score,
        "collection_id": collection_id,  # Audit trail
        "collection_blob": collection_blob,  # Reference back to source
    }

    # Add optional fields only if present (keep payload lean)
    if subreddit:
        payload["subreddit"] = subreddit
    if url:
        payload["url"] = url
    if upvotes is not None:
        payload["upvotes"] = upvotes
    if comments is not None:
        payload["comments"] = comments

    # Construct full queue message
    message = {
        "operation": "process_topic",
        "service_name": "content-collector",
        "payload": payload,
        "correlation_id": f"{collection_id}_{topic_id}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return message


def create_topic_messages_batch(
    items: List[Dict[str, Any]],
    collection_id: str,
    collection_blob: str,
) -> List[Dict[str, Any]]:
    """Convert a list of collection items to individual topic messages.

    This is a pure function that maps over collection items and produces
    a list of queue messages ready for fanout.

    Args:
        items: List of collection item dicts
        collection_id: Unique identifier for the source collection
        collection_blob: Blob path to source collection

    Returns:
        List of queue message dicts

    Example:
        >>> items = [
        ...     {"id": "t1", "title": "Topic 1", "source": "reddit"},
        ...     {"id": "t2", "title": "Topic 2", "source": "rss"},
        ... ]
        >>> messages = create_topic_messages_batch(items, "col123", "...")
        >>> len(messages)
        2
        >>> all(msg["operation"] == "process_topic" for msg in messages)
        True
    """
    return [
        create_topic_message(item, collection_id, collection_blob) for item in items
    ]


def validate_topic_message(message: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Validate that a topic message has all required fields.

    This is a pure function for validating message structure before sending.

    Args:
        message: Topic message dict to validate

    Returns:
        Tuple of (is_valid, error_message)
            - (True, None) if valid
            - (False, "error description") if invalid

    Example:
        >>> msg = {"operation": "process_topic", "payload": {"topic_id": "t1"}}
        >>> is_valid, error = validate_topic_message(msg)
        >>> is_valid
        True
    """
    # Check top-level required fields
    if message.get("operation") != "process_topic":
        return False, "Missing or invalid 'operation' field"

    payload = message.get("payload")
    if not payload or not isinstance(payload, dict):
        return False, "Missing or invalid 'payload' field"

    # Check required payload fields
    required_fields = ["topic_id", "title", "source", "collection_id"]
    for field in required_fields:
        if not payload.get(field):
            return False, f"Missing required payload field: {field}"

    # All checks passed
    return True, None


def count_topic_messages_by_source(messages: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count topic messages grouped by source type.

    This is a pure function for generating statistics on message batches.

    Args:
        messages: List of topic message dicts

    Returns:
        Dict mapping source type to count

    Example:
        >>> messages = [
        ...     {"payload": {"source": "reddit"}},
        ...     {"payload": {"source": "reddit"}},
        ...     {"payload": {"source": "rss"}},
        ... ]
        >>> counts = count_topic_messages_by_source(messages)
        >>> counts
        {'reddit': 2, 'rss': 1}
    """
    counts: Dict[str, int] = {}

    for message in messages:
        payload = message.get("payload", {})
        source = payload.get("source", "unknown")
        counts[source] = counts.get(source, 0) + 1

    return counts

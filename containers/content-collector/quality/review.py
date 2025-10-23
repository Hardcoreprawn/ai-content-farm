"""
Quality review: Item-level content filtering.

Refactored from batch quality_gate.py for streaming use.
Each item reviewed individually as it flows through pipeline.

Pure functions, defensive coding, no I/O operations.
"""

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def validate_item(item: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate item has required fields and correct types.

    Required fields: id, title, content, source
    Optional: url, collected_at, metadata

    Args:
        item: Object to validate

    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    if not isinstance(item, dict):
        return (False, f"Item not dict: {type(item).__name__}")

    # Required fields
    required = ["id", "title", "content", "source"]
    for field in required:
        if field not in item:
            return (False, f"Missing required field: {field}")

        if not isinstance(item[field], str):
            return (False, f"Field {field} not str: {type(item[field]).__name__}")

    # Optional fields - check type if present
    if "url" in item and not isinstance(item.get("url"), str):
        return (False, f"Field url not str")

    if "collected_at" in item and not isinstance(item.get("collected_at"), str):
        return (False, f"Field collected_at not str")

    if "metadata" in item and not isinstance(item.get("metadata"), dict):
        return (False, f"Field metadata not dict")

    return (True, None)


def check_readability(item: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Basic readability checks (no external API calls).

    Filters:
    - Title too short (< 10 chars)
    - Content too short (< 100 chars)
    - Title is just numbers/symbols
    - Content is mostly HTML/JSON (corrupt)

    Args:
        item: Standardized item dict

    Returns:
        (passes_check: bool, rejection_reason: Optional[str])
    """
    title = item.get("title", "").strip()
    content = item.get("content", "").strip()

    # Title length
    if len(title) < 10:
        return (False, "title_too_short")

    # Content length
    if len(content) < 100:
        return (False, "content_too_short")

    # Title is mostly symbols/numbers
    alphanumeric = sum(1 for c in title if c.isalnum() or c.isspace())
    if alphanumeric < len(title) * 0.5:  # Less than 50% alphanumeric
        return (False, "title_not_readable")

    # Content is mostly HTML tags or JSON
    html_ratio = (content.count("<") + content.count("{")) / max(len(content), 1)
    if html_ratio > 0.15:  # More than 15% HTML/JSON
        return (False, "content_mostly_markup")

    return (True, None)


def check_technical_relevance(item: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Check if content is relevant to tech topics.

    Filters:
    - Missing technical keywords (code, software, development, tech, data, etc)
    - Source is off-topic (funny, videos, nosleep)

    Args:
        item: Standardized item dict

    Returns:
        (passes_check: bool, rejection_reason: Optional[str])
    """
    title = item.get("title", "").lower()
    content = item.get("content", "").lower()
    source = item.get("source", "").lower()

    # Technical keywords to look for
    tech_keywords = {
        "code",
        "software",
        "develop",
        "program",
        "tech",
        "data",
        "api",
        "database",
        "server",
        "security",
        "python",
        "javascript",
        "cloud",
        "algorithm",
        "network",
        "system",
        "app",
        "tool",
        "framework",
    }

    combined = f"{title} {content}"

    # Check if any keyword present
    has_keyword = any(kw in combined for kw in tech_keywords)

    if not has_keyword:
        return (False, "no_technical_keywords")

    # Reject obviously off-topic subreddits
    off_topic_sources = {
        "funny",
        "videos",
        "nosleep",
        "relationship_advice",
        "amitheasshole",
        "tifu",
        "showerthoughts",
    }

    source_name = item.get("metadata", {}).get("subreddit", "").lower()
    if source_name in off_topic_sources:
        return (False, "off_topic_source")

    return (True, None)


def review_item(
    item: Dict[str, Any], check_relevance: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Review single item for quality.

    Pipeline:
    1. Validate required fields
    2. Check readability
    3. Check technical relevance (optional)

    Args:
        item: Standardized item dict
        check_relevance: Whether to apply technical relevance filter

    Returns:
        (passes_review: bool, rejection_reason: Optional[str])

    Examples:
        >>> item = {
        ...     "id": "abc123",
        ...     "title": "Understanding Python Async/Await",
        ...     "content": "Python's async/await is a powerful...",
        ...     "source": "reddit",
        ...     "metadata": {"subreddit": "programming"}
        ... }
        >>> passes, reason = review_item(item)
        >>> passes
        True

        >>> item_bad = {
        ...     "id": "xyz",
        ...     "title": "Hi",
        ...     "content": "Short",
        ...     "source": "reddit"
        ... }
        >>> passes, reason = review_item(item_bad)
        >>> passes, reason
        (False, 'content_too_short')
    """
    # Stage 1: Validate
    is_valid, error = validate_item(item)
    if not is_valid:
        return (False, f"validation_error: {error}")

    # Stage 2: Check readability
    passes_readability, reason = check_readability(item)
    if not passes_readability:
        return (False, reason)

    # Stage 3: Check technical relevance (optional)
    if check_relevance:
        passes_relevance, reason = check_technical_relevance(item)
        if not passes_relevance:
            return (False, reason)

    # Item passes all checks
    return (True, None)

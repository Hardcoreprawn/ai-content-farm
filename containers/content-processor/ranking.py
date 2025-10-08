"""
Pure functional topic ranking logic for content prioritization.

This module provides stateless functions for calculating priority scores
based on engagement metrics, freshness, and content quality indicators.

Contract Version: 1.0.0
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def calculate_engagement_score(upvotes: int, comments: int) -> float:
    """
    Calculate engagement score based on upvotes and comments.

    Pure function with no side effects. Same inputs always produce same output.

    Args:
        upvotes: Number of upvotes (must be >= 0)
        comments: Number of comments (must be >= 0)

    Returns:
        float: Engagement score between 0.0 and 0.3 (0.2 from upvotes, 0.1 from comments)

    Raises:
        ValueError: If upvotes or comments are negative

    Examples:
        >>> calculate_engagement_score(100, 50)
        0.3
        >>> calculate_engagement_score(50, 25)
        0.2
        >>> calculate_engagement_score(0, 0)
        0.0
    """
    if upvotes < 0 or comments < 0:
        raise ValueError("Upvotes and comments must be non-negative")

    # Upvote bonus: linear scale, capped at 100 upvotes = 0.2
    upvote_bonus = min(0.2, upvotes / 100.0) if upvotes > 0 else 0.0

    # Comment bonus: linear scale, capped at 50 comments = 0.1
    comment_bonus = min(0.1, comments / 50.0) if comments > 0 else 0.0

    return upvote_bonus + comment_bonus


def calculate_freshness_score(
    collected_at: datetime, now: Optional[datetime] = None
) -> float:
    """
    Calculate freshness score based on content age.

    Pure function (when 'now' is provided). Freshness decreases linearly over 24 hours.

    Args:
        collected_at: When content was collected (timezone-aware)
        now: Current time for comparison (defaults to datetime.now(timezone.utc))

    Returns:
        float: Freshness score between 0.0 and 0.3
               - 0.3 for content < 1 hour old
               - 0.15 for content 12 hours old
               - 0.0 for content >= 24 hours old

    Raises:
        ValueError: If collected_at is not timezone-aware or is in the future

    Examples:
        >>> from datetime import timedelta
        >>> now = datetime.now(timezone.utc)
        >>> recent = now - timedelta(hours=1)
        >>> calculate_freshness_score(recent, now)
        0.2875
        >>> old = now - timedelta(hours=25)
        >>> calculate_freshness_score(old, now)
        0.0
    """
    if collected_at.tzinfo is None:
        raise ValueError("collected_at must be timezone-aware")

    current_time = now if now is not None else datetime.now(timezone.utc)

    if current_time.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    if collected_at > current_time:
        raise ValueError("collected_at cannot be in the future")

    hours_ago = (current_time - collected_at).total_seconds() / 3600

    # Linear decay over 24 hours: 0.3 bonus at 0 hours, 0.0 at 24+ hours
    if hours_ago >= 24:
        return 0.0

    return (24 - hours_ago) / 24 * 0.3


def calculate_title_quality_score(title: str) -> float:
    """
    Calculate quality score based on title characteristics.

    Pure function with no side effects.

    Args:
        title: Article title to analyze

    Returns:
        float: Quality score between 0.0 and 0.2
               - Up to 0.1 for reasonable length (10-200 chars)
               - Up to 0.1 for engaging keywords

    Examples:
        >>> calculate_title_quality_score("How AI is Changing Technology in 2025")
        0.2
        >>> calculate_title_quality_score("Post")
        0.0
        >>> calculate_title_quality_score("")
        0.0
    """
    if not title or not isinstance(title, str):
        return 0.0

    score = 0.0
    title_lower = title.lower()

    # Length bonus: reasonable title length (10-200 chars)
    if 10 <= len(title) <= 200:
        score += 0.1

    # Engaging keywords bonus
    engaging_keywords = [
        "how",
        "why",
        "what",
        "best",
        "new",
        "guide",
        "tips",
        "breakthrough",
        "revolutionary",
        "discovered",
        "reveals",
        "major",
        "ai",
        "tech",
        "technology",
        "science",
        "future",
        "innovation",
        "2024",
        "2025",
    ]

    if any(keyword in title_lower for keyword in engaging_keywords):
        score += 0.1

    return score


def calculate_url_quality_score(url: str) -> float:
    """
    Calculate quality score based on URL presence and validity.

    Pure function with no side effects.

    Args:
        url: Content URL to validate

    Returns:
        float: 0.05 if valid URL present, 0.0 otherwise

    Examples:
        >>> calculate_url_quality_score("https://example.com/article")
        0.05
        >>> calculate_url_quality_score("")
        0.0
        >>> calculate_url_quality_score("bad")
        0.0
    """
    if not url or not isinstance(url, str):
        return 0.0

    # Basic URL validation: must be reasonably long
    return 0.05 if len(url) > 10 else 0.0


def calculate_priority_score(
    upvotes: int = 0,
    comments: int = 0,
    title: str = "",
    url: str = "",
    collected_at: Optional[datetime] = None,
    now: Optional[datetime] = None,
    base_score: float = 0.6,
) -> float:
    """
    Calculate comprehensive priority score for a topic.

    Pure function that combines multiple scoring factors into a final priority.
    Score range is 0.5 to 1.0 to ensure all content has minimum viability.

    Scoring breakdown:
    - Base score: 0.6 (default, configurable)
    - Engagement: up to 0.3 (0.2 upvotes + 0.1 comments)
    - Freshness: up to 0.3 (linear decay over 24 hours)
    - Title quality: up to 0.2 (0.1 length + 0.1 keywords)
    - URL quality: up to 0.05 (presence of valid URL)
    - Maximum total: 1.0 (capped)
    - Minimum total: 0.5 (floor for all content)

    Args:
        upvotes: Number of upvotes (default 0)
        comments: Number of comments (default 0)
        title: Article title (default "")
        url: Content URL (default "")
        collected_at: When content was collected (optional)
        now: Current time for freshness calculation (optional)
        base_score: Starting score (default 0.6)

    Returns:
        float: Priority score between 0.5 and 1.0

    Raises:
        ValueError: If upvotes/comments negative, or timestamp issues

    Examples:
        >>> calculate_priority_score(100, 50, "How AI Works", "https://example.com")
        1.0
        >>> calculate_priority_score(0, 0, "", "")
        0.6
        >>> calculate_priority_score(-5, 0, "", "")
        Traceback (most recent call last):
        ...
        ValueError: Upvotes and comments must be non-negative
    """
    try:
        # Start with base score
        score = base_score

        # Add engagement score
        score += calculate_engagement_score(upvotes, comments)

        # Add freshness score if timestamp provided
        if collected_at is not None:
            score += calculate_freshness_score(collected_at, now)

        # Add title quality score
        score += calculate_title_quality_score(title)

        # Add URL quality score
        score += calculate_url_quality_score(url)

        # Clamp to [0.5, 1.0] range
        return max(0.5, min(1.0, score))

    except (ValueError, TypeError) as e:
        # Re-raise validation errors, but catch any unexpected type errors
        if isinstance(e, ValueError):
            raise
        return 0.5  # Safe fallback for type errors


def calculate_priority_score_from_dict(item: Dict[str, Any]) -> float:
    """
    Calculate priority score from a dictionary of topic data.

    Convenience wrapper for calculate_priority_score() that extracts
    values from a dictionary with flexible key names.

    Supported key variations:
    - upvotes: "upvotes", "score", "ups"
    - comments: "comments", "num_comments", "comment_count"
    - title: "title"
    - url: "url", "permalink", "link"
    - collected_at: "collected_at", "created_utc"

    Args:
        item: Dictionary containing topic data

    Returns:
        float: Priority score between 0.5 and 1.0

    Examples:
        >>> item = {"upvotes": 50, "comments": 20, "title": "Great Article"}
        >>> score = calculate_priority_score_from_dict(item)
        >>> 0.5 <= score <= 1.0
        True
    """
    try:
        # Extract upvotes (try multiple keys)
        upvotes = item.get("upvotes") or item.get("score") or item.get("ups") or 0
        upvotes = int(upvotes) if upvotes else 0

        # Extract comments (try multiple keys)
        comments = (
            item.get("comments")
            or item.get("num_comments")
            or item.get("comment_count")
            or 0
        )
        comments = int(comments) if comments else 0

        # Extract title
        title = str(item.get("title", ""))

        # Extract URL (try multiple keys)
        url = item.get("url") or item.get("permalink") or item.get("link") or ""
        url = str(url) if url else ""

        # Extract timestamp (try multiple keys)
        collected_at = None
        timestamp_str = item.get("collected_at") or item.get("created_utc")
        if timestamp_str:
            try:
                # Handle both ISO format and Unix timestamp
                if isinstance(timestamp_str, (int, float)):
                    collected_at = datetime.fromtimestamp(
                        timestamp_str, tz=timezone.utc
                    )
                elif isinstance(timestamp_str, str):
                    # Handle ISO format with Z suffix
                    timestamp_str = timestamp_str.replace("Z", "+00:00")
                    collected_at = datetime.fromisoformat(timestamp_str)
            except (ValueError, OSError):
                pass  # Skip freshness bonus if timestamp parsing fails

        return calculate_priority_score(
            upvotes=upvotes,
            comments=comments,
            title=title,
            url=url,
            collected_at=collected_at,
        )

    except Exception:
        # Safe fallback for any unexpected errors in dict parsing
        return 0.5

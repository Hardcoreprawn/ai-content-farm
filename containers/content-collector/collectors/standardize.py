"""
Standardize raw API responses to uniform item format.

All items: id, title, content, source, url, collected_at, metadata, priority_score
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def standardize_reddit_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert raw Reddit post to standardized format.

    Args:
        raw: Reddit post data from JSON API

    Returns:
        Standardized item dict
    """
    post_id = raw.get("id", "")
    title = raw.get("title", "Untitled")
    content = raw.get("selftext", "")
    url = raw.get("url", "")

    # Extract metadata
    score = raw.get("score", 0)
    comments = raw.get("num_comments", 0)
    subreddit = raw.get("subreddit", "unknown")
    created_utc = raw.get("created_utc", 0)

    # Convert UTC timestamp to ISO string
    collected_at = (
        datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
        if created_utc
        else datetime.now(timezone.utc).isoformat()
    )

    return {
        "id": f"reddit_{post_id}",
        "title": title,
        "content": content,
        "source": "reddit",
        "url": url,
        "collected_at": collected_at,
        "priority_score": 0.5,  # Will be overwritten by quality scoring
        "metadata": {
            "subreddit": subreddit,
            "score": score,
            "num_comments": comments,
            "post_id": post_id,
        },
    }


def standardize_mastodon_item(
    raw: Dict[str, Any], instance: str = "unknown"
) -> Dict[str, Any]:
    """
    Convert raw Mastodon status to standardized format.

    Args:
        raw: Mastodon status data from API
        instance: Mastodon instance domain

    Returns:
        Standardized item dict
    """
    status_id = raw.get("id", "")
    content_html = raw.get("content", "")
    url = raw.get("url", "")

    # Strip HTML tags from content for title (first 100 chars)
    import re

    content_text = re.sub(r"<[^>]+>", "", content_html)
    title = content_text[:100].strip() or "Mastodon Post"

    # Extract metadata
    boosts = raw.get("reblogs_count", 0)
    favourites = raw.get("favourites_count", 0)
    replies = raw.get("replies_count", 0)

    account = raw.get("account", {})
    author = account.get("username", "unknown")

    created_at_str = raw.get("created_at", "")
    if created_at_str:
        # Parse ISO datetime string
        try:
            dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            collected_at = dt.isoformat()
        except ValueError:
            collected_at = datetime.now(timezone.utc).isoformat()
    else:
        collected_at = datetime.now(timezone.utc).isoformat()

    return {
        "id": f"mastodon_{status_id}",
        "title": title,
        "content": content_text,
        "source": "mastodon",
        "url": url,
        "collected_at": collected_at,
        "priority_score": 0.5,
        "metadata": {
            "boosts": boosts,
            "favourites": favourites,
            "replies": replies,
            "author": author,
            "instance": instance,
            "status_id": status_id,
        },
    }


def validate_item(item: Dict[str, Any]) -> bool:
    """
    Validate item has required fields.

    Args:
        item: Item dict to validate

    Returns:
        True if valid, False otherwise
    """
    required = ["id", "title", "content", "source", "collected_at"]
    return all(item.get(field) for field in required)

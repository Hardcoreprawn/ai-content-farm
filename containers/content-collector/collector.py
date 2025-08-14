"""
Content Collector - Core Business Logic

Minimal implementation to make tests pass.
Pure functions for collecting content from various sources.
"""

import requests
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from urllib.parse import urlparse


def fetch_from_subreddit(subreddit: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch posts from a specific subreddit.

    Args:
        subreddit: Name of the subreddit
        limit: Maximum number of posts to fetch

    Returns:
        List of raw Reddit post dictionaries
    """
    if not subreddit or subreddit is None:
        return []

    url = f"https://www.reddit.com/r/{subreddit}/hot.json"
    headers = {"User-Agent": "ai-content-farm-collector/1.0"}

    try:
        response = requests.get(
            url,
            headers=headers,
            params={"limit": limit},
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        posts = []

        for child in data.get("data", {}).get("children", []):
            post_data = child.get("data", {})
            if post_data:
                posts.append(post_data)

        return posts

    except Exception as e:
        print(f"Error fetching from r/{subreddit}: {e}")
        return []


def fetch_reddit_posts(subreddits: List[str], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch posts from multiple subreddits.

    Args:
        subreddits: List of subreddit names
        limit: Maximum number of posts per subreddit

    Returns:
        List of raw Reddit post dictionaries
    """
    if not subreddits:
        return []

    all_posts = []

    for subreddit in subreddits:
        posts = fetch_from_subreddit(subreddit, limit)
        all_posts.extend(posts)

    return all_posts


def normalize_reddit_post(raw_post: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a raw Reddit post into our standard format.

    Args:
        raw_post: Raw post data from Reddit API

    Returns:
        Normalized post dictionary

    Raises:
        ValueError: If post is missing required fields
    """
    if not raw_post.get("id") or not raw_post.get("title"):
        raise ValueError("Post must have id and title")

    # Create normalized post
    normalized = {
        "id": raw_post["id"],
        "title": raw_post["title"],
        "score": raw_post.get("score", 0),
        "num_comments": raw_post.get("num_comments", 0),
        "created_utc": raw_post.get("created_utc", 0),
        "url": raw_post.get("url", ""),
        "selftext": raw_post.get("selftext", ""),
        "author": raw_post.get("author", "unknown"),
        "subreddit": raw_post.get("subreddit", ""),
        "permalink": raw_post.get("permalink", ""),

        # Our metadata
        "source": "reddit",
        "source_type": "subreddit",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "raw_data": raw_post,
    }

    return normalized


def filter_content_by_criteria(posts: List[Dict[str, Any]], criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Filter posts based on specified criteria.

    Args:
        posts: List of posts to filter
        criteria: Dictionary of filtering criteria

    Returns:
        Filtered list of posts
    """
    if not posts:
        return []

    filtered_posts = []

    for post in posts:
        # Check score threshold
        min_score = criteria.get("min_score", 0)
        if post.get("score", 0) < min_score:
            continue

        # Check comments threshold
        min_comments = criteria.get("min_comments", 0)
        if post.get("num_comments", 0) < min_comments:
            continue

        # Check include keywords
        include_keywords = criteria.get("include_keywords", [])
        if include_keywords:
            title_lower = post.get("title", "").lower()
            if not any(keyword.lower() in title_lower for keyword in include_keywords):
                continue

        # Check exclude keywords
        exclude_keywords = criteria.get("exclude_keywords", [])
        if exclude_keywords:
            title_lower = post.get("title", "").lower()
            if any(keyword.lower() in title_lower for keyword in exclude_keywords):
                continue

        filtered_posts.append(post)

    return filtered_posts


def deduplicate_content(posts: List[Dict[str, Any]], similarity_threshold: float = 0.9) -> List[Dict[str, Any]]:
    """
    Remove duplicate posts based on ID and title similarity.

    Args:
        posts: List of posts to deduplicate
        similarity_threshold: Threshold for title similarity (0-1)

    Returns:
        Deduplicated list of posts
    """
    if not posts:
        return []

    seen_ids = set()
    seen_titles = []
    deduplicated = []

    for post in posts:
        post_id = post.get("id")
        title = post.get("title", "")

        # Skip if we've seen this ID
        if post_id in seen_ids:
            continue

        # Check title similarity using character-based similarity
        is_similar = False
        if similarity_threshold < 1.0:
            import re
            # Normalize titles by removing punctuation and extra whitespace
            title_normalized = re.sub(r'[^\w\s]', '', title.lower()).strip()
            for seen_title in seen_titles:
                seen_normalized = re.sub(
                    r'[^\w\s]', '', seen_title.lower()).strip()
                if title_normalized and seen_normalized:
                    # Use character-level similarity (Levenshtein-like)
                    max_len = max(len(title_normalized), len(seen_normalized))
                    if max_len == 0:
                        continue

                    # Simple character similarity
                    common_chars = sum(1 for a, b in zip(
                        title_normalized, seen_normalized) if a == b)
                    similarity = common_chars / max_len

                    # Also check if one is a substring of the other (high similarity)
                    if title_normalized in seen_normalized or seen_normalized in title_normalized:
                        similarity = max(similarity, 0.95)

                    if similarity >= similarity_threshold:
                        is_similar = True
                        break

        if not is_similar:
            seen_ids.add(post_id)
            seen_titles.append(title)
            deduplicated.append(post)

    return deduplicated


def collect_content_batch(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Collect content from multiple sources in batch.

    Args:
        sources: List of source configurations

    Returns:
        Dictionary with collected items and metadata
    """
    collected_items = []
    errors = 0
    sources_processed = 0
    criteria_applied = False

    for source in sources:
        try:
            source_type = source.get("type")

            if source_type == "reddit":
                # Extract Reddit-specific configuration
                subreddits = source.get("subreddits", [])
                limit = source.get("limit", 10)
                criteria = source.get("criteria", {})

                # Fetch raw posts
                raw_posts = fetch_reddit_posts(subreddits, limit)

                # Normalize posts
                normalized_posts = []
                for raw_post in raw_posts:
                    try:
                        normalized = normalize_reddit_post(raw_post)
                        normalized_posts.append(normalized)
                    except Exception as e:
                        print(f"Error normalizing post: {e}")
                        continue

                # Apply filtering criteria
                if criteria:
                    normalized_posts = filter_content_by_criteria(
                        normalized_posts, criteria)
                    criteria_applied = True

                collected_items.extend(normalized_posts)
                sources_processed += 1

            else:
                print(f"Unknown source type: {source_type}")
                errors += 1

        except Exception as e:
            print(f"Error processing source {source}: {e}")
            errors += 1

    # Create metadata
    metadata = {
        "total_collected": len(collected_items),
        "sources_processed": sources_processed,
        "errors": errors,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "collection_version": "1.0.0",
    }

    if criteria_applied:
        metadata["criteria_applied"] = True

    return {
        "collected_items": collected_items,
        "metadata": metadata
    }

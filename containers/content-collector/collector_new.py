"""
Content Collector - Core Business Logic

Minimal implementation using modular source collectors.
Pure functions for collecting content from various sources.
"""

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from urllib.parse import urlparse
from source_collectors import SourceCollectorFactory


def fetch_from_subreddit(subreddit: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch posts from a specific subreddit using the modular collector system.

    Args:
        subreddit: Name of the subreddit
        limit: Maximum number of posts to fetch

    Returns:
        List of raw Reddit post dictionaries
    """
    try:
        # Use the modular collector system
        reddit_collector = SourceCollectorFactory.create_collector("reddit")
        params = {
            "subreddits": [subreddit],
            "limit": limit
        }
        posts = reddit_collector.collect_content(params)
        return posts
    except Exception as e:
        print(f"Error in fetch_from_subreddit: {e}")
        return []


def fetch_reddit_posts(subreddits: List[str], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch posts from multiple subreddits.

    Args:
        subreddits: List of subreddit names
        limit: Maximum number of posts to fetch per subreddit

    Returns:
        List of raw Reddit post dictionaries
    """
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

        # Keep raw data for reference
        "raw_data": raw_post
    }

    return normalized


def filter_content_by_criteria(content: List[Dict[str, Any]], criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Filter content based on specified criteria.

    Args:
        content: List of normalized content items
        criteria: Filtering criteria

    Returns:
        Filtered list of content items
    """
    if not criteria:
        return content

    filtered = []

    min_score = criteria.get("min_score", 0)
    min_comments = criteria.get("min_comments", 0)
    max_age_hours = criteria.get("max_age_hours")
    keywords = criteria.get("keywords", [])
    exclude_keywords = criteria.get("exclude_keywords", [])

    for item in content:
        # Check minimum score
        if item.get("score", 0) < min_score:
            continue

        # Check minimum comments
        if item.get("num_comments", 0) < min_comments:
            continue

        # Check age (if specified)
        if max_age_hours:
            created_utc = item.get("created_utc", 0)
            if created_utc:
                age_hours = (datetime.now(
                    timezone.utc).timestamp() - created_utc) / 3600
                if age_hours > max_age_hours:
                    continue

        # Check keywords (if specified)
        if keywords:
            title_lower = item.get("title", "").lower()
            selftext_lower = item.get("selftext", "").lower()
            content_text = f"{title_lower} {selftext_lower}"

            has_keyword = any(
                keyword.lower() in content_text for keyword in keywords)
            if not has_keyword:
                continue

        # Check exclude keywords (if specified)
        if exclude_keywords:
            title_lower = item.get("title", "").lower()
            selftext_lower = item.get("selftext", "").lower()
            content_text = f"{title_lower} {selftext_lower}"

            has_exclude_keyword = any(
                keyword.lower() in content_text for keyword in exclude_keywords)
            if has_exclude_keyword:
                continue

        filtered.append(item)

    return filtered


def apply_quality_filters(content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply quality filters to remove low-quality content.

    Args:
        content: List of content items

    Returns:
        Filtered list of quality content
    """
    filtered = []

    for item in content:
        # Skip deleted or removed posts
        if item.get("author") == "[deleted]" or item.get("title") == "[removed]":
            continue

        # Skip posts with very short titles
        title = item.get("title", "")
        if len(title.strip()) < 10:
            continue

        # Skip promotional or spam-like content
        title_lower = title.lower()
        spam_indicators = ["click here", "buy now", "limited time", "act now"]
        if any(indicator in title_lower for indicator in spam_indicators):
            continue

        filtered.append(item)

    return filtered


def collect_content_batch(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Collect content from multiple sources in batch using modular collectors.

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

            # Use the modular collector factory
            try:
                collector = SourceCollectorFactory.create_collector(
                    source_type)
                raw_posts = collector.collect_content(source)
                sources_processed += 1
            except Exception as e:
                print(f"Error creating collector for {source_type}: {e}")
                errors += 1
                continue

            # Normalize posts
            normalized_posts = []
            for raw_post in raw_posts:
                try:
                    normalized = normalize_reddit_post(raw_post)
                    normalized_posts.append(normalized)
                except Exception as e:
                    print(f"Error normalizing post: {e}")
                    errors += 1

            # Apply criteria filtering if specified
            criteria = source.get("criteria", {})
            if criteria:
                filtered_posts = filter_content_by_criteria(
                    normalized_posts, criteria)
                criteria_applied = True
            else:
                filtered_posts = normalized_posts

            # Apply quality filters
            quality_posts = apply_quality_filters(filtered_posts)

            collected_items.extend(quality_posts)

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
        "criteria_applied": criteria_applied
    }

    return {
        "collected_items": collected_items,
        "metadata": metadata
    }


def deduplicate_content(content: List[Dict[str, Any]], similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
    """
    Remove duplicate content based on title similarity.

    Args:
        content: List of content items
        similarity_threshold: Threshold for considering items similar (0.0-1.0)

    Returns:
        Deduplicated list of content items
    """
    if not content:
        return content

    def normalize_title(title: str) -> str:
        """Normalize title for comparison."""
        # Convert to lowercase and remove extra whitespace
        normalized = re.sub(r'\s+', ' ', title.lower().strip())
        # Remove common prefixes and suffixes
        prefixes = ['breaking:', 'update:', 'news:', 'alert:']
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
        return normalized

    def calculate_similarity(title1: str, title2: str) -> float:
        """Calculate similarity between two titles."""
        norm1 = normalize_title(title1)
        norm2 = normalize_title(title2)

        if norm1 == norm2:
            return 1.0

        # Simple word-based similarity
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    deduplicated = []
    seen_titles = []

    for item in content:
        title = item.get("title", "")
        is_duplicate = False

        for seen_title in seen_titles:
            similarity = calculate_similarity(title, seen_title)
            if similarity >= similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            deduplicated.append(item)
            seen_titles.append(title)

    return deduplicated

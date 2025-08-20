"""
Pure transform functions for content normalization, filtering and deduplication.

These are kept side-effect free so they are easy to unit test and compose.
"""
import re
from datetime import datetime, timezone
from typing import Any, Dict, List


def normalize_content_item(
    raw_item: Dict[str, Any], source_type: str
) -> Dict[str, Any]:
    if source_type == "reddit":
        return normalize_reddit_post(raw_item)
    elif source_type == "web":
        return raw_item
    else:
        return {
            "id": raw_item.get("id", f"unknown_{hash(str(raw_item)) % 100000}"),
            "source": raw_item.get("source", source_type),
            "title": raw_item.get("title", "No title"),
            "content": raw_item.get("content", ""),
            "url": raw_item.get("url", ""),
            "author": raw_item.get("author", "Unknown"),
            "score": raw_item.get("score", 0),
            "num_comments": raw_item.get("num_comments", 0),
            "content_type": raw_item.get("content_type", "unknown"),
            "created_at": raw_item.get(
                "created_at", datetime.now(timezone.utc).isoformat()
            ),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "raw_data": raw_item,
        }


def normalize_reddit_post(raw_post: Dict[str, Any]) -> Dict[str, Any]:
    # Validate required fields
    if not raw_post.get("id") or not raw_post.get("title"):
        raise ValueError("Post must have id and title")

    post_id = raw_post.get("id", "")
    title = raw_post.get("title", "")
    content = raw_post.get("selftext", "") or ""
    url = raw_post.get("url", "")
    score = raw_post.get("score", 0)
    num_comments = raw_post.get("num_comments", 0)
    author = raw_post.get("author", "unknown")
    created_utc = raw_post.get("created_utc", 0)
    subreddit = raw_post.get("subreddit", "")

    try:
        created_at = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
    except (ValueError, TypeError):
        created_at = datetime.now(timezone.utc).isoformat()

    content_type = "text"
    if url and url != f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/":
        content_type = "link"
        if any(url.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
            content_type = "image"
        elif any(url.endswith(ext) for ext in [".mp4", ".webm", ".mov"]):
            content_type = "video"

    return {
        "id": post_id,
        "source": "reddit",
        "source_type": "subreddit",
        "subreddit": subreddit,
        "title": title,
        "content": content,
        "selftext": content or "",
        "url": url,
        "author": author,
        "score": score,
        "num_comments": num_comments,
        "content_type": content_type,
        "created_at": created_at,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "raw_data": raw_post,
    }


def filter_content_by_criteria(
    posts: List[Dict[str, Any]], criteria: Dict[str, Any]
) -> List[Dict[str, Any]]:
    filtered = []

    for post in posts:
        min_score = criteria.get("min_score", 0)
        if post.get("score", 0) < min_score:
            continue

        allowed_types = criteria.get("content_types", [])
        if allowed_types and post.get("content_type") not in allowed_types:
            continue

        keywords = criteria.get("keywords", []) or criteria.get("include_keywords", [])
        if keywords:
            title = post.get("title", "").lower()
            content = post.get("content", "").lower()
            if not any(
                keyword.lower() in title or keyword.lower() in content
                for keyword in keywords
            ):
                continue

        exclude_keywords = criteria.get("exclude_keywords", [])
        if exclude_keywords:
            title = post.get("title", "").lower()
            content = post.get("content", "").lower()
            if any(
                keyword.lower() in title or keyword.lower() in content
                for keyword in exclude_keywords
            ):
                continue

        filtered.append(post)

    return filtered


def deduplicate_content(
    posts: List[Dict[str, Any]], similarity_threshold: float = 0.9
) -> List[Dict[str, Any]]:
    if not posts:
        return []

    def calculate_similarity(text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0
        words1 = set(re.findall(r"\w+", text1.lower()))
        words2 = set(re.findall(r"\w+", text2.lower()))
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union)

    deduplicated = []
    seen_urls = set()
    seen_ids = set()

    for post in posts:
        post_id = post.get("id")
        if post_id and post_id in seen_ids:
            continue
        url = post.get("url", "")
        if url and url in seen_urls:
            continue

        title = post.get("title", "")
        is_duplicate = False

        for existing_post in deduplicated:
            existing_title = existing_post.get("title", "")
            similarity = calculate_similarity(title, existing_title)
            if similarity >= similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            if url:
                seen_urls.add(url)
            if post_id:
                seen_ids.add(post_id)
            deduplicated.append(post)

    return deduplicated

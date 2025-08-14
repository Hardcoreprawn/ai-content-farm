#!/usr/bin/env python3
"""
Content Processor - Business Logic

Pure functions for transforming Reddit data.
No side effects, easy to test.
"""

import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


def clean_title(title: str) -> str:
    """Clean and normalize Reddit post titles"""
    if not title or not title.strip():
        return "[No Title]"

    # Remove leading/trailing whitespace
    cleaned = title.strip()

    # Remove emoji characters (basic removal)
    # This regex removes most emoji characters
    emoji_pattern = re.compile(
        r"[\U0001F600-\U0001F64F]|[\U0001F300-\U0001F5FF]|[\U0001F680-\U0001F6FF]|[\U0001F1E0-\U0001F1FF]",
        flags=re.UNICODE,
    )
    cleaned = emoji_pattern.sub("", cleaned)

    # Normalize multiple spaces to single space
    cleaned = re.sub(r"\s+", " ", cleaned)

    # Final trim
    cleaned = cleaned.strip()

    # Fallback if we ended up with empty string
    if not cleaned:
        return "[No Title]"

    return cleaned


def normalize_score(score: int) -> float:
    """Normalize Reddit score to 0-1 range"""
    if score <= 0:
        return 0.0

    # Use logarithmic scaling for Reddit scores
    # Scores can range from 0 to ~50k+ for viral posts
    # Log scale helps normalize the distribution
    normalized = math.log(score + 1) / math.log(10001)  # +1 to handle score=0

    # Ensure we stay in 0-1 range
    return min(1.0, max(0.0, normalized))


def calculate_engagement_score(score: int, comments: int) -> float:
    """Calculate engagement score based on upvotes and comments"""
    if score <= 0 and comments <= 0:
        return 0.0

    # Handle negative scores (controversial posts)
    if score < 0:
        return max(0.0, 0.1 * (comments / max(1, abs(score))))

    # Weighted combination of score and comments
    # Comments are generally more valuable for engagement
    score_weight = 0.6
    comment_weight = 0.4

    # Normalize both values
    normalized_score = normalize_score(score)
    normalized_comments = min(1.0, comments / 100.0)  # 100 comments = max

    engagement = (score_weight * normalized_score) + (
        comment_weight * normalized_comments
    )

    return min(1.0, engagement)


def extract_content_type(url: str, selftext: str) -> str:
    """Determine content type from URL and selftext"""
    if not url and not selftext:
        return "unknown"

    # Text posts have selftext content
    if selftext and selftext.strip():
        return "text"

    if not url:
        return "unknown"

    # Parse URL to check domain and extension
    try:
        parsed = urlparse(url.lower())
        domain = parsed.netloc
        path = parsed.path

        # Image detection
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
        if any(path.endswith(ext) for ext in image_extensions):
            return "image"

        # Image hosting domains
        image_domains = {"i.imgur.com", "i.redd.it", "imgur.com"}
        if any(domain.endswith(img_domain) for img_domain in image_domains):
            return "image"

        # Video detection
        video_extensions = {".mp4", ".webm", ".avi", ".mov", ".mkv"}
        if any(path.endswith(ext) for ext in video_extensions):
            return "video"

        # Video hosting domains
        video_domains = {
            "youtube.com",
            "youtu.be",
            "vimeo.com",
            "v.redd.it",
            "twitch.tv",
        }
        if any(domain.endswith(vid_domain) for vid_domain in video_domains):
            return "video"

        # Reddit-hosted content
        if domain.endswith("reddit.com"):
            return "text"

        # Default to link for external URLs
        return "link"

    except Exception:
        return "unknown"


def transform_reddit_post(post: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a single Reddit post into structured content"""
    # Extract fields with defaults
    title = post.get("title", "")
    score = post.get("score", 0)
    comments = post.get("num_comments", 0)
    created_utc = post.get("created_utc", 0)
    subreddit = post.get("subreddit", "")
    url = post.get("url", "")
    selftext = post.get("selftext", "")
    reddit_id = post.get("id", "")

    # Generate our own ID if Reddit ID is missing
    if not reddit_id:
        reddit_id = f"unknown_{hash(title + str(score))}"

    # Process the data
    clean_title_text = clean_title(title)
    normalized_score = normalize_score(score)
    engagement_score = calculate_engagement_score(score, comments)
    content_type = extract_content_type(url, selftext)

    # Convert timestamp to ISO format
    if created_utc:
        published_at = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
    else:
        published_at = datetime.now(tz=timezone.utc).isoformat()

    # Build source URL
    if url and not url.startswith("http"):
        source_url = f"https://reddit.com{url}"
    else:
        source_url = url or f"https://reddit.com/r/{subreddit}"

    return {
        "id": reddit_id,
        "title": title,
        "clean_title": clean_title_text,
        "normalized_score": normalized_score,
        "engagement_score": engagement_score,
        "source_url": source_url,
        "published_at": published_at,
        "content_type": content_type,
        "source_metadata": {
            "original_score": score,
            "original_comments": comments,
            "subreddit": subreddit,
            "reddit_id": reddit_id,
            "selftext": selftext[:500] if selftext else "",  # Truncate long text
            "created_utc": created_utc,
        },
    }


def process_reddit_batch(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process a batch of Reddit posts"""
    if not posts:
        return []

    processed_items = []

    for post in posts:
        try:
            processed_item = transform_reddit_post(post)
            processed_items.append(processed_item)
        except Exception as e:
            # Log error but continue processing other items
            print(f"Error processing post {post.get('id', 'unknown')}: {e}")
            continue

    return processed_items

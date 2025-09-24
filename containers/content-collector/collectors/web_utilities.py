"""
Web Collector Utilities

Utility functions for web content processing including HTML cleaning,
score extraction, tag processing, and content deduplication.
"""

import re
from typing import Any, Dict, List
from urllib.parse import urlparse


def clean_html_content(content: str) -> str:
    """
    Clean HTML content by removing tags and normalizing text.

    Args:
        content: Raw HTML content

    Returns:
        Cleaned text content
    """
    if not content:
        return ""

    # Remove HTML tags
    content = re.sub(r"<[^>]+>", " ", content)

    # Normalize whitespace
    content = re.sub(r"\s+", " ", content)

    # Remove common HTML entities
    content = content.replace("&nbsp;", " ")
    content = content.replace("&amp;", "&")
    content = content.replace("&lt;", "<")
    content = content.replace("&gt;", ">")
    content = content.replace("&quot;", '"')

    return content.strip()


def extract_score_from_content(content: str) -> int:
    """
    Extract numerical score/points from content text.

    Args:
        content: Text content that may contain score information

    Returns:
        Extracted score or 0 if not found
    """
    if not content:
        return 0

    # Look for common score patterns
    patterns = [
        r"(\d+)\s*points?",  # "123 points"
        r"Score:\s*(\d+)",  # "Score: 123"
        r"(\d+)\s*pts",  # "123 pts"
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue

    return 0


def extract_tags_from_entry(entry: Any) -> List[str]:
    """
    Extract tags from RSS entry.

    Args:
        entry: RSS entry object

    Returns:
        List of tag strings
    """
    tags = []

    # Check for RSS tags field
    if hasattr(entry, "tags") and entry.tags:
        for tag in entry.tags:
            if hasattr(tag, "term") and tag.term:
                tags.append(tag.term.strip())

    # Check for categories
    if hasattr(entry, "category") and entry.category:
        tags.append(entry.category.strip())

    return tags


def extract_slashdot_department(content: str) -> str:
    """
    Extract Slashdot department from content.

    Args:
        content: Content text

    Returns:
        Department name or empty string
    """
    if not content:
        return ""

    # Look for department pattern
    match = re.search(r"from the ([^<>\n]+) dept", content, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return ""


def meets_content_criteria(
    item: Dict[str, Any], min_score: int = 5, required_tags: List[str] = None
) -> bool:
    """
    Check if content item meets collection criteria.

    Args:
        item: Content item dictionary
        min_score: Minimum score requirement
        required_tags: List of required tags

    Returns:
        True if item meets criteria
    """
    # Check minimum score
    if item.get("score", 0) < min_score:
        return False

    # Check required tags
    if required_tags:
        item_tags = [tag.lower() for tag in item.get("tags", [])]
        if not any(tag.lower() in item_tags for tag in required_tags):
            return False

    return True


def deduplicate_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate items based on URL and title similarity.

    Args:
        items: List of content items

    Returns:
        Deduplicated list of items
    """
    if not items:
        return []

    seen_urls = set()
    seen_titles = set()
    unique_items = []

    for item in items:
        url = item.get("url", "")
        title = item.get("title", "")

        # Skip items without URL or title
        if not url or not title:
            continue

        # Normalize URL for comparison
        parsed_url = urlparse(url)
        normalized_url = f"{parsed_url.netloc}{parsed_url.path}"

        # Normalize title for comparison
        normalized_title = re.sub(r"\s+", " ", title.lower().strip())

        # Check for duplicates
        if normalized_url in seen_urls or normalized_title in seen_titles:
            continue

        seen_urls.add(normalized_url)
        seen_titles.add(normalized_title)
        unique_items.append(item)

    return unique_items

"""
Site-Specific Content Standardizers

Standardization logic for converting content from different sites
(HackerNews, Lobsters, Slashdot) into a unified format.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict
from urllib.parse import urljoin

from .web_utilities import (
    clean_html_content,
    extract_score_from_content,
    extract_slashdot_department,
    extract_tags_from_entry,
)


class HackerNewsStandardizer:
    """Standardizer for HackerNews API content."""

    @staticmethod
    def standardize_story(story: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert HackerNews story to standardized format.

        Args:
            story: Raw HackerNews story data

        Returns:
            Standardized content item
        """
        # Extract timestamp
        timestamp = None
        if "time" in story:
            timestamp = datetime.fromtimestamp(story["time"], tz=timezone.utc)

        # Build standardized item
        standardized = {
            "id": str(story.get("id", "")),
            "title": story.get("title", ""),
            "url": story.get("url", ""),
            "content": story.get("text", ""),
            "author": story.get("by", ""),
            "timestamp": timestamp.isoformat() if timestamp else None,
            "score": story.get("score", 0),
            "comments_count": story.get("descendants", 0),
            "tags": [],
            "source": "hackernews",
            "source_id": str(story.get("id", "")),
            "extra_data": {
                "hn_type": story.get("type", ""),
                "hn_kids": story.get("kids", []),
            },
        }

        # Clean HTML content
        if standardized["content"]:
            standardized["content"] = clean_html_content(standardized["content"])

        # Add HackerNews-specific URL if no URL provided
        if not standardized["url"] and standardized["id"]:
            standardized["url"] = (
                f"https://news.ycombinator.com/item?id={standardized['id']}"
            )

        return standardized


class LobstersStandardizer:
    """Standardizer for Lobsters RSS content."""

    @staticmethod
    def standardize_entry(
        entry: Any, base_url: str = "https://lobste.rs"
    ) -> Dict[str, Any]:
        """
        Convert Lobsters RSS entry to standardized format.

        Args:
            entry: RSS entry object
            base_url: Base URL for the site

        Returns:
            Standardized content item
        """
        # Extract timestamp
        timestamp = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                timestamp = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass

        # Build standardized item
        standardized = {
            "id": getattr(entry, "id", "") or getattr(entry, "link", ""),
            "title": getattr(entry, "title", ""),
            "url": getattr(entry, "link", ""),
            "content": getattr(entry, "summary", "")
            or getattr(entry, "description", ""),
            "author": getattr(entry, "author", ""),
            "timestamp": timestamp.isoformat() if timestamp else None,
            "score": extract_score_from_content(
                getattr(entry, "summary", "") or getattr(entry, "description", "")
            ),
            "comments_count": 0,  # Not available in Lobsters RSS
            "tags": extract_tags_from_entry(entry),
            "source": "lobsters",
            "source_id": getattr(entry, "id", ""),
        }

        # Clean HTML content
        if standardized["content"]:
            standardized["content"] = clean_html_content(standardized["content"])

        # Ensure absolute URL
        if standardized["url"] and not standardized["url"].startswith("http"):
            standardized["url"] = urljoin(base_url, standardized["url"])

        return standardized


class SlashdotStandardizer:
    """Standardizer for Slashdot RSS content."""

    @staticmethod
    def standardize_entry(
        entry: Any, base_url: str = "https://slashdot.org"
    ) -> Dict[str, Any]:
        """
        Convert Slashdot RSS entry to standardized format.

        Args:
            entry: RSS entry object
            base_url: Base URL for the site

        Returns:
            Standardized content item
        """
        # Extract timestamp
        timestamp = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                timestamp = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass

        # Get content with department extraction
        content = getattr(entry, "summary", "") or getattr(entry, "description", "")
        department = extract_slashdot_department(content)

        # Build standardized item
        standardized = {
            "id": getattr(entry, "id", "") or getattr(entry, "link", ""),
            "title": getattr(entry, "title", ""),
            "url": getattr(entry, "link", ""),
            "content": content,
            "author": getattr(entry, "author", ""),
            "timestamp": timestamp.isoformat() if timestamp else None,
            "score": 0,  # Slashdot doesn't provide scores in RSS
            "comments_count": SlashdotStandardizer._extract_comment_count(content),
            "tags": extract_tags_from_entry(entry),
            "source": "slashdot",
            "source_id": getattr(entry, "id", ""),
            "extra_data": {"department": department} if department else {},
        }

        # Clean HTML content
        if standardized["content"]:
            standardized["content"] = clean_html_content(standardized["content"])

        # Ensure absolute URL
        if standardized["url"] and not standardized["url"].startswith("http"):
            standardized["url"] = urljoin(base_url, standardized["url"])

        return standardized

    @staticmethod
    def _extract_comment_count(content: str) -> int:
        """Extract comment count from Slashdot content."""
        if not content:
            return 0

        # Look for comment count patterns
        patterns = [
            r"(\d+)\s*comments?",
            r"Read more of this story at Slashdot",  # Default if no count
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match and match.group(1).isdigit():
                return int(match.group(1))

        return 0


class GenericRSSStandardizer:
    """Standardizer for generic RSS content."""

    @staticmethod
    def standardize_entry(entry: Any, source_name: str = "rss") -> Dict[str, Any]:
        """
        Convert generic RSS entry to standardized format.

        Args:
            entry: RSS entry object
            source_name: Name of the source

        Returns:
            Standardized content item
        """
        # Extract timestamp
        timestamp = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                timestamp = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass

        # Build standardized item
        standardized = {
            "id": getattr(entry, "id", "") or getattr(entry, "link", ""),
            "title": getattr(entry, "title", ""),
            "url": getattr(entry, "link", ""),
            "content": getattr(entry, "summary", "")
            or getattr(entry, "description", ""),
            "author": getattr(entry, "author", ""),
            "timestamp": timestamp.isoformat() if timestamp else None,
            "score": 0,  # Generic RSS doesn't typically have scores
            "comments_count": 0,  # Not available in generic RSS
            "tags": extract_tags_from_entry(entry),
            "source": source_name,
            "source_id": getattr(entry, "id", ""),
        }

        # Clean HTML content
        if standardized["content"]:
            standardized["content"] = clean_html_content(standardized["content"])

        return standardized

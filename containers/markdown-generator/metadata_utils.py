"""
Pure functions for metadata extraction and transformation.

This module contains stateless, side-effect-free functions for extracting
and transforming article metadata from various sources.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from models import ArticleMetadata

logger = logging.getLogger(__name__)

__all__ = [
    "parse_date_string",
    "extract_image_fields_from_unsplash",
    "extract_metadata_from_article",
]


def parse_date_string(date_value: Any) -> Optional[datetime]:
    """
    Parse date from various formats.

    Pure function - no side effects, deterministic output.

    Args:
        date_value: Date in string or datetime format

    Returns:
        Parsed datetime or None if invalid

    Examples:
        >>> parse_date_string("2025-01-15T10:30:00Z")
        datetime.datetime(2025, 1, 15, 10, 30, tzinfo=datetime.timezone.utc)
        >>> parse_date_string(None)
        None
    """
    if isinstance(date_value, datetime):
        return date_value

    if isinstance(date_value, str):
        try:
            return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse date: {date_value}")

    return None


def extract_image_fields_from_unsplash(
    image_data: Dict[str, Any], article_title: str
) -> Dict[str, str]:
    """
    Extract and format image metadata from Unsplash response.

    Pure function - transforms dict to dict with no side effects.

    Args:
        image_data: Raw Unsplash API response
        article_title: Article title for alt text fallback

    Returns:
        Dict with formatted image fields (hero_image, thumbnail, etc.)

    Examples:
        >>> image_data = {
        ...     "url_regular": "https://example.com/photo.jpg",
        ...     "url_small": "https://example.com/thumb.jpg",
        ...     "description": "A photo",
        ...     "color": "#FF5733",
        ...     "photographer": "John Doe",
        ...     "photographer_url": "https://unsplash.com/@johndoe"
        ... }
        >>> result = extract_image_fields_from_unsplash(image_data, "Test Article")
        >>> result["hero_image"]
        'https://example.com/photo.jpg'
    """
    hero_image = image_data.get("url_regular")  # 1080px for hero
    thumbnail = image_data.get("url_small")  # 400px for thumbnail
    image_alt = image_data.get("description", article_title)
    image_color = image_data.get("color")

    # Format credit with photographer name and link
    photographer = image_data.get("photographer", "Unknown")
    photographer_url = image_data.get("photographer_url", "")
    image_credit = f"Photo by [{photographer}]({photographer_url}) on Unsplash"

    return {
        "hero_image": hero_image or "",
        "thumbnail": thumbnail or "",
        "image_alt": image_alt or "",
        "image_credit": image_credit or "",
        "image_color": image_color or "",
    }


def extract_metadata_from_article(
    article_data: Dict[str, Any], image_data: Optional[Dict[str, Any]] = None
) -> ArticleMetadata:
    """
    Extract structured metadata from article JSON.

    Pure function - transforms raw dict to validated Pydantic model.

    Args:
        article_data: Raw article data dictionary
        image_data: Optional stock image metadata from Unsplash

    Returns:
        ArticleMetadata: Validated metadata object

    Examples:
        >>> article = {"title": "Test", "url": "https://example.com", "source": "test"}
        >>> metadata = extract_metadata_from_article(article)
        >>> metadata.title
        'Test'
    """
    # Extract image fields if available
    image_fields = {}
    if image_data:
        image_fields = extract_image_fields_from_unsplash(
            image_data, article_data.get("title", "")
        )

    # Extract source from nested source_metadata if available
    source_metadata = article_data.get("source_metadata", {})
    source = source_metadata.get("source", article_data.get("source", "unknown"))

    return ArticleMetadata(
        title=article_data.get("title", "Untitled"),
        url=article_data.get("url", ""),
        source=source,
        author=article_data.get("author"),
        published_date=parse_date_string(article_data.get("published_date")),
        tags=article_data.get("tags", []),
        category=article_data.get("category"),
        hero_image=image_fields.get("hero_image"),
        thumbnail=image_fields.get("thumbnail"),
        image_alt=image_fields.get("image_alt"),
        image_credit=image_fields.get("image_credit"),
        image_color=image_fields.get("image_color"),
    )

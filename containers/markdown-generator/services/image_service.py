"""
Stock Image Service

Pure functional API for fetching stock photos from Unsplash.
All functions are stateless and side-effect free (except for HTTP calls).
"""

import logging
from typing import Any, Dict, List, Optional

import aiohttp

from libs.http_client import close_http_session, get_http_session

logger = logging.getLogger(__name__)

# Constants
UNSPLASH_API_BASE_URL = "https://api.unsplash.com"
STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "is",
    "are",
    "was",
    "were",
}

# Re-export for backwards compatibility
__all__ = ["close_http_session", "get_http_session"]


def extract_keywords_from_article(
    title: str,
    content: str = "",
    tags: Optional[List[str]] = None,
) -> str:
    """
    Extract search keywords from article metadata.

    Pure function - no side effects, deterministic output.

    Prioritizes:
    1. Tags (if available and relevant)
    2. First 3 meaningful words from title
    3. Fallback to generic "technology"

    Args:
        title: Article title
        content: Article content preview (unused, kept for API compatibility)
        tags: Article tags/categories

    Returns:
        Search query string optimized for Unsplash

    Examples:
        >>> extract_keywords_from_article(
        ...     title="The Future of AI in Healthcare",
        ...     tags=["AI", "healthcare"]
        ... )
        'AI healthcare'
        >>> extract_keywords_from_article(
        ...     title="Understanding Quantum Computing Basics"
        ... )
        'quantum computing basics'
    """
    # Use tags if available (most specific)
    if tags and len(tags) > 0:
        # Clean tags and limit to 2 most relevant
        clean_tags = [tag.strip() for tag in tags if tag.strip()]
        if clean_tags:
            return " ".join(clean_tags[:2])

    # Extract meaningful words from title
    words = [
        w.strip() for w in title.split() if w.strip() and w.lower() not in STOPWORDS
    ]

    if words:
        # Take first 3 meaningful words
        return " ".join(words[:3])

    # Last resort fallback
    return "technology"


def parse_unsplash_photo(photo: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Unsplash API photo response into standardized format.

    Pure function - transforms data structure without side effects.

    Args:
        photo: Raw photo data from Unsplash API

    Returns:
        Standardized image metadata dictionary

    Examples:
        >>> photo = {
        ...     "urls": {"raw": "...", "regular": "...", "small": "..."},
        ...     "user": {"name": "Jane", "links": {"html": "..."}},
        ...     "description": "Test photo",
        ...     "color": "#ABCDEF",
        ...     "links": {"html": "..."}
        ... }
        >>> result = parse_unsplash_photo(photo)
        >>> result["photographer"]
        'Jane'
    """
    return {
        "url_raw": photo["urls"]["raw"],  # Full resolution
        "url_regular": photo["urls"]["regular"],  # 1080px
        "url_small": photo["urls"]["small"],  # 400px
        "photographer": photo["user"]["name"],
        "photographer_url": photo["user"]["links"]["html"],
        "description": photo.get("description") or photo.get("alt_description", ""),
        "color": photo.get("color", "#808080"),
        "unsplash_url": photo["links"]["html"],
    }


async def search_unsplash_image(
    access_key: str,
    query: str,
    orientation: str = "landscape",
) -> Optional[Dict[str, Any]]:
    """
    Search Unsplash API for image matching query.

    Pure async function - performs HTTP call but no other side effects.

    Args:
        access_key: Unsplash API access key
        query: Search query (article topic, keywords)
        orientation: "landscape" (hero), "portrait", "squarish" (thumbnail)

    Returns:
        Dictionary with image URLs and metadata, or None if not found

    Examples:
        >>> result = await search_unsplash_image(
        ...     access_key="test_key",
        ...     query="artificial intelligence"
        ... )
        >>> result["photographer"]
        'John Photographer'
    """
    # Clean and validate query
    clean_query = query.strip()[:100]

    if not clean_query:
        logger.warning("Empty search query provided")
        return None

    try:
        session = await get_http_session()
        params = {
            "query": clean_query,
            "per_page": 1,  # Only need top result
            "orientation": orientation,
            "content_filter": "high",  # Family-friendly only
        }
        headers = {"Authorization": f"Client-ID {access_key}"}
        url = f"{UNSPLASH_API_BASE_URL}/search/photos"

        logger.info(f"Searching Unsplash for: {clean_query}")

        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                logger.error(f"Unsplash API error: {resp.status} - {error_text}")
                return None

            data = await resp.json()

            if not data.get("results"):
                logger.warning(f"No images found for query: {query}")
                return None

            # Parse first result
            photo = data["results"][0]
            result = parse_unsplash_photo(photo)

            logger.info(
                f"Found image by {result['photographer']}: "
                f"{result['description'][:50]}"
            )

            return result

    except aiohttp.ClientError as e:
        logger.error(f"Network error fetching image: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching image: {e}")
        return None


async def fetch_image_for_article(
    access_key: str,
    title: str,
    content: str = "",
    tags: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetch appropriate stock image for an article.

    Pure async function composing keyword extraction and image search.

    Args:
        access_key: Unsplash API key
        title: Article title
        content: Article content preview (unused, kept for API compatibility)
        tags: Article tags

    Returns:
        Image metadata dict or None if not found

    Examples:
        >>> image = await fetch_image_for_article(
        ...     access_key="test_key",
        ...     title="Machine Learning in 2025",
        ...     tags=["machine-learning", "AI"]
        ... )
        >>> image["photographer"]
        'Professional Photographer'
    """
    # Extract keywords (pure function)
    query = extract_keywords_from_article(title, content, tags)

    # Search for landscape image (async HTTP call)
    return await search_unsplash_image(
        access_key=access_key,
        query=query,
        orientation="landscape",
    )


async def download_image_from_url(image_url: str, output_path: str) -> bool:
    """
    Download image from URL to local file.

    Args:
        image_url: Full image URL (e.g., from url_regular)
        output_path: Local file path to save image

    Returns:
        True if successful, False otherwise

    Examples:
        >>> success = await download_image_from_url(
        ...     "https://images.unsplash.com/photo-xyz",
        ...     "/tmp/article-hero.jpg"
        ... )
        >>> success
        True
    """
    try:
        session = await get_http_session()
        async with session.get(image_url) as resp:
            if resp.status != 200:
                logger.error(f"Failed to download image: {resp.status} - {image_url}")
                return False

            content = await resp.read()

            with open(output_path, "wb") as f:
                f.write(content)

            logger.info(f"Downloaded image to {output_path}")
            return True

    except Exception as e:
        logger.error(f"Failed to download image: {e}")
        return False

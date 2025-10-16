"""
Stock Image Service

Pure functional API for fetching stock photos from Unsplash.
All functions are stateless and side-effect free (except for HTTP calls).
"""

import logging
import re
from collections import Counter
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
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "should",
    "could",
    "may",
    "might",
    "must",
    "can",
    "this",
    "that",
    "these",
    "those",
}

MIN_TITLE_LENGTH_FOR_IMAGES = 20  # Skip suspiciously short titles

# Re-export for backwards compatibility
__all__ = ["close_http_session", "get_http_session"]


# ============================================================================
# Skip Logic (Pure Functions)
# ============================================================================


def has_date_prefix(title: str) -> bool:
    """
    Check if title has date prefix that suggests poor quality.

    Pure function - deterministic output.

    Args:
        title: Title to check

    Returns:
        True if title starts with date prefix

    Examples:
        >>> has_date_prefix("(15 Oct) Article Title")
        True
        >>> has_date_prefix("Article Title")
        False
    """
    date_patterns = [
        r"^\(\d{1,2}\s+\w{3}\)",  # (15 Oct)
        r"^\(\w{3}\s+\d{1,2}\)",  # (Oct 15)
        r"^\(\d{4}-\d{2}-\d{2}\)",  # (2025-10-15)
        r"^\[\d{1,2}\s+\w{3}\]",  # [15 Oct]
    ]

    return any(re.match(pattern, title) for pattern in date_patterns)


def should_skip_image(title: str) -> bool:
    """
    Determine if image fetching should be skipped for this title.

    Pure function - decision based on title quality.

    Skip images when:
    1. Title has date prefix (low quality indicator)
    2. Title is too short (< 20 chars, likely truncated/poor)
    3. Title appears to be just a number or ID

    Args:
        title: Article title

    Returns:
        True if image should be skipped

    Examples:
        >>> should_skip_image("(15 Oct) Short")
        True
        >>> should_skip_image("AI")
        True
        >>> should_skip_image("Understanding Quantum Computing")
        False
    """
    if not title or len(title.strip()) < MIN_TITLE_LENGTH_FOR_IMAGES:
        return True

    if has_date_prefix(title):
        return True

    # Skip if title is mostly numbers/symbols
    alpha_chars = sum(c.isalpha() for c in title)
    if alpha_chars < 5:  # Less than 5 letters total
        return True

    return False


# ============================================================================
# Keyword Extraction (Pure Functions)
# ============================================================================


def extract_capitalized_words(text: str, limit: int = 5) -> List[str]:
    """
    Extract capitalized words from text (likely proper nouns/topics).

    Pure function - extracts important terms.

    Args:
        text: Text to analyze
        limit: Maximum number of words to return

    Returns:
        List of capitalized words

    Examples:
        >>> extract_capitalized_words("Windows Security Update")
        ['Windows', 'Security', 'Update']
    """
    # Find capitalized words (not at start of sentence)
    words = re.findall(r"\b[A-Z][a-z]{2,}\b", text)

    # Count frequency
    word_counts = Counter(words)

    # Return most common, limited
    return [word for word, _ in word_counts.most_common(limit)]


def extract_keywords_from_content(content: str, max_keywords: int = 5) -> List[str]:
    """
    Extract meaningful keywords from article content using simple NLP.

    Pure function - frequency-based keyword extraction.

    Args:
        content: Article content to analyze
        max_keywords: Maximum keywords to extract

    Returns:
        List of extracted keywords

    Examples:
        >>> extract_keywords_from_content(
        ...     "Artificial Intelligence is transforming healthcare. "
        ...     "AI systems can analyze medical data."
        ... )
        ['Artificial', 'Intelligence', 'healthcare', 'systems']
    """
    if not content:
        return []

    # Extract capitalized words (proper nouns, important terms)
    capitalized = extract_capitalized_words(content, limit=max_keywords * 2)

    # Extract other meaningful words (longer than 5 chars, not stopwords)
    all_words = re.findall(r"\b[a-zA-Z]{6,}\b", content.lower())
    meaningful_words = [w for w in all_words if w not in STOPWORDS]

    # Count frequency
    word_counts = Counter(meaningful_words)
    common_words = [word for word, _ in word_counts.most_common(max_keywords)]

    # Combine capitalized and common words, prioritize capitalized
    keywords = []
    for word in capitalized:
        if word not in keywords:
            keywords.append(word)

    for word in common_words:
        if word not in [k.lower() for k in keywords] and len(keywords) < max_keywords:
            keywords.append(word)

    return keywords[:max_keywords]


def extract_keywords_from_article(
    title: str,
    content: str = "",
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
) -> Optional[str]:
    """
    Extract search keywords from article metadata with priority fallback.

    Pure function - no side effects, deterministic output.

    Priority order:
    1. Check if image should be skipped (returns None)
    2. Tags (if available and relevant)
    3. Content-extracted keywords
    4. Category
    5. First 3 meaningful words from title
    6. Return None if nothing good (caller should skip image)

    Args:
        title: Article title
        content: Article content preview
        tags: Article tags/categories
        category: Article category

    Returns:
        Search query string optimized for Unsplash, or None to skip image

    Examples:
        >>> extract_keywords_from_article(
        ...     title="The Future of AI in Healthcare",
        ...     tags=["AI", "healthcare"]
        ... )
        'AI healthcare'
        >>> extract_keywords_from_article(
        ...     title="(15 Oct) Short",
        ...     tags=[]
        ... )
        None
        >>> extract_keywords_from_article(
        ...     title="Windows Security Vulnerabilities Found",
        ...     content="Microsoft Windows security researchers discovered..."
        ... )
        'Windows Security Vulnerabilities'
    """
    # Check if we should skip image for this title
    if should_skip_image(title):
        logger.info(f"Skipping image for poor quality title: {title[:50]}")
        return None

    # Priority 1: Use tags if available (most specific)
    if tags and len(tags) > 0:
        clean_tags = [tag.strip() for tag in tags if tag.strip()]
        if clean_tags:
            query = " ".join(clean_tags[:2])
            logger.debug(f"Using tags for image search: {query}")
            return query

    # Priority 2: Extract keywords from content (if substantial)
    if content and len(content) > 100:
        content_keywords = extract_keywords_from_content(content, max_keywords=3)
        if content_keywords:
            query = " ".join(content_keywords)
            logger.debug(f"Using content keywords for image search: {query}")
            return query

    # Priority 3: Use category if available
    if category and category.strip():
        logger.debug(f"Using category for image search: {category}")
        return category.strip()

    # Priority 4: Extract meaningful words from title
    words = [
        w.strip() for w in title.split() if w.strip() and w.lower() not in STOPWORDS
    ]

    if words and len(words) >= 2:
        # Take first 3 meaningful words
        query = " ".join(words[:3])
        logger.debug(f"Using title words for image search: {query}")
        return query

    # If we get here, title has no good keywords - skip image
    logger.info(f"No good keywords found for image search: {title[:50]}")
    return None


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
    category: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetch appropriate stock image for an article.

    Pure async function composing keyword extraction and image search.
    Returns None if image should be skipped or not found.

    Args:
        access_key: Unsplash API key
        title: Article title
        content: Article content preview
        tags: Article tags
        category: Article category

    Returns:
        Image metadata dict or None if skipped/not found

    Examples:
        >>> image = await fetch_image_for_article(
        ...     access_key="test_key",
        ...     title="Machine Learning in 2025",
        ...     tags=["machine-learning", "AI"]
        ... )
        >>> image["photographer"]
        'Professional Photographer'
        >>> # Short/poor titles return None
        >>> image = await fetch_image_for_article(
        ...     access_key="test_key",
        ...     title="(15 Oct) AI"
        ... )
        >>> image is None
        True
    """
    # Extract keywords (pure function) - may return None to skip
    query = extract_keywords_from_article(title, content, tags, category)

    if query is None:
        logger.info(f"Skipping image search for article: {title[:50]}")
        return None

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

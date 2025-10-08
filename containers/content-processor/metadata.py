"""
Pure functional article metadata generation.

This module provides stateless functions for creating article metadata
structures and validating metadata fields.

Contract Version: 1.0.0
"""

from datetime import datetime
from typing import Any, Dict, Optional


def create_article_metadata(
    original_title: str,
    clean_title: str,
    slug: str,
    seo_description: str,
    language: str,
    date_slug: str,
    filename: str,
    url: str,
    translated: bool = False,
    metadata_cost_usd: float = 0.0,
    metadata_tokens: int = 0,
) -> Dict[str, Any]:
    """
    Create complete article metadata structure.

    Pure function that assembles all metadata fields into a standardized dict.

    Args:
        original_title: Original article title (before any processing)
        clean_title: Cleaned/translated SEO title
        slug: URL-safe slug
        seo_description: SEO-optimized description
        language: ISO 639-1 language code (e.g., 'en', 'ja', 'fr')
        date_slug: Date in YYYY-MM-DD format
        filename: Complete filename path
        url: Article URL path
        translated: Whether title was translated
        metadata_cost_usd: Cost of generating metadata
        metadata_tokens: Tokens used for metadata generation

    Returns:
        Dict with complete metadata structure

    Examples:
        >>> meta = create_article_metadata(
        ...     original_title="Test Article",
        ...     clean_title="Test Article",
        ...     slug="test-article",
        ...     seo_description="A test article description",
        ...     language="en",
        ...     date_slug="2025-10-08",
        ...     filename="articles/2025-10-08-test-article.html",
        ...     url="/articles/2025-10-08-test-article.html"
        ... )
        >>> meta["original_title"]
        'Test Article'
        >>> meta["translated"]
        False
    """
    return {
        "original_title": original_title,
        "title": clean_title,
        "slug": slug,
        "seo_description": seo_description,
        "language": language,
        "translated": translated,
        "date_slug": date_slug,
        "filename": filename,
        "url": url,
        "metadata_cost_usd": metadata_cost_usd,
        "metadata_tokens": metadata_tokens,
    }


def validate_metadata_structure(metadata: Dict[str, Any]) -> bool:
    """
    Validate that metadata has all required fields.

    Pure function that checks for required metadata keys.

    Args:
        metadata: Metadata dictionary to validate

    Returns:
        bool: True if all required fields present, False otherwise

    Examples:
        >>> meta = {"original_title": "Test", "title": "Test", "slug": "test",
        ...         "seo_description": "Desc", "language": "en", "translated": False,
        ...         "date_slug": "2025-10-08", "filename": "test.html", "url": "/test.html",
        ...         "metadata_cost_usd": 0.0, "metadata_tokens": 0}
        >>> validate_metadata_structure(meta)
        True
        >>> validate_metadata_structure({"title": "Test"})
        False
    """
    required_fields = [
        "original_title",
        "title",
        "slug",
        "seo_description",
        "language",
        "translated",
        "date_slug",
        "filename",
        "url",
        "metadata_cost_usd",
        "metadata_tokens",
    ]

    return all(field in metadata for field in required_fields)


def needs_translation(title: str) -> bool:
    """
    Detect if title contains non-ASCII characters requiring translation.

    Pure function with no side effects.

    Args:
        title: Title to check

    Returns:
        bool: True if title contains non-ASCII characters

    Examples:
        >>> needs_translation("Hello World")
        False
        >>> needs_translation("米政権内の対中強硬派に焦り")
        True
        >>> needs_translation("Café Résumé")
        True
    """
    if not title or not isinstance(title, str):
        return False

    return not title.isascii()


def parse_date_slug(
    published_date: str, fallback_date: Optional[datetime] = None
) -> str:
    """
    Parse ISO date string to YYYY-MM-DD format.

    Pure function (when fallback_date provided) that extracts date portion.

    Args:
        published_date: ISO 8601 date string or YYYY-MM-DD format
        fallback_date: Optional datetime to use if parsing fails (for testing)

    Returns:
        str: Date in YYYY-MM-DD format

    Examples:
        >>> parse_date_slug("2025-10-06T12:30:00Z")
        '2025-10-06'
        >>> parse_date_slug("2025-10-06")
        '2025-10-06'
        >>> from datetime import datetime, timezone
        >>> fallback = datetime(2025, 1, 1, tzinfo=timezone.utc)
        >>> parse_date_slug("invalid", fallback)
        '2025-01-01'
    """
    try:
        # Handle ISO 8601 with time component
        if "T" in published_date:
            dt = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
        else:
            # Assume already in YYYY-MM-DD format
            dt = datetime.fromisoformat(published_date)

        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        # Use fallback or current date
        if fallback_date:
            return fallback_date.strftime("%Y-%m-%d")
        return datetime.now().strftime("%Y-%m-%d")


def generate_article_filename(
    date_slug: str, slug: str, extension: str = "html"
) -> str:
    """
    Generate complete article filename.

    Pure function that constructs filename from components.

    Args:
        date_slug: Date in YYYY-MM-DD format
        slug: URL-safe article slug
        extension: File extension (default "html")

    Returns:
        str: Complete filename path

    Raises:
        ValueError: If filename would exceed 100 characters

    Examples:
        >>> generate_article_filename("2025-10-08", "test-article")
        'articles/2025-10-08-test-article.html'
        >>> generate_article_filename("2025-10-08", "test", "md")
        'articles/2025-10-08-test.md'
    """
    filename = f"articles/{date_slug}-{slug}.{extension}"

    if len(filename) > 100:
        raise ValueError(
            f"Filename too long ({len(filename)} chars): {filename}. "
            f"Slug must be shorter."
        )

    return filename


def generate_article_url(date_slug: str, slug: str, extension: str = "html") -> str:
    """
    Generate article URL path.

    Pure function that constructs URL from components.

    Args:
        date_slug: Date in YYYY-MM-DD format
        slug: URL-safe article slug
        extension: File extension (default "html")

    Returns:
        str: URL path starting with /

    Examples:
        >>> generate_article_url("2025-10-08", "test-article")
        '/articles/2025-10-08-test-article.html'
        >>> generate_article_url("2025-10-08", "test", "md")
        '/articles/2025-10-08-test.md'
    """
    return f"/articles/{date_slug}-{slug}.{extension}"


def truncate_with_word_boundary(text: str, max_length: int) -> str:
    """
    Truncate text at word boundary without exceeding max length.

    Pure function that truncates intelligently at word boundaries.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        str: Truncated text (no ellipsis added)

    Examples:
        >>> truncate_with_word_boundary("Hello world this is a test", 15)
        'Hello world'
        >>> truncate_with_word_boundary("Short", 100)
        'Short'
        >>> truncate_with_word_boundary("NoSpacesHereAtAll", 10)
        'NoSpacesHe'
    """
    if not text or not isinstance(text, str):
        return ""

    if len(text) <= max_length:
        return text

    # Truncate to max length
    truncated = text[:max_length]

    # Find last space for word boundary
    last_space = truncated.rfind(" ")

    if last_space > 0:
        # Truncate at word boundary
        return truncated[:last_space]

    # No spaces found, return hard truncate
    return truncated


def validate_title_length(
    title: str, min_length: int = 10, max_length: int = 70
) -> bool:
    """
    Validate that title is within acceptable length range.

    Pure function with no side effects.

    Args:
        title: Title to validate
        min_length: Minimum acceptable length (default 10)
        max_length: Maximum acceptable length (default 70)

    Returns:
        bool: True if length is acceptable

    Examples:
        >>> validate_title_length("Good Title Length")
        True
        >>> validate_title_length("Short")
        False
        >>> validate_title_length("This is an extremely long title that exceeds seventy characters total")
        False
    """
    if not title or not isinstance(title, str):
        return False

    return min_length <= len(title) <= max_length


def validate_description_length(
    description: str, min_length: int = 100, max_length: int = 170
) -> bool:
    """
    Validate that description is within acceptable length range for SEO.

    Pure function with no side effects.

    Args:
        description: Description to validate
        min_length: Minimum acceptable length (default 100)
        max_length: Maximum acceptable length (default 170)

    Returns:
        bool: True if length is acceptable

    Examples:
        >>> desc = "This is a good SEO description that is between one hundred and one hundred seventy characters long for optimal display."
        >>> validate_description_length(desc)
        True
        >>> validate_description_length("Too short")
        False
    """
    if not description or not isinstance(description, str):
        return False

    return min_length <= len(description) <= max_length


def validate_language_code(language: str) -> bool:
    """
    Validate that language code is ISO 639-1 format (2 letters).

    Pure function with no side effects.

    Args:
        language: Language code to validate

    Returns:
        bool: True if valid 2-letter code

    Examples:
        >>> validate_language_code("en")
        True
        >>> validate_language_code("ja")
        True
        >>> validate_language_code("eng")
        False
        >>> validate_language_code("1")
        False
    """
    if not language or not isinstance(language, str):
        return False

    return len(language) == 2 and language.isalpha() and language.islower()

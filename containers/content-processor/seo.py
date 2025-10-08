"""
SEO Metadata Generation - Pure Functional Implementation

Pure functions for generating SEO-friendly metadata from article content.
All functions are stateless, side-effect free, and < 50 lines.

Contract Version: 1.0.0
Standards: PEP 8, comprehensive type hints, no side effects
"""

import re
from datetime import datetime
from typing import Dict, Optional


def generate_slug(title: str) -> str:
    """
    Generate URL-safe slug from title.

    Pure function: Same input always produces same output, no side effects.

    Args:
        title: Article title (any string)

    Returns:
        URL-safe slug (lowercase, hyphens, alphanumeric only)

    Examples:
        >>> generate_slug("How AI is Transforming Development")
        'how-ai-is-transforming-development'
        >>> generate_slug("Python 3.12 Released!")
        'python-312-released'
        >>> generate_slug("What's New in AI?")
        'whats-new-in-ai'
    """
    if not title or not isinstance(title, str):
        return ""

    # Convert to lowercase
    slug = title.lower()

    # Remove apostrophes and quotes
    slug = re.sub(r"[''`\"]", "", slug)

    # Replace spaces and special chars with hyphens
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    return slug


def generate_seo_title(title: str, max_length: int = 60) -> str:
    """
    Generate SEO-optimized title (max 60 chars for search engines).

    Pure function: Deterministic output, no side effects.

    Args:
        title: Original article title
        max_length: Maximum length for SEO (default 60)

    Returns:
        SEO-optimized title, truncated if needed

    Examples:
        >>> generate_seo_title("Short Title")
        'Short Title'
        >>> generate_seo_title("A" * 100)
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA...'
    """
    if not title or not isinstance(title, str):
        return ""

    # Already within limit
    if len(title) <= max_length:
        return title

    # Truncate and add ellipsis
    truncated = title[: max_length - 3].rstrip()
    return f"{truncated}..."


def generate_filename(date: datetime, slug: str, extension: str = "md") -> str:
    """
    Generate filename from date and slug.

    Pure function: Same inputs always produce same output.

    Args:
        date: Publication date
        slug: URL slug
        extension: File extension (default "md")

    Returns:
        Filename in format: YYYYMMDD-slug.extension

    Examples:
        >>> from datetime import datetime
        >>> dt = datetime(2025, 10, 8)
        >>> generate_filename(dt, "test-article")
        '20251008-test-article.md'
        >>> generate_filename(dt, "python-312", "json")
        '20251008-python-312.json'
    """
    if not isinstance(date, datetime):
        raise TypeError("date must be datetime object")

    if not slug or not isinstance(slug, str):
        raise ValueError("slug must be non-empty string")

    # Format: YYYYMMDD-slug.extension
    date_str = date.strftime("%Y%m%d")
    return f"{date_str}-{slug}.{extension}"


def generate_article_url(date: datetime, slug: str) -> str:
    """
    Generate article URL path.

    Pure function: Deterministic output.

    Args:
        date: Publication date
        slug: URL slug

    Returns:
        URL path in format: /YYYY/MM/slug

    Examples:
        >>> from datetime import datetime
        >>> dt = datetime(2025, 10, 8)
        >>> generate_article_url(dt, "test-article")
        '/2025/10/test-article'
    """
    if not isinstance(date, datetime):
        raise TypeError("date must be datetime object")

    if not slug or not isinstance(slug, str):
        raise ValueError("slug must be non-empty string")

    # Format: /YYYY/MM/slug
    return f"/{date.year}/{date.month:02d}/{slug}"


def generate_article_id(date: datetime, slug: str) -> str:
    """
    Generate unique article identifier.

    Pure function: Same inputs produce same ID.

    Args:
        date: Publication date
        slug: URL slug

    Returns:
        Article ID in format: YYYYMMDD-slug

    Examples:
        >>> from datetime import datetime
        >>> dt = datetime(2025, 10, 8)
        >>> generate_article_id(dt, "test-article")
        '20251008-test-article'
    """
    if not isinstance(date, datetime):
        raise TypeError("date must be datetime object")

    if not slug or not isinstance(slug, str):
        raise ValueError("slug must be non-empty string")

    # Format: YYYYMMDD-slug
    date_str = date.strftime("%Y%m%d")
    return f"{date_str}-{slug}"


def create_seo_metadata(
    title: str,
    date: datetime,
    seo_title_override: Optional[str] = None,
) -> Dict[str, str]:
    """
    Create complete SEO metadata from title and date.

    Pure function: Combines all SEO generation functions.

    Args:
        title: Original article title
        date: Publication date
        seo_title_override: Optional custom SEO title

    Returns:
        Dictionary with all SEO metadata:
        - slug: URL-safe slug
        - seo_title: SEO-optimized title
        - filename: Markdown filename
        - url: Article URL path
        - article_id: Unique identifier

    Examples:
        >>> from datetime import datetime
        >>> dt = datetime(2025, 10, 8)
        >>> meta = create_seo_metadata("Test Article", dt)
        >>> meta['slug']
        'test-article'
        >>> meta['article_id']
        '20251008-test-article'
    """
    if not title or not isinstance(title, str):
        raise ValueError("title must be non-empty string")

    if not isinstance(date, datetime):
        raise TypeError("date must be datetime object")

    # Generate slug from title
    slug = generate_slug(title)

    if not slug:
        raise ValueError(f"Generated empty slug from title: {title}")

    # Use override or generate SEO title
    seo_title = seo_title_override or generate_seo_title(title)

    # Generate all metadata
    return {
        "slug": slug,
        "seo_title": seo_title,
        "filename": generate_filename(date, slug),
        "url": generate_article_url(date, slug),
        "article_id": generate_article_id(date, slug),
    }

"""
Blob path utility functions for article storage.

NEW FLAT STRUCTURE: articles/YYYY-MM-DD/slug.ext
Generates standardized blob paths for Azure Blob Storage following
consistent naming conventions for easy date-range queries and SEO-friendly URLs.
"""

# ============================================================================
# FLATTENED STRUCTURE FUNCTIONS (articles/ prefix with YYYY-MM-DD format)
# ============================================================================


def generate_articles_path(
    slug: str, published_date: str, extension: str = "json"
) -> str:
    """
    Generate flattened blob path using articles/ prefix with date and slug.

    Creates a clean path structure: articles/YYYY-MM-DD/slug.ext
    Extracts date from ISO timestamp if provided as such.

    Args:
        slug: URL-safe article slug
        published_date: Either YYYY-MM-DD format or ISO 8601 timestamp
        extension: File extension without dot (default: "json")

    Returns:
        str: Blob path in format: articles/YYYY-MM-DD/slug.ext

    Example:
        >>> path = generate_articles_path("saturn-moon-potential", "2025-10-13")
        >>> path
        'articles/2025-10-13/saturn-moon-potential.json'

        >>> # Also works with ISO timestamp
        >>> path = generate_articles_path(
        ...     "saturn-moon-potential",
        ...     "2025-10-13T09:06:54+00:00"
        ... )
        >>> path
        'articles/2025-10-13/saturn-moon-potential.json'
    """
    # Extract date in YYYY-MM-DD format
    if len(published_date) > 10 and "T" in published_date:
        # ISO 8601 timestamp - extract date portion
        date_str = published_date[:10]  # YYYY-MM-DD
    else:
        # Already in YYYY-MM-DD format
        date_str = published_date

    return f"articles/{date_str}/{slug}.{extension}"


def generate_articles_processed_blob_path(article_data: dict) -> str:
    """
    Generate blob path for processed article using articles/ structure.

    Extracts slug and date from article data.

    Args:
        article_data: Article result dict with slug and published_date fields

    Returns:
        str: Blob path for processed article

    Example:
        >>> article = {
        ...     "slug": "saturn-moon",
        ...     "published_date": "2025-10-13T09:06:54+00:00"
        ... }
        >>> generate_articles_processed_blob_path(article)
        'articles/2025-10-13/saturn-moon.json'
    """
    slug = article_data.get("slug", "unknown")
    published_date = article_data.get("published_date", "")

    return generate_articles_path(slug, published_date, "json")


def generate_articles_markdown_blob_path(article_data: dict) -> str:
    """
    Generate blob path for markdown output using articles/ structure.

    Extracts slug and date from article data.

    Args:
        article_data: Article result dict with slug and published_date fields

    Returns:
        str: Blob path for markdown file

    Example:
        >>> article = {
        ...     "slug": "saturn-moon",
        ...     "published_date": "2025-10-13T09:06:54+00:00"
        ... }
        >>> generate_articles_markdown_blob_path(article)
        'articles/2025-10-13/saturn-moon.md'
    """
    slug = article_data.get("slug", "unknown")
    published_date = article_data.get("published_date", "")

    return generate_articles_path(slug, published_date, "md")


def generate_articles_collection_blob_path(
    collection_timestamp: str, collection_id: str = ""
) -> str:
    """
    Generate blob path for collection file using articles/ structure.

    Args:
        collection_timestamp: ISO 8601 timestamp of collection
        collection_id: Optional collection identifier (e.g., "20251013_090700")

    Returns:
        str: Blob path for collection file

    Example:
        >>> path = generate_articles_collection_blob_path(
        ...     "2025-10-13T09:07:00+00:00",
        ...     "20251013_090700"
        ... )
        >>> path
        'articles/2025-10-13/collection-20251013_090700.json'
    """
    # Extract date
    if len(collection_timestamp) > 10 and "T" in collection_timestamp:
        date_str = collection_timestamp[:10]  # YYYY-MM-DD
    else:
        date_str = collection_timestamp

    # Build filename
    if collection_id:
        filename = f"collection-{collection_id}.json"
    else:
        filename = "collection.json"

    return f"articles/{date_str}/{filename}"

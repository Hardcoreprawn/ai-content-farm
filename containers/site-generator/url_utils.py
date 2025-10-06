"""
URL Construction Utilities

Single source of truth for all article URL generation.
Prevents URL inconsistencies between sitemap, RSS, and HTML generation.
"""

from urllib.parse import urljoin


def get_article_url(
    article_slug: str, base_url: str = "", include_html_extension: bool = True
) -> str:
    """
    Get canonical article URL from slug.

    SINGLE SOURCE OF TRUTH for article URL construction.
    All code should use this function to ensure URL consistency.

    Args:
        article_slug: Article slug/identifier (e.g., '123-my-article')
        base_url: Optional base URL to prepend (e.g., 'https://jablab.com')
        include_html_extension: Whether to include .html extension (default True for static hosting)

    Returns:
        Complete article URL path

    Examples:
        >>> get_article_url('123-my-article')
        '/articles/123-my-article.html'
        >>> get_article_url('123-my-article', include_html_extension=False)
        '/articles/123-my-article'
        >>> get_article_url('123-my-article', 'https://jablab.com')
        'https://jablab.com/articles/123-my-article.html'
    """
    if not article_slug:
        raise ValueError("article_slug cannot be empty")

    # Construct path with consistent format
    path = f"/articles/{article_slug}"
    if include_html_extension:
        path += ".html"

    # Add base URL if provided
    if base_url:
        return urljoin(base_url, path)

    return path

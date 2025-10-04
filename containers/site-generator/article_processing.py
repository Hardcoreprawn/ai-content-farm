"""
Pure functions for article processing, sorting, and deduplication.

This module contains functional utilities for transforming and organizing
article collections with no side effects.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def deduplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate articles, keeping the most recent version of each.

    Pure function that deduplicates articles based on ID/topic_id/slug,
    preferring articles with more recent dates.

    Args:
        articles: List of article dictionaries

    Returns:
        List of unique articles (most recent version of each)

    Examples:
        >>> articles = [
        ...     {"id": "123", "title": "Test", "generated_at": "2025-01-01"},
        ...     {"id": "123", "title": "Test Updated", "generated_at": "2025-01-02"},
        ...     {"id": "456", "title": "Other", "generated_at": "2025-01-01"},
        ... ]
        >>> result = deduplicate_articles(articles)
        >>> len(result)
        2
        >>> result[0]["title"]
        'Test Updated'
    """
    if not articles:
        return []

    seen_ids: Dict[str, Dict[str, Any]] = {}

    for article in articles:
        # Get article identifier (try multiple fields)
        article_id = (
            article.get("id") or article.get("topic_id") or article.get("slug", "")
        )

        if not article_id:
            # No ID found, keep the article but generate a unique key
            article_id = f"_no_id_{id(article)}"
            seen_ids[article_id] = article
            continue

        # Check if we've seen this ID before
        if article_id not in seen_ids:
            seen_ids[article_id] = article
        else:
            # Compare dates and keep the newer one
            current_date = _extract_article_date(article)
            existing_date = _extract_article_date(seen_ids[article_id])

            if current_date and existing_date:
                if current_date > existing_date:
                    seen_ids[article_id] = article
            elif current_date:
                # Current has date, existing doesn't
                seen_ids[article_id] = article
            # If neither has a date or only existing has one, keep existing

    unique_articles = list(seen_ids.values())

    if len(unique_articles) < len(articles):
        logger.info(
            f"Deduplicated {len(articles)} articles to {len(unique_articles)} unique articles"
        )

    return unique_articles


def sort_articles_by_date(
    articles: List[Dict[str, Any]], reverse: bool = True
) -> List[Dict[str, Any]]:
    """
    Sort articles by date (newest first by default).

    Pure function that sorts articles based on generated_at or published_date.
    Articles without dates are sorted to the end.

    Args:
        articles: List of article dictionaries
        reverse: If True, sort newest first; if False, oldest first

    Returns:
        Sorted list of articles

    Examples:
        >>> articles = [
        ...     {"title": "Old", "generated_at": "2025-01-01T00:00:00Z"},
        ...     {"title": "New", "generated_at": "2025-01-03T00:00:00Z"},
        ...     {"title": "Middle", "generated_at": "2025-01-02T00:00:00Z"},
        ... ]
        >>> result = sort_articles_by_date(articles)
        >>> [a["title"] for a in result]
        ['New', 'Middle', 'Old']
    """
    if not articles:
        return []

    def sort_key(article: Dict[str, Any]) -> str:
        """Extract sortable date string from article."""
        date_str = _extract_article_date_string(article)
        # Articles without dates get sorted to the end (or beginning if not reversed)
        return date_str if date_str else ("0000" if reverse else "9999")

    sorted_articles = sorted(articles, key=sort_key, reverse=reverse)

    logger.debug(
        f"Sorted {len(articles)} articles by date "
        f"({'newest' if reverse else 'oldest'} first)"
    )

    return sorted_articles


def calculate_last_updated(articles: List[Dict[str, Any]]) -> Optional[datetime]:
    """
    Calculate the most recent update time from a list of articles.

    Pure function that finds the newest date across all articles.

    Args:
        articles: List of article dictionaries

    Returns:
        Most recent datetime, or None if no dates found

    Examples:
        >>> articles = [
        ...     {"generated_at": "2025-01-01T12:00:00Z"},
        ...     {"generated_at": "2025-01-03T12:00:00Z"},
        ...     {"generated_at": "2025-01-02T12:00:00Z"},
        ... ]
        >>> result = calculate_last_updated(articles)
        >>> result.day
        3
    """
    if not articles:
        return None

    latest_date = None

    for article in articles:
        article_date = _extract_article_date(article)
        if article_date:
            if latest_date is None or article_date > latest_date:
                latest_date = article_date

    return latest_date


def prepare_articles_for_display(
    articles: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Prepare articles for display: deduplicate and sort.

    Pure function that combines deduplication and sorting operations
    to prepare articles for rendering in the index page.

    Args:
        articles: List of raw article dictionaries

    Returns:
        Processed list of articles (deduplicated and sorted newest first)

    Examples:
        >>> articles = [
        ...     {"id": "1", "title": "Old", "generated_at": "2025-01-01"},
        ...     {"id": "2", "title": "New", "generated_at": "2025-01-03"},
        ...     {"id": "1", "title": "Old v2", "generated_at": "2025-01-02"},
        ... ]
        >>> result = prepare_articles_for_display(articles)
        >>> len(result)
        2
        >>> result[0]["title"]
        'New'
    """
    if not articles:
        return []

    # Step 1: Deduplicate
    unique_articles = deduplicate_articles(articles)

    # Step 2: Sort by date (newest first)
    sorted_articles = sort_articles_by_date(unique_articles, reverse=True)

    logger.info(
        f"Prepared {len(sorted_articles)} articles for display "
        f"(from {len(articles)} raw articles)"
    )

    return sorted_articles


# Private helper functions


def _extract_article_date(article: Dict[str, Any]) -> Optional[datetime]:
    """
    Extract datetime object from article.

    Args:
        article: Article dictionary

    Returns:
        Datetime object or None if not found/parseable
    """
    date_value = article.get("generated_at") or article.get("published_date")

    if not date_value:
        return None

    try:
        if isinstance(date_value, str):
            # Handle ISO format with or without 'Z' suffix
            return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        elif isinstance(date_value, datetime):
            return date_value
    except (ValueError, TypeError, AttributeError):
        pass

    return None


def _extract_article_date_string(article: Dict[str, Any]) -> str:
    """
    Extract sortable date string from article.

    Args:
        article: Article dictionary

    Returns:
        ISO format date string or empty string if not found
    """
    date_obj = _extract_article_date(article)
    if date_obj:
        return date_obj.isoformat()

    # Fallback to raw string value if it exists
    date_value = article.get("generated_at") or article.get("published_date", "")
    return str(date_value) if date_value else ""

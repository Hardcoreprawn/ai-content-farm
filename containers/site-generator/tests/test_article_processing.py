"""
Tests for article_processing module.

Tests the pure functions for article deduplication, sorting, and processing.
"""

from datetime import datetime, timezone

import pytest
from article_processing import (
    calculate_last_updated,
    deduplicate_articles,
    prepare_articles_for_display,
    sort_articles_by_date,
)


class TestDeduplicateArticles:
    """Tests for article deduplication."""

    def test_empty_list(self):
        """Empty list returns empty list."""
        result = deduplicate_articles([])
        assert result == []

    def test_single_article(self):
        """Single article returns unchanged."""
        articles = [{"id": "1", "title": "Test"}]
        result = deduplicate_articles(articles)
        assert len(result) == 1
        assert result[0]["title"] == "Test"

    def test_no_duplicates(self):
        """Articles with different IDs are all kept."""
        articles = [
            {"id": "1", "title": "First"},
            {"id": "2", "title": "Second"},
            {"id": "3", "title": "Third"},
        ]
        result = deduplicate_articles(articles)
        assert len(result) == 3

    def test_duplicate_keeps_newer(self):
        """Duplicate IDs keep the article with newer date."""
        articles = [
            {"id": "1", "title": "Old", "generated_at": "2025-01-01T00:00:00Z"},
            {"id": "1", "title": "New", "generated_at": "2025-01-03T00:00:00Z"},
        ]
        result = deduplicate_articles(articles)
        assert len(result) == 1
        assert result[0]["title"] == "New"

    def test_duplicate_with_topic_id(self):
        """Uses topic_id if id not present."""
        articles = [
            {"topic_id": "abc", "title": "Old", "generated_at": "2025-01-01T00:00:00Z"},
            {"topic_id": "abc", "title": "New", "generated_at": "2025-01-02T00:00:00Z"},
        ]
        result = deduplicate_articles(articles)
        assert len(result) == 1
        assert result[0]["title"] == "New"

    def test_duplicate_with_slug(self):
        """Uses slug if id and topic_id not present."""
        articles = [
            {
                "slug": "test-article",
                "title": "Old",
                "generated_at": "2025-01-01T00:00:00Z",
            },
            {
                "slug": "test-article",
                "title": "New",
                "generated_at": "2025-01-02T00:00:00Z",
            },
        ]
        result = deduplicate_articles(articles)
        assert len(result) == 1
        assert result[0]["title"] == "New"

    def test_articles_without_id_are_kept(self):
        """Articles without any ID field are kept (treated as unique)."""
        articles = [
            {"title": "No ID 1"},
            {"title": "No ID 2"},
        ]
        result = deduplicate_articles(articles)
        assert len(result) == 2

    def test_mixed_id_types(self):
        """Different ID field types work correctly with priority: id > topic_id > slug."""
        articles = [
            {"id": "1", "title": "Has ID"},
            {"topic_id": "2", "title": "Has topic_id"},
            {"slug": "3", "title": "Has slug"},
        ]
        result = deduplicate_articles(articles)
        # All have different identifier values, so all are unique
        assert len(result) == 3

    def test_id_priority_over_topic_id(self):
        """The 'id' field takes priority over 'topic_id' as the unique identifier."""
        articles = [
            {"id": "unique1", "topic_id": "same", "title": "Has both - ID wins"},
            {"topic_id": "unique2", "title": "Has topic_id only"},
        ]
        result = deduplicate_articles(articles)
        # Two different articles because they have different primary identifiers
        assert len(result) == 2

    def test_duplicate_with_multiple_id_fields(self):
        """When 'id' matches, articles are duplicates regardless of other IDs."""
        articles = [
            {"id": "same", "topic_id": "different1", "title": "First"},
            {"id": "same", "topic_id": "different2", "title": "Second"},
        ]
        result = deduplicate_articles(articles)
        # Same 'id' means duplicate, keep only one
        assert len(result) == 1


class TestSortArticlesByDate:
    """Tests for article sorting by date."""

    def test_empty_list(self):
        """Empty list returns empty list."""
        result = sort_articles_by_date([])
        assert result == []

    def test_single_article(self):
        """Single article returns unchanged."""
        articles = [{"title": "Test", "generated_at": "2025-01-01T00:00:00Z"}]
        result = sort_articles_by_date(articles)
        assert len(result) == 1

    def test_sorts_newest_first_by_default(self):
        """Articles sorted with newest first by default."""
        articles = [
            {"title": "Old", "generated_at": "2025-01-01T00:00:00Z"},
            {"title": "New", "generated_at": "2025-01-03T00:00:00Z"},
            {"title": "Middle", "generated_at": "2025-01-02T00:00:00Z"},
        ]
        result = sort_articles_by_date(articles)
        assert result[0]["title"] == "New"
        assert result[1]["title"] == "Middle"
        assert result[2]["title"] == "Old"

    def test_sorts_oldest_first_when_reverse_false(self):
        """Articles sorted with oldest first when reverse=False."""
        articles = [
            {"title": "New", "generated_at": "2025-01-03T00:00:00Z"},
            {"title": "Old", "generated_at": "2025-01-01T00:00:00Z"},
        ]
        result = sort_articles_by_date(articles, reverse=False)
        assert result[0]["title"] == "Old"
        assert result[1]["title"] == "New"

    def test_uses_published_date_fallback(self):
        """Uses published_date if generated_at not present."""
        articles = [
            {"title": "Old", "published_date": "2025-01-01T00:00:00Z"},
            {"title": "New", "published_date": "2025-01-03T00:00:00Z"},
        ]
        result = sort_articles_by_date(articles)
        assert result[0]["title"] == "New"
        assert result[1]["title"] == "Old"

    def test_articles_without_dates_sorted_to_end(self):
        """Articles without dates are sorted to the end."""
        articles = [
            {"title": "No Date"},
            {"title": "Has Date", "generated_at": "2025-01-01T00:00:00Z"},
        ]
        result = sort_articles_by_date(articles)
        assert result[0]["title"] == "Has Date"
        assert result[1]["title"] == "No Date"


class TestCalculateLastUpdated:
    """Tests for calculating last updated timestamp."""

    def test_empty_list_returns_none(self):
        """Empty list returns None."""
        result = calculate_last_updated([])
        assert result is None

    def test_single_article(self):
        """Single article returns its date."""
        articles = [{"generated_at": "2025-01-15T12:00:00Z"}]
        result = calculate_last_updated(articles)
        assert result.day == 15

    def test_finds_most_recent_date(self):
        """Returns the most recent date from multiple articles."""
        articles = [
            {"generated_at": "2025-01-01T12:00:00Z"},
            {"generated_at": "2025-01-15T12:00:00Z"},
            {"generated_at": "2025-01-10T12:00:00Z"},
        ]
        result = calculate_last_updated(articles)
        assert result.day == 15

    def test_handles_published_date_fallback(self):
        """Uses published_date if generated_at not present."""
        articles = [
            {"published_date": "2025-01-20T12:00:00Z"},
            {"generated_at": "2025-01-15T12:00:00Z"},
        ]
        result = calculate_last_updated(articles)
        assert result.day == 20

    def test_ignores_invalid_dates(self):
        """Ignores articles with invalid or missing dates."""
        articles = [
            {"generated_at": "invalid"},
            {"generated_at": "2025-01-15T12:00:00Z"},
            {"title": "No date"},
        ]
        result = calculate_last_updated(articles)
        assert result.day == 15

    def test_all_invalid_dates_returns_none(self):
        """Returns None if no valid dates found."""
        articles = [
            {"generated_at": "invalid"},
            {"title": "No date"},
        ]
        result = calculate_last_updated(articles)
        assert result is None


class TestPrepareArticlesForDisplay:
    """Tests for the combined prepare function."""

    def test_empty_list(self):
        """Empty list returns empty list."""
        result = prepare_articles_for_display([])
        assert result == []

    def test_deduplicates_and_sorts(self):
        """Deduplicates and sorts articles correctly."""
        articles = [
            {"id": "1", "title": "Old v1", "generated_at": "2025-01-01T00:00:00Z"},
            {"id": "2", "title": "New", "generated_at": "2025-01-03T00:00:00Z"},
            {"id": "1", "title": "Old v2", "generated_at": "2025-01-02T00:00:00Z"},
            {"id": "3", "title": "Middle", "generated_at": "2025-01-02T12:00:00Z"},
        ]
        result = prepare_articles_for_display(articles)

        # Should have 3 unique articles
        assert len(result) == 3

        # Should be sorted newest first
        assert result[0]["title"] == "New"
        assert result[1]["title"] == "Middle"

        # Should keep newer version of duplicate
        old_article = [a for a in result if a["id"] == "1"][0]
        assert old_article["title"] == "Old v2"

    def test_preserves_all_article_fields(self):
        """All article fields are preserved through processing."""
        articles = [
            {
                "id": "1",
                "title": "Test",
                "content": "Content here",
                "source": "reddit",
                "quality_score": 0.95,
                "generated_at": "2025-01-01T00:00:00Z",
            }
        ]
        result = prepare_articles_for_display(articles)

        assert result[0]["title"] == "Test"
        assert result[0]["content"] == "Content here"
        assert result[0]["source"] == "reddit"
        assert result[0]["quality_score"] == 0.95


class TestEdgeCases:
    """Edge case tests for article processing."""

    def test_datetime_objects_vs_strings(self):
        """Handles both datetime objects and ISO strings."""
        dt_obj = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        articles = [
            {"id": "1", "title": "Object", "generated_at": dt_obj},
            {"id": "2", "title": "String", "generated_at": "2025-01-10T12:00:00Z"},
        ]
        result = sort_articles_by_date(articles)
        assert result[0]["title"] == "Object"

    def test_iso_format_with_z_suffix(self):
        """Handles ISO format with 'Z' suffix correctly."""
        articles = [{"generated_at": "2025-01-15T12:00:00Z"}]
        result = calculate_last_updated(articles)
        assert result is not None
        assert result.day == 15

    def test_large_list_performance(self):
        """Handles large lists efficiently."""
        articles = [
            {
                "id": str(i),
                "title": f"Article {i}",
                "generated_at": f"2025-01-{(i % 28) + 1:02d}T12:00:00Z",
            }
            for i in range(1000)
        ]
        result = prepare_articles_for_display(articles)
        assert len(result) == 1000  # All unique
        # Verify it's sorted
        assert result[0]["generated_at"] > result[-1]["generated_at"]

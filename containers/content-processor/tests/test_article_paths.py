"""
Blackbox contract tests for article blob path generation.

Tests verify the contract: paths must follow articles/YYYY-MM-DD/slug.ext format
and be queryable by date prefix. No internal implementation testing.
"""

import pytest
from utils.blob_utils import (
    generate_articles_markdown_blob_path,
    generate_articles_processed_blob_path,
)


class TestProcessedArticlePaths:
    """Contract: processed articles must be at articles/YYYY-MM-DD/slug.json"""

    def test_contract_path_format_with_iso_timestamp(self):
        """Verify path format with ISO 8601 timestamp."""
        article = {
            "slug": "saturn-moon-potential-for-life-discovery",
            "published_date": "2025-10-13T09:06:54+00:00",
        }
        path = generate_articles_processed_blob_path(article)

        # Contract: articles/YYYY-MM-DD/slug.json
        assert (
            path == "articles/2025-10-13/saturn-moon-potential-for-life-discovery.json"
        )

    def test_contract_path_format_with_date_string(self):
        """Verify path format with YYYY-MM-DD date string."""
        article = {"slug": "ai-breakthrough", "published_date": "2025-10-13"}
        path = generate_articles_processed_blob_path(article)

        assert path == "articles/2025-10-13/ai-breakthrough.json"

    def test_contract_queryable_by_date_prefix(self):
        """Contract: paths must be queryable by date (blob list --prefix)."""
        article = {"slug": "any-article", "published_date": "2025-10-13T14:30:00Z"}
        path = generate_articles_processed_blob_path(article)

        # Must support: list blobs with prefix="articles/2025-10-13/"
        assert path.startswith("articles/2025-10-13/")
        assert path.endswith(".json")

    def test_contract_date_extraction_from_various_iso_formats(self):
        """Contract: handle various ISO 8601 timestamp formats."""
        test_cases = [
            ("2025-10-13T09:06:54+00:00", "2025-10-13"),
            ("2025-10-13T09:06:54Z", "2025-10-13"),
            ("2025-10-13T09:06:54.123456Z", "2025-10-13"),
            ("2025-10-13", "2025-10-13"),
        ]

        for timestamp, expected_date in test_cases:
            article = {"slug": "test", "published_date": timestamp}
            path = generate_articles_processed_blob_path(article)
            assert f"articles/{expected_date}/" in path


class TestMarkdownArticlePaths:
    """Contract: markdown articles must be at articles/YYYY-MM-DD/slug.md"""

    def test_contract_path_format_with_iso_timestamp(self):
        """Verify markdown path format with ISO 8601 timestamp."""
        article = {
            "slug": "saturn-moon-potential",
            "published_date": "2025-10-13T09:06:54+00:00",
        }
        path = generate_articles_markdown_blob_path(article)

        # Contract: articles/YYYY-MM-DD/slug.md
        assert path == "articles/2025-10-13/saturn-moon-potential.md"

    def test_contract_path_format_with_date_string(self):
        """Verify markdown path format with date string."""
        article = {"slug": "ai-news", "published_date": "2025-10-13"}
        path = generate_articles_markdown_blob_path(article)

        assert path == "articles/2025-10-13/ai-news.md"

    def test_contract_markdown_derived_from_processed(self):
        """Contract: markdown path = processed path with .json → .md."""
        article = {"slug": "test-article", "published_date": "2025-10-13"}

        processed = generate_articles_processed_blob_path(article)
        markdown = generate_articles_markdown_blob_path(article)

        # Must be simple extension swap
        assert markdown == processed.replace(".json", ".md")


class TestPathConsistencyAcrossTimeZones:
    """Contract: date extraction must be timezone-agnostic."""

    def test_various_iso_timezone_formats(self):
        """Contract: extract date regardless of timezone offset."""
        timestamps = [
            "2025-10-13T09:06:54+00:00",  # UTC
            "2025-10-13T09:06:54-05:00",  # EST
            "2025-10-13T09:06:54+09:00",  # JST
            "2025-10-13T09:06:54Z",  # Zulu
        ]

        for ts in timestamps:
            article = {"slug": "test", "published_date": ts}
            path = generate_articles_processed_blob_path(article)
            # Should always extract 2025-10-13 portion
            assert "articles/2025-10-13/" in path


class TestPathEdgeCases:
    """Contract: handle edge cases gracefully."""

    def test_missing_slug_uses_fallback(self):
        """Contract: missing slug uses 'unknown' fallback."""
        article = {"published_date": "2025-10-13T09:06:54+00:00"}
        path = generate_articles_processed_blob_path(article)

        assert "unknown.json" in path

    def test_slug_with_url_safe_characters(self):
        """Contract: preserve URL-safe slugs (alphanumeric, dash, underscore)."""
        article = {
            "slug": "article-with-dashes_and_underscores-123",
            "published_date": "2025-10-13",
        }
        path = generate_articles_processed_blob_path(article)

        assert "article-with-dashes_and_underscores-123" in path

    def test_full_article_result_object(self):
        """Contract: work with complete article result data from processor."""
        article = {
            "slug": "article-slug",
            "published_date": "2025-10-13T15:30:00Z",
            "title": "Article Title",
            "content": "Full article content...",
            "topic_id": "topic_123",
            "word_count": 3500,
            "quality_score": 0.85,
            "cost": 0.042,
            "source_metadata": {"source": "reddit"},
        }
        path = generate_articles_processed_blob_path(article)

        # Should extract what it needs, ignore extra fields
        assert path == "articles/2025-10-13/article-slug.json"

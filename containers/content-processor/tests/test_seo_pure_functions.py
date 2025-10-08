"""
Tests for SEO Metadata Generation - Pure Functions

Tests all SEO generation functions with comprehensive test cases.
Validates that functions are pure (same input → same output, no side effects).

Standards: PEP 8, type hints, comprehensive coverage
"""

from datetime import datetime

import pytest
from seo import (
    create_seo_metadata,
    generate_article_id,
    generate_article_url,
    generate_filename,
    generate_seo_title,
    generate_slug,
)


class TestGenerateSlug:
    """Test slug generation from titles."""

    def test_basic_slug_generation(self) -> None:
        """Test basic title to slug conversion."""
        assert generate_slug("How AI Transforms Dev") == "how-ai-transforms-dev"
        assert generate_slug("Test Article Title") == "test-article-title"

    def test_slug_removes_punctuation(self) -> None:
        """Test that punctuation is removed."""
        assert generate_slug("Python 3.12 Released!") == "python-312-released"
        assert generate_slug("What's New?") == "whats-new"
        assert generate_slug("Machine Learning: A Guide") == "machine-learning-a-guide"

    def test_slug_handles_special_characters(self) -> None:
        """Test handling of special characters."""
        assert generate_slug("C++ & Python") == "c-python"
        assert generate_slug("AI/ML Engineer") == "aiml-engineer"
        assert generate_slug("@mentions #hashtags") == "mentions-hashtags"

    def test_slug_handles_multiple_spaces(self) -> None:
        """Test that multiple spaces become single hyphen."""
        assert generate_slug("Too    Many     Spaces") == "too-many-spaces"

    def test_slug_strips_leading_trailing_hyphens(self) -> None:
        """Test that leading/trailing hyphens are removed."""
        assert generate_slug("- Leading Hyphen") == "leading-hyphen"
        assert generate_slug("Trailing Hyphen -") == "trailing-hyphen"

    def test_slug_empty_input(self) -> None:
        """Test empty input returns empty string."""
        assert generate_slug("") == ""
        assert generate_slug("   ") == ""

    def test_slug_non_string_input(self) -> None:
        """Test non-string input returns empty string."""
        assert generate_slug(None) == ""  # type: ignore
        assert generate_slug(123) == ""  # type: ignore

    def test_slug_unicode_characters(self) -> None:
        """Test handling of unicode characters."""
        # Unicode is preserved (modern URLs support it)
        slug = generate_slug("Café Münchën")
        assert slug == "café-münchën"

    def test_slug_is_deterministic(self) -> None:
        """Test that same input always produces same output (purity)."""
        title = "Test Deterministic Behavior"
        slug1 = generate_slug(title)
        slug2 = generate_slug(title)
        slug3 = generate_slug(title)
        assert slug1 == slug2 == slug3


class TestGenerateSeoTitle:
    """Test SEO title generation."""

    def test_short_title_unchanged(self) -> None:
        """Test that short titles are not modified."""
        assert generate_seo_title("Short Title") == "Short Title"
        assert generate_seo_title("Test") == "Test"

    def test_long_title_truncated(self) -> None:
        """Test that long titles are truncated to 60 chars."""
        long_title = "This is a very long title that definitely exceeds the sixty character limit"
        result = generate_seo_title(long_title)
        assert len(result) <= 60
        assert result.endswith("...")

    def test_title_at_max_length(self) -> None:
        """Test title exactly at max length."""
        title = "A" * 60
        assert generate_seo_title(title) == title

    def test_empty_input(self) -> None:
        """Test empty input returns empty string."""
        assert generate_seo_title("") == ""

    def test_custom_max_length(self) -> None:
        """Test custom max length parameter."""
        title = "This is a test title"
        assert len(generate_seo_title(title, max_length=10)) <= 10

    def test_seo_title_is_deterministic(self) -> None:
        """Test that same input produces same output (purity)."""
        title = "Test SEO Title Generation"
        seo1 = generate_seo_title(title)
        seo2 = generate_seo_title(title)
        assert seo1 == seo2


class TestGenerateFilename:
    """Test filename generation."""

    def test_basic_filename_generation(self) -> None:
        """Test basic filename format."""
        date = datetime(2025, 10, 8)
        filename = generate_filename(date, "test-article")
        assert filename == "20251008-test-article.md"

    def test_custom_extension(self) -> None:
        """Test custom file extension."""
        date = datetime(2025, 10, 8)
        assert generate_filename(date, "test", "json") == "20251008-test.json"
        assert generate_filename(date, "test", "html") == "20251008-test.html"

    def test_different_dates(self) -> None:
        """Test various date formats."""
        assert generate_filename(datetime(2025, 1, 1), "test") == "20250101-test.md"
        assert generate_filename(datetime(2025, 12, 31), "test") == "20251231-test.md"

    def test_invalid_date_raises_error(self) -> None:
        """Test that invalid date raises TypeError."""
        with pytest.raises(TypeError):
            generate_filename("2025-10-08", "test")  # type: ignore

    def test_empty_slug_raises_error(self) -> None:
        """Test that empty slug raises ValueError."""
        with pytest.raises(ValueError):
            generate_filename(datetime(2025, 10, 8), "")

    def test_filename_is_deterministic(self) -> None:
        """Test that same inputs produce same output (purity)."""
        date = datetime(2025, 10, 8)
        fn1 = generate_filename(date, "test")
        fn2 = generate_filename(date, "test")
        assert fn1 == fn2


class TestGenerateArticleUrl:
    """Test article URL generation."""

    def test_basic_url_generation(self) -> None:
        """Test basic URL format."""
        date = datetime(2025, 10, 8)
        url = generate_article_url(date, "test-article")
        assert url == "/2025/10/test-article"

    def test_single_digit_month(self) -> None:
        """Test that single-digit months are zero-padded."""
        date = datetime(2025, 3, 15)
        url = generate_article_url(date, "test")
        assert url == "/2025/03/test"

    def test_different_years(self) -> None:
        """Test various years."""
        assert generate_article_url(datetime(2024, 1, 1), "test") == "/2024/01/test"
        assert generate_article_url(datetime(2026, 12, 31), "test") == "/2026/12/test"

    def test_invalid_date_raises_error(self) -> None:
        """Test that invalid date raises TypeError."""
        with pytest.raises(TypeError):
            generate_article_url("2025-10-08", "test")  # type: ignore

    def test_url_is_deterministic(self) -> None:
        """Test that same inputs produce same output (purity)."""
        date = datetime(2025, 10, 8)
        url1 = generate_article_url(date, "test")
        url2 = generate_article_url(date, "test")
        assert url1 == url2


class TestGenerateArticleId:
    """Test article ID generation."""

    def test_basic_article_id(self) -> None:
        """Test basic article ID format."""
        date = datetime(2025, 10, 8)
        article_id = generate_article_id(date, "test-article")
        assert article_id == "20251008-test-article"

    def test_article_id_different_dates(self) -> None:
        """Test various dates."""
        assert generate_article_id(datetime(2025, 1, 1), "test") == "20250101-test"
        assert generate_article_id(datetime(2025, 12, 31), "test") == "20251231-test"

    def test_invalid_date_raises_error(self) -> None:
        """Test that invalid date raises TypeError."""
        with pytest.raises(TypeError):
            generate_article_id("2025-10-08", "test")  # type: ignore

    def test_article_id_is_deterministic(self) -> None:
        """Test that same inputs produce same output (purity)."""
        date = datetime(2025, 10, 8)
        id1 = generate_article_id(date, "test")
        id2 = generate_article_id(date, "test")
        assert id1 == id2


class TestCreateSeoMetadata:
    """Test complete SEO metadata creation."""

    def test_complete_metadata_structure(self) -> None:
        """Test that all metadata fields are generated."""
        date = datetime(2025, 10, 8)
        metadata = create_seo_metadata("Test Article", date)

        # Verify all required fields present
        assert "slug" in metadata
        assert "seo_title" in metadata
        assert "filename" in metadata
        assert "url" in metadata
        assert "article_id" in metadata

    def test_metadata_values_correct(self) -> None:
        """Test that metadata values are correct."""
        date = datetime(2025, 10, 8)
        metadata = create_seo_metadata("How AI Transforms Development", date)

        assert metadata["slug"] == "how-ai-transforms-development"
        assert metadata["seo_title"] == "How AI Transforms Development"
        assert metadata["filename"] == "20251008-how-ai-transforms-development.md"
        assert metadata["url"] == "/2025/10/how-ai-transforms-development"
        assert metadata["article_id"] == "20251008-how-ai-transforms-development"

    def test_metadata_with_seo_title_override(self) -> None:
        """Test custom SEO title override."""
        date = datetime(2025, 10, 8)
        metadata = create_seo_metadata(
            "Test Article", date, seo_title_override="Custom SEO Title"
        )

        assert metadata["seo_title"] == "Custom SEO Title"

    def test_metadata_empty_title_raises_error(self) -> None:
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError):
            create_seo_metadata("", datetime(2025, 10, 8))

    def test_metadata_invalid_date_raises_error(self) -> None:
        """Test that invalid date raises TypeError."""
        with pytest.raises(TypeError):
            create_seo_metadata("Test", "2025-10-08")  # type: ignore

    def test_metadata_is_deterministic(self) -> None:
        """Test that same inputs produce same output (purity)."""
        date = datetime(2025, 10, 8)
        meta1 = create_seo_metadata("Test Article", date)
        meta2 = create_seo_metadata("Test Article", date)
        assert meta1 == meta2

    def test_metadata_long_title_truncates_seo_title(self) -> None:
        """Test that long titles are truncated in SEO title."""
        date = datetime(2025, 10, 8)
        long_title = "A" * 100
        metadata = create_seo_metadata(long_title, date)

        # SEO title should be truncated
        assert len(metadata["seo_title"]) <= 60
        # But slug and other fields use full title
        assert len(metadata["slug"]) == 100

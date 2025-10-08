"""
Tests for pure functional metadata generation.

Black box testing: validates inputs and outputs only, not implementation.

Contract Version: 1.0.0
"""

from datetime import datetime, timezone

import pytest
from metadata import (
    create_article_metadata,
    generate_article_filename,
    generate_article_url,
    needs_translation,
    parse_date_slug,
    truncate_with_word_boundary,
    validate_description_length,
    validate_language_code,
    validate_metadata_structure,
    validate_title_length,
)


class TestCreateArticleMetadata:
    """Test article metadata creation."""

    def test_minimal_metadata(self):
        """Create metadata with minimal required fields."""
        meta = create_article_metadata(
            original_title="Test",
            clean_title="Test Article",
            slug="test-article",
            seo_description="Test description",
            language="en",
            date_slug="2025-10-08",
            filename="articles/2025-10-08-test-article.html",
            url="/articles/2025-10-08-test-article.html",
        )
        assert meta["original_title"] == "Test"
        assert meta["title"] == "Test Article"
        assert meta["translated"] is False
        assert meta["metadata_cost_usd"] == 0.0

    def test_complete_metadata(self):
        """Create metadata with all fields."""
        meta = create_article_metadata(
            original_title="米政権内",
            clean_title="US Administration",
            slug="us-administration",
            seo_description="Article about US admin",
            language="ja",
            date_slug="2025-10-08",
            filename="articles/2025-10-08-us-administration.html",
            url="/articles/2025-10-08-us-administration.html",
            translated=True,
            metadata_cost_usd=0.00015,
            metadata_tokens=50,
        )
        assert meta["translated"] is True
        assert meta["language"] == "ja"
        assert meta["metadata_cost_usd"] == 0.00015
        assert meta["metadata_tokens"] == 50

    def test_metadata_has_all_keys(self):
        """Metadata contains all expected keys."""
        meta = create_article_metadata(
            original_title="Test",
            clean_title="Test",
            slug="test",
            seo_description="Desc",
            language="en",
            date_slug="2025-10-08",
            filename="test.html",
            url="/test.html",
        )
        expected_keys = [
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
        assert all(key in meta for key in expected_keys)


class TestValidateMetadataStructure:
    """Test metadata structure validation."""

    def test_valid_metadata(self):
        """Valid metadata passes validation."""
        meta = {
            "original_title": "Test",
            "title": "Test",
            "slug": "test",
            "seo_description": "Desc",
            "language": "en",
            "translated": False,
            "date_slug": "2025-10-08",
            "filename": "test.html",
            "url": "/test.html",
            "metadata_cost_usd": 0.0,
            "metadata_tokens": 0,
        }
        assert validate_metadata_structure(meta) is True

    def test_missing_field(self):
        """Missing required field fails validation."""
        meta = {"title": "Test", "slug": "test"}
        assert validate_metadata_structure(meta) is False

    def test_empty_dict(self):
        """Empty dict fails validation."""
        assert validate_metadata_structure({}) is False


class TestNeedsTranslation:
    """Test translation detection."""

    def test_ascii_text(self):
        """ASCII text doesn't need translation."""
        assert needs_translation("Hello World") is False

    def test_japanese_text(self):
        """Japanese text needs translation."""
        assert needs_translation("米政権内の対中強硬派に焦り") is True

    def test_french_accents(self):
        """French accents need translation."""
        assert needs_translation("Café Résumé") is True

    def test_empty_string(self):
        """Empty string doesn't need translation."""
        assert needs_translation("") is False

    def test_mixed_content(self):
        """Mixed ASCII and non-ASCII needs translation."""
        assert needs_translation("Hello 世界") is True


class TestParseDateSlug:
    """Test date parsing."""

    def test_iso_with_time(self):
        """ISO 8601 with time component."""
        assert parse_date_slug("2025-10-06T12:30:00Z") == "2025-10-06"

    def test_iso_date_only(self):
        """ISO date without time."""
        assert parse_date_slug("2025-10-06") == "2025-10-06"

    def test_with_timezone(self):
        """ISO date with timezone."""
        assert parse_date_slug("2025-10-06T12:30:00+05:00") == "2025-10-06"

    def test_invalid_date_with_fallback(self):
        """Invalid date uses fallback."""
        fallback = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = parse_date_slug("invalid-date", fallback)
        assert result == "2025-01-01"

    def test_invalid_date_without_fallback(self):
        """Invalid date without fallback uses current date."""
        result = parse_date_slug("invalid-date")
        assert len(result) == 10  # YYYY-MM-DD format
        assert result.count("-") == 2


class TestGenerateArticleFilename:
    """Test filename generation."""

    def test_basic_filename(self):
        """Generate basic HTML filename."""
        filename = generate_article_filename("2025-10-08", "test-article")
        assert filename == "articles/2025-10-08-test-article.html"

    def test_custom_extension(self):
        """Generate filename with custom extension."""
        filename = generate_article_filename("2025-10-08", "test", "md")
        assert filename == "articles/2025-10-08-test.md"

    def test_long_slug_raises_error(self):
        """Very long slug raises ValueError."""
        long_slug = "a" * 100
        with pytest.raises(ValueError, match="too long"):
            generate_article_filename("2025-10-08", long_slug)

    def test_filename_under_limit(self):
        """Filename under 100 chars succeeds."""
        slug = "a" * 50  # Should fit
        filename = generate_article_filename("2025-10-08", slug)
        assert len(filename) < 100


class TestGenerateArticleUrl:
    """Test URL generation."""

    def test_basic_url(self):
        """Generate basic article URL."""
        url = generate_article_url("2025-10-08", "test-article")
        assert url == "/articles/2025-10-08-test-article.html"

    def test_custom_extension(self):
        """Generate URL with custom extension."""
        url = generate_article_url("2025-10-08", "test", "md")
        assert url == "/articles/2025-10-08-test.md"

    def test_url_starts_with_slash(self):
        """URL always starts with /."""
        url = generate_article_url("2025-10-08", "test")
        assert url.startswith("/")


class TestTruncateWithWordBoundary:
    """Test word boundary truncation."""

    def test_no_truncation_needed(self):
        """Text shorter than max returns unchanged."""
        text = "Short text"
        assert truncate_with_word_boundary(text, 100) == "Short text"

    def test_truncate_at_word(self):
        """Truncates at word boundary."""
        text = "Hello world this is a test"
        result = truncate_with_word_boundary(text, 15)
        assert result == "Hello world"
        assert len(result) <= 15

    def test_no_spaces(self):
        """Text with no spaces truncates hard."""
        text = "NoSpacesHereAtAll"
        result = truncate_with_word_boundary(text, 10)
        assert result == "NoSpacesHe"
        assert len(result) == 10

    def test_empty_string(self):
        """Empty string returns empty."""
        assert truncate_with_word_boundary("", 10) == ""

    def test_single_long_word(self):
        """Single word longer than limit truncates."""
        result = truncate_with_word_boundary("Supercalifragilisticexpialidocious", 10)
        assert len(result) == 10


class TestValidateTitleLength:
    """Test title length validation."""

    def test_valid_title(self):
        """Title in valid range passes."""
        assert validate_title_length("Good Title Length") is True

    def test_too_short(self):
        """Title too short fails."""
        assert validate_title_length("Short") is False

    def test_too_long(self):
        """Title too long fails."""
        long_title = "a" * 80
        assert validate_title_length(long_title) is False

    def test_custom_limits(self):
        """Custom limits work correctly."""
        assert validate_title_length("Test", min_length=3, max_length=10) is True
        assert validate_title_length("Test", min_length=5, max_length=10) is False

    def test_empty_string(self):
        """Empty string fails."""
        assert validate_title_length("") is False


class TestValidateDescriptionLength:
    """Test description length validation."""

    def test_valid_description(self):
        """Description in valid range passes."""
        desc = "This is a good SEO description that is between one hundred and one hundred seventy characters long for optimal display."
        assert validate_description_length(desc) is True

    def test_too_short(self):
        """Description too short fails."""
        assert validate_description_length("Too short") is False

    def test_too_long(self):
        """Description too long fails."""
        long_desc = "a" * 200
        assert validate_description_length(long_desc) is False

    def test_custom_limits(self):
        """Custom limits work correctly."""
        desc = "This is exactly fifty characters for testing ok!"
        assert validate_description_length(desc, min_length=40, max_length=60) is True

    def test_empty_string(self):
        """Empty string fails."""
        assert validate_description_length("") is False


class TestValidateLanguageCode:
    """Test language code validation."""

    def test_valid_codes(self):
        """Valid ISO 639-1 codes pass."""
        assert validate_language_code("en") is True
        assert validate_language_code("ja") is True
        assert validate_language_code("fr") is True
        assert validate_language_code("es") is True

    def test_invalid_length(self):
        """Codes not 2 characters fail."""
        assert validate_language_code("eng") is False
        assert validate_language_code("e") is False

    def test_invalid_characters(self):
        """Non-alphabetic characters fail."""
        assert validate_language_code("e1") is False
        assert validate_language_code("e-") is False

    def test_uppercase_fails(self):
        """Uppercase codes fail (must be lowercase)."""
        assert validate_language_code("EN") is False

    def test_empty_string(self):
        """Empty string fails."""
        assert validate_language_code("") is False


class TestPurityAndDeterminism:
    """Test that functions are pure (deterministic, no side effects)."""

    def test_metadata_creation_determinism(self):
        """Same inputs produce same metadata."""
        meta1 = create_article_metadata(
            "Test",
            "Test",
            "test",
            "Desc",
            "en",
            "2025-10-08",
            "test.html",
            "/test.html",
        )
        meta2 = create_article_metadata(
            "Test",
            "Test",
            "test",
            "Desc",
            "en",
            "2025-10-08",
            "test.html",
            "/test.html",
        )
        assert meta1 == meta2

    def test_translation_check_determinism(self):
        """Same title always returns same result."""
        result1 = needs_translation("米政権内")
        result2 = needs_translation("米政権内")
        assert result1 == result2 is True

    def test_date_parsing_determinism(self):
        """Same date string always returns same result."""
        result1 = parse_date_slug("2025-10-06T12:30:00Z")
        result2 = parse_date_slug("2025-10-06T12:30:00Z")
        assert result1 == result2 == "2025-10-06"

    def test_filename_generation_determinism(self):
        """Same inputs produce same filename."""
        file1 = generate_article_filename("2025-10-08", "test")
        file2 = generate_article_filename("2025-10-08", "test")
        assert file1 == file2

    def test_validation_determinism(self):
        """Same input always returns same validation result."""
        result1 = validate_title_length("Good Title")
        result2 = validate_title_length("Good Title")
        assert result1 == result2 is True

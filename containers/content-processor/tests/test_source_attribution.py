"""
Tests for source attribution in content generation.

Ensures that source URLs, platforms, authors, and dates are properly
preserved through the content generation pipeline.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from content_generation import ContentGenerator, GeneratedContent, GenerationRequest


class TestSourceAttribution:
    """Test suite for source attribution preservation."""

    @pytest.fixture
    def generator(self):
        """Create ContentGenerator instance."""
        return ContentGenerator()

    def test_extract_source_attribution_with_all_fields(self, generator):
        """Test extraction when all attribution fields are present."""
        sources = [
            {
                "url": "https://reddit.com/r/technology/abc123",
                "source": "reddit",
                "author": "tech_user",
                "created_at": "2025-10-01T12:00:00Z",
                "title": "Amazing Tech Discovery",
                "summary": "This is a great tech article",
            }
        ]

        attribution = generator._extract_source_attribution(sources)

        assert attribution["original_url"] == "https://reddit.com/r/technology/abc123"
        assert attribution["source_platform"] == "reddit"
        assert attribution["author"] == "tech_user"
        assert attribution["original_date"] == "2025-10-01T12:00:00Z"

    def test_extract_source_attribution_with_timestamp(self, generator):
        """Test extraction with Unix timestamp date."""
        sources = [
            {
                "url": "https://example.com/article",
                "source": "rss",
                "author": "John Doe",
                "created_utc": 1696118400,  # Unix timestamp
                "title": "Test Article",
                "summary": "Test content",
            }
        ]

        attribution = generator._extract_source_attribution(sources)

        assert attribution["original_url"] == "https://example.com/article"
        assert attribution["source_platform"] == "rss"
        assert attribution["author"] == "John Doe"
        # Timestamp should be converted to ISO format
        assert attribution["original_date"] is not None
        assert "2023-10-01" in attribution["original_date"]

    def test_extract_source_attribution_with_missing_fields(self, generator):
        """Test extraction with missing optional fields."""
        sources = [
            {
                "url": "https://mastodon.social/@user/123",
                "source": "mastodon",
                "title": "Mastodon Post",
                "summary": "Interesting thoughts",
                # No author or date
            }
        ]

        attribution = generator._extract_source_attribution(sources)

        assert attribution["original_url"] == "https://mastodon.social/@user/123"
        assert attribution["source_platform"] == "mastodon"
        assert attribution["author"] is None
        assert attribution["original_date"] is None

    def test_extract_source_attribution_with_alternative_field_names(self, generator):
        """Test extraction with alternative field names (link, source_type, etc)."""
        sources = [
            {
                "link": "https://arstechnica.com/article",  # Alternative to 'url'
                "source_type": "web",  # Alternative to 'source'
                "author": "Staff Writer",
                "published": "2025-09-15T10:30:00Z",  # Alternative to 'created_at'
                "title": "Web Article",
                "summary": "Article content",
            }
        ]

        attribution = generator._extract_source_attribution(sources)

        assert attribution["original_url"] == "https://arstechnica.com/article"
        assert attribution["source_platform"] == "web"
        assert attribution["author"] == "Staff Writer"
        assert attribution["original_date"] == "2025-09-15T10:30:00Z"

    def test_extract_source_attribution_with_empty_sources(self, generator):
        """Test extraction with empty sources list."""
        sources = []

        attribution = generator._extract_source_attribution(sources)

        assert attribution["original_url"] is None
        assert attribution["source_platform"] is None
        assert attribution["author"] is None
        assert attribution["original_date"] is None

    def test_extract_source_attribution_uses_first_source(self, generator):
        """Test that extraction uses the first (primary) source."""
        sources = [
            {
                "url": "https://primary.com/article",
                "source": "primary",
                "author": "Primary Author",
                "created_at": "2025-10-01T12:00:00Z",
            },
            {
                "url": "https://secondary.com/article",
                "source": "secondary",
                "author": "Secondary Author",
                "created_at": "2025-09-30T12:00:00Z",
            },
        ]

        attribution = generator._extract_source_attribution(sources)

        # Should use first source
        assert attribution["original_url"] == "https://primary.com/article"
        assert attribution["source_platform"] == "primary"
        assert attribution["author"] == "Primary Author"

    def test_extract_source_attribution_normalizes_platform_name(self, generator):
        """Test that platform names are normalized to lowercase."""
        sources = [
            {
                "url": "https://example.com",
                "source": "REDDIT",  # Uppercase
                "title": "Test",
            }
        ]

        attribution = generator._extract_source_attribution(sources)

        assert attribution["source_platform"] == "reddit"  # Lowercase

    @pytest.mark.asyncio
    async def test_generate_content_includes_attribution(self, generator):
        """Test that generate_content includes source attribution in output."""
        # Mock the Azure OpenAI call using AsyncMock
        generator._generate_with_azure_openai = AsyncMock(
            return_value="TITLE: Test Article\nCONTENT: This is test content with enough words to meet requirements."
        )

        request = GenerationRequest(
            topic="Test Topic",
            content_type="tldr",
            writer_personality="professional",
            sources=[
                {
                    "url": "https://reddit.com/r/test/123",
                    "source": "reddit",
                    "author": "test_user",
                    "created_at": "2025-10-05T10:00:00Z",
                    "title": "Test Post",
                    "summary": "Test summary with enough content",
                }
            ],
        )

        result = await generator.generate_content(request)

        assert isinstance(result, GeneratedContent)
        assert result.original_url == "https://reddit.com/r/test/123"
        assert result.source_platform == "reddit"
        assert result.author == "test_user"
        assert result.original_date == "2025-10-05T10:00:00Z"

    @pytest.mark.asyncio
    async def test_generate_content_handles_missing_sources(self, generator):
        """Test that generate_content handles missing sources gracefully."""
        # Mock the Azure OpenAI call using AsyncMock
        generator._generate_with_azure_openai = AsyncMock(
            return_value="TITLE: Test Article\nCONTENT: This is test content."
        )

        request = GenerationRequest(
            topic="Test Topic",
            content_type="tldr",
            writer_personality="professional",
            sources=[],  # No sources
        )

        result = await generator.generate_content(request)

        assert isinstance(result, GeneratedContent)
        assert result.original_url is None
        assert result.source_platform is None
        assert result.author is None
        assert result.original_date is None


class TestSourceAttributionEdgeCases:
    """Test edge cases and error handling for source attribution."""

    @pytest.fixture
    def generator(self):
        """Create ContentGenerator instance."""
        return ContentGenerator()

    def test_handle_invalid_timestamp(self, generator):
        """Test handling of invalid timestamp values."""
        sources = [
            {
                "url": "https://example.com",
                "source": "web",
                # Invalid timestamp (far future)
                "created_utc": 99999999999999,
            }
        ]

        attribution = generator._extract_source_attribution(sources)

        # Should handle gracefully and return None for unreasonable timestamps
        assert attribution["original_date"] is None

    def test_handle_non_dict_source(self, generator):
        """Test handling of malformed source data."""
        sources = ["not a dict"]  # Invalid source format

        # Should not raise an exception
        try:
            attribution = generator._extract_source_attribution(sources)
            # Should return empty attribution since first item isn't a dict
            assert attribution["original_url"] is None
        except (AttributeError, TypeError):
            pytest.fail("Should handle non-dict sources gracefully")

    def test_handle_source_with_none_values(self, generator):
        """Test handling of None values in source fields."""
        sources = [
            {
                "url": None,
                "source": None,
                "author": None,
                "created_at": None,
            }
        ]

        attribution = generator._extract_source_attribution(sources)

        assert attribution["original_url"] is None
        assert attribution["source_platform"] is None
        assert attribution["author"] is None
        assert attribution["original_date"] is None

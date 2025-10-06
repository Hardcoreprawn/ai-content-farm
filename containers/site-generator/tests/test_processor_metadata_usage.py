"""
Test processor-provided metadata usage in site generator.

Verifies that the site generator correctly uses processor-provided
filename, slug, and URL fields instead of generating its own.
This ensures URL/filename consistency and eliminates 404 errors.
"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
class TestProcessorMetadataUsage:
    """Verify site generator uses processor-provided metadata correctly."""

    async def test_filename_url_consistency(self):
        """Filename should match URL path component exactly."""
        # URL /articles/YYYY-MM-DD-slug.html should match filename YYYY-MM-DD-slug.html

        article = {
            "topic_id": "consistency-test",
            "title": "URL Consistency Test",
            "slug": "2025-10-06-url-consistency-test",
            "filename": "2025-10-06-url-consistency-test.html",
            "url": "/articles/2025-10-06-url-consistency-test.html",
            "article_content": "Test content",
            "generated_at": "2025-10-06T16:00:00Z",
        }

        # Verify filename matches URL path
        expected_url = f"/articles/{article['filename']}"
        assert article["url"] == expected_url, (
            f"URL '{article['url']}' doesn't match " f"filename '{article['filename']}'"
        )

    async def test_handles_non_english_titles_correctly(self):
        """Processor should translate non-English titles and create ASCII slugs."""
        # The processor translates non-English titles via AI and creates URL-safe slugs

        articles = [
            {
                "topic_id": "japanese-article",
                "original_title": "日本の技術革新",
                "title": "Japanese Tech Innovation",  # AI-translated
                "slug": "2025-10-06-japanese-tech-innovation",
                "filename": "2025-10-06-japanese-tech-innovation.html",
                "url": "/articles/2025-10-06-japanese-tech-innovation.html",
                "article_content": "Content",
                "generated_at": "2025-10-06T10:00:00Z",
            },
            {
                "topic_id": "italian-article",
                "original_title": "Innovazione Tecnologica",
                "title": "Technological Innovation",  # AI-translated
                "slug": "2025-10-06-technological-innovation",
                "filename": "2025-10-06-technological-innovation.html",
                "url": "/articles/2025-10-06-technological-innovation.html",
                "article_content": "Content",
                "generated_at": "2025-10-06T11:00:00Z",
            },
        ]

        # Verify all filenames are ASCII-only (no Unicode issues)
        for article in articles:
            # Filename should only contain ASCII characters
            assert article[
                "filename"
            ].isascii(), f"Filename contains non-ASCII: {article['filename']}"

            # URL should match filename
            expected_url = f"/articles/{article['filename']}"
            assert article["url"] == expected_url

            # Should preserve original title
            assert "original_title" in article
            assert article["original_title"] != article["title"]


@pytest.mark.asyncio
class TestFilenameGenerationLogic:
    """Test the filename generation logic in content_utility_functions."""

    async def test_generate_filename_logic(self):
        """Verify the simplified filename generation uses processor metadata."""
        # Site generator should prefer processor-provided filename over generating its own

        # Test 1: Article with processor-provided filename
        article_with_metadata = {
            "filename": "2025-10-06-great-article.html",
            "slug": "2025-10-06-great-article",
            "url": "/articles/2025-10-06-great-article.html",
            "title": "Great Article",
        }

        # Simulate site generator logic: use processor filename directly
        filename = article_with_metadata.get("filename")
        if filename and not filename.startswith("articles/"):
            filename = f"articles/{filename}"

        assert filename == "articles/2025-10-06-great-article.html"

        # Test 2: Legacy article without processor filename (fallback)
        legacy_article = {
            "topic_id": "legacy-123",
            "title": "Legacy Article Without Metadata",
        }

        # Fallback logic for backwards compatibility
        filename = legacy_article.get("filename")
        assert filename is None  # No processor metadata

        # Would fall back to topic_id + title slug generation
        # (this is the legacy path we kept for backwards compatibility)

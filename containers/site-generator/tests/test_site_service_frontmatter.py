"""
Test suite for SiteService frontmatter parsing functionality.

This module tests the critical frontmatter parsing logic that extracts
metadata from markdown files for site generation.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from models import ArticleMetadata
from site_service import SiteService

from config import Config


class TestSiteServiceFrontmatter:
    """Test frontmatter parsing and article metadata extraction."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock(spec=Config)
        config.MARKDOWN_CONTENT_CONTAINER = "markdown-content"
        config.STATIC_SITES_CONTAINER = "static-sites"
        return config

    @pytest.fixture
    def mock_blob_client(self):
        """Create mock blob client."""
        return AsyncMock()

    @pytest.fixture
    def mock_content_manager(self):
        """Create mock content manager."""
        return AsyncMock()

    @pytest.fixture
    def mock_archive_manager(self):
        """Create mock archive manager."""
        return AsyncMock()

    @pytest.fixture
    def site_service(
        self, mock_blob_client, mock_config, mock_content_manager, mock_archive_manager
    ):
        """Create SiteService instance with mocked dependencies."""
        return SiteService(
            blob_client=mock_blob_client,
            config=mock_config,
            content_manager=mock_content_manager,
            archive_manager=mock_archive_manager,
        )

    def test_parse_markdown_frontmatter_success(self, site_service):
        """Test successful frontmatter parsing with all required fields."""
        markdown_content = """---
title: "Test Article Title"
slug: "test-article"
date: "2025-09-22"
time: "14:26:36"
summary: "Test article summary"
tags: ["tech", "ai-curated", "web"]
categories: ["tech", "ai-curated"]
source:
  name: "web"
  url: "https://example.com/test-article"
metadata:
  topic_id: "test_12345"
  word_count: 750
  quality_score: 0.85
  cost: 0.00125
  generated_at: "2025-09-22T14:26:36.123456+00:00"
published: true
---

# Test Article Content

This is the content of the test article.

## Section 1

Some content here.
"""

        result = site_service._parse_markdown_frontmatter("test.md", markdown_content)

        assert result is not None
        assert isinstance(result, ArticleMetadata)
        assert result.title == "Test Article Title"
        assert result.slug == "test-article"
        assert result.topic_id == "test_12345"
        assert result.word_count == 750
        assert result.quality_score == 0.85
        assert result.cost == 0.00125
        assert result.source == "web"
        assert result.original_url == "https://example.com/test-article"
        assert result.generated_at == datetime.fromisoformat(
            "2025-09-22T14:26:36.123456+00:00"
        )
        assert "This is the content of the test article." in result.content

    def test_parse_markdown_frontmatter_missing_metadata(self, site_service):
        """Test frontmatter parsing with missing metadata section."""
        markdown_content = """---
title: "Test Article"
slug: "test"
source:
  name: "web"
  url: "https://example.com/test"
published: true
---

Content here.
"""

        result = site_service._parse_markdown_frontmatter("test.md", markdown_content)

        assert result is not None
        assert result.title == "Test Article"
        assert result.slug == "test"
        assert result.topic_id == "test"  # Should default to filename without .md
        assert result.word_count == 0  # Should default to 0
        assert result.quality_score == 0.0  # Should default to 0.0
        assert result.cost == 0.0  # Should default to 0.0
        assert result.source == "web"
        assert result.original_url == "https://example.com/test"

    def test_parse_markdown_frontmatter_missing_source(self, site_service):
        """Test frontmatter parsing with missing source section."""
        markdown_content = """---
title: "Test Article"
slug: "test"
metadata:
  topic_id: "test_123"
  word_count: 500
  quality_score: 0.75
  cost: 0.001
  generated_at: "2025-09-22T14:26:36+00:00"
published: true
---

Content here.
"""

        result = site_service._parse_markdown_frontmatter("test.md", markdown_content)

        assert result is not None
        assert result.source == "unknown"  # Should default to "unknown"
        assert result.original_url == ""  # Should default to empty string

    def test_parse_markdown_frontmatter_no_frontmatter(self, site_service):
        """Test parsing content without frontmatter."""
        markdown_content = """# Just a title

Some content without frontmatter.
"""

        result = site_service._parse_markdown_frontmatter("test.md", markdown_content)

        assert result is None

    def test_parse_markdown_frontmatter_invalid_yaml(self, site_service):
        """Test parsing with invalid YAML frontmatter."""
        markdown_content = """---
title: "Test Article
invalid_yaml: [unclosed bracket
---

Content here.
"""

        result = site_service._parse_markdown_frontmatter("test.md", markdown_content)

        assert result is None

    def test_parse_markdown_frontmatter_invalid_datetime(self, site_service):
        """Test parsing with invalid datetime format."""
        markdown_content = """---
title: "Test Article"
metadata:
  topic_id: "test_123"
  generated_at: "invalid-datetime"
source:
  name: "web"
  url: "https://example.com/test"
---

Content here.
"""

        # This should handle the datetime parsing gracefully
        result = site_service._parse_markdown_frontmatter("test.md", markdown_content)

        # The function should handle datetime parsing errors and either use a default
        # or fail gracefully depending on implementation
        # For now, we expect it to handle this case without crashing

    @pytest.mark.asyncio
    async def test_get_markdown_articles_integration(
        self, site_service, mock_blob_client
    ):
        """Test the complete flow of getting and parsing markdown articles."""
        # Mock the blob listing
        mock_blob_client.list_blobs.return_value = [
            {"name": "article1.md"},
            {"name": "article2.md"},
            {"name": "not-markdown.txt"},  # Should be ignored
        ]

        # Mock the blob content download
        article1_content = """---
title: "Article 1"
slug: "article-1"
metadata:
  topic_id: "test_001"
  word_count: 600
  quality_score: 0.8
  cost: 0.001
  generated_at: "2025-09-22T14:26:36+00:00"
source:
  name: "web"
  url: "https://example.com/article1"
---

Article 1 content.
"""

        article2_content = """---
title: "Article 2"
slug: "article-2"
metadata:
  topic_id: "test_002"
  word_count: 800
  quality_score: 0.9
  cost: 0.0015
  generated_at: "2025-09-22T15:30:00+00:00"
source:
  name: "rss"
  url: "https://example.com/article2"
---

Article 2 content.
"""

        mock_blob_client.download_text.side_effect = [
            article1_content,
            article2_content,
        ]

        # Test the method
        articles = await site_service._get_markdown_articles()

        # Verify results
        assert len(articles) == 2
        assert articles[0].title == "Article 1"
        assert articles[0].topic_id == "test_001"
        assert articles[1].title == "Article 2"
        assert articles[1].topic_id == "test_002"

        # Verify blob client was called correctly
        mock_blob_client.list_blobs.assert_called_once_with(
            container_name="markdown-content"
        )
        assert mock_blob_client.download_text.call_count == 2

    @pytest.mark.asyncio
    async def test_get_markdown_articles_blob_error(
        self, site_service, mock_blob_client
    ):
        """Test handling of blob storage errors during article retrieval."""
        # Mock blob listing to raise an exception
        mock_blob_client.list_blobs.side_effect = Exception("Blob storage error")

        # Test the method
        articles = await site_service._get_markdown_articles()

        # Should return empty list on error
        assert articles == []

    @pytest.mark.asyncio
    async def test_get_markdown_articles_download_error(
        self, site_service, mock_blob_client
    ):
        """Test handling of download errors for individual articles."""
        # Mock the blob listing
        mock_blob_client.list_blobs.return_value = [
            {"name": "good_article.md"},
            {"name": "bad_article.md"},
        ]

        # Mock download to succeed for first, fail for second
        good_content = """---
title: "Good Article"
metadata:
  topic_id: "good_001"
  generated_at: "2025-09-22T14:26:36+00:00"
source:
  name: "web"
  url: "https://example.com/good"
---

Good content.
"""

        mock_blob_client.download_text.side_effect = [
            good_content,
            Exception("Download failed"),
        ]

        # Test the method
        articles = await site_service._get_markdown_articles()

        # Should return only the successful article
        assert len(articles) == 1
        assert articles[0].title == "Good Article"

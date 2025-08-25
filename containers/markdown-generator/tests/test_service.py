"""Tests for markdown generator service logic."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from service_logic import ContentWatcher, MarkdownGenerator


class TestMarkdownGenerator:
    """Test cases for MarkdownGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_blob_client = Mock()
        self.generator = MarkdownGenerator(self.mock_blob_client)

    @pytest.mark.asyncio
    async def test_generate_markdown_from_ranked_content_success(self):
        """Test successful markdown generation from ranked content."""
        # Mock the blob storage upload methods
        self.mock_blob_client.upload_text.return_value = "test-url"
        self.mock_blob_client.upload_json.return_value = "test-manifest-url"

        content_items = [
            {
                "title": "Test Article",
                "clean_title": "Test Article",
                "content": "Test content",
                "ai_summary": "Test summary",
                "final_score": 95.5,
            }
        ]

        result = await self.generator.generate_markdown_from_ranked_content(
            content_items
        )

        assert result is not None
        assert result["status"] == "success"
        assert result["files_generated"] == 2  # 1 article + 1 index
        assert "timestamp" in result
        assert "markdown_files" in result
        assert len(result["markdown_files"]) == 1

        # Verify blob storage methods were called
        assert self.mock_blob_client.upload_text.call_count >= 2  # article + index
        self.mock_blob_client.upload_json.assert_called_once()  # manifest

    @pytest.mark.asyncio
    async def test_generate_markdown_empty_content(self):
        """Test markdown generation with empty content."""
        result = await self.generator.generate_markdown_from_ranked_content([])

        assert result is None

    def test_create_slug(self):
        """Test slug creation from titles."""
        # Test normal title
        slug = self.generator._create_slug("This is a Test Title")
        assert slug == "this-is-a-test-title"

    def test_generate_standard_markdown(self):
        """Test standard markdown template generation."""
        item = {
            "title": "Test Article",
            "clean_title": "Test Article",
            "content": "This is test content for the article.",
            "ai_summary": "A brief summary",
            "final_score": 85.0,
            "topics": ["AI", "Technology"],
            "sentiment": "positive",
            "source_url": "https://example.com/article",
        }

        markdown = self.generator._generate_post_markdown(
            item, rank=1, template_style="standard"
        )

        assert "---" in markdown  # YAML front matter
        assert 'title: "Test Article"' in markdown
        assert "rank: 1" in markdown
        assert "ai_score: 85.000" in markdown
        assert "A brief summary" in markdown
        assert "**Topics:** AI, Technology" in markdown


class TestContentWatcher:
    """Test cases for ContentWatcher class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_blob_client = Mock()
        self.mock_generator = Mock()
        self.watcher = ContentWatcher(self.mock_blob_client, self.mock_generator)

    @pytest.mark.asyncio
    async def test_check_for_new_ranked_content_success(self):
        """Test successful detection and processing of new ranked content."""
        # Mock blob storage responses
        mock_blobs = [
            {
                "name": "ranked-content/test-content-20240819_120000.json",
                "last_modified": "2024-08-19T12:00:00Z",
            }
        ]

        mock_content = {
            "content": [
                {
                    "title": "Test Article",
                    "clean_title": "Test Article",
                    "content": "Test content",
                    "final_score": 95.0,
                }
            ]
        }

        self.mock_blob_client.list_blobs.return_value = mock_blobs
        self.mock_blob_client.download_json.return_value = mock_content

        # Mock generator response
        generation_result = {
            "status": "success",
            "files_generated": 2,
            "timestamp": "20240819_120000",
        }
        self.mock_generator.generate_markdown_from_ranked_content = AsyncMock(
            return_value=generation_result
        )

        result = await self.watcher.check_for_new_ranked_content()

        assert result is not None
        assert result["status"] == "success"

        # Verify calls
        self.mock_blob_client.list_blobs.assert_called_once()
        self.mock_blob_client.download_json.assert_called_once()
        self.mock_generator.generate_markdown_from_ranked_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_for_new_ranked_content_no_content(self):
        """Test behavior when no ranked content is found."""
        self.mock_blob_client.list_blobs.return_value = []

        result = await self.watcher.check_for_new_ranked_content()

        assert result is None
        self.mock_blob_client.list_blobs.assert_called_once()
        self.mock_generator.generate_markdown_from_ranked_content.assert_not_called()

    def test_get_watcher_status(self):
        """Test watcher status reporting."""
        # Add some processed blobs
        self.watcher.processed_blobs.add("blob1")
        self.watcher.processed_blobs.add("blob2")

        status = self.watcher.get_watcher_status()

        assert status["watching"] is True
        assert status["processed_blobs"] == 2
        assert "last_check" in status
        assert "watch_interval" in status


class TestMarkdownTemplateGeneration:
    """Test cases for markdown template generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_blob_client = Mock()
        self.generator = MarkdownGenerator(self.mock_blob_client)

    def test_generate_index_markdown_standard(self):
        """Test standard index markdown generation."""
        markdown_files = [
            {
                "slug": "test-article-1",
                "title": "Test Article 1",
                "score": 95.0,
                "rank": 1,
            }
        ]

        index_content = self.generator._generate_index_markdown(
            markdown_files, "20240819_120000", "standard"
        )

        assert "---" in index_content  # YAML front matter
        assert 'type: "index"' in index_content
        assert "Test Article 1" in index_content

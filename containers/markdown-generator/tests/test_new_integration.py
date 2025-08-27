"""Integration tests for markdown generator service with standard blob storage."""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from service_logic import ContentWatcher, MarkdownGenerator

from libs.blob_storage import BlobStorageClient


class TestMarkdownGeneratorIntegration:
    """Integration tests for markdown generation workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_blob_client = Mock(spec=BlobStorageClient)
        self.generator = MarkdownGenerator(self.mock_blob_client)

    @pytest.mark.asyncio
    async def test_full_markdown_generation_workflow(self):
        """Test complete workflow from ranked content to markdown files."""
        # Mock blob storage operations
        self.mock_blob_client.upload_text.return_value = (
            "https://test.blob.url/markdown.md"
        )
        self.mock_blob_client.upload_json.return_value = (
            "https://test.blob.url/manifest.json"
        )

        # Test data
        ranked_content = [
            {
                "title": "AI Breakthrough in Language Models",
                "clean_title": "AI Breakthrough in Language Models",
                "ai_summary": "New language model achieves unprecedented performance on complex reasoning tasks.",
                "final_score": 95.5,
                "topics": ["AI", "Machine Learning", "NLP"],
                "sentiment": "positive",
                "source_url": "https://example.com/ai-breakthrough",
                "content_type": "article",
                "source_metadata": {
                    "site_name": "Tech News",
                    "author": "Dr. Sarah Johnson",
                },
                "published_at": "2025-08-19T10:00:00Z",
                "engagement_score": 88.2,
            },
            {
                "title": "Quantum Computing Milestone Reached",
                "clean_title": "Quantum Computing Milestone Reached",
                "ai_summary": "Scientists demonstrate practical quantum advantage in optimization problems.",
                "final_score": 92.1,
                "topics": ["Quantum Computing", "Technology"],
                "sentiment": "positive",
                "source_url": "https://example.com/quantum-milestone",
                "content_type": "research",
                "source_metadata": {
                    "site_name": "Science Journal",
                    "author": "Prof. Mike Chen",
                },
                "published_at": "2025-08-19T09:30:00Z",
                "engagement_score": 85.7,
            },
        ]

        # Execute generation
        result = await self.generator.generate_markdown_from_ranked_content(
            ranked_content
        )

        # Verify result structure
        assert result is not None
        assert result["status"] == "success"
        assert result["files_generated"] == 3  # 2 articles + 1 index
        assert len(result["markdown_files"]) == 2
        assert "timestamp" in result

        # Verify file details
        file1 = result["markdown_files"][0]
        assert file1["title"] == "AI Breakthrough in Language Models"
        assert file1["slug"] == "ai-breakthrough-in-language-models"
        assert file1["score"] == 95.5

        file2 = result["markdown_files"][1]
        assert file2["title"] == "Quantum Computing Milestone Reached"
        assert file2["slug"] == "quantum-computing-milestone-reached"
        assert file2["score"] == 92.1

        # Verify blob storage calls
        assert self.mock_blob_client.upload_text.call_count == 3  # 2 articles + 1 index
        assert self.mock_blob_client.upload_json.call_count == 1  # 1 manifest

    @pytest.mark.asyncio
    async def test_content_watcher_integration(self):
        """Test content watcher integration with blob storage."""
        mock_generator = Mock(spec=MarkdownGenerator)
        watcher = ContentWatcher(self.mock_blob_client, mock_generator)

        # Mock blob storage responses
        mock_blobs = [
            {
                "name": "ranked-content/test-content-20250819_120000.json",
                "last_modified": "2025-08-19T12:00:00Z",
            }
        ]

        mock_content = {
            "content": [
                {
                    "title": "Test Article",
                    "clean_title": "Test Article",
                    "ai_summary": "Test summary",
                    "final_score": 90.0,
                    "topics": ["Technology"],
                    "sentiment": "positive",
                }
            ]
        }

        self.mock_blob_client.list_blobs.return_value = mock_blobs
        self.mock_blob_client.download_json.return_value = mock_content

        # Mock generation result
        generation_result = {
            "status": "success",
            "files_generated": 2,
            "timestamp": "20250819_120000",
        }
        mock_generator.generate_markdown_from_ranked_content = AsyncMock(
            return_value=generation_result
        )

        # Execute watcher check
        result = await watcher.check_for_new_ranked_content()

        # Verify results
        assert result is not None
        assert result["status"] == "success"
        assert result["files_generated"] == 2

        # Verify method calls
        self.mock_blob_client.list_blobs.assert_called_once()
        self.mock_blob_client.download_json.assert_called_once()
        mock_generator.generate_markdown_from_ranked_content.assert_called_once()

    def test_slug_generation_edge_cases(self):
        """Test slug generation with various edge cases."""
        test_cases = [
            ("Simple Title", "simple-title"),
            ("Title with Numbers 123", "title-with-numbers-123"),
            ("Special Characters!@#$%", "special-characters"),
            ("Multiple   Spaces", "multiple-spaces"),
            ("CamelCase Title", "camelcase-title"),
            ("Title-with-hyphens", "title-with-hyphens"),
            (
                "Very Long Title That Should Be Truncated Because It Exceeds Reasonable Length Limits",
                "very-long-title-that-should-be-truncated-because-i",
            ),
            ("", ""),
            ("   ", ""),
        ]

        for title, expected_slug in test_cases:
            actual_slug = self.generator._create_slug(title)
            assert (
                actual_slug == expected_slug
            ), f"Failed for '{title}': expected '{expected_slug}', got '{actual_slug}'"

    def test_markdown_template_structure(self):
        """Test that generated markdown has proper structure."""
        test_item = {
            "title": "Test Article",
            "clean_title": "Test Article",
            "ai_summary": "This is a test summary for the article.",
            "final_score": 87.5,
            "topics": ["AI", "Testing", "Technology"],
            "sentiment": "positive",
            "source_url": "https://example.com/test",
            "content_type": "article",
            "source_metadata": {"site_name": "Test Site"},
            "published_at": "2025-08-19T12:00:00Z",
            "engagement_score": 82.3,
        }

        markdown = self.generator._generate_post_markdown(test_item, rank=1)

        # Verify structure
        assert markdown.startswith("---")  # YAML frontmatter
        assert 'title: "Test Article"' in markdown
        assert 'slug: "test-article"' in markdown
        assert "ai_score: 87.500" in markdown
        assert 'topics: ["AI", "Testing", "Technology"]' in markdown
        assert 'sentiment: "positive"' in markdown
        assert "rank: 1" in markdown

        # Verify content sections
        assert "# Test Article" in markdown
        assert "## Summary" in markdown
        assert "## Key Information" in markdown
        assert "## Source" in markdown
        assert "This is a test summary for the article." in markdown
        assert "**Topics:** AI, Testing, Technology" in markdown
        assert "[Test Site](https://example.com/test)" in markdown

    @pytest.mark.asyncio
    async def test_error_handling_in_generation(self):
        """Test error handling during markdown generation."""
        # Test with empty content
        result = await self.generator.generate_markdown_from_ranked_content([])
        assert result is None

        # Test with malformed content
        malformed_content = [{"title": "No required fields"}]
        result = await self.generator.generate_markdown_from_ranked_content(
            malformed_content
        )
        assert result is not None  # Should handle gracefully with defaults

    def test_index_generation(self):
        """Test index markdown generation."""
        content_items = [
            {
                "title": "First Article",
                "clean_title": "First Article",
                "final_score": 95.0,
                "ai_summary": "Summary of first article",
            },
            {
                "title": "Second Article",
                "clean_title": "Second Article",
                "final_score": 88.5,
                "ai_summary": "Summary of second article",
            },
        ]

        index_content = self.generator._generate_index_markdown(
            content_items, "20250819_120000"
        )

        # Verify index structure
        assert index_content.startswith("---")
        assert 'title: "AI Curated Content Index"' in index_content
        assert 'type: "index"' in index_content
        assert "total_articles: 2" in index_content
        assert 'timestamp: "20250819_120000"' in index_content

        # Verify content listings
        assert "# AI Curated Content Index" in index_content
        assert "First Article" in index_content
        assert "Second Article" in index_content
        assert "Total Articles: 2" in index_content


class TestBlobStorageIntegration:
    """Integration tests for blob storage operations."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("config.config.AZURE_STORAGE_CONNECTION_STRING", "test_connection"):
            self.blob_client = Mock(spec=BlobStorageClient)

    def test_blob_client_operations(self):
        """Test that blob client operations are called correctly."""
        generator = MarkdownGenerator(self.blob_client)

        # Mock return values
        self.blob_client.upload_text.return_value = "https://test.url/file.md"
        self.blob_client.upload_json.return_value = "https://test.url/manifest.json"

        # Test data
        content_items = [
            {
                "title": "Test",
                "clean_title": "Test",
                "ai_summary": "Summary",
                "final_score": 85.0,
            }
        ]

        # Execute (sync version for testing)
        import asyncio

        result = asyncio.run(
            generator.generate_markdown_from_ranked_content(content_items)
        )

        # Verify blob operations were called
        assert self.blob_client.upload_text.called
        assert self.blob_client.upload_json.called
        assert result["status"] == "success"

    def test_content_watcher_blob_operations(self):
        """Test content watcher blob storage operations."""
        mock_generator = Mock()
        watcher = ContentWatcher(self.blob_client, mock_generator)

        # Test status method
        status = watcher.get_watcher_status()
        assert "watching" in status
        assert "processed_blobs" in status
        assert "last_check" in status

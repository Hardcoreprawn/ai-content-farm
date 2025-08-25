"""Integration tests for markdown generator service operations."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from service_logic import ContentWatcher, MarkdownGenerator

from libs.blob_storage import BlobContainers, BlobStorageClient


class TestMarkdownGeneratorIntegration:
    """Test markdown generator integration functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock blob client that can be used in mock mode
        with patch.dict("os.environ", {"BLOB_STORAGE_MOCK": "true"}):
            self.blob_client = BlobStorageClient()
        self.markdown_generator = MarkdownGenerator(self.blob_client)
        self.content_watcher = ContentWatcher(self.blob_client, self.markdown_generator)

    def test_blob_client_initialization(self):
        """Test blob storage client initialization."""
        with patch.dict("os.environ", {"BLOB_STORAGE_MOCK": "true"}):
            client = BlobStorageClient()
            assert client is not None
            assert client._mock is True

    @pytest.mark.asyncio
    async def test_content_watcher_get_latest_ranked_content_success(self):
        """Test successful retrieval of latest ranked content via ContentWatcher."""
        # Mock blob data
        mock_content = {
            "content": [
                {
                    "title": "Test Article",
                    "final_score": 0.8,
                    "ai_summary": "Test summary",
                }
            ]
        }

        # Mock the blob client methods
        mock_blobs = [
            {
                "name": "ranked-content/ranked_20240101_120000.json",
                "last_modified": datetime.now(timezone.utc).isoformat(),
            }
        ]

        with patch.object(self.blob_client, "list_blobs", return_value=mock_blobs):
            with patch.object(
                self.blob_client, "download_json", return_value=mock_content
            ):
                result = await self.content_watcher._get_latest_ranked_content()

                # Assertions
                assert result is not None
                content_items, blob_name = result
                assert len(content_items) == 1
                assert content_items[0]["title"] == "Test Article"
                assert blob_name == "ranked-content/ranked_20240101_120000.json"

    @pytest.mark.asyncio
    async def test_content_watcher_get_latest_ranked_content_no_blobs(self):
        """Test retrieval when no blobs exist."""
        with patch.object(self.blob_client, "list_blobs", return_value=[]):
            result = await self.content_watcher._get_latest_ranked_content()
            assert result is None

    @pytest.mark.asyncio
    async def test_markdown_generator_generate_from_content(self):
        """Test markdown generation from content items."""
        content_items = [
            {
                "title": "Test Article",
                "link": "https://example.com/test",
                "description": "Test description",
                "ai_summary": "Test summary",
                "final_score": 0.8,
                "published_date": "2024-01-01T12:00:00Z",
            }
        ]

        # Mock the upload operations
        with patch.object(self.blob_client, "upload_json", return_value=True):
            with patch.object(self.blob_client, "upload_text", return_value=True):
                result = (
                    await self.markdown_generator.generate_markdown_from_ranked_content(
                        content_items
                    )
                )

                # Assertions
                assert result is not None
                assert result["status"] == "success"
                assert result["files_generated"] == 2  # 1 markdown + 1 index
                assert "blob_manifest" in result
                assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_content_watcher_check_for_new_content(self):
        """Test checking for new ranked content and triggering generation."""
        # Mock content data
        mock_content = {
            "content": [
                {
                    "title": "Test Article",
                    "link": "https://example.com/test",
                    "description": "Test description",
                    "ai_summary": "Test summary",
                    "final_score": 0.8,
                    "published_date": "2024-01-01T12:00:00Z",
                }
            ]
        }

        mock_blobs = [
            {
                "name": "ranked-content/ranked_20240101_120000.json",
                "last_modified": datetime.now(timezone.utc).isoformat(),
            }
        ]

        # Mock all the required operations
        with patch.object(self.blob_client, "list_blobs", return_value=mock_blobs):
            with patch.object(
                self.blob_client, "download_json", return_value=mock_content
            ):
                with patch.object(self.blob_client, "upload_json", return_value=True):
                    with patch.object(
                        self.blob_client, "upload_text", return_value=True
                    ):
                        result = (
                            await self.content_watcher.check_for_new_ranked_content()
                        )

                        # Assertions
                        assert result is not None
                        assert result["status"] == "success"
                        assert result["files_generated"] == 2

    def test_blob_client_health_check(self):
        """Test blob storage health check."""
        # Test health check with mock client
        health_result = self.blob_client.health_check()

        assert health_result is not None
        assert "status" in health_result
        assert "environment" in health_result
        assert "connection_type" in health_result

    def test_content_watcher_status(self):
        """Test content watcher status."""
        status = self.content_watcher.get_watcher_status()

        assert status is not None
        assert "watching" in status
        assert "processed_blobs" in status
        assert "last_check" in status
        assert status["watching"] is True


class TestMarkdownGeneratorErrorHandling:
    """Test error handling in markdown generator operations."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch.dict("os.environ", {"BLOB_STORAGE_MOCK": "true"}):
            self.blob_client = BlobStorageClient()
        self.markdown_generator = MarkdownGenerator(self.blob_client)
        self.content_watcher = ContentWatcher(self.blob_client, self.markdown_generator)

    @pytest.mark.asyncio
    async def test_content_watcher_handles_json_decode_error(self):
        """Test handling of JSON decode errors."""
        mock_blobs = [
            {
                "name": "ranked-content/invalid.json",
                "last_modified": datetime.now(timezone.utc).isoformat(),
            }
        ]

        with patch.object(self.blob_client, "list_blobs", return_value=mock_blobs):
            with patch.object(
                self.blob_client,
                "download_json",
                side_effect=Exception("JSON decode error"),
            ):
                result = await self.content_watcher._get_latest_ranked_content()
                assert result is None

    @pytest.mark.asyncio
    async def test_markdown_generator_handles_upload_error(self):
        """Test error handling during markdown upload."""
        content_items = [
            {
                "title": "Test Article",
                "link": "https://example.com/test",
                "description": "Test description",
                "ai_summary": "Test summary",
                "final_score": 0.8,
            }
        ]

        with patch.object(
            self.blob_client, "upload_json", side_effect=Exception("Upload error")
        ):
            result = (
                await self.markdown_generator.generate_markdown_from_ranked_content(
                    content_items
                )
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_markdown_generator_empty_content_items(self):
        """Test handling of empty content items."""
        result = await self.markdown_generator.generate_markdown_from_ranked_content([])
        # Should return None on error, not raise exception
        assert result is None


class TestMarkdownGeneratorConfiguration:
    """Test markdown generator configuration handling."""

    def test_blob_client_mock_mode_initialization(self):
        """Test blob client initialization in mock mode."""
        with patch.dict(
            "os.environ", {"BLOB_STORAGE_MOCK": "true", "ENVIRONMENT": "development"}
        ):
            client = BlobStorageClient()
            assert client._mock is True
            assert client.environment == "development"

    def test_blob_client_development_mode_initialization(self):
        """Test blob client initialization in development mode."""
        with patch.dict(
            "os.environ",
            {
                "BLOB_STORAGE_MOCK": "false",
                "ENVIRONMENT": "development",
                "AZURE_STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=testkey;EndpointSuffix=core.windows.net",
            },
        ):
            client = BlobStorageClient()
            assert client._mock is False
            assert client.environment == "development"
            assert hasattr(client, "blob_service_client")

"""Integration tests for blob storage operations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from datetime import datetime, timezone

# Create a mock AzureError that inherits from Exception for testing


class MockAzureError(Exception):
    pass


# Mock Azure dependencies with proper exception types
with patch('azure.storage.blob.BlobServiceClient'), \
        patch('azure.core.exceptions.ResourceNotFoundError'), \
        patch('azure.core.exceptions.AzureError', MockAzureError):
    from libs.blob_storage import BlobStorageClient


class TestBlobStorageIntegration:
    """Test blob storage integration functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch('config.config.AZURE_STORAGE_CONNECTION_STRING', 'test_connection'):
            self.blob_client = BlobStorageClient()

    @patch('blob_storage.BlobStorageClient._ensure_containers_exist')
    def test_blob_client_initialization(self, mock_ensure):
        """Test blob storage client initialization."""
        with patch('config.config.AZURE_STORAGE_CONNECTION_STRING', 'test_connection'):
            client = BlobStorageClient()
            assert client is not None
            mock_ensure.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_latest_ranked_content_success(self):
        """Test successful retrieval of latest ranked content."""
        # Mock blob data
        mock_content = {
            "items": [
                {
                    "title": "Test Article",
                    "final_score": 0.8,
                    "ai_summary": "Test summary"
                }
            ]
        }

        # Mock blob operations
        mock_blob = MagicMock()
        mock_blob.name = "ranked_20240101_120000.json"
        mock_blob.last_modified = datetime.now(timezone.utc)

        mock_container_client = MagicMock()
        mock_container_client.list_blobs.return_value = [mock_blob]

        mock_blob_client = MagicMock()
        mock_blob_client.download_blob.return_value.readall.return_value = json.dumps(
            mock_content).encode()
        mock_container_client.get_blob_client.return_value = mock_blob_client

        self.blob_client.client.get_container_client.return_value = mock_container_client

        # Test the method
        result = await self.blob_client.get_latest_ranked_content()

        # Assertions
        assert result is not None
        content_items, blob_name = result
        assert len(content_items) == 1
        assert content_items[0]["title"] == "Test Article"
        assert blob_name == "ranked_20240101_120000.json"

    @pytest.mark.asyncio
    async def test_get_latest_ranked_content_no_blobs(self):
        """Test retrieval when no blobs exist."""
        mock_container_client = MagicMock()
        mock_container_client.list_blobs.return_value = []
        self.blob_client.client.get_container_client.return_value = mock_container_client

        result = await self.blob_client.get_latest_ranked_content()
        assert result is None

    @pytest.mark.asyncio
    async def test_save_generated_markdown_success(self):
        """Test successful saving of generated markdown."""
        # Test data
        markdown_files = [
            {
                "slug": "test-article",
                "title": "Test Article",
                "score": 0.8,
                "content": "# Test Article\n\nContent here"
            }
        ]

        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_posts": 1,
            "index_content": "# Index\n\nIndex content"
        }

        timestamp = "20240101_120000"

        # Mock container client
        mock_container_client = MagicMock()
        mock_blob_client = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client
        self.blob_client.client.get_container_client.return_value = mock_container_client

        # Test the method
        result = await self.blob_client.save_generated_markdown(
            markdown_files, manifest, timestamp
        )

        # Assertions
        assert result == f"manifests/{timestamp}_manifest.json"

        # Verify blob uploads were called
        assert mock_blob_client.upload_blob.call_count >= 3  # markdown + index + manifest

    @pytest.mark.asyncio
    async def test_check_blob_health_success(self):
        """Test successful blob health check."""
        # Mock containers
        mock_container1 = MagicMock()
        mock_container1.name = "ranked-content"
        mock_container2 = MagicMock()
        mock_container2.name = "generated-content"

        self.blob_client.client.list_containers.return_value = [
            mock_container1, mock_container2]

        result = await self.blob_client.check_blob_health()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_blob_health_missing_containers(self):
        """Test blob health check with missing containers."""
        # Mock containers - missing required ones
        mock_container = MagicMock()
        mock_container.name = "other-container"

        self.blob_client.client.list_containers.return_value = [mock_container]

        result = await self.blob_client.check_blob_health()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_generation_statistics_success(self):
        """Test successful retrieval of generation statistics."""
        # Mock blobs with name attribute
        mock_blob1 = MagicMock()
        mock_blob1.name = "markdown/20240101/article1.md"
        mock_blob2 = MagicMock()
        mock_blob2.name = "markdown/20240101/article2.md"
        mock_blob3 = MagicMock()
        mock_blob3.name = "manifests/20240101_manifest.json"
        mock_blob4 = MagicMock()
        mock_blob4.name = "other/file.txt"

        mock_blobs = [mock_blob1, mock_blob2, mock_blob3, mock_blob4]

        mock_container_client = MagicMock()
        mock_container_client.list_blobs.return_value = mock_blobs
        self.blob_client.client.get_container_client.return_value = mock_container_client

        result = await self.blob_client.get_generation_statistics()

        assert result["markdown_files"] == 2
        assert result["manifests"] == 1
        assert "container" in result


class TestBlobStorageErrorHandling:
    """Test blob storage error handling scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch('config.config.AZURE_STORAGE_CONNECTION_STRING', 'test_connection'):
            self.blob_client = BlobStorageClient()

    @pytest.mark.asyncio
    async def test_get_latest_ranked_content_json_error(self):
        """Test handling of JSON decode errors."""
        # Mock blob with invalid JSON
        mock_blob = MagicMock()
        mock_blob.name = "test.json"
        mock_blob.last_modified = datetime.now(timezone.utc)

        mock_container_client = MagicMock()
        mock_container_client.list_blobs.return_value = [mock_blob]

        mock_blob_client = MagicMock()
        mock_blob_client.download_blob.return_value.readall.return_value = b"invalid json"
        mock_container_client.get_blob_client.return_value = mock_blob_client

        self.blob_client.client.get_container_client.return_value = mock_container_client

        result = await self.blob_client.get_latest_ranked_content()
        assert result is None

    @pytest.mark.asyncio
    async def test_save_generated_markdown_error(self):
        """Test error handling during markdown save."""
        # Mock container client that raises exception
        mock_container_client = MagicMock()
        mock_container_client.get_blob_client.side_effect = Exception(
            "Storage error")
        self.blob_client.client.get_container_client.return_value = mock_container_client

        markdown_files = [
            {"slug": "test", "title": "Test", "score": 0.8, "content": "test"}]
        manifest = {"total_posts": 1}
        timestamp = "20240101_120000"

        # Should raise generic exception instead of AzureError in tests
        with pytest.raises(Exception):
            await self.blob_client.save_generated_markdown(markdown_files, manifest, timestamp)

    @pytest.mark.asyncio
    async def test_check_blob_health_exception(self):
        """Test blob health check when exception occurs."""
        self.blob_client.client.list_containers.side_effect = Exception(
            "Connection error")

        result = await self.blob_client.check_blob_health()
        assert result is False


class TestBlobStorageConfiguration:
    """Test blob storage configuration scenarios."""

    def test_initialization_without_connection_string(self):
        """Test initialization without connection string raises error."""
        with patch('config.config.AZURE_STORAGE_CONNECTION_STRING', None):
            with pytest.raises(ValueError, match="Azure storage connection string is required"):
                BlobStorageClient()

    @patch('blob_storage.BlobStorageClient._ensure_containers_exist')
    def test_initialization_with_connection_string(self, mock_ensure):
        """Test successful initialization with connection string."""
        with patch('config.config.AZURE_STORAGE_CONNECTION_STRING', 'test_connection'):
            client = BlobStorageClient()
            assert client is not None
            mock_ensure.assert_called_once()

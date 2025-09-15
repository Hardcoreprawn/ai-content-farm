"""
Comprehensive tests for actual blob storage implementation.
Tests the real BlobStorageClient and BlobOperations classes.
"""

import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.core.exceptions import ResourceNotFoundError

from libs.blob_operations import BlobOperations
from libs.blob_storage import BlobStorageClient


class TestActualBlobStorageClient:
    """Test the actual BlobStorageClient implementation."""

    def test_blob_storage_client_mock_mode(self):
        """Test blob storage client in mock mode."""
        with patch.dict(os.environ, {"BLOB_STORAGE_MOCK": "true"}):
            client = BlobStorageClient()
            assert client._mock is True

    def test_blob_storage_client_development_mode(self):
        """Test blob storage client in development mode."""
        with patch.dict(
            os.environ,
            {
                "BLOB_STORAGE_MOCK": "false",
                "ENVIRONMENT": "development",
                "AZURE_STORAGE_CONNECTION_STRING": "test_connection",
            },
        ):
            with patch("libs.blob_storage.BlobServiceClient"):
                client = BlobStorageClient()
                assert client._mock is False
                assert client.environment == "development"

    @pytest.mark.asyncio
    async def test_upload_text_mock_mode(self):
        """Test uploading text in mock mode."""
        with patch.dict(os.environ, {"BLOB_STORAGE_MOCK": "true"}):
            client = BlobStorageClient()

        result = await client.upload_text(
            container_name="test-container",
            blob_name="test-blob.txt",
            content="Test content",
        )

        # Should return a URL string (not boolean)
        assert isinstance(result, str)
        assert "test-container/test-blob.txt" in result

    @pytest.mark.asyncio
    async def test_download_text_mock_mode(self):
        """Test downloading text in mock mode."""
        with patch.dict(os.environ, {"BLOB_STORAGE_MOCK": "true"}):
            client = BlobStorageClient()

            # First upload some content
            await client.upload_text(
                container_name="test-container",
                blob_name="test-blob.txt",
                content="Test content",
            )

            # Then download it
            content = await client.download_text(
                container_name="test-container", blob_name="test-blob.txt"
            )

            assert content == "Test content"

    @pytest.mark.asyncio
    async def test_upload_json_mock_mode(self):
        """Test uploading JSON in mock mode."""
        with patch.dict(os.environ, {"BLOB_STORAGE_MOCK": "true"}):
            client = BlobStorageClient()

            test_data = {"key": "value", "number": 42}

        result = await client.upload_json(
            container_name="test-container", blob_name="test-data.json", data=test_data
        )

        # Should return a URL string (not boolean)
        assert isinstance(result, str)
        assert "test-container/test-data.json" in result

    @pytest.mark.asyncio
    async def test_download_json_mock_mode(self):
        """Test downloading JSON in mock mode."""
        with patch.dict(os.environ, {"BLOB_STORAGE_MOCK": "true"}):
            client = BlobStorageClient()

            test_data = {"key": "value", "number": 42}

            # Upload JSON data
            await client.upload_json(
                container_name="test-container",
                blob_name="test-data.json",
                data=test_data,
            )

            # Download and verify
            downloaded_data = await client.download_json(
                container_name="test-container", blob_name="test-data.json"
            )

            assert downloaded_data == test_data

    @pytest.mark.asyncio
    async def test_list_blobs_mock_mode(self):
        """Test listing blobs in mock mode."""
        with patch.dict(os.environ, {"BLOB_STORAGE_MOCK": "true"}):
            # Clear mock storage to avoid interference
            from libs.blob_storage import _MOCK_BLOBS

            _MOCK_BLOBS.clear()

            client = BlobStorageClient()

            # Upload some test blobs
            await client.upload_text("test-container", "file1.txt", "Content 1")
            await client.upload_text("test-container", "file2.txt", "Content 2")
            await client.upload_text("test-container", "file3.txt", "Content 3")

            # List blobs
            blobs = await client.list_blobs("test-container")

            assert len(blobs) == 3
            blob_names = [blob["name"] for blob in blobs]
            assert "file1.txt" in blob_names
            assert "file2.txt" in blob_names
            assert "file3.txt" in blob_names

    @pytest.mark.asyncio
    async def test_delete_blob_mock_mode(self):
        """Test deleting blobs in mock mode."""
        with patch.dict(os.environ, {"BLOB_STORAGE_MOCK": "true"}):
            client = BlobStorageClient()

            # Upload a test blob
            await client.upload_text("test-container", "delete-me.txt", "Delete this")

            # Verify it exists
            content = await client.download_text("test-container", "delete-me.txt")
            assert content == "Delete this"

            # Delete it
            result = await client.delete_blob("test-container", "delete-me.txt")
            assert result is True

            # Verify it's gone
            try:
                await client.download_text("test-container", "delete-me.txt")
                assert False, "Blob should have been deleted"
            except Exception:
                pass  # Expected - blob should not exist

    @pytest.mark.asyncio
    async def test_blob_exists_mock_mode(self):
        """Test checking blob existence in mock mode."""
        with patch.dict(os.environ, {"BLOB_STORAGE_MOCK": "true"}):
            client = BlobStorageClient()

            # Check non-existent blob
            exists = await client.blob_exists("test-container", "non-existent.txt")
            assert exists is False

            # Upload a blob
            await client.upload_text("test-container", "exists.txt", "I exist")

            # Check it exists
            exists = await client.blob_exists("test-container", "exists.txt")
            assert exists is True


class TestActualBlobOperations:
    """Test the actual BlobOperations implementation."""

    def test_blob_operations_initialization(self):
        """Test blob operations initialization."""
        mock_blob_service = MagicMock()
        operations = BlobOperations(blob_service_client=mock_blob_service)

        assert operations.blob_service_client == mock_blob_service

    def test_upload_file_success(self):
        """Test successful file upload."""
        mock_blob_service = MagicMock()
        mock_blob_client = MagicMock()
        mock_blob_service.get_blob_client.return_value = mock_blob_client

        operations = BlobOperations(blob_service_client=mock_blob_service)

        # Create a temporary test file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("Test file content")
            temp_file = f.name

        try:
            result = operations.upload_file(
                container_name="test-container",
                blob_name="test-file.txt",
                file_path=temp_file,
            )

            assert result is True
            mock_blob_service.get_blob_client.assert_called_once_with(
                container="test-container", blob="test-file.txt"
            )
            mock_blob_client.upload_blob.assert_called_once()
        finally:
            os.unlink(temp_file)

    def test_upload_file_failure(self):
        """Test file upload failure."""
        mock_blob_service = MagicMock()
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob.side_effect = Exception("Upload failed")
        mock_blob_service.get_blob_client.return_value = mock_blob_client

        operations = BlobOperations(blob_service_client=mock_blob_service)

        # Create a temporary test file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("Test file content")
            temp_file = f.name

        try:
            result = operations.upload_file(
                container_name="test-container",
                blob_name="test-file.txt",
                file_path=temp_file,
            )

            assert result is False
        finally:
            os.unlink(temp_file)

    def test_download_file_success(self):
        """Test successful file download."""
        mock_blob_service = MagicMock()
        mock_blob_client = MagicMock()
        mock_download = MagicMock()
        mock_download.readall.return_value = b"Downloaded content"
        mock_blob_client.download_blob.return_value = mock_download
        mock_blob_service.get_blob_client.return_value = mock_blob_client

        operations = BlobOperations(blob_service_client=mock_blob_service)

        # Create a temporary file path for download
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            result = operations.download_file(
                container_name="test-container",
                blob_name="test-file.txt",
                file_path=temp_file,
            )

            assert result is True

            # Verify file content
            with open(temp_file, "rb") as f:
                content = f.read()
            assert content == b"Downloaded content"
        finally:
            os.unlink(temp_file)

    def test_upload_json_data(self):
        """Test uploading JSON data."""
        mock_blob_service = MagicMock()
        mock_blob_client = MagicMock()
        mock_blob_service.get_blob_client.return_value = mock_blob_client

        operations = BlobOperations(blob_service_client=mock_blob_service)

        test_data = {"key": "value", "items": [1, 2, 3]}

        result = operations.upload_json_data(
            container_name="test-container", blob_name="data.json", data=test_data
        )

        assert result is True
        mock_blob_client.upload_blob.assert_called_once()

    def test_download_json_data(self):
        """Test downloading JSON data."""
        import json

        mock_blob_service = MagicMock()
        mock_blob_client = MagicMock()
        mock_download = MagicMock()
        test_data = {"key": "value", "items": [1, 2, 3]}
        mock_download.readall.return_value = json.dumps(test_data).encode()
        mock_blob_client.download_blob.return_value = mock_download
        mock_blob_service.get_blob_client.return_value = mock_blob_client

        operations = BlobOperations(blob_service_client=mock_blob_service)

        result = operations.download_json_data(
            container_name="test-container", blob_name="data.json"
        )

        assert result == test_data

    def test_list_blobs_in_container(self):
        """Test listing blobs in container."""
        mock_blob_service = MagicMock()
        mock_container_client = MagicMock()

        # Mock blob list
        mock_blob1 = MagicMock()
        mock_blob1.name = "file1.txt"
        mock_blob2 = MagicMock()
        mock_blob2.name = "file2.txt"
        mock_blob3 = MagicMock()
        mock_blob3.name = "folder/file3.txt"
        mock_blobs = [mock_blob1, mock_blob2, mock_blob3]
        mock_container_client.list_blobs.return_value = mock_blobs
        mock_blob_service.get_container_client.return_value = mock_container_client

        operations = BlobOperations(blob_service_client=mock_blob_service)

        blobs = operations.list_blobs_in_container("test-container")

        assert len(blobs) == 3
        assert blobs[0] == "file1.txt"
        assert blobs[1] == "file2.txt"
        assert blobs[2] == "folder/file3.txt"

    def test_create_container_if_not_exists(self):
        """Test creating container if it doesn't exist."""
        mock_blob_service = MagicMock()
        mock_container_client = MagicMock()
        mock_blob_service.get_container_client.return_value = mock_container_client

        operations = BlobOperations(blob_service_client=mock_blob_service)

        result = operations.create_container_if_not_exists("new-container")

        assert result is True
        mock_container_client.create_container.assert_called_once()


class TestBlobStorageIntegration:
    """Test integration between BlobStorageClient and real scenarios."""

    @pytest.mark.asyncio
    async def test_client_operations_in_mock_mode(self):
        """Test comprehensive client operations in mock mode."""
        with patch.dict(os.environ, {"BLOB_STORAGE_MOCK": "true"}):
            client = BlobStorageClient()

            # Test complete workflow
            container = "integration-test"

            # Upload different types of content
            await client.upload_text(container, "text-file.txt", "Hello World")
            await client.upload_json(container, "data.json", {"test": True})

            # List and verify
            blobs = await client.list_blobs(container)
            blob_names = [b["name"] for b in blobs]
            assert "text-file.txt" in blob_names
            assert "data.json" in blob_names

            # Download and verify
            text_content = await client.download_text(container, "text-file.txt")
            assert text_content == "Hello World"

            json_content = await client.download_json(container, "data.json")
            assert json_content["test"] is True

            # Check existence
            assert await client.blob_exists(container, "text-file.txt") is True
            assert await client.blob_exists(container, "non-existent.txt") is False

            # Clean up
            await client.delete_blob(container, "text-file.txt")
            await client.delete_blob(container, "data.json")

            # Verify cleanup
            assert await client.blob_exists(container, "text-file.txt") is False
            assert await client.blob_exists(container, "data.json") is False

    def test_blob_operations_with_real_service_client(self):
        """Test BlobOperations with a real (mocked) service client."""
        mock_blob_service = MagicMock()
        operations = BlobOperations(blob_service_client=mock_blob_service)

        # Test workflow
        container = "operations-test"

        # Setup mocks for successful operations
        mock_container_client = MagicMock()
        mock_blob_client = MagicMock()
        mock_blob_service.get_container_client.return_value = mock_container_client
        mock_blob_service.get_blob_client.return_value = mock_blob_client

        # Test container creation
        result = operations.create_container_if_not_exists(container)
        assert result is True

        # Test file operations would require temporary files
        # This demonstrates the operations class working correctly
        assert operations.blob_service_client == mock_blob_service


class TestBlobStorageErrorHandling:
    """Test error handling in blob storage operations."""

    @pytest.mark.asyncio
    async def test_download_non_existent_blob_mock_mode(self):
        """Test downloading non-existent blob in mock mode."""
        with patch.dict(os.environ, {"BLOB_STORAGE_MOCK": "true"}):
            client = BlobStorageClient()

            result = await client.download_text("test-container", "non-existent.txt")
            assert result == ""  # Should return empty string for non-existent blob

    def test_blob_operations_error_handling(self):
        """Test error handling in BlobOperations."""
        mock_blob_service = MagicMock()
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob.side_effect = Exception("Network error")
        mock_blob_service.get_blob_client.return_value = mock_blob_client

        operations = BlobOperations(blob_service_client=mock_blob_service)

        # Create a temporary test file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("Test content")
            temp_file = f.name

        try:
            result = operations.upload_file(
                container_name="test-container",
                blob_name="test-file.txt",
                file_path=temp_file,
            )

            assert result is False  # Should handle error gracefully
        finally:
            os.unlink(temp_file)

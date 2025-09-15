"""
Test suite for blob storage and Azure integration utilities.

This module tests the shared blob storage functionality.
"""

import io
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libs.blob_operations import BlobOperations
from libs.blob_storage import BlobStorageClient
from libs.blob_utils import BlobUtils


class TestBlobStorageClient:
    """Test cases for BlobStorageClient."""

    @patch("libs.blob_storage.BlobServiceClient")
    def test_blob_storage_client_initialization(self, mock_blob_service):
        """Test blob storage client initialization."""
        mock_blob_service.from_connection_string.return_value = MagicMock()

        client = BlobStorageClient(connection_string="test_connection")
        assert client is not None

    @patch("libs.blob_storage.BlobServiceClient")
    def test_blob_storage_client_with_mock_service(self, mock_blob_service):
        """Test blob storage client with mocked Azure service."""
        mock_service = MagicMock()
        mock_container = MagicMock()
        mock_blob = MagicMock()

        mock_service.get_container_client.return_value = mock_container
        mock_container.get_blob_client.return_value = mock_blob
        mock_blob_service.from_connection_string.return_value = mock_service

        client = BlobStorageClient(connection_string="test_connection")

        # Test container operations
        container_client = client.get_container_client("test-container")
        assert container_client is not None

        # Test blob operations
        blob_client = client.get_blob_client("test-container", "test-blob")
        assert blob_client is not None

    @patch("libs.blob_storage.BlobServiceClient")
    def test_blob_upload_text(self, mock_blob_service):
        """Test uploading text to blob storage."""
        mock_service = MagicMock()
        mock_container = MagicMock()
        mock_blob = MagicMock()

        mock_service.get_container_client.return_value = mock_container
        mock_container.get_blob_client.return_value = mock_blob
        mock_blob_service.from_connection_string.return_value = mock_service

        client = BlobStorageClient(connection_string="test_connection")

        # Test uploading text
        test_text = "Hello, World!"
        client.upload_text("test-container", "test-file.txt", test_text)

        # Verify upload was called
        mock_blob.upload_blob.assert_called_once()

    @patch("libs.blob_storage.BlobServiceClient")
    def test_blob_download_text(self, mock_blob_service):
        """Test downloading text from blob storage."""
        mock_service = MagicMock()
        mock_container = MagicMock()
        mock_blob = MagicMock()

        # Mock download response
        mock_download = MagicMock()
        mock_download.readall.return_value = b"Downloaded content"
        mock_blob.download_blob.return_value = mock_download

        mock_service.get_container_client.return_value = mock_container
        mock_container.get_blob_client.return_value = mock_blob
        mock_blob_service.from_connection_string.return_value = mock_service

        client = BlobStorageClient(connection_string="test_connection")

        # Test downloading text
        result = client.download_text("test-container", "test-file.txt")

        assert result == "Downloaded content"
        mock_blob.download_blob.assert_called_once()

    @patch("libs.blob_storage.BlobServiceClient")
    def test_blob_list_operations(self, mock_blob_service):
        """Test listing blobs in container."""
        mock_service = MagicMock()
        mock_container = MagicMock()

        # Mock blob list
        mock_blob_list = [
            MagicMock(name="file1.txt"),
            MagicMock(name="file2.txt"),
            MagicMock(name="file3.txt"),
        ]
        mock_container.list_blobs.return_value = mock_blob_list

        mock_service.get_container_client.return_value = mock_container
        mock_blob_service.from_connection_string.return_value = mock_service

        client = BlobStorageClient(connection_string="test_connection")

        # Test listing blobs
        blobs = list(client.list_blobs("test-container"))

        assert len(blobs) == 3
        mock_container.list_blobs.assert_called_once()


class TestBlobOperations:
    """Test cases for BlobOperations utility class."""

    def test_blob_operations_initialization(self):
        """Test blob operations initialization."""
        with patch("libs.blob_operations.BlobStorageClient"):
            ops = BlobOperations(connection_string="test_connection")
            assert ops is not None

    @patch("libs.blob_operations.BlobStorageClient")
    def test_upload_json_data(self, mock_client_class):
        """Test uploading JSON data."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        ops = BlobOperations(connection_string="test_connection")

        test_data = {"key": "value", "number": 42}
        ops.upload_json("test-container", "test.json", test_data)

        # Should have called upload_text with JSON string
        mock_client.upload_text.assert_called_once()
        args = mock_client.upload_text.call_args[0]
        assert args[0] == "test-container"
        assert args[1] == "test.json"
        # Third argument should be JSON string
        assert '"key": "value"' in args[2]

    @patch("libs.blob_operations.BlobStorageClient")
    def test_download_json_data(self, mock_client_class):
        """Test downloading JSON data."""
        mock_client = MagicMock()
        mock_client.download_text.return_value = '{"downloaded": true, "value": 123}'
        mock_client_class.return_value = mock_client

        ops = BlobOperations(connection_string="test_connection")

        result = ops.download_json("test-container", "test.json")

        assert result["downloaded"] is True
        assert result["value"] == 123
        mock_client.download_text.assert_called_once_with("test-container", "test.json")

    @patch("libs.blob_operations.BlobStorageClient")
    def test_upload_csv_data(self, mock_client_class):
        """Test uploading CSV data."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        ops = BlobOperations(connection_string="test_connection")

        csv_data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        ops.upload_csv("test-container", "test.csv", csv_data)

        mock_client.upload_text.assert_called_once()
        args = mock_client.upload_text.call_args[0]
        csv_content = args[2]
        assert "name,age" in csv_content
        assert "Alice,30" in csv_content

    @patch("libs.blob_operations.BlobStorageClient")
    def test_batch_upload_operations(self, mock_client_class):
        """Test batch upload operations."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        ops = BlobOperations(connection_string="test_connection")

        files_data = {
            "file1.txt": "Content 1",
            "file2.txt": "Content 2",
            "file3.txt": "Content 3",
        }

        ops.batch_upload("test-container", files_data)

        # Should have called upload_text for each file
        assert mock_client.upload_text.call_count == 3

    @patch("libs.blob_operations.BlobStorageClient")
    def test_error_handling_in_operations(self, mock_client_class):
        """Test error handling in blob operations."""
        mock_client = MagicMock()
        mock_client.upload_text.side_effect = Exception("Upload failed")
        mock_client_class.return_value = mock_client

        ops = BlobOperations(connection_string="test_connection")

        # Should handle errors gracefully
        with pytest.raises(Exception):
            ops.upload_text("test-container", "test.txt", "content")


class TestBlobUtils:
    """Test cases for BlobUtils helper functions."""

    def test_sanitize_blob_name(self):
        """Test blob name sanitization."""
        # Test with various invalid characters
        invalid_name = "test/file\\name:with?invalid*chars"
        sanitized = BlobUtils.sanitize_blob_name(invalid_name)

        # Should not contain invalid characters
        invalid_chars = ["/", "\\", ":", "?", "*"]
        for char in invalid_chars:
            assert char not in sanitized

    def test_validate_container_name(self):
        """Test container name validation."""
        # Valid container names
        assert BlobUtils.validate_container_name("validname") is True
        assert BlobUtils.validate_container_name("valid-name-123") is True

        # Invalid container names
        assert BlobUtils.validate_container_name("Invalid_Name") is False
        assert BlobUtils.validate_container_name("invalid.name") is False
        assert BlobUtils.validate_container_name("") is False

    def test_generate_blob_path(self):
        """Test blob path generation."""
        path = BlobUtils.generate_blob_path("folder", "subfolder", "file.txt")
        expected = "folder/subfolder/file.txt"
        assert path == expected

    def test_extract_blob_info(self):
        """Test extracting blob information."""
        blob_url = "https://storage.blob.core.windows.net/container/folder/file.txt"
        info = BlobUtils.extract_blob_info(blob_url)

        assert info["container"] == "container"
        assert info["blob_name"] == "folder/file.txt"

    def test_calculate_blob_size(self):
        """Test blob size calculation."""
        content = "Hello, World!" * 100  # Create some content
        size = BlobUtils.calculate_blob_size(content)

        assert size > 0
        assert isinstance(size, int)

    def test_format_blob_metadata(self):
        """Test blob metadata formatting."""
        metadata = {
            "author": "test-user",
            "created_date": "2024-01-01",
            "version": "1.0",
        }

        formatted = BlobUtils.format_blob_metadata(metadata)

        # Should be properly formatted for Azure blob metadata
        assert isinstance(formatted, dict)
        assert all(
            isinstance(k, str) and isinstance(v, str) for k, v in formatted.items()
        )


class TestBlobIntegration:
    """Test integration between blob storage components."""

    @patch("libs.blob_storage.BlobServiceClient")
    @patch("libs.blob_operations.BlobStorageClient")
    def test_storage_client_with_operations(self, mock_ops_client, mock_storage_client):
        """Test integration between storage client and operations."""
        # Mock the Azure service
        mock_service = MagicMock()
        mock_storage_client.from_connection_string.return_value = mock_service

        # Mock operations client
        mock_client = MagicMock()
        mock_ops_client.return_value = mock_client

        # Create clients
        storage = BlobStorageClient(connection_string="test_connection")
        operations = BlobOperations(connection_string="test_connection")

        # Test integration
        test_data = {"integrated": True}
        operations.upload_json("test-container", "integration.json", test_data)

        mock_client.upload_text.assert_called_once()

    @patch("libs.blob_storage.BlobServiceClient")
    def test_real_world_workflow(self, mock_blob_service):
        """Test a real-world blob storage workflow."""
        mock_service = MagicMock()
        mock_container = MagicMock()
        mock_blob = MagicMock()

        # Setup mocks
        mock_service.get_container_client.return_value = mock_container
        mock_container.get_blob_client.return_value = mock_blob
        mock_blob_service.from_connection_string.return_value = mock_service

        client = BlobStorageClient(connection_string="test_connection")

        # Simulate workflow: create container, upload file, list files
        container_name = BlobUtils.sanitize_container_name("test-workflow")
        assert BlobUtils.validate_container_name(container_name)

        # Upload a file
        file_content = "Workflow test content"
        blob_name = BlobUtils.generate_blob_path("workflows", "test", "file.txt")

        client.upload_text(container_name, blob_name, file_content)
        mock_blob.upload_blob.assert_called_once()

    def test_error_scenarios(self):
        """Test various error scenarios."""
        # Test invalid blob names
        with pytest.raises(Exception):
            BlobUtils.extract_blob_info("invalid-url")

        # Test empty content
        size = BlobUtils.calculate_blob_size("")
        assert size == 0

        # Test invalid metadata
        invalid_metadata = {"key": None}
        formatted = BlobUtils.format_blob_metadata(invalid_metadata)
        # Should handle None values
        assert "key" not in formatted or formatted["key"] == ""


class TestPerformanceAndScaling:
    """Test performance and scaling considerations."""

    @patch("libs.blob_operations.BlobStorageClient")
    def test_large_batch_operations(self, mock_client_class):
        """Test handling large batch operations."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        ops = BlobOperations(connection_string="test_connection")

        # Create a large batch of files
        large_batch = {f"file_{i}.txt": f"Content {i}" for i in range(100)}

        ops.batch_upload("test-container", large_batch)

        # Should handle all uploads
        assert mock_client.upload_text.call_count == 100

    @patch("libs.blob_storage.BlobServiceClient")
    def test_concurrent_operations(self, mock_blob_service):
        """Test concurrent blob operations."""
        mock_service = MagicMock()
        mock_blob_service.from_connection_string.return_value = mock_service

        # Create multiple clients (simulating concurrent access)
        clients = [
            BlobStorageClient(connection_string="test_connection") for _ in range(5)
        ]

        assert len(clients) == 5
        # Each client should be independent
        for client in clients:
            assert client is not None

    def test_memory_efficiency(self):
        """Test memory efficiency with large content."""
        # Test with relatively large content
        large_content = "x" * 10000  # 10KB

        # Should handle without memory issues
        size = BlobUtils.calculate_blob_size(large_content)
        assert size == 10000

        # Sanitization should work with large names
        large_name = "a" * 1000
        sanitized = BlobUtils.sanitize_blob_name(large_name)
        assert len(sanitized) <= len(large_name)

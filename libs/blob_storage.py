"""
Azure Blob Storage Client

Unified facade for blob storage operations using refactored modules.
Provides a single interface for all blob storage needs while delegating
to specialized modules for authentication, operations, utilities, and mocking.

This refactored version significantly reduces complexity by using:
- blob_auth.py for authentication management
- blob_operations.py for upload/download operations
- blob_utils.py for utility functions
- blob_mock.py for testing support
"""

import logging
import os
from typing import Any, Dict, List, Optional, Union

from .blob_auth import BlobAuthManager
from .blob_mock import MockBlobStorage
from .blob_operations import BlobOperations
from .blob_utils import BlobUtils

logger = logging.getLogger(__name__)


class BlobStorageClient:
    """Unified blob storage client facade delegating to specialized modules."""

    def __init__(self):
        self._mock = os.getenv("BLOB_STORAGE_MOCK", "false").lower() == "true"

        if self._mock:
            # Use mock storage for testing
            self.mock_storage = MockBlobStorage()
            self.blob_service_client = None
            self.operations = None
            self.utils = None
            logger.info("Blob storage client initialized in MOCK mode")
        else:
            # Use real Azure storage
            self.auth_manager = BlobAuthManager()
            self.blob_service_client = self.auth_manager.get_blob_service_client()
            self.operations = BlobOperations(self.blob_service_client)
            self.utils = BlobUtils(self.blob_service_client)
            self.mock_storage = None
            logger.info("Blob storage client initialized with Azure authentication")

    def test_connection(self, timeout_seconds: float = None) -> Dict[str, Any]:
        """Test blob storage connection."""
        if self._mock:
            return {
                "status": "healthy",
                "connection_type": "mock",
                "message": "Mock storage client is working",
            }

        return self.auth_manager.test_connection(timeout_seconds)

    def ensure_container(self, container_name: str):
        """Ensure container exists (containers are created by Terraform in production)."""
        if self._mock:
            return self.mock_storage.ensure_container(container_name)
        else:
            return self.blob_service_client.get_container_client(container_name)

    # Upload operations - delegate to operations module
    async def upload_json(
        self, container_name: str, blob_name: str, data: Dict[str, Any], **kwargs
    ) -> str:
        """Upload JSON data to blob storage."""
        if self._mock:
            self.mock_storage.upload_data(
                container_name, blob_name, data, "application/json"
            )
            return f"mock://{container_name}/{blob_name}"
        else:
            return self.operations.upload_data(
                container_name, blob_name, data, "application/json", **kwargs
            )

    async def upload_text(
        self, container_name: str, blob_name: str, content: str, **kwargs
    ) -> str:
        """Upload text content to blob storage."""
        if self._mock:
            self.mock_storage.upload_data(
                container_name, blob_name, content, "text/plain"
            )
            return f"mock://{container_name}/{blob_name}"
        else:
            return self.operations.upload_data(
                container_name, blob_name, content, "text/plain", **kwargs
            )

    async def upload_text_with_success(
        self, container_name: str, blob_name: str, content: str, **kwargs
    ) -> bool:
        """Upload text and return boolean success."""
        try:
            await self.upload_text(container_name, blob_name, content, **kwargs)
            return True
        except Exception:
            return False

    async def upload_binary(
        self, container_name: str, blob_name: str, data: bytes, **kwargs
    ) -> str:
        """Upload binary data to blob storage."""
        if self._mock:
            self.mock_storage.upload_data(
                container_name, blob_name, data, "application/octet-stream"
            )
            return f"mock://{container_name}/{blob_name}"
        else:
            return self.operations.upload_data(
                container_name, blob_name, data, "application/octet-stream", **kwargs
            )

    def upload_html_site(
        self, container_name: str, site_files: Dict[str, str], **kwargs
    ) -> Dict[str, str]:
        """Upload an entire HTML site to blob storage.

        Args:
            container_name (str): The name of the blob container.
            site_files (Dict[str, str]): Dictionary mapping file paths to file contents.
            **kwargs: Additional arguments passed to the upload operation.

        Returns:
            Dict[str, str]: Dictionary mapping file paths to their blob URLs.
        """
        if self._mock:
            # Mock implementation - return mock URLs for all files
            uploaded = {}
            for file_path in site_files.keys():
                uploaded[file_path] = f"mock://{container_name}/{file_path}"
            return uploaded
        else:
            # Use operations module for real upload
            return self.operations.upload_site_files(
                container_name, site_files, **kwargs
            )

    # Download operations - delegate to operations module
    async def blob_exists(self, container_name: str, blob_name: str) -> bool:
        """Check if blob exists."""
        if self._mock:
            return self.mock_storage.blob_exists(container_name, blob_name)
        else:
            return self.operations.blob_exists(container_name, blob_name)

    async def download_json(
        self, container_name: str, blob_name: str, **kwargs
    ) -> Dict[str, Any]:
        """Download and parse JSON data from blob.

        Returns:
            Dict[str, Any]: Parsed JSON data, or an empty dict if the blob does not exist or is invalid.
        """
        if self._mock:
            result = self.mock_storage.download_json(container_name, blob_name)
        else:
            result = self.operations.download_json(container_name, blob_name)
        return result if result is not None else {}

    async def download_text(self, container_name: str, blob_name: str) -> str:
        """Download text content from blob."""
        if self._mock:
            return self.mock_storage.download_text(container_name, blob_name)
        else:
            return self.operations.download_text(container_name, blob_name)

    # Utility operations - delegate to utils module
    async def list_blobs(
        self, container_name: str, prefix: str = "", **kwargs
    ) -> List[Dict[str, Any]]:
        """List blobs in container."""
        if self._mock:
            return self.mock_storage.list_blobs(container_name, prefix)
        else:
            return self.utils.list_blobs(container_name, prefix, **kwargs)

    async def delete_blob(self, container_name: str, blob_name: str) -> bool:
        """Delete blob from storage."""
        if self._mock:
            return self.mock_storage.delete_blob(container_name, blob_name)
        else:
            return self.operations.delete_blob(container_name, blob_name)

    def get_blob_url(self, container_name: str, blob_name: str) -> str:
        """Get blob URL."""
        if self._mock:
            return f"mock://{container_name}/{blob_name}"
        else:
            return self.utils.get_blob_url(container_name, blob_name)

    def _get_content_type(self, file_path: str) -> str:
        """Get content type for file."""
        if self._mock:
            return "application/octet-stream"
        else:
            return self.utils.get_content_type(file_path)

    def health_check(self) -> Dict[str, Any]:
        """Health check with fast timeout."""
        return self.test_connection(timeout_seconds=5)


# Factory function and utilities
def get_blob_client() -> BlobStorageClient:
    """Get blob storage client instance."""
    return BlobStorageClient()


def get_timestamped_blob_name(prefix: str, extension: str = "json") -> str:
    """Generate timestamped blob name."""
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"


# Export the main classes and utilities
__all__ = ["BlobStorageClient", "get_blob_client", "get_timestamped_blob_name"]

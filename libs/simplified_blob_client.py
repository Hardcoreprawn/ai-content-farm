"""
Simplified Blob Storage Client - Production Implementation

Clean, focused API with only essential operations.
Replaces the bloated BlobOperations class with 8 core methods.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from azure.storage.blob import BlobServiceClient

from libs.blob_auth import BlobAuthManager

logger = logging.getLogger(__name__)


class SimplifiedBlobClient:
    """Focused blob storage client with only essential operations."""

    def __init__(self, blob_service_client: Optional[BlobServiceClient] = None):
        if blob_service_client:
            # Use provided client (for dependency injection)
            self.blob_service_client = blob_service_client
        else:
            # Create our own Azure client using auth manager
            self.auth_manager = BlobAuthManager()
            self.blob_service_client = self.auth_manager.get_blob_service_client()
            logger.info("SimplifiedBlobClient initialized with Azure authentication")

    def test_connection(self, timeout_seconds: float = None) -> Dict[str, Any]:
        """Test blob storage connection."""
        try:
            # Simple test - try to list containers (lightweight operation)
            containers = list(self.blob_service_client.list_containers())
            return {
                "status": "healthy",
                "connection_type": "azure",
                "message": f"Azure blob storage connection successful. Found {len(containers)} containers.",
            }
        except Exception as e:
            return {
                "status": "error",
                "connection_type": "azure",
                "message": f"Azure blob storage connection failed: {str(e)}",
            }

    async def upload_json(
        self,
        container: str,
        blob_name: str,
        data: Dict[str, Any],
        overwrite: bool = True,
    ) -> bool:
        """Upload JSON data. This covers 90% of all uploads."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container, blob=blob_name
            )

            json_bytes = json.dumps(data, indent=2).encode("utf-8")
            blob_client.upload_blob(
                json_bytes, overwrite=overwrite, content_type="application/json"
            )

            logger.info(f"Uploaded JSON to {container}/{blob_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to upload JSON to {container}/{blob_name}: {e}")
            return False

    async def download_json(
        self, container: str, blob_name: str
    ) -> Optional[Dict[str, Any]]:
        """Download and parse JSON. This covers 90% of all downloads."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container, blob=blob_name
            )

            content = blob_client.download_blob().readall()
            if isinstance(content, bytes):
                content = content.decode("utf-8")

            return json.loads(content)

        except Exception as e:
            logger.error(f"Failed to download JSON from {container}/{blob_name}: {e}")
            return None

    async def upload_text(
        self, container: str, blob_name: str, text: str, overwrite: bool = True
    ) -> bool:
        """Upload text content. For generated articles, logs, etc."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container, blob=blob_name
            )

            blob_client.upload_blob(
                text.encode("utf-8"), overwrite=overwrite, content_type="text/plain"
            )

            logger.info(f"Uploaded text to {container}/{blob_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to upload text to {container}/{blob_name}: {e}")
            return False

    async def download_text(self, container: str, blob_name: str) -> Optional[str]:
        """Download text content. For markdown articles, templates, etc."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container, blob=blob_name
            )

            content = blob_client.download_blob().readall()
            if isinstance(content, bytes):
                return content.decode("utf-8")
            return str(content)

        except Exception as e:
            logger.error(f"Failed to download text from {container}/{blob_name}: {e}")
            return None

    async def upload_binary(
        self,
        container: str,
        blob_name: str,
        data: bytes,
        content_type: str,
        overwrite: bool = True,
    ) -> bool:
        """Upload binary content. For images, audio, video, PDFs, etc."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container, blob=blob_name
            )

            blob_client.upload_blob(
                data, overwrite=overwrite, content_type=content_type
            )

            logger.info(f"Uploaded binary to {container}/{blob_name} ({content_type})")
            return True

        except Exception as e:
            logger.error(f"Failed to upload binary to {container}/{blob_name}: {e}")
            return False

    async def download_binary(self, container: str, blob_name: str) -> Optional[bytes]:
        """Download binary content. For images, audio, video, PDFs, etc."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container, blob=blob_name
            )

            return blob_client.download_blob().readall()

        except Exception as e:
            logger.error(f"Failed to download binary from {container}/{blob_name}: {e}")
            return None

    async def list_blobs(
        self, container: str, prefix: str = ""
    ) -> List[Dict[str, Any]]:
        """List blobs with metadata. Essential for discovery and cleanup."""
        try:
            container_client = self.blob_service_client.get_container_client(container)
            return [
                {
                    "name": blob.name,
                    "size": blob.size,
                    "last_modified": blob.last_modified,
                    "content_type": (
                        blob.content_settings.content_type
                        if blob.content_settings
                        else None
                    ),
                }
                for blob in container_client.list_blobs(name_starts_with=prefix)
            ]
        except Exception as e:
            logger.error(f"Failed to list blobs in {container}: {e}")
            return []

    async def delete_blob(self, container: str, blob_name: str) -> bool:
        """Delete a blob. Essential for cleanup operations."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container, blob=blob_name
            )
            blob_client.delete_blob()
            logger.info(f"Deleted {container}/{blob_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {container}/{blob_name}: {e}")
            return False


# Compatibility layer for gradual migration
class BlobClientAdapter:
    """
    Adapter to make SimplifiedBlobClient compatible with existing container code.
    Provides old method names that delegate to new simplified methods.
    """

    def __init__(self, simplified_client: SimplifiedBlobClient):
        self._client = simplified_client

    # Legacy method compatibility
    async def download_data(self, container_name: str, blob_name: str) -> Optional[str]:
        """Legacy method - use download_text() instead."""
        return await self._client.download_text(container_name, blob_name)

    async def upload_data(
        self,
        container_name: str,
        blob_name: str,
        data: str,
        content_type: str = "text/plain",
        overwrite: bool = True,
    ) -> bool:
        """Legacy method - use upload_text() instead."""
        return await self._client.upload_text(
            container_name, blob_name, data, overwrite
        )

    async def download_json(
        self, container_name: str, blob_name: str
    ) -> Optional[Dict]:
        """Legacy method - already matches new API."""
        return await self._client.download_json(container_name, blob_name)

    async def upload_json_data(
        self, container_name: str, blob_name: str, data: Dict
    ) -> bool:
        """Legacy method - use upload_json() instead."""
        return await self._client.upload_json(container_name, blob_name, data)

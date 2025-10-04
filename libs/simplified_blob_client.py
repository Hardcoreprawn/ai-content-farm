"""
Simplified Blob Storage Client

Focused blob storage operations with functional datetime serialization.
Uses pure functions internally for predictability and testability.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from azure.storage.blob import BlobServiceClient

from libs.blob_auth import BlobAuthManager
from libs.blob_paths import BlobPathManager

logger = logging.getLogger(__name__)


# ============================================================================
# FUNCTIONAL DATETIME SERIALIZATION (Internal Helper)
# Pure function for converting datetime objects - used internally by the class
# ============================================================================


def serialize_datetime(obj: Any) -> Any:
    """
    Pure function to recursively convert datetime objects to ISO format strings.

    This is used internally by upload_json() to handle datetime serialization.
    It's a functional approach: pure, composable, testable, thread-safe.

    Args:
        obj: Any Python object (dict, list, datetime, primitive, etc.)

    Returns:
        Same structure with all datetime objects converted to ISO strings
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_datetime(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [serialize_datetime(item) for item in obj]
    else:
        return obj


class SimplifiedBlobClient:
    """Simplified blob storage client with automatic datetime serialization."""

    def __init__(self, blob_service_client: Optional[BlobServiceClient] = None):
        if blob_service_client:
            self.blob_service_client: BlobServiceClient = blob_service_client
        else:
            auth_manager = BlobAuthManager()
            client = auth_manager.get_blob_service_client()
            if not client:
                raise ValueError("Failed to create blob service client")
            self.blob_service_client = client

        self.path_manager = BlobPathManager()
        logger.info("SimplifiedBlobClient initialized")

    def test_connection(
        self, timeout_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """Test blob storage connection."""
        try:
            if not self.blob_service_client:
                return {
                    "status": "error",
                    "connection_type": "azure",
                    "message": "No blob service client available",
                }
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
        """Upload JSON with automatic datetime serialization."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container, blob=blob_name
            )
            # Use functional datetime serialization internally
            serializable_data = serialize_datetime(data)
            json_bytes = json.dumps(serializable_data, indent=2).encode("utf-8")
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
        """Download and parse JSON."""
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
        self,
        container: str,
        blob_name: str,
        text: str,
        overwrite: bool = True,
        content_type: Optional[str] = None,
    ) -> bool:
        """Upload text content with automatic content type detection."""
        try:
            # Auto-detect content type based on file extension if not provided
            if content_type is None:
                if blob_name.endswith(".html"):
                    content_type = "text/html"
                elif blob_name.endswith(".xml"):
                    content_type = "application/xml"
                elif blob_name.endswith(".json"):
                    content_type = "application/json"
                elif blob_name.endswith(".css"):
                    content_type = "text/css"
                elif blob_name.endswith(".js"):
                    content_type = "application/javascript"
                elif blob_name.endswith(".md"):
                    content_type = "text/markdown"
                else:
                    content_type = "text/plain"

            blob_client = self.blob_service_client.get_blob_client(
                container=container, blob=blob_name
            )
            blob_client.upload_blob(
                text.encode("utf-8"), overwrite=overwrite, content_type=content_type
            )
            logger.info(
                f"Uploaded text to {container}/{blob_name} (content_type={content_type})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upload text to {container}/{blob_name}: {e}")
            return False

    async def download_text(self, container: str, blob_name: str) -> Optional[str]:
        """Download text content."""
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
        """Upload binary content."""
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
        """Download binary content."""
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
        """List blobs with metadata."""
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
        """Delete a blob."""
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


class BlobClientAdapter:
    """Adapter that adds standardized path management to SimplifiedBlobClient."""

    def __init__(self, simplified_client: SimplifiedBlobClient):
        self._client = simplified_client

    async def upload_collection(
        self,
        container_name: str,
        source_identifier: str,
        collection_data: Dict[str, Any],
        timestamp: Optional[datetime] = None,
        overwrite: bool = True,
    ) -> str:
        """Upload collection using standardized path naming."""
        blob_path = self._client.path_manager.get_collection_path(
            source_identifier, timestamp
        )
        await self._client.upload_json(
            container_name, blob_path, collection_data, overwrite
        )
        logger.info(f"Uploaded collection to standardized path: {blob_path}")
        return blob_path

    async def upload_processing_result(
        self,
        container_name: str,
        collection_source: str,
        processing_stage: str,
        result_data: Dict[str, Any],
        timestamp: Optional[datetime] = None,
        overwrite: bool = True,
    ) -> str:
        """Upload processing result using standardized path naming."""
        blob_path = self._client.path_manager.get_processing_path(
            collection_source, processing_stage, timestamp
        )
        await self._client.upload_json(
            container_name, blob_path, result_data, overwrite
        )
        logger.info(f"Uploaded processing result to standardized path: {blob_path}")
        return blob_path

    async def download_data(self, container_name: str, blob_name: str) -> Optional[str]:
        """Download text data."""
        return await self._client.download_text(container_name, blob_name)

    async def upload_data(
        self,
        container_name: str,
        blob_name: str,
        data: str,
        content_type: str = "text/plain",
        overwrite: bool = True,
    ) -> bool:
        """Upload text data."""
        return await self._client.upload_text(
            container_name, blob_name, data, overwrite
        )

    async def download_json(
        self, container_name: str, blob_name: str
    ) -> Optional[Dict]:
        """Download JSON data."""
        return await self._client.download_json(container_name, blob_name)

    async def upload_json_data(
        self, container_name: str, blob_name: str, data: Dict
    ) -> bool:
        """Upload JSON data."""
        return await self._client.upload_json(container_name, blob_name, data)

    def get_collection_path(
        self, source_identifier: str, timestamp: Optional[datetime] = None
    ) -> str:
        """Get standardized collection path."""
        return self._client.path_manager.get_collection_path(
            source_identifier, timestamp
        )

    def get_processing_path(
        self,
        collection_source: str,
        processing_stage: str,
        timestamp: Optional[datetime] = None,
    ) -> str:
        """Get standardized processing path."""
        return self._client.path_manager.get_processing_path(
            collection_source, processing_stage, timestamp
        )

    def get_generated_path(
        self, content_type: str, topic_id: str, timestamp: Optional[datetime] = None
    ) -> str:
        """Get standardized generated content path."""
        return self._client.path_manager.get_generated_path(
            content_type, topic_id, timestamp
        )

    def parse_collection_path(self, blob_path: str) -> Optional[Dict[str, str]]:
        """Parse collection path."""
        return self._client.path_manager.parse_collection_path(blob_path)

    def list_collections_by_date(
        self, year: int, month: int, day: int, hour: Optional[int] = None
    ) -> str:
        """Get path prefix for listing collections by date."""
        return self._client.path_manager.list_collections_by_date(
            year, month, day, hour
        )

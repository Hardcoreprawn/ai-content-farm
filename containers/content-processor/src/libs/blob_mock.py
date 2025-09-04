"""
Mock blob storage implementation

Provides in-memory mock storage for testing and development.
Maintains compatibility with real blob storage API.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Module-level stores for mock mode so all instances share state
_MOCK_CONTAINERS: Dict[str, Dict[str, Any]] = {}
_MOCK_BLOBS: Dict[str, Dict[str, Any]] = {}


class MockBlobStorage:
    """In-memory blob storage mock for testing."""

    def __init__(self):
        """Initialize mock storage."""
        logger.info("Mock blob storage initialized")

    def ensure_container(self, container_name: str) -> bool:
        """Ensure container exists in mock storage."""
        if container_name not in _MOCK_CONTAINERS:
            _MOCK_CONTAINERS[container_name] = {
                "name": container_name,
                "created": datetime.now(timezone.utc).isoformat(),
                "blobs": {},
            }
            logger.debug(f"Mock container created: {container_name}")
        return True

    def upload_data(
        self, container_name: str, blob_name: str, data: Any, content_type: str
    ) -> bool:
        """Upload data to mock storage."""
        try:
            self.ensure_container(container_name)

            # Store data based on content type
            if content_type == "application/json":
                stored_data = json.dumps(data) if not isinstance(data, str) else data
            elif isinstance(data, bytes):
                stored_data = data.decode("utf-8", errors="ignore")
            else:
                stored_data = str(data)

            blob_key = f"{container_name}/{blob_name}"
            _MOCK_BLOBS[blob_key] = {
                "data": stored_data,
                "content_type": content_type,
                "size": len(str(stored_data)),
                "last_modified": datetime.now(timezone.utc).isoformat(),
                "container": container_name,
                "name": blob_name,
            }

            logger.debug(f"Mock blob uploaded: {blob_key}")
            return True

        except Exception as e:
            logger.error(f"Mock upload failed for {container_name}/{blob_name}: {e}")
            return False

    def download_data(self, container_name: str, blob_name: str) -> Optional[str]:
        """Download data from mock storage."""
        try:
            blob_key = f"{container_name}/{blob_name}"
            if blob_key in _MOCK_BLOBS:
                return _MOCK_BLOBS[blob_key]["data"]
            else:
                logger.warning(f"Mock blob not found: {blob_key}")
                return None

        except Exception as e:
            logger.error(f"Mock download failed for {container_name}/{blob_name}: {e}")
            return None

    def list_blobs(self, container_name: str, prefix: str = "") -> List[Dict[str, Any]]:
        """List blobs in mock storage."""
        try:
            blobs = []
            for blob_key, blob_data in _MOCK_BLOBS.items():
                container, blob_name = blob_key.split("/", 1)
                if container == container_name and blob_name.startswith(prefix):
                    blobs.append(
                        {
                            "name": blob_name,
                            "size": blob_data["size"],
                            "last_modified": blob_data["last_modified"],
                            "content_type": blob_data["content_type"],
                        }
                    )

            return sorted(blobs, key=lambda x: x["name"])

        except Exception as e:
            logger.error(f"Mock list failed for {container_name}: {e}")
            return []

    def delete_blob(self, container_name: str, blob_name: str) -> bool:
        """Delete blob from mock storage."""
        try:
            blob_key = f"{container_name}/{blob_name}"
            if blob_key in _MOCK_BLOBS:
                del _MOCK_BLOBS[blob_key]
                logger.debug(f"Mock blob deleted: {blob_key}")
                return True
            else:
                logger.warning(f"Mock blob not found for deletion: {blob_key}")
                return False

        except Exception as e:
            logger.error(f"Mock delete failed for {container_name}/{blob_name}: {e}")
            return False

    def list_containers(self) -> List[str]:
        """List all containers in mock storage."""
        return list(_MOCK_CONTAINERS.keys())

    def get_blob_url(self, container_name: str, blob_name: str) -> str:
        """Get mock blob URL."""
        return f"mock://storage/{container_name}/{blob_name}"

    def health_check(self) -> Dict[str, Any]:
        """Get mock storage health status."""
        return {
            "status": "healthy",
            "service": "mock-blob-storage",
            "containers": len(_MOCK_CONTAINERS),
            "total_blobs": len(_MOCK_BLOBS),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

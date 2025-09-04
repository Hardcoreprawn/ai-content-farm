"""
Blob storage utilities module

Provides utility functions for blob storage operations including
listing, health checks, URL generation, and metadata management.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)


class BlobUtils:
    """Utility functions for blob storage operations."""

    def __init__(self, blob_service_client: BlobServiceClient):
        """Initialize with blob service client."""
        self.blob_service_client = blob_service_client

    def list_blobs(
        self, container_name: str, prefix: str = "", include_metadata: bool = False
    ) -> List[Dict[str, Any]]:
        """List blobs in a container with optional prefix filter."""
        try:
            container_client = self.blob_service_client.get_container_client(
                container_name
            )
            blobs = []

            for blob in container_client.list_blobs(name_starts_with=prefix):
                blob_info = {
                    "name": blob.name,
                    "size": blob.size,
                    "last_modified": (
                        blob.last_modified.isoformat() if blob.last_modified else None
                    ),
                    "content_type": getattr(blob, "content_settings", {}).get(
                        "content_type"
                    ),
                    "etag": blob.etag,
                }

                if include_metadata and hasattr(blob, "metadata"):
                    blob_info["metadata"] = blob.metadata

                blobs.append(blob_info)

            logger.debug(
                f"Listed {len(blobs)} blobs from {container_name} with prefix '{prefix}'"
            )
            return blobs

        except ResourceNotFoundError:
            logger.warning(f"Container not found: {container_name}")
            return []
        except Exception as e:
            logger.error(f"Failed to list blobs in {container_name}: {e}")
            return []

    def list_containers(self) -> List[str]:
        """List all containers."""
        try:
            containers = []
            for container in self.blob_service_client.list_containers():
                containers.append(container.name)

            logger.debug(f"Listed {len(containers)} containers")
            return containers

        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            return []

    def blob_exists(self, container_name: str, blob_name: str) -> bool:
        """Check if a blob exists."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )
            return blob_client.exists()

        except Exception as e:
            logger.error(
                f"Failed to check if blob exists {container_name}/{blob_name}: {e}"
            )
            return False

    def get_blob_properties(
        self, container_name: str, blob_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get blob properties and metadata."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )

            properties = blob_client.get_blob_properties()

            return {
                "name": blob_name,
                "container": container_name,
                "size": properties.size,
                "last_modified": (
                    properties.last_modified.isoformat()
                    if properties.last_modified
                    else None
                ),
                "content_type": (
                    properties.content_settings.content_type
                    if properties.content_settings
                    else None
                ),
                "etag": properties.etag,
                "metadata": properties.metadata or {},
                "creation_time": (
                    properties.creation_time.isoformat()
                    if properties.creation_time
                    else None
                ),
            }

        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {container_name}/{blob_name}")
            return None
        except Exception as e:
            logger.error(
                f"Failed to get properties for {container_name}/{blob_name}: {e}"
            )
            return None

    def delete_blob(self, container_name: str, blob_name: str) -> bool:
        """Delete a blob."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )
            blob_client.delete_blob()

            logger.info(f"Deleted blob: {container_name}/{blob_name}")
            return True

        except ResourceNotFoundError:
            logger.warning(f"Blob not found for deletion: {container_name}/{blob_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete blob {container_name}/{blob_name}: {e}")
            return False

    def delete_blobs_by_prefix(
        self, container_name: str, prefix: str
    ) -> Dict[str, Any]:
        """Delete all blobs with a given prefix."""
        try:
            blobs = self.list_blobs(container_name, prefix)
            results = {"deleted": 0, "failed": 0, "errors": []}

            for blob in blobs:
                if self.delete_blob(container_name, blob["name"]):
                    results["deleted"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Failed to delete {blob['name']}")

            logger.info(
                f"Deleted {results['deleted']} blobs with prefix '{prefix}' from {container_name}"
            )
            return results

        except Exception as e:
            logger.error(f"Failed to delete blobs by prefix {prefix}: {e}")
            return {"deleted": 0, "failed": 0, "errors": [str(e)]}

    def get_blob_url(self, container_name: str, blob_name: str) -> str:
        """Get the URL for a blob."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )
            return blob_client.url

        except Exception as e:
            logger.error(f"Failed to get URL for {container_name}/{blob_name}: {e}")
            return ""

    def get_container_stats(self, container_name: str) -> Dict[str, Any]:
        """Get statistics for a container."""
        try:
            blobs = self.list_blobs(container_name)

            total_size = sum(blob.get("size", 0) for blob in blobs)
            total_count = len(blobs)

            # Group by content type
            content_types = {}
            for blob in blobs:
                content_type = blob.get("content_type", "unknown")
                content_types[content_type] = content_types.get(content_type, 0) + 1

            return {
                "container": container_name,
                "total_blobs": total_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "content_types": content_types,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get stats for container {container_name}: {e}")
            return {"error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on blob storage."""
        try:
            # Try to list containers to test connectivity
            containers = self.list_containers()

            return {
                "status": "healthy",
                "service": "azure-blob-storage",
                "containers_count": len(containers),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Blob storage health check failed: {e}")
            return {
                "status": "unhealthy",
                "service": "azure-blob-storage",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def copy_container_contents(
        self, source_container: str, dest_container: str, prefix: str = ""
    ) -> Dict[str, Any]:
        """Copy all blobs from one container to another."""
        try:
            source_blobs = self.list_blobs(source_container, prefix)
            results = {"copied": 0, "failed": 0, "errors": []}

            # Ensure destination container exists
            self._ensure_container_exists(dest_container)

            for blob in source_blobs:
                try:
                    # Copy blob
                    source_blob_client = self.blob_service_client.get_blob_client(
                        container=source_container, blob=blob["name"]
                    )
                    dest_blob_client = self.blob_service_client.get_blob_client(
                        container=dest_container, blob=blob["name"]
                    )

                    dest_blob_client.start_copy_from_url(source_blob_client.url)
                    results["copied"] += 1

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"Failed to copy {blob['name']}: {str(e)}")

            logger.info(
                f"Copied {results['copied']} blobs from {source_container} to {dest_container}"
            )
            return results

        except Exception as e:
            logger.error(f"Failed to copy container contents: {e}")
            return {"copied": 0, "failed": 0, "errors": [str(e)]}

    def _ensure_container_exists(self, container_name: str) -> bool:
        """Ensure a container exists, create if it doesn't."""
        try:
            container_client = self.blob_service_client.get_container_client(
                container_name
            )

            if not container_client.exists():
                container_client.create_container()
                logger.info(f"Created container: {container_name}")

            return True

        except Exception as e:
            logger.error(f"Failed to ensure container exists {container_name}: {e}")
            return False

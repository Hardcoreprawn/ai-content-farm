"""
Azure Blob Storage Client

Shared module for all containers to handle blob storage operations.
Works with both Azurite (local) and Azure Storage (production).
Uses managed identity and secure authentication patterns for Azure environments.
"""

import io
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, BinaryIO, Dict, List, Optional, Union

from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.storage.blob import BlobClient, BlobServiceClient, ContainerClient

logger = logging.getLogger(__name__)


class BlobStorageClient:
    """Unified blob storage client for all environments with secure authentication."""

    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        self.storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

        try:
            if self.environment == "development" and self.connection_string:
                # Local development with Azurite or connection string
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    self.connection_string
                )
                logger.info(
                    "Blob storage client initialized with connection string (development)"
                )

            elif self.storage_account_name:
                # Production/Azure environment - use managed identity
                credential = DefaultAzureCredential()
                account_url = (
                    f"https://{self.storage_account_name}.blob.core.windows.net"
                )
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url, credential=credential
                )
                logger.info(
                    f"Blob storage client initialized with managed identity for account: {self.storage_account_name}"
                )

            else:
                # Fallback to connection string if provided
                if self.connection_string:
                    self.blob_service_client = BlobServiceClient.from_connection_string(
                        self.connection_string
                    )
                    logger.warning(
                        "Using connection string authentication - consider using managed identity for production"
                    )
                else:
                    raise ValueError(
                        "Either AZURE_STORAGE_ACCOUNT_NAME (for managed identity) or "
                        "AZURE_STORAGE_CONNECTION_STRING must be provided"
                    )

        except Exception as e:
            logger.error(f"Failed to initialize blob storage client: {e}")
            raise

    def ensure_container(self, container_name: str) -> ContainerClient:
        """Ensure container exists and return container client."""
        try:
            container_client = self.blob_service_client.get_container_client(
                container_name
            )

            # Try to get container properties to check if it exists
            try:
                container_client.get_container_properties()
                logger.debug(f"Container '{container_name}' already exists")
            except ResourceNotFoundError:
                # Container doesn't exist, create it
                container_client.create_container()
                logger.info(f"Created container '{container_name}'")

            return container_client

        except Exception as e:
            logger.error(f"Failed to ensure container '{container_name}': {e}")
            raise

    def upload_json(
        self,
        container_name: str,
        blob_name: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload JSON data to blob storage."""
        try:
            container_client = self.ensure_container(container_name)

            # Convert data to JSON string
            json_data = json.dumps(data, indent=2, default=str)

            # Prepare metadata
            blob_metadata = {
                "content_type": "application/json",
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "service": "ai-content-farm",
            }
            if metadata:
                blob_metadata.update(metadata)

            # Upload blob
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(
                json_data,
                overwrite=True,
                content_type="application/json",
                metadata=blob_metadata,
            )

            blob_url = blob_client.url
            logger.info(f"Uploaded JSON to blob: {container_name}/{blob_name}")
            return blob_url

        except Exception as e:
            logger.error(f"Failed to upload JSON to {container_name}/{blob_name}: {e}")
            raise

    def upload_text(
        self,
        container_name: str,
        blob_name: str,
        content: str,
        content_type: str = "text/plain",
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload text content to blob storage."""
        try:
            container_client = self.ensure_container(container_name)

            # Prepare metadata
            blob_metadata = {
                "content_type": content_type,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "service": "ai-content-farm",
            }
            if metadata:
                blob_metadata.update(metadata)

            # Upload blob
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(
                content,
                overwrite=True,
                content_type=content_type,
                metadata=blob_metadata,
            )

            blob_url = blob_client.url
            logger.info(f"Uploaded text to blob: {container_name}/{blob_name}")
            return blob_url

        except Exception as e:
            logger.error(f"Failed to upload text to {container_name}/{blob_name}: {e}")
            raise

    def upload_html_site(
        self,
        container_name: str,
        site_files: Dict[str, str],
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Upload an entire HTML site to blob storage."""
        try:
            container_client = self.ensure_container(container_name)

            # Prepare base metadata
            base_metadata = {
                "site_generated_at": datetime.now(timezone.utc).isoformat(),
                "service": "ai-content-farm-ssg",
            }
            if metadata:
                base_metadata.update(metadata)

            uploaded_files = {}

            for file_path, content in site_files.items():
                # Determine content type based on file extension
                content_type = self._get_content_type(file_path)

                # Prepare file-specific metadata
                file_metadata = base_metadata.copy()
                file_metadata["file_path"] = file_path

                # Upload file
                blob_client = container_client.get_blob_client(file_path)
                blob_client.upload_blob(
                    content,
                    overwrite=True,
                    content_type=content_type,
                    metadata=file_metadata,
                )

                uploaded_files[file_path] = blob_client.url
                logger.debug(f"Uploaded site file: {file_path}")

            logger.info(
                f"Uploaded {len(uploaded_files)} site files to container '{container_name}'"
            )
            return uploaded_files

        except Exception as e:
            logger.error(f"Failed to upload site files to {container_name}: {e}")
            raise

    def download_json(self, container_name: str, blob_name: str) -> Dict[str, Any]:
        """Download and parse JSON data from blob storage."""
        try:
            container_client = self.ensure_container(container_name)
            blob_client = container_client.get_blob_client(blob_name)

            blob_data = blob_client.download_blob().readall()
            json_data = json.loads(blob_data.decode("utf-8"))

            logger.debug(f"Downloaded JSON from blob: {container_name}/{blob_name}")
            return json_data

        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {container_name}/{blob_name}")
            return {}
        except Exception as e:
            logger.error(
                f"Failed to download JSON from {container_name}/{blob_name}: {e}"
            )
            raise

    def download_text(self, container_name: str, blob_name: str) -> str:
        """Download text content from blob storage."""
        try:
            container_client = self.ensure_container(container_name)
            blob_client = container_client.get_blob_client(blob_name)

            blob_data = blob_client.download_blob().readall()
            text_content = blob_data.decode("utf-8")

            logger.debug(f"Downloaded text from blob: {container_name}/{blob_name}")
            return text_content

        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {container_name}/{blob_name}")
            return ""
        except Exception as e:
            logger.error(
                f"Failed to download text from {container_name}/{blob_name}: {e}"
            )
            raise

    def list_blobs(self, container_name: str, prefix: str = "") -> List[Dict[str, Any]]:
        """List blobs in a container with optional prefix filter."""
        try:
            container_client = self.ensure_container(container_name)

            blobs = []
            for blob in container_client.list_blobs(name_starts_with=prefix):
                blobs.append(
                    {
                        "name": blob.name,
                        "size": blob.size,
                        "last_modified": blob.last_modified.isoformat()
                        if blob.last_modified
                        else None,
                        "content_type": blob.content_settings.content_type
                        if blob.content_settings
                        else None,
                        "metadata": blob.metadata or {},
                    }
                )

            logger.debug(
                f"Listed {len(blobs)} blobs from {container_name} with prefix '{prefix}'"
            )
            return blobs

        except Exception as e:
            logger.error(f"Failed to list blobs from {container_name}: {e}")
            raise

    def delete_blob(self, container_name: str, blob_name: str) -> bool:
        """Delete a blob from storage."""
        try:
            container_client = self.ensure_container(container_name)
            blob_client = container_client.get_blob_client(blob_name)

            blob_client.delete_blob()
            logger.info(f"Deleted blob: {container_name}/{blob_name}")
            return True

        except ResourceNotFoundError:
            logger.warning(f"Blob not found for deletion: {container_name}/{blob_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete blob {container_name}/{blob_name}: {e}")
            raise

    def get_blob_url(self, container_name: str, blob_name: str) -> str:
        """Get the URL for a blob."""
        try:
            container_client = self.ensure_container(container_name)
            blob_client = container_client.get_blob_client(blob_name)
            return blob_client.url
        except Exception as e:
            logger.error(
                f"Failed to get blob URL for {container_name}/{blob_name}: {e}"
            )
            raise

    def _get_content_type(self, file_path: str) -> str:
        """Determine content type based on file extension."""
        extension = file_path.lower().split(".")[-1] if "." in file_path else ""

        content_types = {
            "html": "text/html",
            "htm": "text/html",
            "css": "text/css",
            "js": "application/javascript",
            "json": "application/json",
            "xml": "application/xml",
            "txt": "text/plain",
            "md": "text/markdown",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "svg": "image/svg+xml",
            "ico": "image/x-icon",
        }

        return content_types.get(extension, "application/octet-stream")

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on blob storage connectivity."""
        try:
            # Try to list containers to verify connectivity
            containers = list(self.blob_service_client.list_containers())

            return {
                "status": "healthy",
                "connection_type": "managed_identity"
                if self.storage_account_name
                else "connection_string",
                "environment": self.environment,
                "storage_account": self.storage_account_name
                or "connection_string_based",
                "containers_accessible": len(containers),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection_type": "managed_identity"
                if self.storage_account_name
                else "connection_string",
                "environment": self.environment,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


# Container names for different services
class BlobContainers:
    """Standard container names for different content types."""

    COLLECTED_CONTENT = "collected-content"
    PROCESSED_CONTENT = "processed-content"
    ENRICHED_CONTENT = "enriched-content"
    RANKED_CONTENT = "ranked-content"
    MARKDOWN_CONTENT = "markdown-content"
    STATIC_SITES = "static-sites"
    PIPELINE_LOGS = "pipeline-logs"
    CMS_EXPORTS = "cms-exports"


def get_blob_client() -> BlobStorageClient:
    """Get a configured blob storage client."""
    return BlobStorageClient()


def get_timestamped_blob_name(prefix: str, extension: str = "json") -> str:
    """Generate a timestamped blob name."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"

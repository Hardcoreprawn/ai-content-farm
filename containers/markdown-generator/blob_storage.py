"""Blob storage client for markdown generator service."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.storage.blob import BlobClient, BlobServiceClient
from config import config

logger = logging.getLogger(__name__)


class BlobStorageClient:
    """Azure Blob Storage client for markdown generator operations."""

    def __init__(self):
        """Initialize blob storage client."""
        if not config.AZURE_STORAGE_CONNECTION_STRING:
            raise ValueError("Azure storage connection string is required")

        self.client = BlobServiceClient.from_connection_string(
            config.AZURE_STORAGE_CONNECTION_STRING
        )

        # Ensure containers exist
        self._ensure_containers_exist()

    def _ensure_containers_exist(self) -> None:
        """Ensure required blob containers exist."""
        containers = [
            config.RANKED_CONTENT_CONTAINER,
            config.GENERATED_CONTENT_CONTAINER,
        ]

        for container_name in containers:
            try:
                self.client.create_container(container_name)
                logger.info(f"Created container: {container_name}")
            except Exception as e:
                if "ContainerAlreadyExists" in str(e):
                    logger.debug(f"Container already exists: {container_name}")
                else:
                    logger.error(f"Error creating container {container_name}: {e}")
                    raise

    async def get_latest_ranked_content(
        self,
    ) -> Optional[Tuple[List[Dict[str, Any]], str]]:
        """
        Get the latest ranked content from blob storage.

        Returns:
            Tuple of (content_items, blob_name) or None if no content found
        """
        try:
            container_client = self.client.get_container_client(
                config.RANKED_CONTENT_CONTAINER
            )

            # List blobs and find the most recent one
            blobs = container_client.list_blobs()
            latest_blob = None
            latest_time = None

            for blob in blobs:
                if blob.name.endswith(".json"):
                    if latest_time is None or blob.last_modified > latest_time:
                        latest_time = blob.last_modified
                        latest_blob = blob.name

            if not latest_blob:
                logger.debug("No ranked content blobs found")
                return None

            # Download and parse the latest blob
            blob_client = container_client.get_blob_client(latest_blob)
            content = blob_client.download_blob().readall()

            try:
                data = json.loads(content)
                content_items = data.get("items", [])

                if content_items:
                    logger.info(
                        f"Retrieved {len(content_items)} ranked items from {latest_blob}"
                    )
                    return content_items, latest_blob
                else:
                    logger.warning(f"No content items found in {latest_blob}")
                    return None

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in blob {latest_blob}: {e}")
                return None

        except ResourceNotFoundError:
            logger.debug(f"Container {config.RANKED_CONTENT_CONTAINER} not found")
            return None
        except AzureError as e:
            logger.error(f"Azure error retrieving ranked content: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving ranked content: {e}")
            return None

    async def save_generated_markdown(
        self,
        markdown_files: List[Dict[str, Any]],
        manifest: Dict[str, Any],
        timestamp: str,
    ) -> str:
        """
        Save generated markdown files and manifest to blob storage.

        Args:
            markdown_files: List of markdown file info
            manifest: Generation manifest
            timestamp: Generation timestamp

        Returns:
            Blob name of the manifest file
        """
        try:
            container_client = self.client.get_container_client(
                config.GENERATED_CONTENT_CONTAINER
            )

            blob_files = []

            # Upload individual markdown files
            for md_file in markdown_files:
                if "content" in md_file:
                    blob_name = f"markdown/{timestamp}/{md_file['slug']}.md"

                    blob_client = container_client.get_blob_client(blob_name)
                    blob_client.upload_blob(
                        md_file["content"], overwrite=True, content_type="text/markdown"
                    )

                    blob_files.append(
                        {
                            "blob_name": blob_name,
                            "slug": md_file["slug"],
                            "title": md_file["title"],
                            "score": md_file["score"],
                        }
                    )

                    logger.debug(f"Uploaded markdown file: {blob_name}")

            # Upload index file if present
            if "index_content" in manifest:
                index_blob_name = f"markdown/{timestamp}/index.md"
                blob_client = container_client.get_blob_client(index_blob_name)
                blob_client.upload_blob(
                    manifest["index_content"],
                    overwrite=True,
                    content_type="text/markdown",
                )
                manifest["index_blob"] = index_blob_name
                logger.debug(f"Uploaded index file: {index_blob_name}")

            # Update manifest with blob information
            manifest["blob_files"] = blob_files
            manifest[
                "storage_location"
            ] = f"blob://{config.GENERATED_CONTENT_CONTAINER}/markdown/{timestamp}/"

            # Upload manifest
            manifest_blob_name = f"manifests/{timestamp}_manifest.json"
            blob_client = container_client.get_blob_client(manifest_blob_name)
            blob_client.upload_blob(
                json.dumps(manifest, indent=2),
                overwrite=True,
                content_type="application/json",
            )

            logger.info(f"Uploaded manifest: {manifest_blob_name}")
            return manifest_blob_name

        except AzureError as e:
            logger.error(f"Azure error saving markdown: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving markdown: {e}")
            raise

    async def check_blob_health(self) -> bool:
        """Check if blob storage is accessible and containers exist."""
        try:
            # Try to list containers
            containers = list(self.client.list_containers())

            # Check if our required containers exist
            container_names = [c.name for c in containers]
            required_containers = [
                config.RANKED_CONTENT_CONTAINER,
                config.GENERATED_CONTENT_CONTAINER,
            ]

            missing_containers = [
                name for name in required_containers if name not in container_names
            ]

            if missing_containers:
                logger.warning(f"Missing containers: {missing_containers}")
                return False

            return True

        except Exception as e:
            logger.error(f"Blob storage health check failed: {e}")
            return False

    async def get_generation_statistics(self) -> Dict[str, Any]:
        """Get statistics about generated content."""
        try:
            container_client = self.client.get_container_client(
                config.GENERATED_CONTENT_CONTAINER
            )

            # Count markdown files and manifests
            markdown_count = 0
            manifest_count = 0

            for blob in container_client.list_blobs():
                if blob.name.startswith("markdown/") and blob.name.endswith(".md"):
                    markdown_count += 1
                elif blob.name.startswith("manifests/") and blob.name.endswith(".json"):
                    manifest_count += 1

            return {
                "markdown_files": markdown_count,
                "manifests": manifest_count,
                "container": config.GENERATED_CONTENT_CONTAINER,
            }

        except Exception as e:
            logger.error(f"Error getting generation statistics: {e}")
            return {"markdown_files": 0, "manifests": 0, "error": str(e)}

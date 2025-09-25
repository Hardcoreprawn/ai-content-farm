"""
Blob storage operations module

Handles core upload and download operations for Azure Blob Storage.
Provides batch operations and file system integration.
"""

import json
import logging
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)


class BlobOperations:
    """Handles blob storage upload and download operations."""

    def __init__(self, blob_service_client: BlobServiceClient):
        """Initialize with blob service client."""
        self.blob_service_client = blob_service_client

    def upload_file(
        self,
        container_name: str,
        blob_name: str,
        file_path: str,
        overwrite: bool = True,
    ) -> bool:
        """Upload a file to blob storage."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )

            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=overwrite)

            logger.info(f"File uploaded: {file_path} -> {container_name}/{blob_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to upload file {file_path}: {e}")
            return False

    def upload_data(
        self,
        container_name: str,
        blob_name: str,
        data: Union[str, bytes, Dict, List],
        content_type: str = "application/octet-stream",
        overwrite: bool = True,
    ) -> bool:
        """Upload data directly to blob storage."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )

            # Convert data to bytes based on type
            if isinstance(data, (dict, list)):
                upload_data = json.dumps(data, indent=2).encode("utf-8")
                if content_type == "application/octet-stream":
                    content_type = "application/json"
            elif isinstance(data, str):
                upload_data = data.encode("utf-8")
                if content_type == "application/octet-stream":
                    content_type = "text/plain"
            elif isinstance(data, bytes):
                upload_data = data
            else:
                upload_data = str(data).encode("utf-8")
                if content_type == "application/octet-stream":
                    content_type = "text/plain"

            blob_client.upload_blob(
                upload_data, overwrite=overwrite, content_type=content_type
            )

            logger.info(f"Data uploaded to {container_name}/{blob_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to upload data to {container_name}/{blob_name}: {e}")
            return False

    def download_to_file(
        self, container_name: str, blob_name: str, file_path: str
    ) -> bool:
        """Download blob to a file."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )

            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "wb") as download_file:
                download_stream = blob_client.download_blob()
                download_file.write(download_stream.readall())

            logger.info(f"Downloaded {container_name}/{blob_name} to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download {container_name}/{blob_name}: {e}")
            return False

    def download_data(self, container_name: str, blob_name: str) -> Optional[str]:
        """Download blob data as string."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )

            download_stream = blob_client.download_blob()
            content = download_stream.readall()

            # Try to decode as UTF-8
            if isinstance(content, bytes):
                return content.decode("utf-8")
            return str(content)

        except Exception as e:
            logger.error(
                f"Failed to download data from {container_name}/{blob_name}: {e}"
            )
            return None

    def download_text(self, container_name: str, blob_name: str) -> str:
        """Download text content from blob. Alias for download_data with non-optional return."""
        result = self.download_data(container_name, blob_name)
        return result if result is not None else ""

    def download_json(self, container_name: str, blob_name: str) -> Optional[Dict]:
        """Download and parse JSON blob."""
        try:
            content = self.download_text(container_name, blob_name)
            if content:
                return json.loads(content)
            return None

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {container_name}/{blob_name}: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Failed to download JSON from {container_name}/{blob_name}: {e}"
            )
            return None

    def upload_articles_batch(
        self, container_name: str, articles: List[Dict[str, Any]], prefix: str = ""
    ) -> Dict[str, Any]:
        """Upload multiple articles in batch."""
        results = {"success": 0, "failed": 0, "errors": []}

        for article in articles:
            try:
                article_id = article.get("id", article.get("topic_id", "unknown"))
                blob_name = (
                    f"{prefix}{article_id}.json" if prefix else f"{article_id}.json"
                )

                if self.upload_data(
                    container_name, blob_name, article, "application/json"
                ):
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Failed to upload {article_id}")

            except Exception as e:
                results["failed"] += 1
                article_id = article.get("id", article.get("topic_id", "unknown"))
                results["errors"].append(f"Error uploading {article_id}: {str(e)}")

        logger.info(
            f"Batch upload completed: {results['success']} successful, {results['failed']} failed"
        )
        return results

    def download_articles_batch(
        self, container_name: str, article_ids: List[str], prefix: str = ""
    ) -> Dict[str, Dict[str, Any]]:
        """Download multiple articles in batch."""
        articles = {}

        for article_id in article_ids:
            try:
                blob_name = (
                    f"{prefix}{article_id}.json" if prefix else f"{article_id}.json"
                )
                article_data = self.download_json(container_name, blob_name)

                if article_data:
                    articles[article_id] = article_data
                else:
                    logger.warning(f"Failed to download article {article_id}")

            except Exception as e:
                logger.error(f"Error downloading article {article_id}: {e}")

        logger.info(
            f"Downloaded {len(articles)} articles from batch of {len(article_ids)}"
        )
        return articles

    def upload_archive(
        self, container_name: str, archive_path: str, blob_name: Optional[str] = None
    ) -> bool:
        """Upload an archive file to blob storage."""
        try:
            if not blob_name:
                blob_name = f"archives/{os.path.basename(archive_path)}"

            return self.upload_file(container_name, blob_name, archive_path)

        except Exception as e:
            logger.error(f"Failed to upload archive {archive_path}: {e}")
            return False

    def download_and_extract(
        self, container_name: str, blob_name: str, extract_path: str
    ) -> bool:
        """Download and extract an archive."""
        try:
            # Download to temporary file
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_file:
                temp_path = temp_file.name

            if not self.download_to_file(container_name, blob_name, temp_path):
                return False

            # Extract archive
            os.makedirs(extract_path, exist_ok=True)
            with zipfile.ZipFile(temp_path, "r") as zip_ref:
                zip_ref.extractall(extract_path)

            # Cleanup
            os.unlink(temp_path)

            logger.info(f"Downloaded and extracted {blob_name} to {extract_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download and extract {blob_name}: {e}")
            return False

    def copy_blob(
        self,
        source_container: str,
        source_blob: str,
        dest_container: str,
        dest_blob: str,
    ) -> bool:
        """Copy blob between containers."""
        try:
            source_blob_client = self.blob_service_client.get_blob_client(
                container=source_container, blob=source_blob
            )
            dest_blob_client = self.blob_service_client.get_blob_client(
                container=dest_container, blob=dest_blob
            )

            # Get source URL
            source_url = source_blob_client.url

            # Copy blob
            dest_blob_client.start_copy_from_url(source_url)

            logger.info(
                f"Copied {source_container}/{source_blob} to {dest_container}/{dest_blob}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to copy blob: {e}")
            return False

    def download_file(
        self, container_name: str, blob_name: str, file_path: str
    ) -> bool:
        """Download a blob to a file (alias for download_to_file)."""
        return self.download_to_file(container_name, blob_name, file_path)

    def upload_json_data(
        self, container_name: str, blob_name: str, data: Dict[str, Any]
    ) -> bool:
        """Upload JSON data to blob storage."""
        try:
            json_string = json.dumps(data)
            return self.upload_data(
                container_name, blob_name, json_string, "application/json"
            )
        except Exception as e:
            logger.error(f"Failed to upload JSON data: {e}")
            return False

    def download_json_data(
        self, container_name: str, blob_name: str
    ) -> Optional[Dict[str, Any]]:
        """Download JSON data from blob storage (alias for download_json)."""
        return self.download_json(container_name, blob_name)

    def list_blobs_in_container(self, container_name: str) -> List[str]:
        """List blob names in a container."""
        try:
            container_client = self.blob_service_client.get_container_client(
                container_name
            )
            blob_names = []
            for blob in container_client.list_blobs():
                blob_names.append(blob.name)
            return blob_names
        except Exception as e:
            logger.error(f"Failed to list blobs in container {container_name}: {e}")
            return []

    def create_container_if_not_exists(self, container_name: str) -> bool:
        """Create a container if it doesn't exist."""
        try:
            container_client = self.blob_service_client.get_container_client(
                container_name
            )
            container_client.create_container()
            logger.info(f"Created container: {container_name}")
            return True
        except Exception as e:
            if "ContainerAlreadyExists" in str(e):
                logger.debug(f"Container {container_name} already exists")
                return True
            logger.error(f"Failed to create container {container_name}: {e}")
            return False

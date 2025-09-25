"""
Processor Storage Service

Handles saving articles and storage operations for the content processor.
Extracted from ContentProcessor to improve maintainability.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from libs.simplified_blob_client import SimplifiedBlobClient

logger = logging.getLogger(__name__)


class ProcessorStorageService:
    """Service for handling storage operations for processed content."""

    def __init__(self, blob_client):
        """
        Initialize storage service.

        Args:
            blob_client: Configured blob storage client
        """
        self.blob_client = blob_client

    async def save_processed_article(self, article_result: Dict[str, Any]) -> bool:
        """
        Save processed article to the processed-content container.

        Args:
            article_result: Complete article data including metadata

        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            # Generate blob name with timestamp and topic ID
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            topic_id = article_result.get("topic_id", "unknown")
            blob_name = f"{timestamp}_{topic_id}.json"

            # Save to processed-content container
            success = await self.blob_client.upload_json(
                container_name="processed-content",
                blob_name=blob_name,
                data=article_result,
            )

            if success:
                logger.info(f"Saved processed article to blob: {blob_name}")
                return True
            else:
                logger.error(f"Failed to save processed article: {blob_name}")
                return False

        except Exception as e:
            logger.error(f"Error saving processed article: {e}")
            return False

    async def test_storage_connectivity(self) -> bool:
        """
        Test blob storage connectivity.

        Returns:
            bool: True if storage is accessible, False otherwise
        """
        try:
            # test_connection returns Dict[str, Any], not awaitable
            result = self.blob_client.test_connection()
            return result.get("status") == "healthy"
        except Exception as e:
            logger.error(f"Blob storage test failed: {e}")
            return False

    async def get_article_count(self, container_name: str = "processed-content") -> int:
        """
        Get count of articles in storage container.

        Args:
            container_name: Name of storage container to count

        Returns:
            int: Number of articles in container, -1 if error
        """
        try:
            # Note: This would need to be implemented in SimplifiedBlobClient
            # For now, return a placeholder
            logger.debug(f"Getting article count for container: {container_name}")
            return 0

        except Exception as e:
            logger.error(f"Error getting article count: {e}")
            return -1

    async def list_recent_articles(
        self, container_name: str = "processed-content", limit: int = 10
    ) -> list:
        """
        List recent articles from storage.

        Args:
            container_name: Name of storage container
            limit: Maximum number of articles to return

        Returns:
            list: List of recent article metadata
        """
        try:
            # Note: This would need to be implemented in SimplifiedBlobClient
            # For now, return empty list
            logger.debug(f"Listing {limit} recent articles from {container_name}")
            return []

        except Exception as e:
            logger.error(f"Error listing recent articles: {e}")
            return []

    def generate_article_blob_name(
        self, topic_id: str, custom_prefix: str = None
    ) -> str:
        """
        Generate standardized blob name for articles.

        Args:
            topic_id: Unique identifier for the topic
            custom_prefix: Optional custom prefix instead of timestamp

        Returns:
            str: Generated blob name
        """
        try:
            if custom_prefix:
                return f"{custom_prefix}_{topic_id}.json"
            else:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                return f"{timestamp}_{topic_id}.json"

        except Exception as e:
            logger.error(f"Error generating blob name for {topic_id}: {e}")
            return f"unknown_{topic_id}.json"

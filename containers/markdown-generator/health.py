"""Health check implementation for markdown generator service."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from libs.blob_storage import BlobStorageClient

from config import config

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health check functionality for markdown generator service."""

    def __init__(self, blob_client: BlobStorageClient):
        """Initialize health checker with blob storage client."""
        self.blob_client = blob_client

    async def check_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.

        Returns:
            Dictionary containing health status and details
        """
        try:
            health_status = {
                "service": config.SERVICE_NAME,
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": config.VERSION,
                "checks": {},
            }

            # Check blob storage connectivity
            try:
                # Test connectivity by listing containers
                containers = self.blob_client.blob_service_client.list_containers()
                list(containers)  # Force evaluation
                blob_healthy = True
            except Exception as e:
                logger.error(f"Blob storage health check failed: {e}")
                blob_healthy = False

            health_status["checks"]["blob_storage"] = {
                "status": "healthy" if blob_healthy else "unhealthy",
                "containers": {
                    "ranked_content": config.RANKED_CONTENT_CONTAINER,
                    "generated_content": config.GENERATED_CONTENT_CONTAINER,
                },
            }

            # Check configuration
            config_healthy = self._check_configuration()
            health_status["checks"]["configuration"] = {
                "status": "healthy" if config_healthy else "unhealthy",
                "required_settings": [
                    "AZURE_STORAGE_CONNECTION_STRING",
                    "RANKED_CONTENT_CONTAINER",
                    "GENERATED_CONTENT_CONTAINER",
                ],
            }

            # Overall status
            if not blob_healthy or not config_healthy:
                health_status["status"] = "unhealthy"

            return health_status

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "service": config.SERVICE_NAME,
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            }

    def _check_configuration(self) -> bool:
        """Check if all required configuration is present."""
        try:
            config.validate_required_settings()
            return True
        except ValueError as e:
            logger.warning(f"Configuration check failed: {e}")
            return False

    async def get_service_status(self, content_watcher=None) -> Dict[str, Any]:
        """
        Get detailed service status including operational metrics.

        Args:
            content_watcher: Optional content watcher instance for status

        Returns:
            Dictionary containing detailed service status
        """
        try:
            # Basic service info
            status: Dict[str, Any] = {
                "service": config.SERVICE_NAME,
                "version": config.VERSION,
                "status": "running",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Content watcher status
            if content_watcher:
                status["content_watcher"] = content_watcher.get_watcher_status()
            else:
                status["content_watcher"] = {
                    "watching": False,
                    "status": "not_initialized",
                }

            # Blob storage status
            try:
                # Test connectivity by listing containers
                containers = self.blob_client.blob_service_client.list_containers()
                list(containers)  # Force evaluation
                blob_healthy = True
            except Exception as e:
                logger.error(f"Blob storage status check failed: {e}")
                blob_healthy = False

            status["blob_storage"] = {
                "healthy": blob_healthy,
                "containers": {
                    "ranked_content": config.RANKED_CONTENT_CONTAINER,
                    "generated_content": config.GENERATED_CONTENT_CONTAINER,
                },
            }

            # File statistics - get basic blob counts
            try:
                ranked_blobs = self.blob_client.list_blobs(
                    config.RANKED_CONTENT_CONTAINER, "ranked-content/"
                )
                generated_blobs = self.blob_client.list_blobs(
                    config.GENERATED_CONTENT_CONTAINER, "markdown/"
                )
                stats = {
                    "ranked_content_files": len(ranked_blobs),
                    "generated_markdown_files": len(generated_blobs),
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }
            except Exception as e:
                logger.error(f"Failed to get file statistics: {e}")
                stats = {
                    "ranked_content_files": 0,
                    "generated_markdown_files": 0,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "error": str(e),
                }
            status["file_statistics"] = stats

            # Configuration status
            status["configuration"] = {
                "watch_interval": config.WATCH_INTERVAL,
                "max_content_items": config.MAX_CONTENT_ITEMS,
                "template_style": config.MARKDOWN_TEMPLATE_STYLE,
                "auto_notification": config.ENABLE_AUTO_NOTIFICATION,
            }

            return status

        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {
                "service": config.SERVICE_NAME,
                "status": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            }

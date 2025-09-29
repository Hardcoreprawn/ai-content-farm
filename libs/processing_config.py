"""
Processing Configuration Manager

Manages processing-specific configuration that can be loaded from blob storage
or fall back to defaults. This provides a flexible approach for managing
container targeting, processing parameters, and other configuration.
"""

import json
import logging
from typing import Dict, Optional

from .app_config import BlobContainers, ProcessingConfig
from .simplified_blob_client import SimplifiedBlobClient

logger = logging.getLogger(__name__)


class ProcessingConfigManager:
    """Manages processing configuration from blob storage with sensible defaults."""

    def __init__(self, blob_client: Optional[SimplifiedBlobClient] = None):
        self.blob_client = blob_client or SimplifiedBlobClient()
        self._config_cache = {}

    async def get_container_config(self, service_name: str) -> Dict[str, str]:
        """
        Get container configuration for a service.

        Loads from blob storage if available, otherwise uses defaults.

        Args:
            service_name: Name of the service (e.g., 'content-processor')

        Returns:
            Dict with input_container, output_container, etc.
        """
        config_key = f"containers_{service_name}"

        if config_key in self._config_cache:
            return self._config_cache[config_key]

        # Try to load from blob storage first
        try:
            config_blob = f"config/{service_name}-containers.json"
            content = await self.blob_client.download_blob(
                container_name=BlobContainers.COLLECTION_TEMPLATES,
                blob_name=config_blob,
            )
            config = json.loads(content)
            self._config_cache[config_key] = config
            logger.info(
                f"✅ CONFIG: Loaded container config for {service_name} from blob storage"
            )
            return config

        except Exception as e:
            logger.info(
                f"ℹ️ CONFIG: Using default container config for {service_name} (blob config not found: {e})"
            )

        # Fall back to defaults
        defaults = self._get_default_container_config(service_name)
        self._config_cache[config_key] = defaults
        return defaults

    def _get_default_container_config(self, service_name: str) -> Dict[str, str]:
        """Get default container configuration for a service."""
        if service_name == "content-processor":
            return {
                "input_container": BlobContainers.COLLECTED_CONTENT,
                "output_container": BlobContainers.PROCESSED_CONTENT,
                "staging_container": BlobContainers.RANKED_CONTENT,
                "collections_prefix": "collections/",
                "processed_prefix": "processed/",
            }
        elif service_name == "content-collector":
            return {
                "output_container": BlobContainers.COLLECTED_CONTENT,
                "templates_container": BlobContainers.COLLECTION_TEMPLATES,
                "collections_prefix": "collections/",
            }
        elif service_name == "site-generator":
            return {
                "input_container": BlobContainers.MARKDOWN_CONTENT,
                "output_container": BlobContainers.STATIC_SITES,
                "source_prefix": "articles/",
                "output_prefix": "sites/",
            }
        else:
            # Generic defaults
            return {
                "input_container": BlobContainers.COLLECTED_CONTENT,
                "output_container": BlobContainers.PROCESSED_CONTENT,
            }

    async def get_processing_config(self, service_name: str) -> Dict:
        """
        Get processing configuration for a service.

        Args:
            service_name: Name of the service

        Returns:
            Dict with batch sizes, thresholds, timeouts, etc.
        """
        config_key = f"processing_{service_name}"

        if config_key in self._config_cache:
            return self._config_cache[config_key]

        # Try to load from blob storage first
        try:
            config_blob = f"config/{service_name}-processing.json"
            content = await self.blob_client.download_blob(
                container_name=BlobContainers.COLLECTION_TEMPLATES,
                blob_name=config_blob,
            )
            config = json.loads(content)
            self._config_cache[config_key] = config
            logger.info(
                f"✅ CONFIG: Loaded processing config for {service_name} from blob storage"
            )
            return config

        except Exception as e:
            logger.info(
                f"ℹ️ CONFIG: Using default processing config for {service_name} (blob config not found: {e})"
            )

        # Fall back to defaults
        defaults = self._get_default_processing_config(service_name)
        self._config_cache[config_key] = defaults
        return defaults

    def _get_default_processing_config(self, service_name: str) -> Dict:
        """Get default processing configuration for a service."""
        if service_name == "content-processor":
            return {
                "default_batch_size": ProcessingConfig.DEFAULT_BATCH_SIZE,
                "max_batch_size": ProcessingConfig.MAX_BATCH_SIZE,
                "default_priority_threshold": 0.5,
                "timeout_seconds": ProcessingConfig.DEFAULT_TIMEOUT,
                "min_content_length": ProcessingConfig.MIN_CONTENT_LENGTH,
                "max_content_length": ProcessingConfig.MAX_CONTENT_LENGTH,
            }
        elif service_name == "content-collector":
            return {
                "enhanced_contracts_enabled": True,
                "max_items_per_collection": 100,
                "collection_timeout_seconds": 300,
                "retry_attempts": 3,
                "retry_delay_seconds": 5,
                "default_subreddits": ["technology", "programming", "python"],
                "rate_limit_requests_per_minute": 60,
                "batch_size": 25,
            }
        else:
            # Generic defaults
            return {
                "default_batch_size": 10,
                "max_batch_size": 100,
                "timeout_seconds": 300,
            }

    def clear_cache(self):
        """Clear the configuration cache to force reload."""
        self._config_cache.clear()

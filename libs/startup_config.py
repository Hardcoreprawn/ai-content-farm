"""
Standardized Startup Configuration Loader

Provides consistent configuration loading across all containers with:
- Single load at startup
- Sensible defaults if blob config fails
- Non-blocking/opportunistic loading
- Cached configuration for container lifetime
"""

import logging
import os
from typing import Any, Dict, Optional

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)


class StartupConfigLoader:
    """Standardized configuration loader for container startup."""

    def __init__(self, service_name: str):
        """
        Initialize config loader for a specific service.

        Args:
            service_name: Name of the service (e.g., 'site-generator', 'content-processor')
        """
        self.service_name = service_name
        self._config_cache = None
        self._initialized = False

    async def load_initial_configuration(
        self,
        config_location: Optional[str] = None,
        default_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Load configuration once at startup with fallback to defaults.

        Args:
            config_location: Blob path in format "container/path/to/config.json"
                           If None, uses environment variable or constructs default path
            default_config: Default configuration to use if blob loading fails

        Returns:
            Configuration dictionary (either from blob or defaults)
        """
        if self._initialized:
            logger.info(f"Configuration already loaded for {self.service_name}")
            return self._config_cache

        logger.info(f"🔧 Loading initial configuration for {self.service_name}...")

        # Determine config location
        if not config_location:
            config_location = os.getenv(
                f"{self.service_name.upper().replace('-', '_')}_CONFIG_LOCATION",
                f"collection-templates/config/{self.service_name}-containers.json",
            )

        # Set up sensible defaults
        if not default_config:
            default_config = self._get_service_defaults()

        # Attempt to load from blob storage (opportunistic/non-blocking)
        config = await self._load_from_blob(config_location, default_config)

        # Cache the configuration
        self._config_cache = config
        self._initialized = True

        logger.info(f"✅ Configuration loaded for {self.service_name}")
        logger.info(f"📋 Active config: {config}")

        return config

    async def _load_from_blob(
        self, config_location: str, default_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Attempt to load configuration from blob storage with fallback to defaults.

        Args:
            config_location: Blob path in format "container/path/to/config.json"
            default_config: Fallback configuration

        Returns:
            Configuration dictionary
        """
        try:
            # Parse blob location
            parts = config_location.split("/", 1)
            if len(parts) != 2:
                logger.warning(f"Invalid config location format: {config_location}")
                return default_config

            container_name, blob_name = parts

            # Initialize blob client
            storage_account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
            if not storage_account_url:
                logger.warning(
                    "AZURE_STORAGE_ACCOUNT_URL not set, using default config"
                )
                return default_config

            credential = DefaultAzureCredential()
            blob_service_client = BlobServiceClient(
                account_url=storage_account_url, credential=credential
            )

            # Download configuration
            blob_client = blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )

            content = blob_client.download_blob().readall()
            if isinstance(content, bytes):
                content = content.decode("utf-8")

            import json

            blob_config = json.loads(content)

            logger.info(f"📥 Loaded configuration from blob: {config_location}")
            return blob_config

        except Exception as e:
            logger.warning(f"Failed to load config from blob {config_location}: {e}")
            logger.info("🔄 Falling back to default configuration")
            return default_config

    def _get_service_defaults(self) -> Dict[str, Any]:
        """Get sensible defaults for the service."""

        # Common defaults for all services
        base_defaults = {
            "description": f"Default configuration for {self.service_name}",
            "version": "1.0",
            "last_updated": "startup",
        }

        # Service-specific defaults
        if self.service_name == "site-generator":
            return {
                **base_defaults,
                "input_container": "processed-content",
                "output_container": "markdown-content",
                "static_sites_container": "static-sites",
                "input_prefix": "articles/",
                "markdown_prefix": "articles/",
                "sites_prefix": "sites/",
            }
        elif self.service_name == "content-processor":
            return {
                **base_defaults,
                "input_container": "collected-content",
                "output_container": "processed-content",
                "input_prefix": "articles/",
                "output_prefix": "articles/",
            }
        elif self.service_name == "content-collector":
            return {
                **base_defaults,
                "output_container": "collected-content",
                "templates_container": "collection-templates",
                "output_prefix": "articles/",
            }
        else:
            return base_defaults

    def get_cached_config(self) -> Optional[Dict[str, Any]]:
        """Get the cached configuration if available."""
        return self._config_cache if self._initialized else None


# Convenience function for easy integration
async def load_service_config(
    service_name: str,
    config_location: Optional[str] = None,
    default_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to load service configuration.

    Args:
        service_name: Name of the service
        config_location: Optional blob path for config
        default_config: Optional default configuration

    Returns:
        Configuration dictionary
    """
    loader = StartupConfigLoader(service_name)
    return await loader.load_initial_configuration(config_location, default_config)

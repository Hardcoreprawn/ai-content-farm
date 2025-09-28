"""
Site Generator Configuration

Blob-based configuration for the static site generator.
Uses ProcessingConfigManager for dynamic configuration management.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional

# Add the project root to Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from libs.processing_config import ProcessingConfigManager
from libs.simplified_blob_client import SimplifiedBlobClient


class Config:
    """Configuration management for site generator using blob-based config."""

    def __init__(self):
        self.blob_client = SimplifiedBlobClient()
        self.config_manager = ProcessingConfigManager(self.blob_client)
        self._container_config = None
        self._processing_config = None

    async def initialize(self):
        """Initialize configuration from blob storage."""
        self._container_config = await self.config_manager.get_container_config(
            "site-generator"
        )
        self._processing_config = await self.config_manager.get_processing_config(
            "site-generator"
        )

    @property
    def PROCESSED_CONTENT_CONTAINER(self) -> str:
        """Get the processed content container name."""
        if not self._container_config:
            return "processed-content"  # fallback
        return self._container_config.get("input_container", "processed-content")

    @property
    def MARKDOWN_CONTENT_CONTAINER(self) -> str:
        """Get the markdown content container name."""
        if not self._container_config:
            return "markdown-content"  # fallback
        return self._container_config.get("output_container", "markdown-content")

    @property
    def STATIC_SITES_CONTAINER(self) -> str:
        """Get the static sites container name."""
        if not self._container_config:
            return "static-sites"  # fallback
        return self._container_config.get("static_sites_container", "static-sites")

    # Publishing Configuration (still from environment for now)
    PUBLISH_METHOD: str = os.environ.get(
        "PUBLISH_METHOD", "direct"
    )  # direct, archive, both
    WEB_CONTAINER: str = os.environ.get("WEB_CONTAINER", "$web")

    # Deployment target configuration for future static web apps migration
    DEPLOYMENT_TARGET: str = os.environ.get(
        "DEPLOYMENT_TARGET", "blob_storage"
    )  # blob_storage, static_web_apps

    # Site Configuration (still from environment for now)
    SITE_TITLE: str = os.environ.get("SITE_TITLE", "JabLab Tech News")
    SITE_DESCRIPTION: str = os.environ.get(
        "SITE_DESCRIPTION", "AI-curated technology news and insights"
    )
    SITE_DOMAIN: str = os.environ.get("SITE_DOMAIN", "jablab.com")
    SITE_URL: str = os.environ.get("SITE_URL", "https://jablab.com")

    # Azure Storage Configuration - still from environment for auth
    AZURE_STORAGE_CONNECTION_STRING: str = os.environ.get(
        "AZURE_STORAGE_CONNECTION_STRING", ""
    )
    AZURE_STORAGE_ACCOUNT_NAME: str = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME", "")
    AZURE_CLIENT_ID: str = os.environ.get("AZURE_CLIENT_ID", "")

    @property
    def ARTICLES_PER_PAGE(self) -> int:
        """Get articles per page from processing config."""
        if not self._processing_config:
            return 10  # fallback
        return self._processing_config.get("articles_per_page", 10)

    @property
    def MAX_ARTICLES_TOTAL(self) -> int:
        """Get max articles total from processing config."""
        if not self._processing_config:
            return 100  # fallback
        return self._processing_config.get("max_articles_total", 100)

    @property
    def DEFAULT_THEME(self) -> str:
        """Get default theme from processing config."""
        if not self._processing_config:
            return "minimal"  # fallback
        return self._processing_config.get("default_theme", "minimal")

    @property
    def CONCURRENT_OPERATIONS(self) -> int:
        """Get concurrent operations from processing config."""
        if not self._processing_config:
            return 5  # fallback
        return self._processing_config.get("concurrent_operations", 5)

    @property
    def azure_storage_configured(self) -> bool:
        """Check if Azure Storage is properly configured (either connection string or managed identity)."""
        return bool(self.AZURE_STORAGE_CONNECTION_STRING) or bool(
            self.AZURE_STORAGE_ACCOUNT_NAME
        )

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if not self.azure_storage_configured:
            errors.append(
                "Azure Storage configuration required: either AZURE_STORAGE_CONNECTION_STRING "
                "or AZURE_STORAGE_ACCOUNT_NAME must be provided"
            )

        if self.ARTICLES_PER_PAGE <= 0:
            errors.append("ARTICLES_PER_PAGE must be positive")

        if self.MAX_ARTICLES_TOTAL <= 0:
            errors.append("MAX_ARTICLES_TOTAL must be positive")

        return errors

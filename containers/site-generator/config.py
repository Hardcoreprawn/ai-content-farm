"""
Site Generator Configuration

Uses standardized startup configuration for consistent behavior.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add the project root to Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

# Global configuration loaded at startup
_startup_config: Optional[Dict[str, Any]] = None


def set_startup_config(config: Dict[str, Any]):
    """Set the startup configuration."""
    global _startup_config
    _startup_config = config
    logger.info(f"Configuration set: {config}")


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a configuration value with fallback to default."""
    if _startup_config is None:
        logger.warning(f"Configuration not loaded, using default for {key}: {default}")
        return default
    return _startup_config.get(key, default)


class Config:
    """Configuration management for site generator using startup config."""

    def __init__(self):
        pass

    async def initialize(self, startup_config: dict = None):
        """Initialize configuration with startup config."""
        if startup_config:
            set_startup_config(startup_config)
        logger.info("Configuration initialized")

    @property
    def PROCESSED_CONTENT_CONTAINER(self) -> str:
        """Get the processed content container name."""
        return get_config_value("input_container", "processed-content")

    @property
    def MARKDOWN_CONTENT_CONTAINER(self) -> str:
        """Get the markdown content container name."""
        return get_config_value("output_container", "markdown-content")

    @property
    def STATIC_SITES_CONTAINER(self) -> str:
        """Get the static sites container name."""
        return get_config_value("static_sites_container", "static-sites")

    @property
    def INPUT_PREFIX(self) -> str:
        """Get the input prefix for processed content."""
        return get_config_value("input_prefix", "articles/")

    @property
    def MARKDOWN_PREFIX(self) -> str:
        """Get the markdown prefix."""
        return get_config_value("markdown_prefix", "articles/")

    @property
    def SITES_PREFIX(self) -> str:
        """Get the sites prefix."""
        return get_config_value("sites_prefix", "sites/")

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
        return get_config_value("articles_per_page", 10)

    @property
    def MAX_ARTICLES_TOTAL(self) -> int:
        """Get max articles total from processing config."""
        return get_config_value("max_articles_total", 100)

    @property
    def DEFAULT_THEME(self) -> str:
        """Get default theme from processing config."""
        return get_config_value("default_theme", "minimal")

    @property
    def CONCURRENT_OPERATIONS(self) -> int:
        """Get concurrent operations from processing config."""
        return get_config_value("concurrent_operations", 5)

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

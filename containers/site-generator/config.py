"""
Site Generator Configuration

Environment-based configuration for the static site generator.
"""

import os
from typing import Optional


class Config:
    """Configuration management for site generator."""

    # Azure Storage Configuration - supports both connection string and managed identity
    AZURE_STORAGE_CONNECTION_STRING: str = os.environ.get(
        "AZURE_STORAGE_CONNECTION_STRING", ""
    )
    AZURE_STORAGE_ACCOUNT_NAME: str = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME", "")
    AZURE_CLIENT_ID: str = os.environ.get("AZURE_CLIENT_ID", "")

    # Blob Container Names
    PROCESSED_CONTENT_CONTAINER: str = os.environ.get(
        "PROCESSED_CONTENT_CONTAINER", "processed-content"
    )
    MARKDOWN_CONTENT_CONTAINER: str = os.environ.get(
        "MARKDOWN_CONTENT_CONTAINER", "markdown-content"
    )
    STATIC_SITES_CONTAINER: str = os.environ.get(
        "STATIC_SITES_CONTAINER", "static-sites"
    )

    # Publishing Configuration
    PUBLISH_METHOD: str = os.environ.get(
        "PUBLISH_METHOD", "direct"
    )  # direct, archive, both
    WEB_CONTAINER: str = os.environ.get("WEB_CONTAINER", "$web")

    # Deployment target configuration for future static web apps migration
    DEPLOYMENT_TARGET: str = os.environ.get(
        "DEPLOYMENT_TARGET", "blob_storage"
    )  # blob_storage, static_web_apps

    # Site Configuration
    SITE_TITLE: str = os.environ.get("SITE_TITLE", "JabLab Tech News")
    SITE_DESCRIPTION: str = os.environ.get(
        "SITE_DESCRIPTION", "AI-curated technology news and insights"
    )
    SITE_DOMAIN: str = os.environ.get("SITE_DOMAIN", "jablab.com")
    SITE_URL: str = os.environ.get("SITE_URL", "https://jablab.com")

    # Generation Settings
    ARTICLES_PER_PAGE: int = int(os.environ.get("ARTICLES_PER_PAGE", "10"))
    MAX_ARTICLES_TOTAL: int = int(os.environ.get("MAX_ARTICLES_TOTAL", "100"))

    # Theme Settings
    DEFAULT_THEME: str = os.environ.get("DEFAULT_THEME", "minimal")

    # Performance
    CONCURRENT_OPERATIONS: int = int(os.environ.get("CONCURRENT_OPERATIONS", "5"))

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

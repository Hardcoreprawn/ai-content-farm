#!/usr/bin/env python3
"""
Configuration module for Site Generator

Handles environment variables, Azure configuration, and validation.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """Service configuration settings."""

    # Service identity
    service_name: str = "site-generator"
    service_description: str = "Generates static websites from ranked content"
    version: str = "1.0.0"

    # Environment
    environment: str = field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )

    # Azure Storage
    storage_connection_string: str = field(
        default_factory=lambda: os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    )

    # Site generation settings
    default_theme: str = field(
        default_factory=lambda: os.getenv("DEFAULT_THEME", "modern")
    )
    max_articles_per_page: int = field(
        default_factory=lambda: int(os.getenv("MAX_ARTICLES_PER_PAGE", "20"))
    )
    site_title: str = field(
        default_factory=lambda: os.getenv("SITE_TITLE", "AI Content Farm")
    )
    site_description: str = field(
        default_factory=lambda: os.getenv(
            "SITE_DESCRIPTION", "Curated Technology News & Insights"
        )
    )

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.storage_connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING is required")

        if self.environment not in ["development", "staging", "production", "testing"]:
            raise ValueError(f"Invalid environment: {self.environment}")


def get_config() -> ServiceConfig:
    """Get service configuration."""
    return ServiceConfig()


def validate_environment() -> bool:
    """Validate that the environment is properly configured."""
    try:
        from libs.blob_storage import BlobStorageClient

        config = get_config()

        # Test blob storage connectivity
        blob_client = BlobStorageClient()

        # Try to list containers (will create if doesn't exist)
        test_container = f"health-check-{config.service_name}"
        blob_client.ensure_container(test_container)

        logger.info("Environment validation successful")
        return True

    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
        return False

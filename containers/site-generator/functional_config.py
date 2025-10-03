"""
Functional configuration management for site generator.

Provides immutable configuration objects and dependency injection
functions that replace the mutable Config class approach.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

# Third-party imports
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

# Shared library imports
from libs import SecureErrorHandler
from libs.simplified_blob_client import SimplifiedBlobClient

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("site-generator-config")

# Queue configuration constant
QUEUE_NAME = os.getenv("QUEUE_NAME", "site-generation-requests")


@dataclass(frozen=True)
class SiteGeneratorConfig:
    """
    Immutable configuration for site generator operations.

    All configuration values are determined at creation time and cannot be changed,
    ensuring thread safety and predictable behavior.
    """

    # Storage configuration
    AZURE_STORAGE_ACCOUNT_URL: str
    PROCESSED_CONTENT_CONTAINER: str
    MARKDOWN_CONTENT_CONTAINER: str
    STATIC_SITES_CONTAINER: str

    # Queue configuration
    QUEUE_NAME: str

    # Site configuration
    SITE_TITLE: str
    SITE_DESCRIPTION: str
    SITE_DOMAIN: str
    SITE_URL: str

    # Generation settings
    ARTICLES_PER_PAGE: int
    MAX_ARTICLES_TOTAL: int
    DEFAULT_THEME: str

    # Environment
    ENVIRONMENT: str

    def validate(self) -> bool:
        """
        Validate configuration completeness and correctness.

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Validate Azure storage URL format
            if not self.AZURE_STORAGE_ACCOUNT_URL.startswith("https://"):
                logger.error("Azure storage URL must use HTTPS")
                return False

            # Validate required containers are specified
            required_containers = [
                self.PROCESSED_CONTENT_CONTAINER,
                self.MARKDOWN_CONTENT_CONTAINER,
                self.STATIC_SITES_CONTAINER,
            ]

            for container in required_containers:
                if not container or not isinstance(container, str):
                    logger.error(f"Invalid container name: {container}")
                    return False

            # Validate site configuration
            if not self.SITE_TITLE or not self.SITE_DOMAIN:
                logger.error("Site title and domain are required")
                return False

            # Validate numeric settings
            if self.ARTICLES_PER_PAGE <= 0 or self.MAX_ARTICLES_TOTAL <= 0:
                logger.error("Article limits must be positive numbers")
                return False

            logger.info("Configuration validation successful")
            return True

        except (ValueError, TypeError, AttributeError) as e:
            # Handle specific validation errors with secure error handling
            error_response = error_handler.handle_error(
                error=e,
                error_type="validation",
                context={"config_validation": "failed"},
                user_message="Configuration validation failed",
            )
            logger.error(
                f"Configuration validation error: {error_response['error_id']}"
            )
            return False
        except Exception as e:
            # Handle unexpected errors securely
            error_response = error_handler.handle_error(
                error=e,
                error_type="configuration",
                context={"config_validation": "unexpected_error"},
            )
            logger.error(
                f"Unexpected configuration error: {error_response['error_id']}"
            )
            return False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary for compatibility.

        Returns:
            Configuration as dictionary
        """
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        }


def load_configuration(
    startup_config: Optional[Dict[str, Any]] = None,
) -> SiteGeneratorConfig:
    """
    Load immutable configuration from environment variables and startup config.

    Pure function that creates configuration from environment and provided overrides.
    No mutable global state or async initialization required.

    Args:
        startup_config: Optional configuration overrides

    Returns:
        Immutable SiteGeneratorConfig instance

    Raises:
        ValueError: If required configuration is missing or invalid
    """
    startup_config = startup_config or {}

    try:
        config = SiteGeneratorConfig(
            # Storage configuration - required
            AZURE_STORAGE_ACCOUNT_URL=startup_config.get(
                "AZURE_STORAGE_ACCOUNT_URL", os.getenv("AZURE_STORAGE_ACCOUNT_URL", "")
            ),
            PROCESSED_CONTENT_CONTAINER=startup_config.get(
                "PROCESSED_CONTENT_CONTAINER",
                os.getenv("PROCESSED_CONTENT_CONTAINER", "processed-content"),
            ),
            MARKDOWN_CONTENT_CONTAINER=startup_config.get(
                "MARKDOWN_CONTENT_CONTAINER",
                os.getenv("MARKDOWN_CONTENT_CONTAINER", "markdown-content"),
            ),
            STATIC_SITES_CONTAINER=startup_config.get(
                "STATIC_SITES_CONTAINER",
                os.getenv("STATIC_SITES_CONTAINER", "$web"),
            ),
            # Queue configuration
            QUEUE_NAME=startup_config.get(
                "QUEUE_NAME",
                os.getenv("QUEUE_NAME", "site-generation-requests"),
            ),
            # Site configuration
            SITE_TITLE=startup_config.get(
                "SITE_TITLE", os.getenv("SITE_TITLE", "JabLab Tech News")
            ),
            SITE_DESCRIPTION=startup_config.get(
                "SITE_DESCRIPTION",
                os.getenv(
                    "SITE_DESCRIPTION", "AI-curated technology news and insights"
                ),
            ),
            SITE_DOMAIN=startup_config.get(
                "SITE_DOMAIN", os.getenv("SITE_DOMAIN", "jablab.dev")
            ),
            SITE_URL=startup_config.get(
                "SITE_URL", os.getenv("SITE_URL", "https://jablab.dev")
            ),
            # Generation settings
            ARTICLES_PER_PAGE=int(
                startup_config.get(
                    "ARTICLES_PER_PAGE", os.getenv("ARTICLES_PER_PAGE", "10")
                )
            ),
            MAX_ARTICLES_TOTAL=int(
                startup_config.get(
                    "MAX_ARTICLES_TOTAL", os.getenv("MAX_ARTICLES_TOTAL", "100")
                )
            ),
            DEFAULT_THEME=startup_config.get(
                "DEFAULT_THEME", os.getenv("DEFAULT_THEME", "minimal")
            ),
            # Environment
            ENVIRONMENT=startup_config.get(
                "ENVIRONMENT", os.getenv("ENVIRONMENT", "development")
            ),
        )

        # Validate configuration
        if not config.validate():
            raise ValueError("Configuration validation failed")

        logger.info(f"Loaded configuration for environment: {config.ENVIRONMENT}")
        return config

    except (ValueError, TypeError) as e:
        logger.error(f"Configuration loading failed: {e}")
        raise ValueError(f"Invalid configuration: {e}")


def create_blob_client(config: SiteGeneratorConfig) -> SimplifiedBlobClient:
    """
    Create and configure blob storage client.

    Pure function that creates blob client with provided configuration.

    Args:
        config: Site generator configuration

    Returns:
        Configured SimplifiedBlobClient instance

    Returns:
        Initialized SimplifiedBlobClient

    Raises:
        ValueError: If blob client creation fails
    """
    try:
        # Create blob service client with managed identity
        credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(
            account_url=config.AZURE_STORAGE_ACCOUNT_URL, credential=credential
        )

        # Create simplified blob client
        blob_client = SimplifiedBlobClient(blob_service_client)

        logger.debug("Created blob storage client with managed identity")
        return blob_client

    except (ValueError, TypeError) as e:
        # Handle specific Azure credential/configuration errors
        error_response = error_handler.handle_error(
            error=e,
            error_type="configuration",
            context={"blob_client_creation": "credential_error"},
            user_message="Storage configuration error",
        )
        logger.error(f"Blob client creation failed: {error_response['error_id']}")
        raise ValueError("Blob client creation failed") from e
    except Exception as e:
        # Handle unexpected errors securely
        error_response = error_handler.handle_error(
            error=e,
            error_type="service_unavailable",
            context={"blob_client_creation": "unexpected_error"},
        )
        logger.error(f"Unexpected blob client error: {error_response['error_id']}")
        raise ValueError("Blob client creation failed") from e


def create_generator_context(
    startup_config: Optional[Dict[str, Any]] = None, generator_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create complete generator context with all dependencies.

    Pure function that creates all necessary dependencies for site generation
    operations. Returns immutable context dictionary.

    Args:
        startup_config: Optional configuration overrides
        generator_id: Optional generator identifier

    Returns:
        Generator context dictionary with config, blob_client, and metadata

    Raises:
        ValueError: If context creation fails
    """
    try:
        # Load configuration
        config = load_configuration(startup_config)

        # Create blob client
        blob_client = create_blob_client(config)

        # Create generator metadata
        generator_id = generator_id or str(uuid4())[:8]

        # Return immutable context
        return {
            "config": config,
            "blob_client": blob_client,
            "generator_id": generator_id,
            "config_dict": config.to_dict(),  # For backward compatibility
            "created_at": "utcnow().isoformat()",
        }

    except Exception as e:
        logger.error(f"Generator context creation failed: {e}")
        raise ValueError(f"Context creation failed: {e}")


# Configuration validation functions


def validate_storage_connectivity(config: SiteGeneratorConfig) -> bool:
    """
    Validate that storage account is accessible.

    Args:
        config: Site generator configuration

    Returns:
        True if storage is accessible, False otherwise
    """
    try:
        blob_client = create_blob_client(config)

        # Try to list containers (basic connectivity test)
        credential = DefaultAzureCredential()
        service_client = BlobServiceClient(
            account_url=config.AZURE_STORAGE_ACCOUNT_URL, credential=credential
        )

        # Quick connectivity test
        list(service_client.list_containers(max_results=1))

        logger.debug("Storage connectivity validated")
        return True

    except Exception as e:
        logger.error(f"Storage connectivity validation failed: {e}")
        return False


async def validate_required_containers(config: SiteGeneratorConfig) -> Dict[str, bool]:
    """
    Validate that all required containers exist.

    Args:
        config: Site generator configuration

    Returns:
        Dictionary mapping container names to existence status
    """
    container_status = {}
    required_containers = [
        config.PROCESSED_CONTENT_CONTAINER,
        config.MARKDOWN_CONTENT_CONTAINER,
        config.STATIC_SITES_CONTAINER,
    ]

    try:
        blob_client = create_blob_client(config)

        for container_name in required_containers:
            try:
                # Try to list blobs in container (tests existence and permissions)
                # list_blobs already returns a List and tests container accessibility
                await blob_client.list_blobs(container_name, prefix="")
                container_status[container_name] = True

            except Exception as e:
                logger.warning(f"Container {container_name} not accessible: {e}")
                container_status[container_name] = False

        return container_status

    except Exception as e:
        logger.error(f"Container validation failed: {e}")
        return {container: False for container in required_containers}

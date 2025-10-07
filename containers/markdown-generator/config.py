"""
Configuration management for markdown-generator container.

This module handles all configuration settings including Azure Storage,
logging, and processing parameters.
"""

import logging
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["Settings", "get_settings", "configure_logging"]


class Settings(BaseSettings):
    """Application settings with environment variable loading."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = Field(default="markdown-generator", description="App name")
    version: str = Field(default="1.0.0", description="App version")
    environment: str = Field(default="production", description="Environment name")
    log_level: str = Field(default="INFO", description="Logging level")

    # Azure Storage settings
    storage_account_name: str = Field(
        default="", description="Azure Storage account name"
    )
    storage_connection_string: Optional[str] = Field(
        None, description="Storage connection string (optional)"
    )
    input_container: str = Field(
        default="processed-content",
        description="Input container for JSON files",
    )
    output_container: str = Field(
        default="markdown-content",
        description="Output container for markdown files",
    )

    # Queue settings
    queue_name: str = Field(
        default="markdown-generation-requests",
        description="Storage queue name",
    )
    queue_polling_interval_seconds: int = Field(
        default=5, description="Queue polling interval"
    )
    queue_visibility_timeout_seconds: int = Field(
        default=300, description="Message visibility timeout (5 minutes)"
    )
    max_dequeue_count: int = Field(default=3, description="Max retry attempts")

    # Processing settings
    max_batch_size: int = Field(default=10, description="Maximum batch processing size")
    processing_timeout_seconds: int = Field(
        default=30, description="Per-article processing timeout"
    )
    enable_overwrite: bool = Field(
        default=False, description="Allow overwriting existing files"
    )

    # Monitoring settings
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_flush_interval_seconds: int = Field(
        default=60, description="Metrics flush interval"
    )

    # Application Insights (optional)
    applicationinsights_connection_string: Optional[str] = Field(
        None, description="Application Insights connection string"
    )

    def get_storage_connection_string(self) -> str:
        """
        Get storage connection string from explicit config or construct it.

        Returns:
            str: Azure Storage connection string

        Raises:
            ValueError: If connection string cannot be determined
        """
        if self.storage_connection_string:
            return self.storage_connection_string

        # Construct from account name (uses managed identity)
        if self.storage_account_name:
            return (
                f"DefaultEndpointsProtocol=https;"
                f"AccountName={self.storage_account_name};"
                f"EndpointSuffix=core.windows.net"
            )

        raise ValueError(
            "Either storage_connection_string or storage_account_name "
            "must be provided"
        )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings: Application settings

    Note:
        This function is cached to ensure single instance across app.
        Settings loads from environment variables automatically.
    """
    return Settings()  # type: ignore[call-arg]


def configure_logging(settings: Optional[Settings] = None) -> None:
    """
    Configure application logging.

    Args:
        settings: Optional settings instance (will create if None)
    """
    if settings is None:
        settings = get_settings()

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set specific loggers
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: level={settings.log_level}, "
        f"environment={settings.environment}"
    )

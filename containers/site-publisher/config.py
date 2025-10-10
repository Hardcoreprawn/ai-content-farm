"""
Configuration management for site-publisher.

Uses Pydantic Settings for environment-based configuration.
"""

from functools import lru_cache
from typing import TYPE_CHECKING

from pydantic_settings import BaseSettings

if TYPE_CHECKING:
    # For type checkers only - not executed at runtime
    pass


class Settings(BaseSettings):
    """Site publisher configuration from environment variables."""

    # Azure Storage
    azure_storage_account_name: str
    markdown_container: str = "markdown-content"
    output_container: str = "$web"
    backup_container: str = "$web-backup"

    # Queue Configuration
    queue_name: str = "site-publishing-requests"
    queue_polling_interval_seconds: int = 30

    # Hugo Configuration
    hugo_version: str = "0.138.0"
    hugo_theme: str = "PaperMod"
    hugo_base_url: str = ""  # Set to static website URL

    # Build Configuration
    max_markdown_files: int = 10000  # DOS prevention
    max_file_size_mb: int = 10  # Max size per file
    build_timeout_seconds: int = 300  # 5 minutes

    # Logging
    log_level: str = "INFO"

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings instance loaded from environment variables.

    Note:
        Pydantic will automatically load from environment variables.
        The IDE may show a warning about missing azure_storage_account_name,
        but this is a false positive - Pydantic loads it from env vars.
    """
    return Settings()  # type: ignore[call-arg]  # Pydantic loads from env vars

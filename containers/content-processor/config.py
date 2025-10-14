#!/usr/bin/env python3
"""
Content Processor Configuration

Minimal configuration using Pydantic for type safety.
Only includes settings actually used by the application.

Version: 2.0.0 - Simplified configuration (removed unused fields)
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Content Processor configuration.

    Loads from environment variables with sensible defaults.
    """

    # Service metadata
    service_version: str = "1.0.0"
    environment: str = "development"

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # Logging
    log_level: str = "INFO"

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Note: No module-level instantiation!
# main.py creates the settings instance when needed.
# This eliminates import-time side effects and Pylance confusion.

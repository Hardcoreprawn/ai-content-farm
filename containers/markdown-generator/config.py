"""Configuration management for markdown generator service."""

import os
from typing import Optional


class Config:
    """Configuration settings for markdown generator service."""

    # Service configuration
    SERVICE_NAME: str = "markdown-generator"
    VERSION: str = "1.0.0"
    PORT: int = int(os.getenv("PORT", "8000"))

    # Azure Blob Storage configuration
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = os.getenv(
        "AZURE_STORAGE_CONNECTION_STRING")

    # Blob container names
    RANKED_CONTENT_CONTAINER: str = os.getenv(
        "RANKED_CONTENT_CONTAINER", "ranked-content")
    GENERATED_CONTENT_CONTAINER: str = os.getenv(
        "GENERATED_CONTENT_CONTAINER", "generated-content")

    # Content processing settings
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "/app/temp")
    WATCH_INTERVAL: int = int(os.getenv("WATCH_INTERVAL", "30"))  # seconds
    MAX_CONTENT_ITEMS: int = int(os.getenv("MAX_CONTENT_ITEMS", "50"))

    # Markdown generation settings
    MARKDOWN_TEMPLATE_STYLE: str = os.getenv(
        "MARKDOWN_TEMPLATE_STYLE", "standard")
    ENABLE_AUTO_NOTIFICATION: bool = os.getenv(
        "ENABLE_AUTO_NOTIFICATION", "true").lower() == "true"

    # External service URLs (fallback for development)
    CONTENT_RANKER_URL: str = os.getenv(
        "CONTENT_RANKER_URL", "http://content-ranker:8000")
    MARKDOWN_CONVERTER_URL: str = os.getenv(
        "MARKDOWN_CONVERTER_URL", "http://markdown-converter:8000")

    @classmethod
    def validate_required_settings(cls) -> bool:
        """Validate that all required settings are present."""
        required_settings = [
            cls.AZURE_STORAGE_CONNECTION_STRING,
        ]

        missing_settings = [
            setting for setting in required_settings
            if setting is None or setting == ""
        ]

        if missing_settings:
            raise ValueError(
                f"Missing required configuration: {missing_settings}")

        return True


# Global config instance
config = Config()

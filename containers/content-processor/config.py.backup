#!/usr/bin/env python3
"""
Standardized Configuration for Content Processor

Uses pydantic-settings BaseSettings for type-safe configuration management.
Now using standardized base config for consistency across all containers.

Version: 1.0.1 - Fixed Pydantic serialization for enhanced metadata
"""

import logging
import os
import sys
from typing import Dict, Optional

from pydantic import Field

from libs.config_base import BaseContainerConfig

# Add libs to path for shared config
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))


class ContentProcessorSettings(BaseContainerConfig):
    """
    Content Processor configuration using standardized base config.

    Inherits common container configuration and adds processor-specific settings.
    """

    service_name: str = Field(default="content-processor", description="Service name")

    # Service Information (inherit most from base, override as needed)
    service_version: str = Field(default="1.0.0", description="Service version")
    log_level: str = Field(default="INFO", description="Logging level")

    # Processing-specific containers (extending the base set)
    processed_content_container: str = Field(
        default="processed-content",
        description="Container for processed content output",
    )
    enriched_content_container: str = Field(
        default="enriched-content", description="Container for enriched content"
    )

    # OpenAI Configuration (Multi-Region Support)
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API Key")

    # Azure OpenAI Configuration
    azure_openai_endpoint: Optional[str] = Field(
        default=None, description="Primary Azure OpenAI endpoint"
    )
    azure_openai_api_key: Optional[str] = Field(
        default=None, description="Azure OpenAI API key"
    )
    azure_openai_api_version: str = Field(
        default="2024-06-01", description="Azure OpenAI API version"
    )

    # Regional OpenAI endpoints for failover
    openai_endpoint_uk_south: Optional[str] = Field(
        default=None, description="OpenAI UK South endpoint"
    )
    openai_endpoint_west_europe: Optional[str] = Field(
        default=None, description="OpenAI West Europe endpoint"
    )
    openai_model_default: str = Field(
        default="gpt-3.5-turbo", description="Default OpenAI model"
    )
    openai_max_retries: int = Field(
        default=3, description="Max retries for OpenAI API calls"
    )

    # Reddit API Configuration
    reddit_client_id: Optional[str] = Field(
        default=None, description="Reddit client ID"
    )
    reddit_client_secret: Optional[str] = Field(
        default=None, description="Reddit client secret"
    )
    reddit_user_agent: str = Field(
        default="content-processor/1.0", description="Reddit user agent"
    )

    # Processing Configuration
    max_concurrent_processes: int = Field(
        default=5, description="Maximum concurrent processes"
    )
    processing_timeout_seconds: int = Field(
        default=300, description="Processing timeout in seconds"
    )
    quality_threshold: float = Field(
        default=0.7, description="Quality threshold for content"
    )

    def get_openai_endpoints(self) -> Dict[str, str]:
        """Get available OpenAI endpoints for multi-region support."""
        endpoints = {}
        if self.azure_openai_endpoint:
            endpoints["primary"] = self.azure_openai_endpoint
        if self.openai_endpoint_uk_south:
            endpoints["uk_south"] = self.openai_endpoint_uk_south
        if self.openai_endpoint_west_europe:
            endpoints["west_europe"] = self.openai_endpoint_west_europe
        return endpoints

    def get_openai_endpoint_for_region(self, region: str) -> Optional[str]:
        """Get OpenAI endpoint for specific region."""
        region_map = {
            "uksouth": self.openai_endpoint_uk_south,
            "westeurope": self.openai_endpoint_west_europe,
            "primary": self.azure_openai_endpoint,
        }
        return region_map.get(region.lower())

    def is_local_environment(self) -> bool:
        """Check if running in local development environment."""
        return self.environment.lower() in ["local", "development", "testing"]

    def get_reddit_credentials(self) -> Optional[Dict[str, str]]:
        """Get Reddit API credentials if available."""
        if self.reddit_client_id and self.reddit_client_secret:
            return {
                "client_id": self.reddit_client_id,
                "client_secret": self.reddit_client_secret,
                "user_agent": self.reddit_user_agent,
            }
        return None

    def setup_logging(self) -> None:
        """Configure logging based on settings."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


# Global settings instance
settings = ContentProcessorSettings()


# Backward compatibility for existing code
def get_config() -> ContentProcessorSettings:
    """Get configuration instance (backward compatibility)."""
    return settings


# Configure logging on import
settings.setup_logging()

# Export environment constant for compatibility
ENVIRONMENT = settings.environment

logger = logging.getLogger(__name__)
logger.info(
    f"Content Processor configuration loaded: {settings.service_name} v{settings.service_version} "
    f"(environment: {settings.environment})"
)

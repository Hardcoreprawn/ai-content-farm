"""
Shared Configuration Base Classes

Provides standardized configuration management using pydantic-settings
for type-safe, validated environment variable handling.
"""

from typing import Optional

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class BaseContainerConfig(BaseSettings):
    """
    Base configuration class for all containers.

    Provides common settings that all containers need,
    with type safety and automatic environment variable loading.
    """

    # Service Configuration
    service_name: str = Field(..., description="Name of the service")
    version: str = Field(default="1.0.0", description="Service version")
    port: int = Field(default=8000, description="HTTP server port")
    environment: str = Field(default="development", description="Environment name")

    # Azure Blob Storage Configuration
    storage_account_name: str = Field(
        default="aicontentfarmstg", description="Azure Storage Account name"
    )
    storage_account_url: Optional[str] = Field(
        default=None,
        description="Azure Storage Account URL (auto-generated if not provided)",
    )
    blob_connection_string: Optional[str] = Field(
        default=None, description="Blob storage connection string for local development"
    )

    # Azure Key Vault Configuration
    azure_key_vault_url: Optional[str] = Field(
        default=None, description="Azure Key Vault URL for secrets"
    )
    azure_client_id: Optional[str] = Field(
        default=None, description="Azure Client ID for managed identity authentication"
    )

    # Common Container Names
    collected_content_container: str = Field(
        default="collected-content", description="Container for collected content"
    )
    generated_content_container: str = Field(
        default="generated-content", description="Container for generated content"
    )
    published_sites_container: str = Field(
        default="published-sites", description="Container for published websites"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Auto-generate storage URL if not provided
        if not self.storage_account_url and self.storage_account_name:
            self.storage_account_url = (
                f"https://{self.storage_account_name}.blob.core.windows.net"
            )

    model_config = ConfigDict(
        # Load from environment variables
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Allow extra fields for container-specific config
        extra="allow",
    )


class ContentCollectorConfig(BaseContainerConfig):
    """Configuration specific to content-collector container."""

    service_name: str = Field(default="content-collector", description="Service name")

    # Reddit Configuration
    reddit_client_id: Optional[str] = Field(
        default=None, description="Reddit API client ID"
    )
    reddit_client_secret: Optional[str] = Field(
        default=None, description="Reddit API client secret"
    )
    reddit_user_agent: str = Field(
        default="azure:content-womble:v2.0.2 (by /u/hardcorepr4wn)",
        description="Reddit API user agent",
    )

    # Collection Configuration
    max_items_per_collection: int = Field(
        default=100, description="Maximum items to collect per run"
    )
    default_subreddits: list[str] = Field(
        default_factory=lambda: ["technology", "programming", "python"],
        description="Default subreddits to monitor",
    )


class ContentProcessorConfig(BaseContainerConfig):
    """Configuration specific to content-processor container."""

    service_name: str = Field(default="content-processor", description="Service name")

    # Processing Configuration
    ranking_algorithm: str = Field(
        default="engagement_score", description="Algorithm for content ranking"
    )
    max_processing_batch_size: int = Field(
        default=50, description="Maximum items to process in one batch"
    )


class ContentGeneratorConfig(BaseContainerConfig):
    """Configuration specific to content-processor container (includes generation functionality)."""

    service_name: str = Field(default="content-processor", description="Service name")

    # AI Service Configuration
    azure_openai_endpoint: Optional[str] = Field(
        default=None, description="Azure OpenAI endpoint"
    )
    azure_openai_api_key: Optional[str] = Field(
        default=None, description="Azure OpenAI API key"
    )
    azure_openai_api_version: str = Field(
        default="2024-02-15-preview", description="Azure OpenAI API version"
    )
    azure_openai_deployment_name: str = Field(
        default="gpt-35-turbo", description="Azure OpenAI deployment name"
    )

    # Fallback Configuration
    openai_api_key: Optional[str] = Field(
        default=None, description="OpenAI API key fallback"
    )
    claude_api_key: Optional[str] = Field(
        default=None, description="Claude API key fallback"
    )
    default_ai_model: str = Field(
        default="gpt-3.5-turbo", description="Default AI model to use"
    )


class SiteGeneratorConfig(BaseContainerConfig):
    """Configuration specific to site-generator container."""

    service_name: str = Field(default="site-generator", description="Service name")

    # Site Generation Configuration
    site_template: str = Field(default="default", description="Site template to use")
    max_articles_per_page: int = Field(
        default=10, description="Maximum articles per page"
    )
    enable_rss: bool = Field(default=True, description="Enable RSS feed generation")

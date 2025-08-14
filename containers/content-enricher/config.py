"""
Content Enricher Configuration

Environment-based configuration management.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AzureConfig:
    """Azure-specific configuration."""

    subscription_id: Optional[str] = None
    resource_group: Optional[str] = None
    key_vault_name: Optional[str] = None
    storage_account: Optional[str] = None
    app_insights_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_endpoint: Optional[str] = None


@dataclass
class EnricherConfig:
    """Content Enricher service configuration."""

    # Azure configuration (required)
    azure: AzureConfig

    # Service settings
    service_name: str = "content-enricher"
    version: str = "1.0.0"
    debug: bool = False

    # Processing settings
    max_batch_size: int = 100
    max_summary_length: int = 200
    enable_ai_summaries: bool = True

    # Environment
    environment: str = "local"


def get_config() -> EnricherConfig:
    """
    Get configuration based on environment variables.

    Returns:
        EnricherConfig instance with environment-specific settings
    """
    # Azure configuration
    azure_config = AzureConfig(
        subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID"),
        resource_group=os.getenv("AZURE_RESOURCE_GROUP"),
        key_vault_name=os.getenv("AZURE_KEY_VAULT_NAME"),
        storage_account=os.getenv("AZURE_STORAGE_ACCOUNT"),
        app_insights_key=os.getenv("AZURE_APP_INSIGHTS_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_endpoint=os.getenv("OPENAI_ENDPOINT"),
    )

    # Main configuration
    config = EnricherConfig(
        debug=os.getenv("DEBUG", "false").lower() == "true",
        max_batch_size=int(os.getenv("MAX_BATCH_SIZE", "100")),
        max_summary_length=int(os.getenv("MAX_SUMMARY_LENGTH", "200")),
        enable_ai_summaries=os.getenv(
            "ENABLE_AI_SUMMARIES", "true").lower() == "true",
        azure=azure_config,
        environment=os.getenv("ENVIRONMENT", "local"),
    )

    logger.info(f"Configuration loaded for environment: {config.environment}")

    return config


def health_check() -> Dict[str, Any]:
    """
    Perform health check on dependencies.

    Returns:
        Dictionary with health status of various components
    """
    config = get_config()
    health_status = {
        "service": config.service_name,
        "version": config.version,
        "environment": config.environment,
        "azure_connectivity": False,
        "openai_available": False,
    }

    # Check Azure connectivity
    try:
        if config.azure.subscription_id:
            # In a real implementation, this would check Azure services
            health_status["azure_connectivity"] = True
    except Exception as e:
        logger.warning(f"Azure connectivity check failed: {e}")

    # Check OpenAI availability
    try:
        if config.azure.openai_api_key:
            # In a real implementation, this would ping OpenAI API
            health_status["openai_available"] = True
    except Exception as e:
        logger.warning(f"OpenAI availability check failed: {e}")

    return health_status

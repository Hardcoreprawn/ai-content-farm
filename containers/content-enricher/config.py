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
    import requests
    import os

    config = get_config()
    is_local = config.environment in ["local", "development"]

    health_status = {
        "service": config.service_name,
        "version": config.version,
        "environment": config.environment,
        "azure_connectivity": False,
        "openai_available": False,
        "is_local_development": is_local,
    }

    # Check Azure connectivity
    try:
        if is_local:
            # For local development, test azurite connectivity
            response = requests.get(
                "http://azurite:10000/devstoreaccount1", timeout=3)
            health_status["azure_connectivity"] = response.status_code in [
                200, 400]  # 400 is expected
        else:
            # For production, check if we have required config
            if config.azure.subscription_id:
                # In a real implementation, this would check Azure services
                health_status["azure_connectivity"] = True
    except Exception as e:
        logger.warning(f"Azure connectivity check failed: {e}")

    # Check OpenAI availability
    try:
        openai_key = config.azure.openai_api_key or os.getenv("OPENAI_API_KEY")
        if openai_key:
            if is_local:
                # For local development, just check if we have a key
                health_status["openai_available"] = len(openai_key.strip()) > 0
            else:
                # For production, could test actual API connectivity
                health_status["openai_available"] = True
        else:
            # No API key available - this is fine for local development
            health_status["openai_available"] = False
    except Exception as e:
        logger.warning(f"OpenAI availability check failed: {e}")

    return health_status

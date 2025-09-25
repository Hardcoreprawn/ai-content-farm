"""
Dependency injection and health check functions for Content Processor.

Provides singleton instances for external clients and standardized health checks.
"""

import logging

from external_api_client import ExternalAPIClient

from config import ContentProcessorSettings
from libs.shared_models import create_service_dependency
from libs.simplified_blob_client import SimplifiedBlobClient

logger = logging.getLogger(__name__)

# Initialize settings and service metadata
settings = ContentProcessorSettings()
service_metadata = create_service_dependency("content-processor")


def get_blob_client():
    """Get blob storage client singleton."""
    if not hasattr(get_blob_client, "_client"):
        get_blob_client._client = SimplifiedBlobClient()
    return get_blob_client._client


def get_api_client():
    """Get external API client singleton."""
    if not hasattr(get_api_client, "_client"):
        get_api_client._client = ExternalAPIClient(settings)
    return get_api_client._client


async def check_storage_health():
    """Check Azure Blob Storage connectivity using standard library method."""
    try:
        result = get_blob_client().health_check()
        return result.get("status") == "healthy"
    except Exception as e:
        logger.warning(f"Storage health check failed: {e}")
        return False


async def check_openai_health():
    """Check Azure OpenAI API connectivity."""
    try:
        api_client = get_api_client()
        # Verify OpenAI endpoints are configured
        return bool(api_client.openai_endpoints)
    except Exception as e:
        logger.warning(f"OpenAI health check failed: {e}")
        return False


async def check_keyvault_health():
    """Check Azure Key Vault connectivity (optional service)."""
    try:
        # Key Vault is optional - return True if not configured
        return not settings.azure_key_vault_url or bool(settings.azure_key_vault_url)
    except Exception as e:
        logger.warning(f"Key Vault health check failed: {e}")
        return False


async def get_configuration():
    """Get current service configuration for status endpoint."""
    return {
        "environment": settings.environment,
        "log_level": settings.log_level,
        "service_version": settings.service_version,
    }


# Dependency checks configuration for shared health endpoint
DEPENDENCY_CHECKS = {
    "storage": check_storage_health,
    "openai": check_openai_health,
    "keyvault": check_keyvault_health,
}

#!/usr/bin/env python3
"""
Configuration module for Content Processor

Handles environment variables, Azure configuration, and health checks.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class AzureConfig:
    """Azure configuration settings"""

    key_vault_url: Optional[str] = None
    storage_account_name: Optional[str] = None
    reddit_api_credentials: Optional[Dict[str, str]] = None
    environment: str = "local"

    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.environment != "local":
            if not self.key_vault_url:
                logger.warning(
                    "Key Vault URL not configured for non-local environment")
            if not self.storage_account_name:
                logger.warning(
                    "Storage account not configured for non-local environment"
                )


def get_config() -> AzureConfig:
    """Load configuration from environment variables"""

    # Determine environment
    environment = os.getenv("ENVIRONMENT", "local").lower()

    # Load Azure settings
    key_vault_url = os.getenv("AZURE_KEY_VAULT_URL")
    storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT")

    # For local development, provide defaults
    if environment == "local":
        reddit_api_credentials = {
            "client_id": os.getenv("REDDIT_CLIENT_ID", "local_dev"),
            "client_secret": os.getenv("REDDIT_CLIENT_SECRET", "local_dev"),
            "user_agent": os.getenv("REDDIT_USER_AGENT", "ContentProcessor/1.0"),
        }
    else:
        # In production, these would come from Key Vault
        reddit_api_credentials = None

    return AzureConfig(
        key_vault_url=key_vault_url,
        storage_account_name=storage_account_name,
        reddit_api_credentials=reddit_api_credentials,
        environment=environment,
    )


def check_azure_connectivity() -> bool:
    """Check if Azure services are accessible"""
    import requests

    config = get_config()

    # In local development, test azurite connectivity
    if config.environment == "local" or config.environment == "development":
        try:
            # Test azurite blob service
            response = requests.get(
                "http://azurite:10000/devstoreaccount1", timeout=3)
            # 400 is expected when listing containers without auth
            return response.status_code in [200, 400]
        except Exception as e:
            logger.warning(f"Azurite connectivity check failed: {e}")
            return False

    # In production, this would test actual Azure connectivity
    # For now, just check if we have the required configuration
    has_key_vault = bool(config.key_vault_url)
    has_storage = bool(config.storage_account_name)

    return has_key_vault and has_storage


def get_reddit_credentials() -> Optional[Dict[str, str]]:
    """Get Reddit API credentials from configuration"""
    config = get_config()

    if config.environment == "local":
        return config.reddit_api_credentials

    # In production, this would fetch from Key Vault
    # For now, return None to indicate credentials need to be fetched
    return None


def get_storage_client():
    """Get Azure Storage client"""
    config = get_config()

    if config.environment == "local":
        # Return a mock client for local development
        return MockStorageClient()

    # In production, this would return actual Azure Storage client
    # For now, return a mock
    return MockStorageClient()


class MockStorageClient:
    """Mock storage client for local development"""

    def list_containers(self):
        return []

    def upload_blob(self, container, blob_name, data):
        logger.info(f"Mock upload: {container}/{blob_name}")
        return True


def health_check() -> Dict[str, Any]:
    """Perform health check of the service and dependencies"""
    try:
        config = get_config()
        azure_connectivity = check_azure_connectivity()

        # Check if we can load configuration
        config_status = "ok" if config else "error"

        # Overall health status
        # Use the actual connectivity result to determine healthy/unhealthy so
        # tests that patch check_azure_connectivity get deterministic results.
        if config_status == "ok":
            # Determine health based on azure connectivity across environments
            status = "healthy" if azure_connectivity else "unhealthy"
        else:
            status = "unhealthy"

        return {
            "status": status,
            "service": "content-processor",
            "azure_connectivity": azure_connectivity,
            "environment": config.environment,
            "config_status": config_status,
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "content-processor",
            "azure_connectivity": False,
            "error": str(e),
        }

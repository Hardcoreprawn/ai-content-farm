#!/usr/bin/env python3
"""
Azure Key Vault integration for Content Collector.

Provides secure credential retrieval from Azure Key Vault.
"""

import logging
import os
from typing import Any, Dict, Optional

from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient

logger = logging.getLogger(__name__)


class KeyVaultClient:
    """Azure Key Vault client for secure credential management."""

    def __init__(self):
        """Initialize the Key Vault client."""
        self.vault_url = os.getenv("AZURE_KEY_VAULT_URL")
        self.client: Optional[SecretClient] = None
        self._secrets_cache: Dict[str, str] = {}

        # Log the configuration status
        if self.vault_url:
            logger.info("Azure Key Vault URL configured")
            try:
                self._initialize_client()
            except Exception as e:
                logger.error(f"Failed to initialize Key Vault client: {e}")
                logger.info("Will fall back to environment variables for credentials")
                self.client = None
        else:
            logger.info("AZURE_KEY_VAULT_URL not configured")
            logger.info(
                "Local development mode: will use environment variables for credentials"
            )
            logger.info(
                "To use Azure Key Vault, set AZURE_KEY_VAULT_URL and authentication credentials"
            )
            logger.info(
                "Run ./setup-local-dev.sh to configure Azure Key Vault integration"
            )

    def _initialize_client(self):
        """Initialize the Azure Key Vault client with proper authentication."""
        if not self.vault_url:
            raise ValueError("Key Vault URL is required but not set")

        try:
            # Try managed identity first (for Azure environments)
            if os.getenv("AZURE_CLIENT_ID"):
                logger.info("Using managed identity for Key Vault authentication")
                credential = ManagedIdentityCredential(
                    client_id=os.getenv("AZURE_CLIENT_ID")
                )
            else:
                # Fall back to default credential chain
                logger.info(
                    "Using default credential chain for Key Vault authentication"
                )
                credential = DefaultAzureCredential()

            self.client = SecretClient(vault_url=self.vault_url, credential=credential)

            # Test the connection
            self._test_connection()
            logger.info("Key Vault client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Key Vault client: {e}")
            self.client = None
            raise

    def _test_connection(self):
        """Test the Key Vault connection."""
        if not self.client:
            raise ValueError("Key Vault client not initialized")

        try:
            # Try to list secrets (this will fail if permissions are insufficient)
            list(self.client.list_properties_of_secrets())
            logger.info("Key Vault connection test successful")
        except Exception as e:
            logger.warning(f"Key Vault connection test failed: {e}")
            # Don't raise here as the client might still work for getting specific secrets

    def get_secret(self, secret_name: str, use_cache: bool = True) -> Optional[str]:
        """
        Retrieve a secret from Key Vault.

        Args:
            secret_name: Name of the secret to retrieve
            use_cache: Whether to use cached values

        Returns:
            Secret value or None if not found
        """
        if not self.client:
            logger.warning("Key Vault client not available, cannot retrieve secret")
            return None

        # Check cache first
        if use_cache and secret_name in self._secrets_cache:
            logger.debug("Using cached value for secret")
            return self._secrets_cache[secret_name]

        try:
            logger.debug("Retrieving secret from Key Vault")
            secret = self.client.get_secret(secret_name)

            # Cache the secret
            if use_cache and secret.value:
                self._secrets_cache[secret_name] = secret.value

            logger.info("Successfully retrieved secret from Key Vault")
            return secret.value

        except AzureError as e:
            logger.error(f"Azure error retrieving secret: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving secret: {e}")
            return None

    def get_reddit_credentials(self) -> Dict[str, Optional[str]]:
        """
        Get Reddit API credentials from Key Vault.

        Returns:
            Dictionary with Reddit credentials
        """
        credentials = {
            "client_id": self.get_secret("reddit-client-id"),
            "client_secret": self.get_secret("reddit-client-secret"),
            "user_agent": self.get_secret("reddit-user-agent"),
        }

        # Log which credentials were found (without values)
        found_creds = [key for key, value in credentials.items() if value is not None]
        missing_creds = [key for key, value in credentials.items() if value is None]

        if found_creds:
            logger.info(f"Retrieved Reddit credentials from Key Vault: {len(found_creds)} items")

        if missing_creds:
            logger.warning(f"Missing Reddit credentials in Key Vault: {len(missing_creds)} items")

        return credentials

    def is_available(self) -> bool:
        """Check if Key Vault integration is available."""
        return self.client is not None

    def clear_cache(self):
        """Clear the secrets cache."""
        self._secrets_cache.clear()
        logger.debug("Key Vault secrets cache cleared")


# Global Key Vault client instance
_keyvault_client: Optional[KeyVaultClient] = None


def get_keyvault_client() -> KeyVaultClient:
    """Get the global Key Vault client instance."""
    global _keyvault_client

    if _keyvault_client is None:
        _keyvault_client = KeyVaultClient()

    return _keyvault_client


def get_reddit_credentials_with_fallback() -> Dict[str, Optional[str]]:
    """
    Get Reddit credentials with Key Vault + environment variable fallback.

    Tries Key Vault first, then falls back to environment variables.

    Returns:
        Dictionary with Reddit credentials
    """
    credentials: Dict[str, Optional[str]] = {
        "client_id": None,
        "client_secret": None,
        "user_agent": None,
    }

    # Try Key Vault first
    kv_client = get_keyvault_client()
    if kv_client.is_available():
        logger.info("Attempting to retrieve Reddit credentials from Key Vault")
        kv_credentials = kv_client.get_reddit_credentials()

        # Use Key Vault values if available
        for key, value in kv_credentials.items():
            if value:
                credentials[key] = value

    # Fall back to environment variables for missing values
    env_fallbacks = {
        "client_id": "REDDIT_CLIENT_ID",
        "client_secret": "REDDIT_CLIENT_SECRET",
        "user_agent": "REDDIT_USER_AGENT",
    }

    for key, env_var in env_fallbacks.items():
        if not credentials[key]:
            env_value = os.getenv(env_var)
            if env_value:
                credentials[key] = env_value
                logger.info(f"Using environment variable for Reddit {key}")

    # Log final status
    available_creds = [key for key, value in credentials.items() if value is not None]
    missing_creds = [key for key, value in credentials.items() if value is None]

    if available_creds:
        logger.info(f"Reddit credentials available: {len(available_creds)} items")

    if missing_creds:
        logger.warning(f"Reddit credentials missing: {len(missing_creds)} items")
        logger.warning(
            "Reddit API functionality may be limited without proper credentials"
        )

    return credentials


def health_check_keyvault() -> Dict[str, Any]:
    """
    Perform a health check on Key Vault connectivity.

    Returns:
        Health check results
    """
    kv_client = get_keyvault_client()

    health_info = {
        "key_vault_configured": kv_client.vault_url is not None,
        "key_vault_url": "***" if kv_client.vault_url else None,
        "client_available": kv_client.is_available(),
        "status": "unknown",
    }

    if not kv_client.vault_url:
        health_info["status"] = "not_configured"
        health_info["message"] = "Key Vault URL not configured"
        return health_info

    if not kv_client.is_available():
        health_info["status"] = "unavailable"
        health_info["message"] = "Key Vault client initialization failed"
        return health_info

    try:
        # Test retrieving a Reddit credential
        test_secret = kv_client.get_secret("reddit-client-id", use_cache=False)
        health_info["test_secret_retrieval"] = test_secret is not None

        if test_secret:
            health_info["status"] = "healthy"
            health_info["message"] = "Key Vault accessible and secrets retrievable"
        else:
            health_info["status"] = "degraded"
            health_info["message"] = "Key Vault accessible but test secret not found"

    except Exception as e:
        health_info["status"] = "error"
        health_info["message"] = f"Key Vault health check failed: {e}"
        health_info["error"] = str(e)

    return health_info

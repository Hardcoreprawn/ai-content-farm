"""Health check implementation for content generator service."""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from config import Config
from libs.blob_storage import BlobStorageClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from openai import AzureOpenAI

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health check functionality for content generator service."""

    def __init__(self, blob_client: Optional[BlobStorageClient] = None):
        """Initialize health checker with optional blob storage client."""
        self.blob_client = blob_client
        self.config = Config()

    async def check_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.

        Returns:
            Dictionary containing health status and details
        """
        try:
            health_status = {
                "service": "content-generator",
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "checks": {}
            }

            # Check blob storage connectivity if available
            if self.blob_client:
                blob_healthy = await self.check_blob_storage()
                health_status["checks"]["blob_storage"] = {
                    "status": "healthy" if blob_healthy else "unhealthy"
                }

            # Check Azure Key Vault connectivity
            keyvault_status = await self._check_keyvault()
            health_status["checks"]["azure_keyvault"] = keyvault_status

            # Check Azure OpenAI service
            openai_status = await self._check_azure_openai()
            health_status["checks"]["azure_openai"] = openai_status

            # Check configuration
            config_status = self._check_configuration()
            health_status["checks"]["configuration"] = config_status

            # Overall health determination
            all_checks_healthy = all(
                check.get("status") == "healthy"
                for check in health_status["checks"].values()
            )

            if not all_checks_healthy:
                health_status["status"] = "degraded"

            return health_status

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "service": "content-generator",
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "error": str(e)
            }

    async def check_blob_storage(self) -> bool:
        """Check blob storage connectivity."""
        try:
            if not self.blob_client:
                return False
            # Use the shared library's health check method
            health_result = self.blob_client.health_check()
            return health_result.get("status") == "healthy"
        except Exception as e:
            logger.error(f"Blob storage connectivity check failed: {e}")
            return False

    async def _check_keyvault(self) -> Dict[str, Any]:
        """Check Azure Key Vault connectivity."""
        try:
            # Since we're not using Key Vault integration yet in this config,
            # just return a placeholder status
            return {
                "status": "not_implemented",
                "message": "Key Vault integration not yet implemented in this config"
            }

        except Exception as e:
            logger.warning(f"Key Vault health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "message": f"Key Vault connection failed: {str(e)}"
            }

    async def _check_azure_openai(self) -> Dict[str, Any]:
        """Check Azure OpenAI connectivity."""
        try:
            # Get Azure OpenAI configuration from environment
            endpoint = self.config.AZURE_OPENAI_ENDPOINT
            api_key = self.config.AZURE_OPENAI_API_KEY

            if not endpoint or not api_key:
                return {
                    "status": "unhealthy",
                    "message": "Azure OpenAI configuration not available in environment variables"
                }

            # Test connection with a simple completion
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=self.config.AZURE_OPENAI_API_VERSION
            )

            # Test with minimal request
            response = client.chat.completions.create(
                model=self.config.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "user", "content": "Say 'OK' if you can respond."}],
                max_tokens=5,
                temperature=0
            )

            if response.choices and response.choices[0].message.content:
                return {
                    "status": "healthy",
                    "message": "Azure OpenAI connection successful",
                    "model": self.config.AZURE_OPENAI_DEPLOYMENT_NAME,
                    "endpoint": endpoint
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": "Azure OpenAI returned empty response"
                }

        except Exception as e:
            logger.warning(f"Azure OpenAI health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "message": f"Azure OpenAI connection failed: {str(e)}"
            }

    def _check_configuration(self) -> Dict[str, Any]:
        """Check service configuration."""
        try:
            config_status = {
                "azure_openai_endpoint": bool(self.config.AZURE_OPENAI_ENDPOINT),
                "azure_openai_api_key": bool(self.config.AZURE_OPENAI_API_KEY),
                "blob_connection_string": bool(self.config.BLOB_CONNECTION_STRING),
                "service_name": self.config.SERVICE_NAME,
                "version": self.config.VERSION
            }

            missing_config = [key for key, value in config_status.items()
                              if not value and key not in ["service_name", "version"]]

            if missing_config:
                return {
                    "status": "unhealthy",
                    "message": f"Missing configuration: {', '.join(missing_config)}",
                    "config_status": config_status
                }

            return {
                "status": "healthy",
                "message": "All required configuration present",
                "config_status": config_status
            }

        except Exception as e:
            logger.error(f"Configuration check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def get_readiness_status(self) -> Dict[str, Any]:
        """
        Get readiness status (simplified health check for Kubernetes readiness probe).

        Returns:
            Dict containing readiness status
        """
        try:
            # Quick check of essential services
            endpoint = self.config.AZURE_OPENAI_ENDPOINT
            api_key = self.config.AZURE_OPENAI_API_KEY

            if endpoint and api_key:
                return {
                    "status": "ready",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {
                    "status": "not_ready",
                    "message": "Azure OpenAI configuration not available",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        except Exception as e:
            logger.error(f"Readiness check failed: {str(e)}")
            return {
                "status": "not_ready",
                "message": f"Readiness check failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def get_liveness_status(self) -> Dict[str, Any]:
        """
        Get liveness status (basic service liveness for Kubernetes liveness probe).

        Returns:
            Dict containing liveness status
        """
        return {
            "status": "alive",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "content-generator"
        }

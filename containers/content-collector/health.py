"""
Content Collector Health Checks

Provides comprehensive health check functionality for the content collector.
"""

from typing import Dict, Any
from datetime import datetime, timezone
from config import Config
from libs.blob_storage import BlobStorageClient
from keyvault_client import health_check_keyvault


class HealthChecker:
    """Health check functionality for content collector."""

    def __init__(self):
        """Initialize health checker."""
        self.storage = BlobStorageClient()

    def check_dependencies(self) -> Dict[str, Any]:
        """Check all service dependencies."""
        dependencies = {}

        # Check Azure Storage
        try:
            # Try to list containers to verify connection
            container_client = self.storage.blob_service_client.list_containers()
            list(container_client)  # Force evaluation
            dependencies["azure_storage"] = {
                "status": "healthy",
                "message": "Azure Storage connection successful"
            }
        except Exception as e:
            dependencies["azure_storage"] = {
                "status": "unhealthy",
                "message": f"Azure Storage connection failed: {str(e)}"
            }

        # Check Key Vault (if configured)
        try:
            kv_health = health_check_keyvault()
            dependencies["key_vault"] = kv_health
        except Exception as e:
            dependencies["key_vault"] = {
                "status": "warning",
                "message": f"Key Vault health check failed: {str(e)}"
            }

        # Check Reddit API configuration
        if Config.REDDIT_CLIENT_ID and Config.REDDIT_CLIENT_SECRET:
            dependencies["reddit_api"] = {
                "status": "healthy",
                "message": "Reddit API credentials configured"
            }
        else:
            dependencies["reddit_api"] = {
                "status": "warning",
                "message": "Reddit API credentials not fully configured"
            }

        return dependencies

    def get_full_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        dependencies = self.check_dependencies()
        config_issues = Config.validate_config()

        # Determine overall health
        overall_status = "healthy"
        if any(dep["status"] == "unhealthy" for dep in dependencies.values()):
            overall_status = "unhealthy"
        elif any(dep["status"] == "warning" for dep in dependencies.values()) or config_issues:
            overall_status = "warning"

        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "content-collector",
            "version": "1.0.0",
            "dependencies": dependencies,
            "config_issues": config_issues,
            "environment": Config.ENVIRONMENT
        }

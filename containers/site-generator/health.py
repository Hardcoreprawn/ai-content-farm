#!/usr/bin/env python3
"""
Health check implementation for Site Generator
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from config import get_config

from libs.blob_storage import BlobStorageClient

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health check implementation."""

    def __init__(self):
        self.config = get_config()
        self.start_time = datetime.now(timezone.utc)
        self.request_count = 0
        self.last_activity = datetime.now(timezone.utc)
        self.generation_count = 0

    async def check_health(self) -> Dict[str, Any]:
        """Basic health check."""
        try:
            # Test blob storage connectivity
            blob_client = BlobStorageClient()
            test_container = f"health-check-{self.config.service_name}"
            blob_client.ensure_container(test_container)

            # Test template directory existence
            import os

            template_dir = "/app/templates"
            if not os.path.exists(template_dir):
                os.makedirs(template_dir, exist_ok=True)

            self.last_activity = datetime.now(timezone.utc)
            self.request_count += 1

            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": self.config.service_name,
                "version": self.config.version,
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": self.config.service_name,
                "version": self.config.version,
                "error": str(e),
            }

    async def get_detailed_status(self) -> Dict[str, Any]:
        """Detailed status information."""
        try:
            # Check dependencies
            dependencies = await self._check_dependencies()

            # Calculate uptime
            uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()

            return {
                "status": "healthy"
                if all(dep["status"] == "healthy" for dep in dependencies.values())
                else "degraded",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": self.config.service_name,
                "version": self.config.version,
                "environment": self.config.environment,
                "dependencies": dependencies,
                "metrics": {
                    "uptime_seconds": int(uptime),
                    "requests_processed": self.request_count,
                    "sites_generated": self.generation_count,
                    "last_activity": self.last_activity.isoformat(),
                },
                "configuration": {
                    "default_theme": self.config.default_theme,
                    "max_articles_per_page": self.config.max_articles_per_page,
                    "site_title": self.config.site_title,
                },
            }

        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return {
                "status": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": self.config.service_name,
                "error": str(e),
            }

    async def _check_dependencies(self) -> Dict[str, Dict[str, Any]]:
        """Check status of dependencies."""
        dependencies = {}

        # Check blob storage
        try:
            blob_client = BlobStorageClient()
            test_container = f"health-check-{self.config.service_name}"
            blob_client.ensure_container(test_container)
            dependencies["azure_storage"] = {
                "status": "healthy",
                "response_time_ms": 0,  # Could measure actual response time
            }
        except Exception as e:
            dependencies["azure_storage"] = {"status": "unhealthy", "error": str(e)}

        # Check if we can access content containers
        try:
            blob_client = BlobStorageClient()
            blob_client.ensure_container("ranked-content")
            blob_client.ensure_container("published-sites")
            dependencies["content_containers"] = {
                "status": "healthy",
                "containers": ["ranked-content", "published-sites"],
            }
        except Exception as e:
            dependencies["content_containers"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        # Check template system
        try:
            import os

            template_dir = "/app/templates"
            if os.path.exists(template_dir):
                dependencies["template_system"] = {
                    "status": "healthy",
                    "template_directory": template_dir,
                }
            else:
                dependencies["template_system"] = {
                    "status": "degraded",
                    "message": "Template directory not found, will create on demand",
                }
        except Exception as e:
            dependencies["template_system"] = {"status": "unhealthy", "error": str(e)}

        return dependencies

    def increment_generation_count(self):
        """Increment the count of generated sites."""
        self.generation_count += 1
        self.last_activity = datetime.now(timezone.utc)

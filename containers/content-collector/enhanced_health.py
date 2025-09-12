#!/usr/bin/env python3
"""
Enhanced Health Endpoint for Content Collector

Integrates mTLS validation with existing health checks to provide comprehensive
service status including secure communication capabilities.
"""

import asyncio
import os
from typing import Dict, List

from fastapi import HTTPException
from fastapi.responses import JSONResponse

# Import existing health check functions
from libs.mtls_health import enhanced_health_check


class ContentCollectorHealthChecker:
    """Enhanced health checker for Content Collector with mTLS validation"""

    def __init__(self):
        self.service_name = "content-collector"
        self.dependencies = ["content-processor"]  # Services this one calls

    async def check_reddit_api_connectivity(self) -> Dict:
        """Check Reddit API connectivity with current credentials"""
        result = {"status": "healthy", "details": {}}

        try:
            # Check if Reddit credentials are configured
            reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
            reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")

            if not reddit_client_id or not reddit_client_secret:
                result["status"] = "warning"
                result["details"]["warning"] = "Reddit credentials not fully configured"
            else:
                result["details"]["credentials"] = "configured"

            # Note: In production, you might want to test actual Reddit API connectivity
            # but be careful about rate limits and authentication in health checks

        except Exception as e:
            result["status"] = "unhealthy"
            result["details"]["error"] = str(e)

        return result

    async def check_blob_storage_connectivity(self) -> Dict:
        """Check Azure Blob Storage connectivity"""
        result = {"status": "healthy", "details": {}}

        try:
            # Check if storage account is configured
            storage_account = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
            client_id = os.getenv("AZURE_CLIENT_ID")

            if not storage_account:
                result["status"] = "unhealthy"
                result["details"]["error"] = "Storage account not configured"
            elif not client_id:
                result["status"] = "warning"
                result["details"]["warning"] = "Managed identity not configured"
            else:
                result["details"]["storage_account"] = storage_account
                result["details"]["authentication"] = "managed_identity"

        except Exception as e:
            result["status"] = "unhealthy"
            result["details"]["error"] = str(e)

        return result

    async def check_servicebus_connectivity(self) -> Dict:
        """Check Azure Service Bus connectivity"""
        result = {"status": "healthy", "details": {}}

        try:
            # Check Service Bus configuration
            connection_string = os.getenv("AZURE_SERVICEBUS_CONNECTION_STRING")

            if not connection_string:
                result["status"] = "warning"
                result["details"][
                    "warning"
                ] = "Service Bus connection string not configured"
            else:
                result["details"]["configured"] = True

        except Exception as e:
            result["status"] = "unhealthy"
            result["details"]["error"] = str(e)

        return result

    async def get_enhanced_health_status(self) -> Dict:
        """Get comprehensive health status including mTLS validation"""

        # Run existing health checks
        existing_checks = {
            "reddit_api": await self.check_reddit_api_connectivity(),
            "blob_storage": await self.check_blob_storage_connectivity(),
            "servicebus": await self.check_servicebus_connectivity(),
        }

        # Add mTLS validation
        return await enhanced_health_check(
            service_name=self.service_name,
            existing_checks=existing_checks,
            dependencies=self.dependencies,
        )


# Global health checker instance
health_checker = ContentCollectorHealthChecker()


async def enhanced_collector_health() -> JSONResponse:
    """Enhanced health endpoint for Content Collector"""
    try:
        health_data = await health_checker.get_enhanced_health_status()

        # Map status to HTTP status codes
        status_code = 200
        if health_data["status"] == "warning":
            status_code = 200  # Warning is still OK for load balancers
        elif health_data["status"] == "unhealthy":
            status_code = 503  # Service Unavailable

        return JSONResponse(status_code=status_code, content=health_data)

    except Exception as e:
        # If health check itself fails, return minimal error response
        return JSONResponse(
            status_code=500,
            content={
                "service": "content-collector",
                "status": "unhealthy",
                "error": f"Health check failed: {str(e)}",
                "timestamp": "error",
            },
        )


# Integration function for existing FastAPI app
def add_enhanced_health_endpoint(app):
    """Add enhanced health endpoint to existing FastAPI app"""

    @app.get("/health/detailed", response_class=JSONResponse)
    async def detailed_health():
        """Detailed health endpoint with mTLS validation"""
        return await enhanced_collector_health()

    @app.get("/health/mtls", response_class=JSONResponse)
    async def mtls_health():
        """mTLS-specific health information"""
        try:
            from libs.mtls_health import get_mtls_health_data

            mtls_data = await get_mtls_health_data(
                service_name="content-collector", dependencies=["content-processor"]
            )

            status_code = 200
            if mtls_data["overall_status"] == "unhealthy":
                status_code = 503

            return JSONResponse(status_code=status_code, content=mtls_data)

        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": f"mTLS health check failed: {str(e)}",
                    "status": "unhealthy",
                },
            )

    @app.get("/health/dependencies", response_class=JSONResponse)
    async def dependency_health():
        """Check connectivity to dependent services"""
        try:
            from libs.mtls_health import MTLSHealthChecker

            checker = MTLSHealthChecker("content-collector")
            dep_data = await checker.check_service_dependencies(["content-processor"])

            status_code = 200
            if dep_data["status"] == "unhealthy":
                status_code = 503

            return JSONResponse(status_code=status_code, content=dep_data)

        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": f"Dependency health check failed: {str(e)}",
                    "status": "unhealthy",
                },
            )

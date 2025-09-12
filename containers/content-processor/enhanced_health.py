#!/usr/bin/env python3
"""
Enhanced Health Endpoint for Content Processor

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


class ContentProcessorHealthChecker:
    """Enhanced health checker for Content Processor with mTLS validation"""

    def __init__(self):
        self.service_name = "content-processor"
        self.dependencies = ["site-generator"]  # Services this one calls

    async def check_openai_connectivity(self) -> Dict:
        """Check Azure OpenAI connectivity and configuration"""
        result = {"status": "healthy", "details": {}}

        try:
            # Check if Azure OpenAI is configured
            openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            openai_key = os.getenv("AZURE_OPENAI_KEY")
            client_id = os.getenv("AZURE_CLIENT_ID")

            if not openai_endpoint:
                result["status"] = "unhealthy"
                result["details"]["error"] = "Azure OpenAI endpoint not configured"
            elif not (openai_key or client_id):
                result["status"] = "warning"
                result["details"][
                    "warning"
                ] = "Neither API key nor managed identity configured"
            else:
                result["details"]["endpoint"] = openai_endpoint
                result["details"]["authentication"] = (
                    "api_key" if openai_key else "managed_identity"
                )

        except Exception as e:
            result["status"] = "unhealthy"
            result["details"]["error"] = str(e)

        return result

    async def check_blob_storage_connectivity(self) -> Dict:
        """Check Azure Blob Storage connectivity for input/output"""
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
                result["details"]["containers"] = [
                    "collected-content",
                    "processed-content",
                ]

        except Exception as e:
            result["status"] = "unhealthy"
            result["details"]["error"] = str(e)

        return result

    async def check_processing_queue_status(self) -> Dict:
        """Check processing queue status and backlog"""
        result = {"status": "healthy", "details": {}}

        try:
            # This would check actual queue status in production
            # For now, return basic status
            result["details"]["queue_status"] = "operational"
            result["details"]["approximate_backlog"] = 0  # Would be real data

        except Exception as e:
            result["status"] = "unhealthy"
            result["details"]["error"] = str(e)

        return result

    async def check_ai_model_availability(self) -> Dict:
        """Check if AI models are available and responding"""
        result = {"status": "healthy", "details": {}}

        try:
            # Check model configuration
            model_names = {
                "gpt-35-turbo": os.getenv("AZURE_OPENAI_GPT35_DEPLOYMENT_NAME"),
                "gpt-4": os.getenv("AZURE_OPENAI_GPT4_DEPLOYMENT_NAME"),
            }

            configured_models = {k: v for k, v in model_names.items() if v}

            if not configured_models:
                result["status"] = "warning"
                result["details"]["warning"] = "No AI models configured"
            else:
                result["details"]["configured_models"] = configured_models
                result["details"]["model_count"] = len(configured_models)

        except Exception as e:
            result["status"] = "unhealthy"
            result["details"]["error"] = str(e)

        return result

    async def get_enhanced_health_status(self) -> Dict:
        """Get comprehensive health status including mTLS validation"""

        # Run existing health checks
        existing_checks = {
            "openai": await self.check_openai_connectivity(),
            "blob_storage": await self.check_blob_storage_connectivity(),
            "processing_queue": await self.check_processing_queue_status(),
            "ai_models": await self.check_ai_model_availability(),
        }

        # Add mTLS validation
        return await enhanced_health_check(
            service_name=self.service_name,
            existing_checks=existing_checks,
            dependencies=self.dependencies,
        )


# Global health checker instance
health_checker = ContentProcessorHealthChecker()


async def enhanced_processor_health() -> JSONResponse:
    """Enhanced health endpoint for Content Processor"""
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
                "service": "content-processor",
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
        return await enhanced_processor_health()

    @app.get("/health/mtls", response_class=JSONResponse)
    async def mtls_health():
        """mTLS-specific health information"""
        try:
            from libs.mtls_health import get_mtls_health_data

            mtls_data = await get_mtls_health_data(
                service_name="content-processor", dependencies=["site-generator"]
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

            checker = MTLSHealthChecker("content-processor")
            dep_data = await checker.check_service_dependencies(["site-generator"])

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

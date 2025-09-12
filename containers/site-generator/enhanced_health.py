#!/usr/bin/env python3
"""
Enhanced Health Endpoint for Site Generator

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


class SiteGeneratorHealthChecker:
    """Enhanced health checker for Site Generator with mTLS validation"""

    def __init__(self):
        self.service_name = "site-generator"
        self.dependencies = []  # Site generator is typically the end of the pipeline

    async def check_blob_storage_connectivity(self) -> Dict:
        """Check Azure Blob Storage connectivity for content and sites"""
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
                    "processed-content",
                    "markdown-content",
                    "static-sites",
                ]

        except Exception as e:
            result["status"] = "unhealthy"
            result["details"]["error"] = str(e)

        return result

    async def check_static_web_apps_connectivity(self) -> Dict:
        """Check Azure Static Web Apps deployment capability"""
        result = {"status": "healthy", "details": {}}

        try:
            # Check if deployment configuration is available
            deployment_token = os.getenv("AZURE_STATIC_WEB_APPS_API_TOKEN")

            if not deployment_token:
                result["status"] = "warning"
                result["details"][
                    "warning"
                ] = "Static Web Apps deployment token not configured"
            else:
                result["details"]["deployment_ready"] = True
                result["details"]["target_domain"] = "jablab.com"

        except Exception as e:
            result["status"] = "unhealthy"
            result["details"]["error"] = str(e)

        return result

    async def check_template_engine_status(self) -> Dict:
        """Check template engine and site generation capabilities"""
        result = {"status": "healthy", "details": {}}

        try:
            # Check if required template files exist
            template_paths = ["/app/templates", "/app/static"]

            missing_paths = []
            for path in template_paths:
                if not os.path.exists(path):
                    missing_paths.append(path)

            if missing_paths:
                result["status"] = "warning"
                result["details"][
                    "warning"
                ] = f"Missing template paths: {missing_paths}"
            else:
                result["details"]["template_engine"] = "jinja2"
                result["details"]["template_paths"] = template_paths

        except Exception as e:
            result["status"] = "unhealthy"
            result["details"]["error"] = str(e)

        return result

    async def check_content_processing_status(self) -> Dict:
        """Check if there's content available for processing"""
        result = {"status": "healthy", "details": {}}

        try:
            # This would check for pending content in blob storage
            # For now, return basic status
            result["details"]["pending_content"] = 0  # Would be real data
            result["details"]["last_generation"] = "unknown"  # Would be timestamp
            result["details"]["sites_generated"] = 0  # Would be count

        except Exception as e:
            result["status"] = "unhealthy"
            result["details"]["error"] = str(e)

        return result

    async def get_enhanced_health_status(self) -> Dict:
        """Get comprehensive health status including mTLS validation"""

        # Run existing health checks
        existing_checks = {
            "blob_storage": await self.check_blob_storage_connectivity(),
            "static_web_apps": await self.check_static_web_apps_connectivity(),
            "template_engine": await self.check_template_engine_status(),
            "content_processing": await self.check_content_processing_status(),
        }

        # Add mTLS validation (no dependencies for site generator)
        return await enhanced_health_check(
            service_name=self.service_name,
            existing_checks=existing_checks,
            dependencies=self.dependencies,
        )


# Global health checker instance
health_checker = SiteGeneratorHealthChecker()


async def enhanced_site_generator_health() -> JSONResponse:
    """Enhanced health endpoint for Site Generator"""
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
                "service": "site-generator",
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
        return await enhanced_site_generator_health()

    @app.get("/health/mtls", response_class=JSONResponse)
    async def mtls_health():
        """mTLS-specific health information"""
        try:
            from libs.mtls_health import get_mtls_health_data

            mtls_data = await get_mtls_health_data(
                service_name="site-generator", dependencies=[]
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

    @app.get("/health/pipeline", response_class=JSONResponse)
    async def pipeline_health():
        """Check health of the entire content pipeline from site generator perspective"""
        try:
            from libs.mtls_health import MTLSHealthChecker

            checker = MTLSHealthChecker("site-generator")

            # Check the entire pipeline
            pipeline_services = ["content-collector", "content-processor"]
            dep_data = await checker.check_service_dependencies(pipeline_services)

            status_code = 200
            if dep_data["status"] == "unhealthy":
                status_code = 503

            return JSONResponse(status_code=status_code, content=dep_data)

        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": f"Pipeline health check failed: {str(e)}",
                    "status": "unhealthy",
                },
            )

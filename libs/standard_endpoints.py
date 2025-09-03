"""
Standard FastAPI Endpoints for Content Platform

Reusable endpoint functions that are common across all containers.
Reduces code duplication and ensures consistent API patterns.
"""

import time
from typing import Any, Callable, Dict, List, Optional

from fastapi import Depends

from .shared_models import (
    HealthStatus,
    ServiceStatus,
    StandardResponse,
    create_success_response,
)

# Global variable to track service start time
_service_start_time = time.time()


def create_standard_health_endpoint(
    service_name: str,
    version: str = "1.0.0",
    dependency_checks: Optional[Dict[str, Callable]] = None,
    service_metadata_dep: Optional[Callable] = None,
):
    """
    Create a standardized health endpoint for any container.

    Args:
        service_name: Name of the service (e.g., "content-collector")
        version: Service version
        dependency_checks: Dict of dependency name -> async check function
        service_metadata_dep: FastAPI dependency for service metadata

    Returns:
        FastAPI endpoint function
    """

    async def health_endpoint(
        metadata: Dict[str, Any] = (
            Depends(service_metadata_dep) if service_metadata_dep else {}
        )
    ) -> StandardResponse:
        """Standard health check endpoint."""

        # Calculate uptime
        uptime_seconds = time.time() - _service_start_time

        # Check dependencies
        dependencies = {}
        issues = []

        if dependency_checks:
            for dep_name, check_func in dependency_checks.items():
                try:
                    dependencies[dep_name] = await check_func()
                except Exception as e:
                    dependencies[dep_name] = False
                    issues.append(f"{dep_name}: {str(e)}")

        # Determine overall health status
        overall_status = "healthy"
        if issues:
            overall_status = "warning" if all(dependencies.values()) else "unhealthy"

        health_data = HealthStatus(
            status=overall_status,
            service=service_name,
            version=version,
            dependencies=dependencies,
            issues=issues,
            uptime_seconds=uptime_seconds,
        )

        return create_success_response(
            message=(
                "Service is healthy"
                if overall_status == "healthy"
                else f"Service has issues: {', '.join(issues)}"
            ),
            data=health_data.dict(),
            metadata=metadata,
        )

    return health_endpoint


def create_standard_status_endpoint(
    service_name: str,
    get_stats: Optional[Callable] = None,
    get_last_operation: Optional[Callable] = None,
    get_configuration: Optional[Callable] = None,
    service_metadata_dep: Optional[Callable] = None,
):
    """
    Create a standardized status endpoint for any container.

    Args:
        service_name: Name of the service
        get_stats: Optional function to get service statistics
        get_last_operation: Optional function to get last operation details
        get_configuration: Optional function to get current configuration
        service_metadata_dep: FastAPI dependency for service metadata

    Returns:
        FastAPI endpoint function
    """

    async def status_endpoint(
        metadata: Dict[str, Any] = (
            Depends(service_metadata_dep) if service_metadata_dep else {}
        )
    ) -> StandardResponse:
        """Standard status endpoint with detailed service information."""

        # Calculate uptime
        uptime_seconds = time.time() - _service_start_time

        # Gather optional data
        stats = await get_stats() if get_stats else {}
        last_operation = await get_last_operation() if get_last_operation else None
        configuration = await get_configuration() if get_configuration else {}

        status_data = ServiceStatus(
            service=service_name,
            status="running",
            uptime_seconds=uptime_seconds,
            stats=stats,
            last_operation=last_operation,
            configuration=configuration,
        )

        return create_success_response(
            message=f"{service_name} is running",
            data=status_data.dict(),
            metadata=metadata,
        )

    return status_endpoint


def create_standard_root_endpoint(
    service_name: str,
    description: str,
    version: str = "1.0.0",
    available_endpoints: Optional[List[str]] = None,
    service_metadata_dep: Optional[Callable] = None,
):
    """
    Create a standardized root endpoint for any container.

    Args:
        service_name: Name of the service
        description: Service description
        version: Service version
        available_endpoints: List of available endpoint paths
        service_metadata_dep: FastAPI dependency for service metadata

    Returns:
        FastAPI endpoint function
    """

    default_endpoints = ["/health", "/status", "/docs", "/redoc"]

    all_endpoints = default_endpoints + (available_endpoints or [])

    async def root_endpoint(
        metadata: Dict[str, Any] = (
            Depends(service_metadata_dep) if service_metadata_dep else {}
        )
    ) -> StandardResponse:
        """Root endpoint with service information."""

        root_data = {
            "service": service_name,
            "description": description,
            "version": version,
            "available_endpoints": sorted(all_endpoints),
            "documentation": {"swagger_ui": "/docs", "redoc": "/redoc"},
        }

        return create_success_response(
            message=f"Welcome to {service_name}", data=root_data, metadata=metadata
        )

    return root_endpoint

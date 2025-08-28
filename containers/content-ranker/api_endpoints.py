"""
Standardized API endpoints for Content Ranker service.

This module contains the current FastAPI-native standardized API endpoints that follow
the platform's StandardResponse format and modern error handling patterns. These are
the recommended endpoints for all new integrations.

All endpoints use the /api/content-ranker prefix and return standardized JSON responses
with proper status codes, metadata, and error handling.
"""

import logging
import os
import sys
import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from models import RankingRequest
from service_logic import ContentRankerService

from config import health_check
from libs.shared_models import (
    HealthStatus,
    ServiceStatus,
    StandardResponse,
    create_error_response,
    create_service_dependency,
)

# Add the project root to the path to import shared libraries
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Import shared dependencies and models

# Configure logging
logger = logging.getLogger(__name__)

# Create router for standardized API endpoints
router = APIRouter(prefix="/api/content-ranker", tags=["Content Ranker API"])

# Initialize the ranker service
ranker_service = ContentRankerService()

# Create service-specific dependency for automatic metadata injection
service_metadata = create_service_dependency("content-ranker")


@router.get("/health", response_model=StandardResponse)
async def api_health_check(metadata: Dict[str, Any] = Depends(service_metadata)):
    """Standardized health check endpoint using FastAPI-native patterns."""
    start_time = time.time()
    try:
        # Get health check data
        health_data = health_check()

        health_status = HealthStatus(
            status=health_data.get("status", "healthy"),
            service="content-ranker",
            version="1.0.0",
            dependencies=health_data.get("dependencies", {}),
            issues=health_data.get("issues", []),
            uptime_seconds=health_data.get("uptime_seconds"),
            environment=health_data.get("environment"),
        )

        # Add execution time to metadata
        execution_time_ms = round((time.time() - start_time) * 1000, 2)
        metadata["execution_time_ms"] = execution_time_ms

        return StandardResponse(
            status="success",
            message="Content ranker service is healthy",
            data=health_status.model_dump(),
            errors=None,
            metadata=metadata,
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=create_error_response(
                message="Health check failed",
                errors=["Service health check unavailable"],
                metadata=metadata,
            ).model_dump(),
        )


@router.get("/status", response_model=StandardResponse)
async def api_status(metadata: Dict[str, Any] = Depends(service_metadata)):
    """Standardized status endpoint using FastAPI-native patterns."""
    try:
        # Get current status from the ranker service
        status_data = await ranker_service.get_ranking_status()

        service_status = ServiceStatus(
            service="content-ranker",
            status="running",
            uptime_seconds=status_data.get("uptime_seconds"),
            stats=status_data.get("stats", {}),
            last_operation=status_data.get("last_operation"),
            configuration=status_data.get("configuration", {}),
        )

        return StandardResponse(
            status="success",
            message="Service status retrieved",
            data=service_status.model_dump(),
            errors=None,
            metadata=metadata,
        )
    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Status check failed",
                errors=["Unable to retrieve service status"],
                metadata=metadata,
            ).model_dump(),
        )


@router.post("/process", response_model=StandardResponse)
async def api_process_content(
    request: RankingRequest, metadata: Dict[str, Any] = Depends(service_metadata)
):
    """Standardized content ranking endpoint using FastAPI-native patterns."""
    start_time = time.time()

    # Validate request
    if not request.content_items:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                message="Validation failed",
                errors=["At least one content item must be provided"],
                metadata=metadata,
            ).model_dump(),
        )

    try:
        # Extract parameters for the service call
        weights = request.options.weights if request.options else None
        target_topics = request.options.target_topics if request.options else None
        limit = request.options.limit if request.options else None

        # Perform ranking using the service
        ranking_result = await ranker_service.rank_content_batch(
            weights=weights, target_topics=target_topics, limit=limit
        )
        execution_time = time.time() - start_time

        # Get ranked items from the result
        ranked_items = ranking_result.get("ranked_items", [])

        # Prepare response data
        response_data = {
            "ranked_items": ranked_items,
            "items_processed": len(ranked_items),
            "execution_time_seconds": execution_time,
            "ranking_criteria": target_topics or [],
            "ranking_summary": {
                "total_items": len(ranked_items),
                "algorithm": "multi-factor",
                "processing_time": execution_time,
                "weights_used": weights or {},
            },
        }

        # Update metadata with execution info
        metadata.update(
            {
                "execution_time_seconds": execution_time,
                "execution_time_ms": max(1, int(execution_time * 1000)),
                "items_processed": len(ranked_items),
            }
        )

        return StandardResponse(
            status="success",
            message=f"Content ranking completed successfully. Ranked {len(ranked_items)} items.",
            data=response_data,
            errors=None,
            metadata=metadata,
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Error in content ranking: {e}", exc_info=True)

        # Update metadata with error info
        metadata.update(
            {
                "execution_time_seconds": execution_time,
                "execution_time_ms": max(1, int(execution_time * 1000)),
                "error_type": "InternalError",
            }
        )

        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                message="Content ranking failed",
                errors=["An unexpected error occurred during ranking"],
                metadata=metadata,
            ).model_dump(),
        )


@router.get("/docs", response_model=StandardResponse)
async def api_docs(metadata: Dict[str, Any] = Depends(service_metadata)):
    """API documentation endpoint using FastAPI-native patterns."""
    docs_data = {
        "service": "content-ranker",
        "version": "1.0.0",
        "description": "Content ranking service with multi-factor scoring algorithms",
        "supported_algorithms": ["relevance", "engagement", "quality", "hybrid"],
        "authentication": "Azure AD / Managed Identity (when deployed)",
        "rate_limiting": "Applied at Azure Container Apps level",
        "endpoints": {
            "/api/content-ranker/health": "Standardized health check",
            "/api/content-ranker/status": "Standardized status",
            "/api/content-ranker/process": "Standardized content ranking",
            "/api/content-ranker/docs": "This documentation",
            # Legacy endpoints
            "/": "Service information",
            "/health": "Legacy health check",
            "/status": "Legacy status",
            "/rank": "Legacy content ranking",
            "/rank/enriched": "Legacy enriched content ranking",
            "/rank/batch": "Legacy batch ranking",
            "/docs": "Legacy documentation",
        },
        "endpoint_categories": {
            "legacy": {
                "GET /": "Service information",
                "GET /health": "Legacy health check",
                "GET /status": "Legacy status",
                "POST /rank": "Legacy content ranking",
                "POST /rank/enriched": "Legacy enriched content ranking",
                "POST /rank/batch": "Legacy batch ranking",
                "GET /docs": "Legacy documentation",
            },
            "standardized": {
                "GET /api/content-ranker/health": "Standardized health check",
                "GET /api/content-ranker/status": "Standardized status",
                "POST /api/content-ranker/process": "Standardized content ranking",
                "GET /api/content-ranker/docs": "This documentation",
            },
        },
        "response_format": {
            "status": "success|error|processing",
            "message": "Human-readable description",
            "data": "Response data (optional)",
            "errors": "Error details (optional)",
            "metadata": "Request metadata including timestamp, function, version",
        },
    }

    return StandardResponse(
        status="success",
        message="API documentation retrieved",
        data=docs_data,
        errors=None,
        metadata=metadata,
    )

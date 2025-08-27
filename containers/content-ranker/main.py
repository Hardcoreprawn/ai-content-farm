#!/usr/bin/env python3
"""
Content Ranker - Main FastAPI Application

Ranks enriched content using multi-factor scoring algorithms.
API endpoints for content ranking and health monitoring.
Updated to use standardized response formats and endpoint patterns.
"""

import json
import logging
import os

# Import standardized models
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from models import (
    BatchRankingRequest,
    ContentItem,
    HealthResponse,
    RankedItem,
    RankingOptions,
    RankingRequest,
    RankingResponse,
    SpecificRankingRequest,
)
from pydantic import BaseModel, Field, ValidationError

# Import our business logic
from ranker import rank_content_items
from service_logic import ContentRankerService
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import get_config, health_check
from libs.shared_models import (
    APIError,
    ErrorCodes,
    HealthStatus,
    ServiceStatus,
    StandardResponse,
    wrap_legacy_response,
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize service
ranker_service = ContentRankerService()

# Function name for standardized responses
FUNCTION_NAME = "content-ranker"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    try:
        await ranker_service.ensure_containers()
        logger.info("Content ranker service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise

    yield

    # Shutdown (if needed)
    logger.info("Content ranker service shutting down")


# Create FastAPI app
app = FastAPI(
    title="Content Ranker",
    description="Ranks enriched content using multi-factor scoring algorithms",
    version="1.0.0",
    lifespan=lifespan,
)

# Exception handlers for standardized error responses


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with standardized format."""
    logger.error(f"HTTP error {exc.status_code}: {exc.detail}")

    if exc.status_code == 401:
        error = ErrorCodes.unauthorized(str(exc.detail))
    elif exc.status_code == 403:
        error = ErrorCodes.forbidden(str(exc.detail))
    elif exc.status_code == 404:
        error = ErrorCodes.not_found("endpoint")
    elif exc.status_code == 400:
        error = ErrorCodes.validation_error("request", str(exc.detail))
    else:
        error = ErrorCodes.internal_error(str(exc.detail))

    error.function_name = FUNCTION_NAME
    response = error.to_standard_response()
    return JSONResponse(status_code=exc.status_code, content=response.model_dump())


@app.exception_handler(StarletteHTTPException)
async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle Starlette HTTP exceptions with standardized format."""
    logger.error(f"Starlette HTTP error {exc.status_code}: {exc.detail}")

    if exc.status_code == 404:
        error = ErrorCodes.not_found("endpoint")
    elif exc.status_code == 405:
        error = ErrorCodes.validation_error(
            "method", "Method not allowed for this endpoint"
        )
    elif exc.status_code == 401:
        error = ErrorCodes.unauthorized(str(exc.detail))
    elif exc.status_code == 403:
        error = ErrorCodes.forbidden(str(exc.detail))
    elif exc.status_code == 400:
        error = ErrorCodes.validation_error("request", str(exc.detail))
    else:
        error = ErrorCodes.internal_error(str(exc.detail))

    error.function_name = FUNCTION_NAME
    response = error.to_standard_response()
    return JSONResponse(status_code=exc.status_code, content=response.model_dump())


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with standardized format."""
    error = ErrorCodes.internal_error(
        str(exc), "Please check your request and try again"
    )
    error.function_name = FUNCTION_NAME
    response = error.to_standard_response()
    return JSONResponse(status_code=500, content=response.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with standardized format."""
    # Extract first error for main message
    first_error = exc.errors()[0] if exc.errors() else {}
    field_name = (
        first_error.get("loc", ["unknown"])[-1] if first_error.get("loc") else "unknown"
    )

    error = ErrorCodes.validation_error(
        str(field_name), first_error.get("msg", "Validation failed")
    )
    error.function_name = FUNCTION_NAME
    response = error.to_standard_response()

    # Add all validation errors to the response
    all_errors = [
        f"Field '{'.'.join(map(str, err.get('loc', [])))}': {err.get('msg', 'Invalid')}"
        for err in exc.errors()
    ]
    response.errors = all_errors

    return JSONResponse(status_code=422, content=response.model_dump())


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# API Routes


@app.get("/")
async def root():
    """Root endpoint with service information."""
    start_time = time.time()

    service_data = {
        "service": "content-ranker",
        "version": "1.0.0",
        "description": "Content ranking service with multi-factor scoring",
        "status": "running",
        "endpoints": {
            # Legacy endpoints
            "health": "/health",
            "status": "/status",
            "rank_enriched": "/rank/enriched",
            "rank_batch": "/rank/batch",
            "rank": "/rank",
            # Standardized API endpoints
            "api_health": "/api/content-ranker/health",
            "api_status": "/api/content-ranker/status",
            "api_process": "/api/content-ranker/process",
            "api_docs": "/api/content-ranker/docs",
        },
    }

    execution_time = max(1, int((time.time() - start_time) * 1000))

    response = StandardResponse.success(
        message="Content Ranker API running", data=service_data
    )
    response.metadata["execution_time_ms"] = execution_time
    response.metadata["function"] = FUNCTION_NAME
    response.metadata["version"] = "1.0.0"

    return response.model_dump()


@app.get("/health", response_model=HealthResponse)
async def health():
    """
    Health check endpoint.

    Returns service health status and Azure connectivity.
    """
    try:
        # Perform health checks
        health_status = health_check()

        return HealthResponse(
            status=health_status["status"],
            service="content-ranker",
            azure_connectivity=health_status.get("azure_connectivity") == "connected",
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/status")
async def get_status():
    """
    Get detailed service status including content statistics.

    Returns:
        Service status with content counts and container information
    """
    try:
        status = await ranker_service.get_ranking_status()
        return status
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get service status")


@app.post("/rank/enriched")
async def rank_enriched_content(request: BatchRankingRequest):
    """
    Rank all enriched content using multi-factor scoring.

    Retrieves all enriched content from blob storage and ranks it
    based on the specified weights and criteria.
    """
    try:
        result = await ranker_service.rank_content_batch(
            weights=request.weights,
            target_topics=request.target_topics,
            limit=request.limit,
        )
        return result
    except Exception as e:
        logger.error(f"Enriched content ranking failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to rank enriched content")


@app.post("/rank/batch")
async def rank_content_batch_endpoint(request: BatchRankingRequest):
    """
    Rank content using batch processing.

    Args:
        request: Batch ranking request with weights and options

    Returns:
        Ranked content items with metadata
    """
    try:
        result = await ranker_service.rank_content_batch(
            weights=request.weights,
            target_topics=request.target_topics,
            limit=request.limit,
        )
        return result
    except Exception as e:
        logger.error(f"Batch ranking failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process batch ranking")


@app.post("/rank", response_model=RankingResponse)
async def rank_content(request: SpecificRankingRequest):
    """
    Rank specific content items using multi-factor scoring.

    Combines engagement scores, recency factors, and topic relevance
    to provide intelligent content ranking.

    Args:
        request: Ranking request with content items and options

    Returns:
        Ranked content items with scoring metadata

    Raises:
        HTTPException: If ranking fails
    """
    try:
        # Rank the provided content items
        ranked_items = await ranker_service.rank_specific_content(
            content_items=request.content_items,
            weights=request.weights,
            target_topics=request.target_topics,
            limit=request.limit,
        )

        # Create response metadata
        metadata = {
            "total_items_processed": len(request.content_items),
            "items_returned": len(ranked_items),
            "ranking_algorithm": "multi_factor_composite",
            "factors_used": ["engagement", "recency", "topic_relevance"],
        }

        return RankingResponse(ranked_items=ranked_items, metadata=metadata)

    except Exception as e:
        logger.error(f"Content ranking failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to rank content items")


# ========================================
# STANDARDIZED API ENDPOINTS
# ========================================


@app.get("/api/content-ranker/health")
async def api_health():
    """Standardized health check endpoint."""
    start_time = time.time()

    try:
        # Perform health checks
        health_status = health_check()

        health_data = HealthStatus(
            status=health_status["status"],
            service="content-ranker",
            version="1.0.0",
            dependencies={
                "azure_connectivity": health_status.get("azure_connectivity")
                == "connected"
            },
            uptime_seconds=None,  # Could be calculated if needed
            environment="container",
        )

        execution_time = max(1, int((time.time() - start_time) * 1000))

        response = StandardResponse.success(
            message="Content ranker service is healthy", data=health_data.model_dump()
        )
        response.metadata["execution_time_ms"] = execution_time
        response.metadata["function"] = FUNCTION_NAME
        response.metadata["version"] = "1.0.0"

        return response.model_dump()

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        execution_time = max(1, int((time.time() - start_time) * 1000))

        error = ErrorCodes.internal_error(
            "Health check failed", "Service may be experiencing issues"
        )
        error.function_name = FUNCTION_NAME
        response = error.to_standard_response()
        response.metadata["execution_time_ms"] = execution_time

        return JSONResponse(status_code=503, content=response.model_dump())


@app.get("/api/content-ranker/status")
async def api_status():
    """Standardized status endpoint."""
    start_time = time.time()

    try:
        status = await ranker_service.get_ranking_status()

        status_data = ServiceStatus(
            service="content-ranker",
            status="running",
            uptime_seconds=None,  # Could be calculated if needed
            stats=status if isinstance(status, dict) else {"raw_status": str(status)},
            last_operation=None,  # Could be set to last ranking operation
        )

        execution_time = max(1, int((time.time() - start_time) * 1000))

        response = StandardResponse.success(
            message="Content ranker status retrieved successfully",
            data=status_data.model_dump(),
        )
        response.metadata["execution_time_ms"] = execution_time
        response.metadata["function"] = FUNCTION_NAME
        response.metadata["version"] = "1.0.0"

        return response.model_dump()

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        execution_time = max(1, int((time.time() - start_time) * 1000))

        error = ErrorCodes.internal_error(str(e), "Failed to retrieve service status")
        error.function_name = FUNCTION_NAME
        response = error.to_standard_response()
        response.metadata["execution_time_ms"] = execution_time

        return JSONResponse(status_code=500, content=response.model_dump())


@app.post("/api/content-ranker/process")
async def api_process(request: SpecificRankingRequest):
    """Standardized content ranking endpoint."""
    start_time = time.time()

    try:
        # Rank the provided content items using the same logic as /rank
        ranked_items = await ranker_service.rank_specific_content(
            content_items=request.content_items,
            weights=request.weights,
            target_topics=request.target_topics,
            limit=request.limit,
        )

        # Create result data - convert items to dict safely
        items_list = []
        for item in ranked_items:
            if isinstance(item, dict):
                items_list.append(item)
            elif hasattr(item, "model_dump"):
                items_list.append(item.model_dump())
            elif hasattr(item, "dict"):
                items_list.append(item.dict())
            else:
                # Convert to dict representation
                items_list.append({"item": str(item)})

        result_data = {
            "ranked_items": items_list,
            "metadata": {
                "total_items_processed": len(request.content_items),
                "items_returned": len(ranked_items),
                "ranking_algorithm": "multi_factor_composite",
                "factors_used": ["engagement", "recency", "topic_relevance"],
            },
        }

        execution_time = max(1, int((time.time() - start_time) * 1000))

        response = StandardResponse.success(
            message=f"Successfully ranked {len(ranked_items)} content items",
            data=result_data,
        )
        response.metadata["execution_time_ms"] = execution_time
        response.metadata["function"] = FUNCTION_NAME
        response.metadata["version"] = "1.0.0"

        return response.model_dump()

    except Exception as e:
        logger.error(f"Content ranking failed: {e}")
        execution_time = max(1, int((time.time() - start_time) * 1000))

        error = ErrorCodes.internal_error(str(e), "Failed to rank content items")
        error.function_name = FUNCTION_NAME
        response = error.to_standard_response()
        response.metadata["execution_time_ms"] = execution_time

        return JSONResponse(status_code=500, content=response.model_dump())


@app.get("/api/content-ranker/docs")
async def api_docs():
    """API documentation and usage information."""
    docs_data = {
        "service": "content-ranker",
        "version": "1.0.0",
        "description": "Ranks content using multi-factor scoring algorithms",
        "endpoints": {
            "/api/content-ranker/health": {
                "method": "GET",
                "description": "Health check with dependency status",
                "response": "StandardResponse with HealthStatus data",
            },
            "/api/content-ranker/status": {
                "method": "GET",
                "description": "Service status and ranking statistics",
                "response": "StandardResponse with ServiceStatus data",
            },
            "/api/content-ranker/process": {
                "method": "POST",
                "description": "Rank content items using multi-factor scoring",
                "body": "SpecificRankingRequest",
                "response": "StandardResponse with ranking results",
            },
        },
        "ranking_factors": [
            {
                "name": "engagement",
                "description": "User engagement metrics (scores, comments, shares)",
                "weight_range": "0.0 - 1.0",
            },
            {
                "name": "recency",
                "description": "Content freshness and time-based relevance",
                "weight_range": "0.0 - 1.0",
            },
            {
                "name": "topic_relevance",
                "description": "Relevance to specified target topics",
                "weight_range": "0.0 - 1.0",
            },
        ],
        "sample_request": {
            "content_items": [
                {
                    "id": "item_001",
                    "title": "Sample Content",
                    "content": "Content text...",
                    "enrichment": {
                        "sentiment": {"compound": 0.5},
                        "topics": ["technology"],
                        "summary": "Brief summary",
                    },
                }
            ],
            "weights": {"engagement": 0.4, "recency": 0.3, "topic_relevance": 0.3},
            "target_topics": ["technology"],
            "limit": 10,
        },
    }

    response = StandardResponse.success(
        message="Content ranker API documentation", data=docs_data
    )
    response.metadata["function"] = FUNCTION_NAME
    response.metadata["version"] = "1.0.0"

    return response.model_dump()


if __name__ == "__main__":
    config = get_config()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.get("environment") == "development",
    )

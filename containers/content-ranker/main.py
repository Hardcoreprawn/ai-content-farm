#!/usr/bin/env python3
"""
Content Ranker - Main FastAPI Application

Ranks enriched content using multi-factor scoring algorithms.
Simplified main application that assembles routers for legacy and standardized API endpoints.

The business logic is in service_logic.py
Legacy endpoints are in legacy_endpoints.py
Standardized API endpoints are in api_endpoints.py
"""

import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Add the project root to the path to import shared libraries
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Import our API routers
from api_endpoints import router as api_router
from legacy_endpoints import router as legacy_router

# Import business logic for app lifecycle
from service_logic import ContentRankerService

from config import get_config
from libs.shared_models import (
    ErrorCodes,
    StandardResponseFactory,
    create_error_response,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize service for app lifecycle
ranker_service = ContentRankerService()

# Function name for standardized responses
FUNCTION_NAME = "content-ranker"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info(f"Starting {FUNCTION_NAME} service...")
    try:
        await ranker_service.ensure_containers()
        logger.info("Service startup completed successfully")
    except Exception as e:
        logger.error(f"Service startup failed: {e}")

    yield

    # Shutdown
    logger.info(f"Shutting down {FUNCTION_NAME} service...")


# Create FastAPI application
app = FastAPI(
    title="Content Ranker Service",
    description="Ranks content using multi-factor scoring algorithms with both legacy and standardized API endpoints",
    version="1.0.0",
    lifespan=lifespan,
)

# Include API routers
app.include_router(
    api_router
)  # Standardized API endpoints with /api/content-ranker prefix
app.include_router(legacy_router)  # Legacy endpoints for backward compatibility


# Basic application endpoints
@app.get("/")
async def root():
    """Root endpoint providing service information and available endpoints."""
    return {
        "service": "content-ranker",
        "version": "1.0.0",
        "description": "Content ranking service with multi-factor scoring algorithms",
        "status": "running",
        "endpoints": {
            # Standardized API endpoints (recommended)
            "api_health": "/api/content-ranker/health",
            "api_status": "/api/content-ranker/status",
            "api_process": "/api/content-ranker/process",
            "api_docs": "/api/content-ranker/docs",
            # Legacy endpoints (backward compatibility)
            "legacy_rank": "/rank",
            "legacy_rank_batch": "/rank/batch",
            "legacy_rank_enriched": "/rank/enriched",
        },
        "api_categories": {
            "standardized": "Use /api/content-ranker/* endpoints for new integrations",
            "legacy": "Existing endpoints maintained for backward compatibility",
        },
    }


@app.get("/health")
async def legacy_health():
    """Legacy health check endpoint for backward compatibility."""
    try:
        from config import health_check

        health_data = health_check()
        return {
            "status": health_data.get("status", "healthy"),
            "service": "content-ranker",
            "version": "1.0.0",
            "message": "Legacy health endpoint - use /api/content-ranker/health for standardized format",
        }
    except Exception as e:
        logger.error(f"Legacy health check failed: {e}")
        raise HTTPException(status_code=503, detail="Health check failed")


@app.get("/status")
async def legacy_status():
    """Legacy status endpoint for backward compatibility."""
    try:
        status_data = await ranker_service.get_ranking_status()
        return {
            "status": "running",
            "service": "content-ranker",
            "data": status_data,
            "message": "Legacy status endpoint - use /api/content-ranker/status for standardized format",
        }
    except Exception as e:
        logger.error(f"Legacy status check failed: {e}")
        raise HTTPException(status_code=500, detail="Status check failed")


@app.get("/docs")
async def legacy_docs():
    """Legacy documentation endpoint for backward compatibility."""
    return {
        "service": "content-ranker",
        "version": "1.0.0",
        "message": "Legacy docs endpoint - use /api/content-ranker/docs for standardized format",
        "migration_info": {
            "recommendation": "Migrate to standardized API endpoints under /api/content-ranker/",
            "legacy_support": "Legacy endpoints will be maintained for backward compatibility",
            "new_endpoints": {
                "health": "/api/content-ranker/health",
                "status": "/api/content-ranker/status",
                "process": "/api/content-ranker/process",
                "docs": "/api/content-ranker/docs",
            },
        },
    }


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with standardized error responses."""
    logger.error(f"HTTP {exc.status_code}: {exc.detail}")

    error_response = create_error_response(
        message=f"HTTP {exc.status_code} Error",
        errors=[str(exc.detail)],
        metadata={
            "timestamp": time.time(),
            "function": FUNCTION_NAME,
            "path": str(request.url.path),
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=exc.status_code, content=error_response.model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with standardized error responses."""
    logger.error(f"Validation error: {exc}")

    error_response = create_error_response(
        message="Request validation failed",
        errors=[str(error) for error in exc.errors()],
        metadata={
            "timestamp": time.time(),
            "function": FUNCTION_NAME,
            "path": str(request.url.path),
            "method": request.method,
        },
    )

    return JSONResponse(status_code=422, content=error_response.model_dump())


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions with standardized error responses."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    error_response = create_error_response(
        message="Internal server error",
        errors=["An unexpected error occurred"],
        metadata={
            "timestamp": time.time(),
            "function": FUNCTION_NAME,
            "path": str(request.url.path),
            "method": request.method,
        },
    )

    return JSONResponse(status_code=500, content=error_response.model_dump())


if __name__ == "__main__":
    config = get_config()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.port,
        reload=config.debug,
        log_level="info",
    )

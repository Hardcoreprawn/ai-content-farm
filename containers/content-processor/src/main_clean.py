#!/usr/bin/env python3
"""
Standardized Content Processor FastAPI Application

Implements standardized API endpoints following libs/standard_endpoints.py patterns.
Uses pydantic-settings configuration and secure error handling.

Phase 1: Foundation implementation for issue #390
- Standard API endpoints (/health, /status, /process)
- Shared library integration
- OWASP-compliant error handling
- Pydantic-settings configuration
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Union

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Local imports
from src.config import ContentProcessorSettings, settings
from src.libs.secure_error_handler import SecureErrorHandler
from src.libs.shared_models import StandardResponse, create_success_response
from src.libs.standard_endpoints import (
    create_standard_health_endpoint,
    create_standard_root_endpoint,
    create_standard_status_endpoint,
)
from src.processing_service import ContentProcessingService
from src.processing_service import ProcessingRequest as ServiceProcessingRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances - initialized during lifespan
error_handler: SecureErrorHandler = None
processing_service: ContentProcessingService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup/shutdown operations.

    Initializes shared services and cleans up resources.
    """
    global error_handler, processing_service

    try:
        # Startup
        logger.info("Starting Content Processor service")

        # Initialize error handler
        error_handler = SecureErrorHandler()

        # Initialize processing service
        processing_service = ContentProcessingService(settings)
        await processing_service.initialize()

        logger.info("Content Processor service started successfully")

        yield

    except Exception as e:
        logger.error(f"Failed to start Content Processor service: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down Content Processor service")

        if processing_service:
            await processing_service.cleanup()

        logger.info("Content Processor service shutdown complete")


# Create FastAPI application with lifespan management
app = FastAPI(
    title="Content Processor API",
    description="Processes content using AI services with standardized endpoints",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Standard Endpoints",
            "description": "Standard health, status, and root endpoints",
        },
        {"name": "Processing", "description": "Content processing operations"},
    ],
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_settings() -> ContentProcessorSettings:
    """Dependency to get current settings."""
    return settings


def get_error_handler() -> SecureErrorHandler:
    """Dependency to get current error handler."""
    return error_handler


def get_processing_service() -> ContentProcessingService:
    """Dependency to get current processing service."""
    return processing_service


# Custom root endpoint with service-specific information
@app.get("/", tags=["Standard Endpoints"])
async def root() -> StandardResponse:
    """
    Custom root endpoint for content processor.

    Provides service identification and basic information.
    """
    return create_success_response(
        message="Content Processor API is running",
        data={
            "service": "content-processor",
            "version": "1.0.0",
            "description": "AI-powered content processing service",
            "features": [
                "Content quality analysis",
                "AI-powered content generation",
                "Multi-region OpenAI support",
                "Retry logic and failover",
            ],
        },
    )


# Custom status endpoint with detailed service status
@app.get("/status", tags=["Standard Endpoints"])
async def status(
    processing_service: ContentProcessingService = Depends(get_processing_service),
) -> StandardResponse:
    """
    Custom status endpoint with processing service health information.

    Returns detailed status including external service connectivity.
    """
    try:
        # Get processing service status
        service_status = await processing_service.get_status()

        status_data = {
            "service": "content-processor",
            "status": "healthy",
            "timestamp": service_status.get("timestamp"),
            "external_apis": service_status.get("external_apis", {}),
            "performance": service_status.get("performance", {}),
            "configuration": {
                "max_content_length": settings.max_content_length,
                "processing_timeout": settings.processing_timeout,
                "retry_attempts": settings.retry_attempts,
                "regions_available": len(settings.get_available_regions()),
            },
        }

        return create_success_response(
            message="Content processor is healthy", data=status_data
        )

    except Exception as e:
        error_handler.log_error(e, {"endpoint": "status"})
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")


# Add standard health endpoint
app.include_router(create_standard_health_endpoint(), tags=["Standard Endpoints"])


# Content processing models
class ProcessingRequest(BaseModel):
    """Request model for content processing."""

    content: str
    processing_type: str = "general"
    options: Dict[str, Any] = {}


class ProcessingResult(BaseModel):
    """Response model for processed content."""

    processed_content: str
    quality_score: float
    processing_metadata: Dict[str, Any]


@app.post("/process", tags=["Processing"])
async def process_content(
    request: ProcessingRequest,
    processing_service: ContentProcessingService = Depends(get_processing_service),
    error_handler: SecureErrorHandler = Depends(get_error_handler),
) -> StandardResponse:
    """
    Process content using AI services.

    This endpoint processes input content using configured AI services
    with quality analysis and metadata generation.
    """
    try:
        # Validate content length
        if len(request.content) > settings.max_content_length:
            raise HTTPException(
                status_code=400,
                detail=f"Content too long. Maximum {settings.max_content_length} characters allowed.",
            )

        # Convert to service request format
        service_request = ServiceProcessingRequest(
            content=request.content,
            processing_type=request.processing_type,
            options=request.options,
        )

        # Process content using the processing service
        result = await processing_service.process_content(service_request)

        # Format response
        response_data = ProcessingResult(
            processed_content=result.processed_content,
            quality_score=result.quality_score,
            processing_metadata=result.metadata,
        )

        return create_success_response(
            message="Content processed successfully", data=response_data.dict()
        )

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors, etc.)
        raise
    except Exception as e:
        # Log and handle unexpected errors securely
        error_handler.log_error(
            e,
            {
                "endpoint": "process_content",
                "content_length": len(request.content),
                "processing_type": request.processing_type,
            },
        )

        raise HTTPException(
            status_code=500, detail="An error occurred while processing content"
        )


@app.get("/process/status", tags=["Processing"])
async def processing_status(
    processing_service: ContentProcessingService = Depends(get_processing_service),
) -> StandardResponse:
    """
    Get detailed processing service status and statistics.
    """
    try:
        status = await processing_service.get_detailed_status()

        return create_success_response(
            message="Processing status retrieved successfully", data=status
        )

    except Exception as e:
        error_handler.log_error(e, {"endpoint": "processing_status"})
        raise HTTPException(
            status_code=500, detail="Unable to retrieve processing status"
        )


# Exception handlers for proper error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions with standardized responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None,
            "timestamp": StandardResponse.get_timestamp(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions with secure error responses."""
    if error_handler:
        error_handler.log_error(exc, {"request_url": str(request.url)})

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An internal error occurred",
            "data": None,
            "timestamp": StandardResponse.get_timestamp(),
        },
    )


# Health check for container orchestration
@app.get("/health/ready", tags=["Standard Endpoints"])
async def readiness_check(
    processing_service: ContentProcessingService = Depends(get_processing_service),
) -> StandardResponse:
    """
    Kubernetes-style readiness probe.

    Checks if the service is ready to accept requests.
    """
    try:
        # Check if processing service is ready
        is_ready = await processing_service.is_ready()

        if not is_ready:
            raise HTTPException(status_code=503, detail="Service not ready")

        return create_success_response(message="Service is ready", data={"ready": True})

    except HTTPException:
        raise
    except Exception as e:
        if error_handler:
            error_handler.log_error(e, {"endpoint": "readiness_check"})
        raise HTTPException(status_code=503, detail="Service not ready")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")

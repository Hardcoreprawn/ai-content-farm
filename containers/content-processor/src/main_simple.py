#!/usr/bin/env python3
"""
Simplified Content Processor FastAPI Application

A working version while we complete the full integration.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Local imports
from src.config import ContentProcessorSettings, settings
from src.libs.shared_models import StandardResponse, create_success_response

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager."""
    logger.info("Starting Content Processor service")
    yield
    logger.info("Shutting down Content Processor service")


# Create FastAPI application
app = FastAPI(
    title="Content Processor API",
    description="Processes content using AI services with standardized endpoints",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/", tags=["Standard Endpoints"])
async def root() -> StandardResponse:
    """Root endpoint."""
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


@app.get("/health", tags=["Standard Endpoints"])
async def health() -> StandardResponse:
    """Health check endpoint."""
    return create_success_response(
        message="Service is healthy",
        data={
            "status": "healthy",
            "service": "content-processor",
            "version": "1.0.0",
            "uptime_seconds": (
                time.time() - app.state.start_time
                if hasattr(app.state, "start_time")
                else 0
            ),
        },
    )


@app.get("/status", tags=["Standard Endpoints"])
async def status() -> StandardResponse:
    """Status endpoint with detailed information."""
    return create_success_response(
        message="Content processor is healthy",
        data={
            "service": "content-processor",
            "status": "healthy",
            "timestamp": time.time(),
            "configuration": {
                "processing_timeout": settings.processing_timeout_seconds,
                "max_concurrent_processes": settings.max_concurrent_processes,
                "quality_threshold": settings.quality_threshold,
            },
        },
    )


@app.post("/process", tags=["Processing"])
async def process_content(request: ProcessingRequest) -> StandardResponse:
    """Process content using AI services."""
    try:
        # Validate content length
        max_content_length = 10000
        if len(request.content) > max_content_length:
            raise HTTPException(
                status_code=400,
                detail=f"Content too long. Maximum {max_content_length} characters allowed.",
            )

        # Mock processing for now (Phase 3 completion in progress)
        mock_result = ProcessingResult(
            processed_content=f"Processed: {request.content[:100]}{'...' if len(request.content) > 100 else ''}",
            quality_score=0.85,
            processing_metadata={
                "processing_type": request.processing_type,
                "options": request.options,
                "timestamp": time.time(),
                "model_used": "mock-processor",
                "status": "completed",
            },
        )

        return create_success_response(
            message="Content processed successfully", data=mock_result.dict()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Processing error: {e}")
        raise HTTPException(
            status_code=500, detail="An error occurred while processing content"
        )


@app.get("/process/status", tags=["Processing"])
async def processing_status() -> StandardResponse:
    """Get processing service status."""
    return create_success_response(
        message="Processing status retrieved successfully",
        data={
            "active_processes": 0,
            "queue_size": 0,
            "total_processed": 0,
            "success_rate": 1.0,
            "average_processing_time": 0.0,
            "status": "ready",
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None,
            "timestamp": time.time(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An internal error occurred",
            "data": None,
            "timestamp": time.time(),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

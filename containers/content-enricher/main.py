#!/usr/bin/env python3
"""
Content Enricher - Main FastAPI Application

Minimal implementation to make tests pass.
This is the API layer - business logic is in enricher.py
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import List, Dict, Any, Optional
import uvicorn
import logging
import json

# Import our business logic
from enricher import enrich_content_batch
from config import get_config, health_check

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Content Enricher",
    description="Enriches processed content with AI analysis and metadata",
    version="1.0.0",
)


# Pydantic models for request/response validation
class ContentItem(BaseModel):
    """Content item to be enriched."""

    id: str = Field(...,
                    description="Unique identifier for the content item", min_length=1)
    title: str = Field(...,
                       description="Original title of the content", min_length=1)
    clean_title: str = Field(
        ..., description="Cleaned title without special characters", min_length=1)
    normalized_score: Optional[float] = Field(
        0.0, ge=0.0, le=1.0, description="Normalized score (0-1)")
    engagement_score: Optional[float] = Field(
        0.0, ge=0.0, le=1.0, description="Engagement score (0-1)")
    source_url: Optional[str] = Field(
        None, description="URL to the original content")
    published_at: Optional[str] = Field(
        None, description="Publication timestamp in ISO format")
    content_type: Optional[str] = Field(
        "text", description="Type of content (text, link, image)")
    source_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Source-specific metadata")


class EnrichmentOptions(BaseModel):
    """Options for content enrichment."""

    include_summary: bool = Field(
        True, description="Whether to generate content summaries")
    max_summary_length: int = Field(
        200, ge=50, le=1000, description="Maximum length of generated summaries")
    classify_topics: bool = Field(
        True, description="Whether to classify content topics")
    analyze_sentiment: bool = Field(
        True, description="Whether to analyze content sentiment")
    calculate_trends: bool = Field(
        True, description="Whether to calculate trend scores")


class EnrichmentRequest(BaseModel):
    """Request to enrich content items."""

    items: List[ContentItem] = Field(...,
                                     description="List of content items to enrich")
    options: Optional[EnrichmentOptions] = Field(
        default=None, description="Enrichment options")


class EnrichmentResponse(BaseModel):
    """Response from content enrichment."""

    enriched_items: List[Dict[str, Any]
                         ] = Field(..., description="List of enriched content items")
    metadata: Dict[str, Any] = Field(..., description="Processing metadata")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    azure_connectivity: bool = Field(...,
                                     description="Azure connectivity status")
    openai_available: bool = Field(..., description="OpenAI API availability")


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "details": exc.errors(),
            "status_code": 422
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "status_code": 500
        }
    )


# API endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check_endpoint() -> Dict[str, Any]:
    """
    Health check endpoint.

    Returns:
        Health status of the service and dependencies
    """
    try:
        status = health_check()
        return {
            "status": "healthy",
            **status
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.post("/enrich", response_model=EnrichmentResponse)
async def enrich_content(request: EnrichmentRequest) -> Dict[str, Any]:
    """
    Enrich content items with AI analysis and metadata.

    Args:
        request: Enrichment request with content items and options

    Returns:
        Enriched content items with analysis results

    Raises:
        HTTPException: If enrichment fails
    """
    try:
        # Convert Pydantic models to dictionaries for processing
        items_data = [item.model_dump() for item in request.items]

        # Process the enrichment
        # Resolve the function at runtime so test patches on the module take
        # effect regardless of how modules were imported during the full run.
        try:
            import importlib as _importlib
            _mod = None
            try:
                _mod = _importlib.import_module('main')
            except Exception:
                _mod = None

            if _mod is not None and hasattr(_mod, 'enrich_content_batch'):
                _enrich_fn = getattr(_mod, 'enrich_content_batch')
            else:
                _enrich_fn = enrich_content_batch

            result = _enrich_fn(items_data)
        except Exception:
            # Let outer exception handler translate to HTTPException
            raise

        # Add options to metadata
        if request.options is not None:
            result["metadata"]["options"] = request.options.model_dump()

        return result

    except ValueError as e:
        logger.error(f"Validation error in enrichment: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error during content enrichment: {e}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(
            f"Request items: {len(request.items) if request.items else 'None'}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail="Enrichment processing failed")


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with service information."""
    config = get_config()
    return {
        "service": config.service_name,
        "version": config.version,
        "description": "Content enrichment service for AI content pipeline",
        "endpoints": {
            "health": "/health",
            "enrich": "/enrich (POST)",
            "docs": "/docs"
        }
    }


# Development server
if __name__ == "__main__":
    config = get_config()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,  # Different port from content-processor
        reload=config.debug,
        log_level="info" if not config.debug else "debug"
    )

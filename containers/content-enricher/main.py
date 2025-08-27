#!/usr/bin/env python3
"""
Content Enricher - Main FastAPI Application

Minimal implementation to make tests pass.
This is the API layer - business logic is in enricher.py
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import uvicorn

# Import our business logic
from enricher import enrich_content_batch
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from models import (
    ContentItem,
    EnrichmentOptions,
    EnrichmentRequest,
    EnrichmentResponse,
    HealthResponse,
)
from pydantic import BaseModel, Field, ValidationError
from service_logic import ContentEnricherService
from starlette.exceptions import HTTPException as StarletteHTTPException

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

# Store service start time for uptime calculation
service_start_time = datetime.now(timezone.utc)

# Initialize service lazily to avoid import-time dependencies
enricher_service = None


def get_enricher_service() -> ContentEnricherService:
    """Get or create the enricher service instance."""
    global enricher_service
    if enricher_service is None:
        enricher_service = ContentEnricherService()
    return enricher_service


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "details": exc.errors(),
            "status_code": 422,
        },
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
            "status_code": 500,
        },
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
        return {"status": "healthy", **status}
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
                _mod = _importlib.import_module("main")
            except Exception:
                _mod = None

            if _mod is not None and hasattr(_mod, "enrich_content_batch"):
                _enrich_fn = getattr(_mod, "enrich_content_batch")
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
            f"Request items: {len(request.items) if request.items else 'None'}"
        )
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Enrichment processing failed")


# Pipeline integration endpoints


@app.post("/enrich/processed")
async def enrich_processed_content(processed_data: Dict[str, Any]):
    """Enrich processed content from the content-processor."""
    try:
        result = await get_enricher_service().enrich_processed_content(
            processed_data=processed_data, save_to_storage=True
        )
        return result
    except Exception as e:
        logger.error(f"Error enriching processed content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/enrich/batch")
async def enrich_batch():
    """Enrich a batch of unenriched processed content."""
    try:
        unenriched = await get_enricher_service().find_unenriched_processed_content(
            limit=5
        )

        if not unenriched:
            return {
                "message": "No unenriched processed content found",
                "enriched_count": 0,
                "results": [],
            }

        results = []
        for processed_info in unenriched:
            try:
                result = await get_enricher_service().enrich_processed_content(
                    processed_data=processed_info["processed_data"],
                    save_to_storage=True,
                )
                results.append(
                    {
                        "process_id": processed_info["process_id"],
                        "status": "success",
                        "enrichment_id": result["enrichment_id"],
                        "enriched_items": len(result["enriched_items"]),
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "process_id": processed_info["process_id"],
                        "status": "error",
                        "error": str(e),
                    }
                )

        successful_count = sum(1 for r in results if r["status"] == "success")
        return {
            "message": f"Enriched {successful_count} processed content items",
            "enriched_count": successful_count,
            "results": results,
        }
    except Exception as e:
        logger.error(f"Error in batch enrichment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status():
    """Get enricher service status and pipeline information."""
    try:
        # Get service statistics
        stats = get_enricher_service().get_service_stats()

        # Get unenriched count
        unenriched = await get_enricher_service().find_unenriched_processed_content(
            limit=100
        )
        unenriched_count = len(unenriched)

        return {
            "service": "content-enricher",
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
            "pipeline": {
                "unenriched_processed_content": unenriched_count,
                "last_batch_enriched": stats.get("last_enriched"),
                "enrichment_capacity": "ready",
            },
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
            "enrich_processed": "/enrich/processed (POST)",
            "enrich_batch": "/enrich/batch (POST)",
            "status": "/status",
            "docs": "/docs",
        },
    }


# Development server
if __name__ == "__main__":
    config = get_config()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,  # Different port from content-processor
        reload=config.debug,
        log_level="info" if not config.debug else "debug",
    )

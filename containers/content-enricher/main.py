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
from fastapi import Depends, FastAPI, HTTPException, Request
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
from libs.shared_models import (
    ErrorCodes,
    StandardResponse,
    StandardResponseFactory,
    create_service_dependency,
)

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

# Create service dependency
service_metadata = create_service_dependency("content-enricher")

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
    """Handle general exceptions securely."""
    # Use secure error handling - logs actual error but returns generic message
    error = ErrorCodes.secure_internal_error(exc, "content-enricher")
    error.function_name = "content-enricher"
    response = error.to_standard_response()
    return JSONResponse(status_code=500, content=response.model_dump())


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
        # Use secure validation error for client-facing message
        error = ErrorCodes.secure_validation_error(
            "enrichment_data", "Invalid enrichment data format"
        )
        error.function_name = "content-enricher"
        response = error.to_standard_response()
        raise HTTPException(status_code=400, detail=response.message)
    except Exception as e:
        logger.error(f"Error during content enrichment: {e}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(
            f"Request items: {len(request.items) if request.items else 'None'}"
        )
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        # Use secure error response instead of generic string
        error = ErrorCodes.secure_internal_error(e, "content_enrichment")
        error.function_name = "content-enricher"
        response = error.to_standard_response()
        raise HTTPException(status_code=500, detail=response.message)


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
        # Use secure error response
        error = ErrorCodes.secure_internal_error(e, "enrich_processed_content")
        error.function_name = "content-enricher"
        response = error.to_standard_response()
        raise HTTPException(status_code=500, detail=response.message)


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
                        "error": "Enrichment failed",  # Generic error message
                    }
                )
                # Log actual error server-side
                logger.error(
                    f"Error enriching process_id {processed_info['process_id']}: {e}",
                    exc_info=True,
                )

        successful_count = sum(1 for r in results if r["status"] == "success")
        return {
            "message": f"Enriched {successful_count} processed content items",
            "enriched_count": successful_count,
            "results": results,
        }
    except Exception as e:
        logger.error(f"Error in batch enrichment: {e}")
        # Use secure error response
        error = ErrorCodes.secure_internal_error(e, "batch_enrichment")
        error.function_name = "content-enricher"
        response = error.to_standard_response()
        raise HTTPException(status_code=500, detail=response.message)


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
        # Use secure error response
        error = ErrorCodes.secure_internal_error(e, "status_endpoint")
        error.function_name = "content-enricher"
        response = error.to_standard_response()
        raise HTTPException(status_code=500, detail=response.message)


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


# ================================
# STANDARDIZED API ENDPOINTS
# ================================


@app.get("/api/content-enricher/health", response_model=StandardResponse)
async def api_health(metadata: dict = Depends(service_metadata)) -> StandardResponse:
    """
    Standardized health check endpoint.
    Returns standardized response format with service health status.
    """
    try:
        status = health_check()
        return StandardResponse(
            status="success",
            message="Content enricher service is healthy",
            data={"status": "healthy", **status},
            errors=None,
            metadata=metadata,
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return StandardResponse(
            status="error",
            message="Service unhealthy",
            data={"status": "unhealthy", "error": "Health check failed"},
            errors=None,
            metadata=metadata,
        )


@app.get("/api/content-enricher/status", response_model=StandardResponse)
async def api_status(metadata: dict = Depends(service_metadata)) -> StandardResponse:
    """
    Standardized status endpoint.
    Returns detailed service status and pipeline information.
    """
    try:
        # Get service statistics
        stats = get_enricher_service().get_service_stats()

        # Get unenriched count
        unenriched = await get_enricher_service().find_unenriched_processed_content(
            limit=100
        )
        unenriched_count = len(unenriched)

        status_data = {
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

        return StandardResponse(
            status="success",
            message="Content enricher status retrieved successfully",
            data=status_data,
            errors=None,
            metadata=metadata,
        )
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return StandardResponse(
            status="error",
            message="Failed to retrieve service status",
            data={"error": "Status retrieval failed"},
            errors=None,
            metadata=metadata,
        )


@app.post("/api/content-enricher/process", response_model=StandardResponse)
async def api_process_content(
    request: EnrichmentRequest, metadata: dict = Depends(service_metadata)
) -> StandardResponse:
    """
    Standardized content enrichment endpoint.
    Processes content enrichment requests using standardized response format.
    """
    try:
        # Convert Pydantic models to dictionaries for processing
        items_data = [item.model_dump() for item in request.items]

        # Process the enrichment using the same logic as legacy endpoint
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

        return StandardResponse(
            status="success",
            message=f"Successfully enriched {len(request.items)} content items",
            data=result,
            errors=None,
            metadata=metadata,
        )

    except ValueError as e:
        logger.error(f"Validation error in enrichment: {e}")
        return StandardResponse(
            status="error",
            message="Invalid enrichment data format",
            data={"error": "Validation error", "details": str(e)},
            errors=None,
            metadata=metadata,
        )
    except Exception as e:
        logger.error(f"Error during content enrichment: {e}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(
            f"Request items: {len(request.items) if request.items else 'None'}"
        )
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")

        return StandardResponse(
            status="error",
            message="Content enrichment failed",
            data={"error": "Internal error during enrichment"},
            errors=None,
            metadata=metadata,
        )


@app.get("/api/content-enricher/docs", response_model=StandardResponse)
async def api_docs(metadata: dict = Depends(service_metadata)) -> StandardResponse:
    """
    Standardized API documentation endpoint.
    Returns service documentation and available endpoints.
    """
    config = get_config()
    docs_data = {
        "service": config.service_name,
        "version": config.version,
        "description": "Content enrichment service for AI content pipeline",
        "endpoints": {
            "health": {
                "path": "/api/content-enricher/health",
                "method": "GET",
                "description": "Service health check",
            },
            "status": {
                "path": "/api/content-enricher/status",
                "method": "GET",
                "description": "Detailed service status and pipeline information",
            },
            "process": {
                "path": "/api/content-enricher/process",
                "method": "POST",
                "description": "Enrich content items with AI analysis and metadata",
            },
            "docs": {
                "path": "/api/content-enricher/docs",
                "method": "GET",
                "description": "API documentation",
            },
        },
        "legacy_endpoints": {
            "health": "/health",
            "enrich": "/enrich (POST)",
            "enrich_processed": "/enrich/processed (POST)",
            "enrich_batch": "/enrich/batch (POST)",
            "status": "/status",
            "root": "/",
            "docs": "/docs",
        },
    }

    return StandardResponse(
        status="success",
        message="API documentation retrieved successfully",
        data=docs_data,
        errors=None,
        metadata=metadata,
    )


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

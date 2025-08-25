#!/usr/bin/env python3
"""
Content Ranker - Main FastAPI Application

Ranks enriched content using multi-factor scoring algorithms.
API endpoints for content ranking and health monitoring.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

# Import our business logic
from ranker import rank_content_items
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import get_config, health_check
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
from service_logic import ContentRankerService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize service
ranker_service = ContentRankerService()


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

# Global exception handlers


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle value errors"""
    logger.error(f"Value error: {exc}")
    return JSONResponse(
        status_code=400, content={"detail": "Invalid input data", "error": str(exc)}
    )


@app.exception_handler(json.JSONDecodeError)
async def json_error_handler(request: Request, exc: json.JSONDecodeError):
    """Handle JSON decode errors"""
    logger.error(f"JSON decode error: {exc}")
    return JSONResponse(
        status_code=400, content={"detail": "Malformed JSON", "error": str(exc)}
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    logger.error(f"Validation error: {exc}")
    errors = []
    for error in exc.errors():
        errors.append({"loc": error["loc"], "msg": error["msg"], "type": error["type"]})
    return JSONResponse(
        status_code=422, content={"detail": "Validation error", "errors": errors}
    )


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


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "content-ranker",
        "version": "1.0.0",
        "description": "Content ranking service with multi-factor scoring",
    }


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
            azure_connectivity=health_status.get("azure_connectivity"),
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


if __name__ == "__main__":
    config = get_config()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.get("environment") == "development",
    )

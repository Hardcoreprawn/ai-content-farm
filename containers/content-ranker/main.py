#!/usr/bin/env python3
"""
Content Ranker - Main FastAPI Application

Ranks enriched content using multi-factor scoring algorithms.
API endpoints for content ranking and health monitoring.
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
from ranker import rank_content_items
from config import get_config, health_check

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Content Ranker",
    description="Ranks enriched content using multi-factor scoring algorithms",
    version="1.0.0"
)

# Pydantic models for request/response


class ContentItem(BaseModel):
    """Enriched content item to be ranked."""

    id: str = Field(..., description="Unique identifier for the content item")
    title: str = Field(..., description="Content title")
    clean_title: Optional[str] = Field(None, description="Cleaned title")
    normalized_score: Optional[float] = Field(
        0.0, ge=0.0, le=1.0, description="Normalized engagement score")
    engagement_score: Optional[float] = Field(
        0.0, ge=0.0, le=1.0, description="Engagement score")
    published_at: Optional[str] = Field(
        None, description="Publication timestamp")
    content_type: Optional[str] = Field("text", description="Content type")

    # Enrichment data
    topic_classification: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Topic classification results")
    sentiment_analysis: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Sentiment analysis results")
    trend_analysis: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Trend analysis results")
    source_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Source metadata")


class RankingOptions(BaseModel):
    """Options for content ranking."""

    weights: Optional[Dict[str, float]] = Field(
        None,
        description="Custom weights for ranking factors (engagement, recency, topic_relevance)"
    )
    target_topics: Optional[List[str]] = Field(
        None,
        description="Target topics for relevance scoring"
    )
    limit: Optional[int] = Field(
        None,
        ge=1,
        le=1000,
        description="Maximum number of items to return"
    )


class RankingRequest(BaseModel):
    """Request to rank content items."""

    items: List[ContentItem] = Field(...,
                                     description="List of enriched content items to rank")
    options: Optional[RankingOptions] = Field(
        default=None, description="Ranking options")


class RankedItem(BaseModel):
    """Content item with ranking scores."""

    # Original content (dynamic fields)
    # We'll use Dict[str, Any] to allow flexible content structure


class RankingResponse(BaseModel):
    """Response from content ranking."""

    ranked_items: List[Dict[str, Any]
                       ] = Field(..., description="Ranked content items with scores")
    metadata: Dict[str, Any] = Field(..., description="Ranking metadata")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    azure_connectivity: Optional[bool] = Field(
        None, description="Azure connectivity status")


# Global exception handlers

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle value errors"""
    logger.error(f"Value error: {exc}")
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid input data", "error": str(exc)}
    )


@app.exception_handler(json.JSONDecodeError)
async def json_error_handler(request: Request, exc: json.JSONDecodeError):
    """Handle JSON decode errors"""
    logger.error(f"JSON decode error: {exc}")
    return JSONResponse(
        status_code=400,
        content={"detail": "Malformed JSON", "error": str(exc)}
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    logger.error(f"Validation error: {exc}")
    errors = []
    for error in exc.errors():
        errors.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        })
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": errors}
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# API Routes

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "content-ranker",
        "version": "1.0.0",
        "description": "Content ranking service with multi-factor scoring"
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
            azure_connectivity=health_status.get("azure_connectivity")
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service unhealthy"
        )


@app.post("/rank", response_model=RankingResponse)
async def rank_content(request: RankingRequest):
    """
    Rank content items using multi-factor scoring.

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
        # Convert Pydantic models to dictionaries for processing
        items_data = [item.model_dump() for item in request.items]

        # Extract ranking options
        weights = None
        target_topics = None
        limit = None

        if request.options:
            weights = request.options.weights
            target_topics = request.options.target_topics
            limit = request.options.limit

        # Perform content ranking
        ranked_items = rank_content_items(
            content_items=items_data,
            weights=weights,
            target_topics=target_topics,
            limit=limit
        )

        # Create response metadata
        metadata = {
            "total_items_processed": len(items_data),
            "items_returned": len(ranked_items),
            "ranking_algorithm": "multi_factor_composite",
            "factors_used": ["engagement", "recency", "topic_relevance"]
        }

        # Add options to metadata
        if request.options:
            metadata["options_applied"] = request.options.model_dump()

        # Add weight information from ranking
        if ranked_items:
            first_item_scores = ranked_items[0].get("ranking_scores", {})
            metadata["weights_used"] = first_item_scores.get(
                "weights_used", {})

        return RankingResponse(
            ranked_items=ranked_items,
            metadata=metadata
        )

    except ValueError as e:
        logger.error(f"Validation error in ranking: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error during content ranking: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Ranking processing failed"
        )


if __name__ == "__main__":
    config = get_config()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.get("environment") == "development"
    )

#!/usr/bin/env python3
"""
Content Processor - Main FastAPI Application

Minimal implementation to make tests pass.
This is the API layer - business logic is in processor.py
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
from processor import transform_reddit_post, process_reddit_batch
from config import get_config, health_check

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Content Processor",
    description="Transforms raw Reddit data into structured content",
    version="1.0.0"
)

# Pydantic models for request/response


class RedditPost(BaseModel):
    title: str
    score: int
    num_comments: Optional[int] = 0
    created_utc: Optional[int] = 0
    subreddit: Optional[str] = ""
    url: Optional[str] = ""
    selftext: Optional[str] = ""
    id: Optional[str] = ""


class ProcessRequest(BaseModel):
    source: str = Field(..., description="Data source (e.g., 'reddit')")
    data: List[RedditPost] = Field(..., description="List of posts to process")
    options: Dict[str, Any] = Field(
        default_factory=dict, description="Processing options")


class ProcessedItem(BaseModel):
    id: str
    title: str
    clean_title: str
    normalized_score: float
    engagement_score: float
    source_url: str
    published_at: str
    content_type: str
    source_metadata: Dict[str, Any]


class ProcessResponse(BaseModel):
    processed_items: List[ProcessedItem]
    metadata: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    service: str
    azure_connectivity: Optional[bool] = None

# Global exception handlers


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle JSON parsing errors"""
    logger.error(f"Value error (likely JSON parsing): {exc}")
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid JSON format", "error": str(exc)}
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
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": exc.errors()}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

# Health check endpoint


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint for container orchestration"""
    try:
        status = health_check()
        return HealthResponse(**status)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            service="content-processor",
            azure_connectivity=False
        )

# Main processing endpoint


@app.post("/process", response_model=ProcessResponse)
async def process_content(request: ProcessRequest):
    """Process Reddit data into structured content"""
    try:
        # Validate source
        if request.source != "reddit":
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported source: {request.source}"
            )

        # Validate data
        if not request.data:
            raise HTTPException(
                status_code=422,
                detail="No data provided"
            )

        # Convert Pydantic models to dicts for processing
        reddit_posts = [post.model_dump() for post in request.data]

        # Process the data
        processed_items_raw = process_reddit_batch(reddit_posts)

        # Convert back to Pydantic models for response
        processed_items = [ProcessedItem(**item)
                           for item in processed_items_raw]

        # Create response metadata
        metadata = {
            "source": request.source,
            "items_processed": len(processed_items),
            "options": request.options,
            "processing_version": "1.0.0"
        }

        return ProcessResponse(
            processed_items=processed_items,
            metadata=metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )

# Root endpoint


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "content-processor",
        "version": "1.0.0",
        "status": "running",
        "endpoints": ["/health", "/process"]
    }

# Development server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

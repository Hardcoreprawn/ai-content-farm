#!/usr/bin/env python3
"""
Content Processor - Main FastAPI Application

Minimal implementation to make tests pass.
This is the API layer - business logic is in processor.py
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
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
    """
    Flexible processing request that supports multiple input formats.

    Supports both:
    - Legacy format: {source: "reddit", data: [...]}
    - New format: {items: [...], source: "reddit"} 
    """
    # Primary fields (new format)
    items: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of content items to process (new format)"
    )

    # Legacy fields (backward compatibility)
    source: Optional[str] = Field(
        default=None,
        description="Data source (e.g., 'reddit') - legacy format"
    )
    data: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of posts to process - legacy format"
    )

    # Options (flexible)
    options: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Processing options"
    )

    class Config:
        # Allow extra fields and ignore them for forward compatibility
        extra = "ignore"

    @field_validator('items', 'data', mode='before')
    @classmethod
    def validate_items_or_data(cls, v):
        """Ensure we have valid item data."""
        if v is not None and not isinstance(v, list):
            raise ValueError("Items/data must be a list")
        return v

    @model_validator(mode='after')
    def validate_has_items_or_data(self):
        """Ensure we have either items or data field provided."""
        if self.items is None and self.data is None:
            raise ValueError("Either 'items' or 'data' field is required")
        return self

    def get_items(self) -> List[Dict[str, Any]]:
        """Get items from either new format or legacy format."""
        if self.items is not None:
            return self.items
        elif self.data is not None:
            return self.data
        else:
            raise ValueError("Either 'items' or 'data' field is required")

    def get_source(self) -> str:
        """Get source, defaulting to 'unknown' if not specified."""
        if self.source:
            return self.source
        # Try to infer from first item
        items = self.get_items()
        if items and len(items) > 0:
            first_item = items[0]
            if isinstance(first_item, dict):
                return first_item.get('source', 'unknown')
        return 'unknown'


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
    # Ensure errors are serializable (stringify any non-serializable entries)
    try:
        errors = exc.errors()
    except Exception:
        errors = [str(exc)]

    # Stringify context objects that may contain exceptions
    safe_errors = []
    for e in errors:
        try:
            # Attempt to JSON-serialize the error; if not possible, stringify
            import json as _json
            _json.dumps(e)
            safe_errors.append(e)
        except Exception:
            safe_errors.append({k: (str(v) if not isinstance(v, (str, int, float, bool, list, dict, type(None))) else v) for k, v in (e.items() if isinstance(e, dict) else {"error": str(e)}.items())})

    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": safe_errors}
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
        # Get source and items using the flexible methods
        source = request.get_source()
        items = request.get_items()

        # For now, we primarily support Reddit data
        # Future: Add other source processors
        if source not in ["reddit", "unknown"]:
            logger.warning(f"Processing source '{source}' as generic content")

        # Validate data
        if not items:
            raise HTTPException(
                status_code=422,
                detail="No items provided"
            )

        # Process the data (items are already dicts)
        if source == "reddit":
            processed_items_raw = process_reddit_batch(items)
        else:
            # Generic processing for unknown sources
            processed_items_raw = process_reddit_batch(
                items)  # Use Reddit processor as fallback

        # Convert to Pydantic models for response validation
        processed_items = []
        for item in processed_items_raw:
            try:
                processed_items.append(ProcessedItem(**item))
            except ValidationError as e:
                logger.error(f"Failed to validate processed item: {e}")
                # Skip invalid items but continue processing
                continue

        # Create response metadata
        metadata = {
            "source": source,
            "items_processed": len(processed_items),
            "items_received": len(items),
            "items_skipped": len(items) - len(processed_items),
            "options": request.options or {},
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

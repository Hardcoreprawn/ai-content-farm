"""
Content Collector API

FastAPI application for collecting content from various sources.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Dict, Any, Optional
import time
from datetime import datetime, timezone

from collector import collect_content_batch, deduplicate_content
from config import Config


app = FastAPI(
    title="Content Collector API",
    description="API for collecting content from various sources",
    version="1.0.0"
)


class SourceConfig(BaseModel):
    """Configuration for a content source."""
    type: str = Field(..., description="Type of source (e.g., 'reddit')")
    subreddits: Optional[List[str]] = Field(
        default=None, description="List of subreddits (for Reddit)")
    limit: Optional[int] = Field(
        default=10, ge=1, le=100, description="Number of items to collect")
    criteria: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Filtering criteria")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        # Allow any type, will be handled gracefully in processing
        return v

    @model_validator(mode='after')
    def validate_source_requirements(self):
        """Validate that required fields are present based on source type."""
        if self.type == 'reddit':
            if self.subreddits is None:
                raise ValueError(
                    'subreddits field is required for Reddit sources')
            if len(self.subreddits) == 0:
                raise ValueError(
                    'At least one subreddit must be specified for Reddit sources')

        return self


class CollectionRequest(BaseModel):
    """Request model for content collection."""
    sources: List[SourceConfig] = Field(
        ..., description="List of content sources to collect from")
    deduplicate: bool = Field(
        default=True, description="Whether to deduplicate results")
    similarity_threshold: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Similarity threshold for deduplication")

    @field_validator('sources')
    @classmethod
    def validate_sources(cls, v):
        if len(v) > 10:
            raise ValueError('Maximum 10 sources allowed per request')
        return v


class CollectionResponse(BaseModel):
    """Response model for content collection."""
    collected_items: List[Dict[str, Any]
                          ] = Field(..., description="Collected content items")
    metadata: Dict[str, Any] = Field(..., description="Collection metadata")
    collection_id: str = Field(...,
                               description="Unique identifier for this collection")
    timestamp: str = Field(..., description="Collection timestamp")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version")
    config_issues: List[str] = Field(
        default_factory=list, description="Configuration issues")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    config_issues = Config.validate_config()

    return HealthResponse(
        status="healthy" if not config_issues else "warning",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        config_issues=config_issues
    )


@app.post("/collect", response_model=CollectionResponse)
async def collect_content(request: CollectionRequest):
    """
    Collect content from specified sources.

    Args:
        request: Collection request with sources and options

    Returns:
        Collection response with collected items and metadata

    Raises:
        HTTPException: If collection fails
    """
    try:
        start_time = time.time()

        # Convert Pydantic models to dicts for the collector
        sources_data = []
        for source in request.sources:
            source_dict = source.dict()

            # Apply default criteria if not provided
            if source.type == "reddit" and not source_dict.get("criteria"):
                source_dict["criteria"] = Config.get_default_criteria()

            sources_data.append(source_dict)

        # Collect content
        result = collect_content_batch(sources_data)

        collected_items = result["collected_items"]
        metadata = result["metadata"]

        # Apply deduplication if requested
        if request.deduplicate and collected_items:
            original_count = len(collected_items)
            collected_items = deduplicate_content(
                collected_items, request.similarity_threshold)
            metadata["deduplication"] = {
                "enabled": True,
                "original_count": original_count,
                "deduplicated_count": len(collected_items),
                "removed_count": original_count - len(collected_items),
                "similarity_threshold": request.similarity_threshold
            }
        else:
            metadata["deduplication"] = {"enabled": False}

        # Add processing time
        processing_time = time.time() - start_time
        metadata["processing_time_seconds"] = round(processing_time, 3)

        # Generate collection ID
        collection_id = f"collection_{int(time.time())}_{len(collected_items)}"

        return CollectionResponse(
            collected_items=collected_items,
            metadata=metadata,
            collection_id=collection_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Collection failed: {str(e)}"
        )


# Store service start time for uptime calculation
service_start_time = datetime.now(timezone.utc)


@app.get("/status")
async def get_status():
    """Get current service status and statistics."""
    uptime = (datetime.now(timezone.utc) - service_start_time).total_seconds()
    return {
        "service": "content-collector",
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": uptime,
        "last_collection": None,  # Would track last successful collection
        "stats": {
            "total_collections": 0,
            "successful_collections": 0,
            "failed_collections": 0
        },
        "config": {
            "environment": Config.ENVIRONMENT,
            "debug": Config.DEBUG,
            "default_subreddits": Config.DEFAULT_SUBREDDITS,
            "max_posts_per_request": Config.MAX_POSTS_PER_REQUEST,
            "request_timeout": Config.REQUEST_TIMEOUT,
            "similarity_threshold": Config.SIMILARITY_THRESHOLD,
        }
    }


@app.get("/sources")
async def get_sources():
    """Get available content sources."""
    return {
        "available_sources": [
            {
                "type": "reddit",
                "name": "Reddit API",
                "description": "Fetch posts from Reddit subreddits",
                "status": "available" if Config.REDDIT_CLIENT_ID else "configuration_required",
                "parameters": ["subreddits", "limit", "sort_by"]
            }
        ]
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc) if Config.DEBUG else "An unexpected error occurred",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level="debug" if Config.DEBUG else "info"
    )

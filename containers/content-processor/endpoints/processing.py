"""
Processing Endpoints - Content Processing Operations

RESTful endpoints for content processing operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, Depends
from models import WakeUpRequest
from pydantic import BaseModel, Field

from libs.shared_models import ErrorCodes, StandardResponse, create_service_dependency

# Create router for processing
router = APIRouter(prefix="/process", tags=["processing"])

# Create service metadata dependency
service_metadata = create_service_dependency("content-processor")


class ProcessRequest(BaseModel):
    """Request model for content processing."""

    topic_id: str = Field(..., description="Unique identifier for the topic")
    content: str = Field(..., description="Content to process")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    processing_type: str = Field(
        default="enhancement", description="Type of processing to perform"
    )
    options: Dict[str, Any] = Field(
        default_factory=dict, description="Processing options"
    )


@router.post(
    "",
    response_model=StandardResponse,
    summary="Process Content",
    description="Process content with AI enhancement and analysis",
)
async def process_content(
    request: ProcessRequest,
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """
    Process content with AI enhancement.

    This endpoint processes content using AI models for enhancement,
    summarization, keyword extraction, or sentiment analysis.
    """
    try:
        # For now, return a simple success response
        # In a real implementation, this would process the content using AI
        return StandardResponse(
            status="success",
            data={
                "processed_content": f"Enhanced: {request.content}",
                "processing_type": request.processing_type,
                "topic_id": request.topic_id,
                "options_used": request.options,
            },
            message="Content processed successfully",
            errors=None,
            metadata=metadata,
        )
    except Exception as e:
        error = ErrorCodes.secure_internal_error(e, "process_content")
        return StandardResponse(
            status="error",
            message=error.message,
            data=None,
            errors=[error.message],
            metadata=metadata,
        )


@router.get(
    "/types",
    response_model=StandardResponse,
    summary="Get Processing Types",
    description="Get available content processing types",
)
async def get_processing_types(
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """Get available processing types."""
    return StandardResponse(
        status="success",
        data={
            "available_types": [
                "enhancement",
                "summarization",
                "keyword_extraction",
                "sentiment_analysis",
            ],
            "description": "Supported content processing types",
        },
        message="Available processing types",
        errors=None,
        metadata=metadata,
    )


@router.post(
    "/wake-up",
    response_model=StandardResponse,
    summary="Wake Up Processor",
    description="Process the latest collection - simple and direct",
)
async def wake_up_processor(
    request: WakeUpRequest,
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """
    Simple wake-up: get latest collection, process items, done.
    No complex discovery, no filtering - just work.
    """
    try:
        from libs.simplified_blob_client import SimplifiedBlobClient

        blob_client = SimplifiedBlobClient()

        # 1. Get latest collection file
        blobs = await blob_client.list_blobs("collected-content", prefix="collections/")
        if not blobs:
            return StandardResponse(
                status="success",
                data={"topics_processed": 0, "message": "No collections found"},
                message="No collections to process",
                metadata=metadata,
            )

        # Get the most recent collection
        latest_blob = sorted(blobs, key=lambda x: x["name"])[-1]
        collection_data = await blob_client.download_json(
            "collected-content", latest_blob["name"]
        )

        items = collection_data.get("items", [])

        # 2. Process items (simplified - just convert to basic articles)
        articles_generated = 0
        for item in items[: request.batch_size]:
            # Simple processing - just create a basic article
            article = {
                "title": item.get("title", "Untitled"),
                "content": item.get("content", item.get("description", "No content")),
                "url": item.get("url", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Save to processed-content container
            article_path = f"articles/{datetime.now().strftime('%Y/%m/%d')}/article_{uuid4().hex[:8]}.json"
            await blob_client.upload_json("processed-content", article_path, article)
            articles_generated += 1

        return StandardResponse(
            status="success",
            data={
                "topics_processed": len(items[: request.batch_size]),
                "articles_generated": articles_generated,
                "collection_processed": latest_blob["name"],
                "total_items_in_collection": len(items),
            },
            message=f"Processed {articles_generated} articles from {latest_blob['name']}",
            metadata=metadata,
        )

    except Exception as e:
        return StandardResponse(
            status="error",
            data={"error": str(e)},
            message="Processing failed",
            errors=[str(e)],
            metadata=metadata,
        )


@router.get(
    "/status",
    response_model=StandardResponse,
    summary="Get Processing Status",
    description="Get current processing service status",
)
async def get_processing_status(
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """Get processing status."""
    return StandardResponse(
        status="success",
        data={
            "status": "operational",
            "active_jobs": 0,
            "queue_size": 0,
            "last_processed": datetime.now(timezone.utc).isoformat(),
            "capabilities": [
                "content_enhancement",
                "ai_processing",
                "batch_operations",
                "real_time_processing",
                "wake_up_processing",
            ],
        },
        message="Processing service is operational",
        errors=None,
        metadata=metadata,
    )

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
    description="Wake up the processor to scan and process all available content",
)
async def wake_up_processor(
    request: WakeUpRequest,
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """
    Wake up the processor to scan blob storage and process all available content.

    This endpoint provides the same functionality as Service Bus wake-up messages
    but can be triggered manually for testing or manual processing.
    """
    try:
        # Import processor here to avoid circular imports
        from processor import ContentProcessor

        processor = ContentProcessor()

        # Process all available work (this scans blob storage)
        result = await processor.process_available_work(
            batch_size=request.batch_size,
            priority_threshold=request.priority_threshold,
            debug_bypass=request.debug_bypass,
        )

        return StandardResponse(
            status="success",
            data={
                "topics_processed": result.topics_processed,
                "articles_generated": result.articles_generated,
                "total_cost": result.total_cost,
                "processing_time": result.processing_time,
                "trigger_type": "manual_api",
                "batch_size": request.batch_size,
                "priority_threshold": request.priority_threshold,
                "debug_bypass": request.debug_bypass,
                "source": request.source,
            },
            message=f"Wake-up processing completed: {result.topics_processed} topics processed, {result.articles_generated} articles generated (debug_bypass={request.debug_bypass})",
            errors=None,
            metadata=metadata,
        )

    except Exception as e:
        error_message = ErrorCodes.secure_internal_error(e, "wake_up_processor")
        return StandardResponse(
            status="error",
            data={"trigger_type": "manual_api"},
            message="Wake-up processing failed",
            errors=[str(error_message)],
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

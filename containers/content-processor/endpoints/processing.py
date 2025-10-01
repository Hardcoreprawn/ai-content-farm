"""
Processing Endpoints - Content Processing Operations

RESTful endpoints for content processing operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends
from models import WakeUpRequest
from pydantic import BaseModel, Field

from libs.queue_client import send_wake_up_message
from libs.shared_models import ErrorCodes, StandardResponse, create_service_dependency

# Create router for processing
router = APIRouter(prefix="/process", tags=["processing"])

# Create service metadata dependency
service_metadata = create_service_dependency("content-processor")

# Job tracking (in-memory for now, could use Redis/database for production)
_processing_jobs: Dict[str, Dict[str, Any]] = {}


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
    description="Process the latest collection asynchronously",
    status_code=202,
)
async def wake_up_processor(
    request: WakeUpRequest,
    background_tasks: BackgroundTasks,
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """
    Async wake-up: queue processing job and return immediately.
    Use /process/jobs/{job_id} to check status.
    """
    job_id = str(uuid4())

    # Initialize job tracking
    _processing_jobs[job_id] = {
        "job_id": job_id,
        "status": "accepted",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None,
        "topics_processed": 0,
        "articles_generated": 0,
        "collection_processed": None,
        "error": None,
        "request": {
            "source": request.source,
            "batch_size": request.batch_size,
            "priority_threshold": request.priority_threshold,
        },
    }

    # Queue the processing work
    background_tasks.add_task(
        _process_collection_async,
        job_id=job_id,
        request=request,
    )

    return StandardResponse(
        status="accepted",
        data={
            "job_id": job_id,
            "status": "accepted",
            "message": "Processing job queued",
            "status_endpoint": f"/process/jobs/{job_id}",
        },
        message=f"Processing job {job_id} accepted and queued",
        errors=None,
        metadata=metadata,
    )


async def _process_collection_async(job_id: str, request: WakeUpRequest):
    """
    Background task: actually process the collection.
    Updates job status as it progresses.
    """
    try:
        from libs.simplified_blob_client import SimplifiedBlobClient

        # Update job status to processing
        _processing_jobs[job_id]["status"] = "processing"
        _processing_jobs[job_id]["started_at"] = datetime.now(timezone.utc).isoformat()

        blob_client = SimplifiedBlobClient()

        # 1. Get latest collection file
        blobs = await blob_client.list_blobs("collected-content", prefix="collections/")
        if not blobs:
            _processing_jobs[job_id]["status"] = "completed"
            _processing_jobs[job_id]["completed_at"] = datetime.now(
                timezone.utc
            ).isoformat()
            _processing_jobs[job_id]["message"] = "No collections found"
            return

        # Get the most recent collection
        latest_blob = sorted(blobs, key=lambda x: x["name"])[-1]
        collection_data = await blob_client.download_json(
            "collected-content", latest_blob["name"]
        )

        items = collection_data.get("items", [])
        _processing_jobs[job_id]["collection_processed"] = latest_blob["name"]
        _processing_jobs[job_id]["total_items"] = len(items)

        # 2. Process items (simplified - just create basic articles)
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

            # Update progress
            _processing_jobs[job_id]["articles_generated"] = articles_generated
            _processing_jobs[job_id]["topics_processed"] = articles_generated

        # Trigger site-generator if we processed articles
        if articles_generated > 0:
            try:
                await send_wake_up_message(
                    queue_name="site-generation-requests",
                    service_name="content-processor",
                    payload={
                        "trigger": "content_processed",
                        "topics_processed": articles_generated,
                        "articles_generated": articles_generated,
                        "collection": latest_blob["name"],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                _processing_jobs[job_id]["site_generator_triggered"] = True
            except Exception as e:
                _processing_jobs[job_id]["site_generator_triggered"] = False
                _processing_jobs[job_id]["site_generator_error"] = str(e)

        # Mark as completed
        _processing_jobs[job_id]["status"] = "completed"
        _processing_jobs[job_id]["completed_at"] = datetime.now(
            timezone.utc
        ).isoformat()

    except Exception as e:
        # Mark as failed
        _processing_jobs[job_id]["status"] = "failed"
        _processing_jobs[job_id]["completed_at"] = datetime.now(
            timezone.utc
        ).isoformat()
        _processing_jobs[job_id]["error"] = str(e)


@router.get(
    "/jobs/{job_id}",
    response_model=StandardResponse,
    summary="Get Job Status",
    description="Check the status of a processing job",
)
async def get_job_status(
    job_id: str,
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """Get the status of a processing job."""
    job_data = _processing_jobs.get(job_id)

    if not job_data:
        return StandardResponse(
            status="error",
            data=None,
            message=f"Job {job_id} not found",
            errors=[f"No job found with ID: {job_id}"],
            metadata=metadata,
        )

    return StandardResponse(
        status="success",
        data=job_data,
        message=f"Job status: {job_data['status']}",
        errors=None,
        metadata=metadata,
    )


@router.get(
    "/jobs",
    response_model=StandardResponse,
    summary="List All Jobs",
    description="Get all processing jobs (recent first)",
)
async def list_jobs(
    limit: Optional[int] = 50,
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """List all processing jobs."""
    jobs = sorted(
        _processing_jobs.values(), key=lambda x: x["created_at"], reverse=True
    )[:limit]

    return StandardResponse(
        status="success",
        data={
            "jobs": jobs,
            "total": len(_processing_jobs),
            "showing": len(jobs),
        },
        message=f"Found {len(jobs)} jobs",
        errors=None,
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

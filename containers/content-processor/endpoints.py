"""
Core API endpoints for content processor.

Functional endpoints following agent instructions:
- Clear REST semantics and error handling
- Standardized response format using shared models
- Observable operations with health/status
- Event-driven wake-up pattern
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from models import (
    ProcessBatchRequest,
    ProcessingResult,
    ProcessorStatus,
    WakeUpRequest,
    WakeUpResponse,
)
from processor import ContentProcessor

from libs.shared_models import ErrorCodes, StandardResponse

logger = logging.getLogger(__name__)

# Global processor instance (initialized once per container)
_processor_instance: ContentProcessor = None


def get_processor() -> ContentProcessor:
    """Get or create processor instance - functional singleton pattern."""
    global _processor_instance

    if _processor_instance is None:
        _processor_instance = ContentProcessor()

    return _processor_instance


async def service_metadata() -> Dict[str, Any]:
    """Service metadata dependency for all endpoints."""
    return {
        "function": "content-processor",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "processor_id": str(uuid4())[:8],
    }


async def root_endpoint(metadata: Dict[str, Any]) -> StandardResponse:
    """Root endpoint with service information."""
    return StandardResponse(
        status="success",
        message="Content Processor - Event-driven article generation",
        data={
            "service": "content-processor",
            "pattern": "wake-up work queue",
            "endpoints": [
                "POST /api/processor/wake-up",
                "POST /api/processor/process-batch",
                "GET /api/processor/health",
                "GET /api/processor/status",
                "GET /api/processor/docs",
            ],
        },
        metadata=metadata,
    )


async def health_endpoint(metadata: Dict[str, Any]) -> StandardResponse:
    """Health check with dependency validation."""
    try:
        processor = get_processor()
        health_status = await processor.check_health()

        status = (
            "success"
            if health_status.azure_openai_available
            and health_status.blob_storage_available
            else "error"
        )

        return StandardResponse(
            status=status,
            message="Health check completed",
            data={
                "processor_id": health_status.processor_id,
                "azure_openai_available": health_status.azure_openai_available,
                "blob_storage_available": health_status.blob_storage_available,
                "last_health_check": health_status.last_health_check.isoformat(),
            },
            metadata=metadata,
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return StandardResponse(
            status="error",
            message="Health check failed",
            errors=[f"Health validation error: {str(e)}"],
            metadata=metadata,
        )


async def wake_up_endpoint(
    request: WakeUpRequest, metadata: Dict[str, Any]
) -> StandardResponse:
    """
    Primary wake-up endpoint implementing the work queue pattern.

    Event-driven processing: collector signals work available,
    processor autonomously finds and processes topics.
    """
    try:
        logger.info(f"Wake-up signal received from {request.source}")

        processor = get_processor()
        result = await processor.process_available_work(
            batch_size=request.batch_size,
            priority_threshold=request.priority_threshold,
            options=request.processing_options,
        )

        response_data = WakeUpResponse(
            processor_id=metadata["processor_id"],
            topics_found=result.topics_processed + len(result.failed_topics),
            work_completed=[
                {
                    "topic_id": topic_id,
                    "status": "completed",
                    "processing_time": result.processing_time
                    / max(result.topics_processed, 1),
                }
                for topic_id in result.completed_topics
            ],
            total_processed=result.topics_processed,
            total_cost=result.total_cost,
            processing_time_seconds=result.processing_time,
        )

        message = f"Processed {result.topics_processed} topics, generated {result.articles_generated} articles"

        return StandardResponse(
            status="success",
            message=message,
            data=response_data.model_dump(),
            metadata=metadata,
        )

    except Exception as e:
        error = ErrorCodes.secure_internal_error(e, "wake_up_endpoint")
        return StandardResponse(
            status="error",
            message=error.message,
            errors=[error.message],
            metadata=metadata,
        )


async def process_batch_endpoint(
    request: ProcessBatchRequest, metadata: Dict[str, Any]
) -> StandardResponse:
    """Manual batch processing for specific topics."""
    try:
        logger.info(
            f"Manual batch processing requested for {len(request.topic_ids)} topics"
        )

        processor = get_processor()
        result = await processor.process_specific_topics(
            topic_ids=request.topic_ids,
            force_reprocess=request.force_reprocess,
            options=request.processing_options,
        )

        return StandardResponse(
            status="success",
            message=f"Batch processing completed: {result.articles_generated} articles generated",
            data={
                "topics_processed": result.topics_processed,
                "articles_generated": result.articles_generated,
                "total_cost": result.total_cost,
                "processing_time": result.processing_time,
                "completed_topics": result.completed_topics,
                "failed_topics": result.failed_topics,
            },
            metadata=metadata,
        )

    except Exception as e:
        error = ErrorCodes.secure_internal_error(e, "process_batch_endpoint")
        return StandardResponse(
            status="error",
            message=error.message,
            errors=[error.message],
            metadata=metadata,
        )


async def status_endpoint(metadata: Dict[str, Any]) -> StandardResponse:
    """Current processing status and metrics."""
    try:
        processor = get_processor()
        status = await processor.get_status()

        return StandardResponse(
            status="success",
            message="Status retrieved successfully",
            data={
                "processor_id": status.processor_id,
                "status": status.status,
                "current_topics": status.current_topics,
                "session_metrics": {
                    "topics_processed": status.session_topics_processed,
                    "cost_usd": status.session_cost,
                    "processing_time": status.session_processing_time,
                },
                "system_health": {
                    "azure_openai_available": status.azure_openai_available,
                    "blob_storage_available": status.blob_storage_available,
                },
            },
            metadata=metadata,
        )

    except Exception as e:
        error = ErrorCodes.secure_internal_error(e, "status_endpoint")
        return StandardResponse(
            status="error",
            message=error.message,
            errors=[error.message],
            metadata=metadata,
        )


async def docs_endpoint(metadata: Dict[str, Any]) -> StandardResponse:
    """API documentation and usage examples."""
    return StandardResponse(
        status="success",
        message="API documentation",
        data={
            "service": "Content Processor",
            "version": "1.0.0",
            "pattern": "Event-driven wake-up work queue",
            "usage": {
                "wake_up": {
                    "method": "POST",
                    "endpoint": "/api/processor/wake-up",
                    "description": "Primary endpoint - collector signals work available",
                    "example": {
                        "source": "collector",
                        "batch_size": 10,
                        "priority_threshold": 0.7,
                    },
                },
                "health": {
                    "method": "GET",
                    "endpoint": "/api/processor/health",
                    "description": "Health check and dependency validation",
                },
                "status": {
                    "method": "GET",
                    "endpoint": "/api/processor/status",
                    "description": "Current processing status and metrics",
                },
            },
            "cost_target": "$3-8/month",
            "architecture": "Functional processing with Azure OpenAI integration",
        },
        metadata=metadata,
    )

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
from typing import Any, Dict, Optional
from uuid import uuid4

from content_generation import (
    BatchGenerationRequest,
    BatchGenerationResponse,
    GeneratedContent,
    GenerationRequest,
    GenerationStatus,
    get_content_generator,
)
from fastapi import APIRouter, HTTPException
from models import (
    ProcessBatchRequest,
    ProcessingResult,
    ProcessorStatus,
    WakeUpRequest,
    WakeUpResponse,
)
from processor import ContentProcessor
from pydantic import BaseModel, Field

from libs.queue_client import send_wake_up_message
from libs.shared_models import ErrorCodes, StandardResponse

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()

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
        message="Content Processor - Event-driven processing & AI content generation",
        data={
            "service": "content-processor",
            "version": "1.0.0",
            "pattern": "wake-up work queue + content generation",
            "processing_endpoints": [
                "POST /api/processor/wake-up",
                "POST /api/processor/process-batch",
                "GET /api/processor/health",
                "GET /api/processor/status",
                "GET /api/processor/docs",
            ],
            "generation_endpoints": [
                "POST /api/processor/generate/tldr",
                "POST /api/processor/generate/blog",
                "POST /api/processor/generate/deepdive",
                "POST /api/processor/generate/batch",
                "GET /api/processor/generation/status/{batch_id}",
            ],
            "capabilities": [
                "content_processing",
                "ai_generation",
                "batch_operations",
                "health_monitoring",
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
                "service": "content-processor",
                "status": "healthy" if status == "success" else "unhealthy",
                "processor_id": health_status.processor_id,
                "dependencies": {
                    "azure_openai": health_status.azure_openai_available,
                    "blob_storage": health_status.blob_storage_available,
                },
                "azure_openai_available": health_status.azure_openai_available,
                "blob_storage_available": health_status.blob_storage_available,
                "last_health_check": health_status.last_health_check.isoformat(),
            },
            metadata=metadata,
        )

    except Exception as e:
        logger.error("Health check failed")
        logger.debug(f"Health check error details: {str(e)}", exc_info=True)
        return StandardResponse(
            status="error",
            message="Health check failed",
            errors=["Health validation error"],
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
            debug_bypass=request.debug_bypass,
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

        # If we successfully processed content, notify site-generator to generate site
        if result.topics_processed > 0:
            try:
                await send_wake_up_message(
                    queue_name="site-generation-requests",
                    service_name="content-processor",
                    payload={
                        "trigger": "content_processed",
                        "topics_processed": result.topics_processed,
                        "articles_generated": result.articles_generated,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                logger.info(
                    f"Sent wake-up message to site-generator for {result.topics_processed} processed topics"
                )
            except Exception as e:
                logger.warning(f"Failed to send wake-up message to site-generator: {e}")
                # Don't fail the main processing response if queue message fails

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

        # If we successfully processed content, notify site-generator to generate site
        if result.topics_processed > 0:
            try:
                await send_wake_up_message(
                    queue_name="site-generation-requests",
                    service_name="content-processor",
                    payload={
                        "trigger": "batch_processed",
                        "topics_processed": result.topics_processed,
                        "articles_generated": result.articles_generated,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                logger.info(
                    f"Sent wake-up message to site-generator for batch processing of {result.topics_processed} topics"
                )
            except Exception as e:
                logger.warning(f"Failed to send wake-up message to site-generator: {e}")
                # Don't fail the main processing response if queue message fails

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


# Simple process request model for testing
class ProcessRequest(BaseModel):
    """Simple process request for testing."""

    content: str = Field(..., description="Content to process")
    processing_type: str = Field("enhancement", description="Type of processing")
    options: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Processing options"
    )


# Route registrations - only service-specific endpoints
# Standard endpoints (/, /health, /status) are handled by main.py


@router.get("/docs")
async def docs():
    """API documentation and usage examples."""
    metadata = await service_metadata()
    return await docs_endpoint(metadata)


@router.post("/wake-up")
async def wake_up(request: WakeUpRequest):
    """Wake-up endpoint - collector signals work available."""
    metadata = await service_metadata()
    return await wake_up_endpoint(request, metadata)


@router.post("/process-batch")
async def process_batch(request: ProcessBatchRequest):
    """Manual batch processing endpoint."""
    metadata = await service_metadata()
    return await process_batch_endpoint(request, metadata)


@router.post("/process")
async def process(request: ProcessRequest):
    """Simple process endpoint for testing."""
    metadata = await service_metadata()
    try:
        # For now, return a simple success response
        # In a real implementation, this would process the content
        return StandardResponse(
            status="success",
            message="Content processed successfully",
            data={
                "processed_content": f"Enhanced: {request.content}",
                "processing_type": request.processing_type,
                "options_used": request.options,
            },
            metadata=metadata,
        )
    except Exception as e:
        error = ErrorCodes.secure_internal_error(e, "process_endpoint")
        return StandardResponse(
            status="error",
            message=error.message,
            errors=[error.message],
            metadata=metadata,
        )


@router.get("/process/types")
async def process_types():
    """Get available processing types."""
    metadata = await service_metadata()
    return StandardResponse(
        status="success",
        message="Available processing types",
        data={
            "available_types": [
                "enhancement",
                "summarization",
                "keyword_extraction",
                "sentiment_analysis",
            ],
            "description": "Supported content processing types",
        },
        metadata=metadata,
    )


@router.get("/process/status")
async def process_status():
    """Get processing status."""
    metadata = await service_metadata()
    return StandardResponse(
        status="success",
        message="Processing status information",
        data={
            "active_jobs": 0,
            "queue_size": 0,
            "last_processed": None,
            "processing_enabled": True,
        },
        metadata=metadata,
    )


# Content Generation Endpoints (merged from content-generator)
# These endpoints provide AI-powered content generation capabilities


@router.post("/generate/tldr", response_model=GeneratedContent)
async def generate_tldr(request: GenerationRequest):
    """Generate TLDR content (200-400 words)."""
    try:
        # Force content type to tldr
        request.content_type = "tldr"

        generator = get_content_generator()
        result = await generator.generate_content(request)

        logger.info(f"Generated TLDR for topic: {request.topic}")
        return result

    except Exception as e:
        logger.error("TLDR generation failed")
        logger.debug(f"TLDR generation error details: {str(e)}")
        raise HTTPException(status_code=500, detail="Generation failed")


@router.post("/generate/blog", response_model=GeneratedContent)
async def generate_blog(request: GenerationRequest):
    """Generate blog content (600-1000 words)."""
    try:
        # Force content type to blog
        request.content_type = "blog"

        generator = get_content_generator()
        result = await generator.generate_content(request)

        logger.info(f"Generated blog for topic: {request.topic}")
        return result

    except Exception as e:
        logger.error("Blog generation failed")
        logger.debug(f"Blog generation error details: {str(e)}")
        raise HTTPException(status_code=500, detail="Generation failed")


@router.post("/generate/deepdive", response_model=GeneratedContent)
async def generate_deepdive(request: GenerationRequest):
    """Generate deep dive content (1200+ words)."""
    try:
        # Force content type to deepdive
        request.content_type = "deepdive"

        generator = get_content_generator()
        result = await generator.generate_content(request)

        logger.info(f"Generated deep dive for topic: {request.topic}")
        return result

    except Exception as e:
        logger.error("Deep dive generation failed")
        logger.debug(f"Deep dive generation error details: {str(e)}")
        raise HTTPException(status_code=500, detail="Generation failed")


@router.post("/generate/batch", response_model=BatchGenerationResponse)
async def generate_batch(request: BatchGenerationRequest):
    """Start batch content generation."""
    try:
        generator = get_content_generator()
        result = await generator.start_batch_generation(request)

        logger.info(f"Started batch generation for {len(request.topics)} topics")
        return result

    except Exception as e:
        logger.error("Batch generation start failed")
        logger.debug(f"Batch generation error details: {str(e)}")
        raise HTTPException(status_code=500, detail="Batch generation failed")


@router.get("/generation/status/{batch_id}", response_model=GenerationStatus)
async def get_generation_status(batch_id: str):
    """Get status of batch generation."""
    try:
        generator = get_content_generator()
        status = generator.get_batch_status(batch_id)

        if not status:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Status retrieval failed")
        logger.debug(f"Status retrieval error details: {str(e)}")
        raise HTTPException(status_code=500, detail="Status retrieval failed")


# Documentation endpoint (simplified pattern)


@router.get("/generate/docs")
async def generation_docs():
    """Content generation API documentation."""
    metadata = await service_metadata()
    return StandardResponse(
        status="success",
        message="Content generation API documentation",
        data={
            "service": "Content Processor - Generation Module",
            "version": "1.0.0",
            "endpoints": {
                "/generate/tldr": "Generate TLDR articles (200-400 words)",
                "/generate/blog": "Generate blog posts (600-1000 words)",
                "/generate/deepdive": "Generate deep dive analysis (1200+ words)",
                "/generate/batch": "Start batch generation",
                "/generation/status/{batch_id}": "Get batch generation status",
            },
            "content_types": ["tldr", "blog", "deepdive"],
            "writer_personalities": [
                "professional",
                "casual",
                "expert",
                "skeptical",
                "enthusiast",
            ],
            "usage_example": {
                "topic": "Latest AI developments",
                "content_type": "blog",
                "writer_personality": "professional",
                "sources": [{"title": "Source 1", "summary": "Summary text"}],
            },
        },
        metadata=metadata,
    )

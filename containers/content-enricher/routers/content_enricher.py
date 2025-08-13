"""
Content Enricher Router

FastAPI router for AI-powered content enhancement with async job processing.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from core.enricher_model import (
    EnrichmentRequest, EnrichmentJobResponse, EnrichmentJobStatusRequest, 
    EnrichmentJobStatusResponse, EnrichmentConfig
)
from core.enricher_engine import process_content_enrichment

# Router instance
router = APIRouter(prefix="/api/content-enricher", tags=["content-enricher"])

# In-memory job storage (would be replaced with Redis/database in production)
job_storage: Dict[str, Dict[str, Any]] = {}


def update_job_status(
    job_id: str,
    status: str,
    progress: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    results: Optional[Dict[str, Any]] = None
):
    """Update job status in storage"""
    job_storage[job_id] = {
        "job_id": job_id,
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
        "progress": progress,
        "error": error,
        "results": results
    }


async def process_enrichment_job(
    job_id: str,
    request: EnrichmentRequest
):
    """
    Process content enrichment asynchronously using the enricher engine.
    """
    try:
        # Update status to processing
        update_job_status(job_id, "processing")
        
        # Prepare configuration
        config = request.config or {}
        default_config = EnrichmentConfig().dict()
        enrichment_config = {**default_config, **config}
        
        # Prepare topics data
        topics_data = {"source": request.source}
        if request.topics:
            topics_data["topics"] = request.topics
        elif request.blob_path:
            # In a full implementation, would load from blob storage
            topics_data["topics"] = []
        
        # Process enrichment using core engine
        result = process_content_enrichment(topics_data, enrichment_config)
        
        # Convert EnrichedTopic objects to dicts for JSON serialization
        enriched_topics_dict = [topic.dict() for topic in result.enriched_topics]
        
        # Update job with successful results
        update_job_status(
            job_id,
            "completed",
            results={
                "source": result.source,
                "total_enriched": result.total_enriched,
                "enriched_topics": enriched_topics_dict,
                "processing_time": f"{result.processing_time:.2f} seconds",
                "ai_model": result.ai_model_used,
                "errors": result.errors
            }
        )
        
    except Exception as e:
        # Update job with error
        update_job_status(
            job_id,
            "failed",
            error=str(e)
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "content-enricher",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/process", response_model=EnrichmentJobResponse)
async def create_enrichment_job(
    request: EnrichmentRequest,
    background_tasks: BackgroundTasks
):
    """Create a new content enrichment job"""
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Validate input
    if not request.topics and not request.blob_path:
        raise HTTPException(
            status_code=400,
            detail="Either 'topics' or 'blob_path' must be provided"
        )
    
    # Create initial job status
    update_job_status(job_id, "queued")
    
    # Start background processing
    background_tasks.add_task(
        process_enrichment_job,
        job_id,
        request
    )
    
    # Return job ticket
    return EnrichmentJobResponse(
        job_id=job_id,
        status="queued",
        message="Content enrichment started. Use job_id to check status.",
        timestamp=datetime.utcnow().isoformat(),
        source=request.source,
        topics_count=len(request.topics) if request.topics else None
    )


@router.post("/status", response_model=EnrichmentJobStatusResponse)
async def check_job_status(request: EnrichmentJobStatusRequest):
    """Check the status of a content enrichment job"""
    if request.action != "status":
        raise HTTPException(
            status_code=400, 
            detail="Only 'status' action is supported"
        )
    
    job_data = job_storage.get(request.job_id)
    if not job_data:
        raise HTTPException(
            status_code=404, 
            detail=f"Job {request.job_id} not found"
        )
    
    return EnrichmentJobStatusResponse(**job_data)


@router.get("/docs")
async def get_api_documentation():
    """API documentation endpoint"""
    return {
        "service": "Content Enricher",
        "version": "2.0.0",
        "description": "AI-powered content enhancement with summaries, categorization, and metadata extraction",
        "endpoints": {
            "POST /process": {
                "description": "Create content enrichment job",
                "features": [
                    "AI-generated summaries",
                    "Content categorization", 
                    "Sentiment analysis",
                    "Key phrase extraction",
                    "Reading time estimation",
                    "Quality scoring"
                ]
            },
            "POST /status": "Check job status",
            "GET /health": "Health check",
            "GET /docs": "This documentation"
        },
        "configuration": {
            "enable_ai_summary": "Generate AI summaries (default: true)",
            "enable_sentiment_analysis": "Analyze sentiment (default: true)", 
            "enable_categorization": "Categorize content (default: true)",
            "enable_key_phrases": "Extract key phrases (default: true)",
            "max_summary_length": "Maximum summary length (default: 300)"
        }
    }

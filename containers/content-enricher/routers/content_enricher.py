"""
Content Enricher Router

FastAPI router for AI-powered content enhancement with async job processing.
Maintains the same API contract while using the pure functions architecture.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from core.enhancement_engine import enhance_topics_batch, EnhancementConfig
from core.enhancement_model import (
    EnhancementRequest, JobResponse, JobStatusRequest, JobStatusResponse,
    JobResultRequest, JobResultResponse, EnhancementResult, EnhancedTopic
)

# Router instance
router = APIRouter(prefix="/api/content-enricher", tags=["content-enricher"])

# In-memory job storage (would be replaced with Redis/database in production)
job_storage: Dict[str, Dict[str, Any]] = {}


async def get_blob_storage_client() -> BlobServiceClient:
    """
    Get Azure Blob Storage client with managed identity authentication.
    
    Falls back to connection string for local development.
    """
    storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    
    if connection_string:
        # Local development with Azurite
        return BlobServiceClient.from_connection_string(connection_string)
    elif storage_account_name:
        # Production with managed identity
        credential = DefaultAzureCredential()
        return BlobServiceClient(
            account_url=f"https://{storage_account_name}.blob.core.windows.net",
            credential=credential
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Azure Storage not configured. Set AZURE_STORAGE_ACCOUNT_NAME or AZURE_STORAGE_CONNECTION_STRING"
        )


def update_job_status(
    job_id: str,
    status: str,
    progress: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    results: Optional[EnhancementResult] = None
):
    """Update job status in storage"""
    job_storage[job_id] = {
        "job_id": job_id,
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
        "progress": progress,
        "error": error,
        "results": results.dict() if results else None
    }


async def process_enrichment_job(
    job_id: str,
    request: EnhancementRequest
):
    """
    Process content enrichment asynchronously.
    
    This function handles the async processing while delegating
    the actual enhancement to pure functions.
    """
    try:
        # Update status to processing
        update_job_status(job_id, "processing")
        
        # Get topics data
        topics_data = []
        
        if request.topics:
            # Direct topic data provided
            topics_data = request.topics
        elif request.blob_path:
            # Load from blob storage
            blob_client = await get_blob_storage_client()
            
            # Parse blob path (format: container/path/file.json)
            path_parts = request.blob_path.split('/', 1)
            if len(path_parts) != 2:
                raise ValueError(f"Invalid blob path format: {request.blob_path}")
            
            container_name, blob_name = path_parts
            
            # Download blob content
            blob_client_instance = blob_client.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            blob_content = blob_client_instance.download_blob().readall().decode('utf-8')
            blob_data = json.loads(blob_content)
            
            # Support different input formats
            if 'topics' in blob_data:
                topics_data = blob_data['topics']
            elif 'ranked_topics' in blob_data:
                topics_data = blob_data['ranked_topics']
            elif isinstance(blob_data, list):
                topics_data = blob_data
            else:
                raise ValueError("Blob data must contain 'topics' or 'ranked_topics' array")
        else:
            raise ValueError("Either 'topics' or 'blob_path' must be provided")
        
        if not topics_data:
            raise ValueError("No topics found for enhancement")
        
        # Create enhancement configuration
        config = EnhancementConfig()
        if request.config:
            # Update config with provided values
            for key, value in request.config.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        # Perform enhancement
        enhancement_results = await enhance_topics_batch(topics_data, config)
        
        # Convert to API response format
        enhanced_topics = []
        successful_enhancements = 0
        total_processing_time = 0.0
        
        for i, (original_topic, enhancement_result) in enumerate(zip(topics_data, enhancement_results)):
            # Create enhanced topic by combining original data with enhancements
            enhanced_topic = EnhancedTopic(
                title=original_topic.get('title', ''),
                content=original_topic.get('content') or original_topic.get('selftext', ''),
                source_url=original_topic.get('source_url') or original_topic.get('external_url') or original_topic.get('url', ''),
                author=original_topic.get('author', ''),
                created_utc=original_topic.get('created_utc', ''),
                score=original_topic.get('score', 0),
                num_comments=original_topic.get('num_comments', 0),
                subreddit=original_topic.get('subreddit', ''),
                ranking_score=original_topic.get('ranking_score') or original_topic.get('final_score'),
                ranking_position=original_topic.get('ranking_position', i + 1),
                ai_summary=enhancement_result.summary,
                key_insights=enhancement_result.key_insights,
                tags=enhancement_result.tags,
                sentiment=enhancement_result.sentiment,
                enhancement_metadata=enhancement_result.enhancement_metadata,
                processing_time_seconds=enhancement_result.processing_time_seconds,
                enhancement_success=enhancement_result.success,
                enhancement_error=enhancement_result.error
            )
            enhanced_topics.append(enhanced_topic)
            
            if enhancement_result.success:
                successful_enhancements += 1
            total_processing_time += enhancement_result.processing_time_seconds
        
        # Create enhancement results
        results = EnhancementResult(
            total_topics=len(enhanced_topics),
            enhanced_topics=enhanced_topics,
            processing_time_seconds=total_processing_time,
            timestamp=datetime.utcnow().isoformat(),
            enhancement_statistics={
                "successful_enhancements": successful_enhancements,
                "failed_enhancements": len(enhanced_topics) - successful_enhancements,
                "success_rate": successful_enhancements / len(enhanced_topics) if enhanced_topics else 0,
                "average_processing_time": total_processing_time / len(enhanced_topics) if enhanced_topics else 0,
                "openai_available": enhancement_results[0].enhancement_metadata.get("method") == "openai_enhanced" if enhancement_results else False
            },
            config_used={
                "openai_model": config.openai_model,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "include_sentiment": config.include_sentiment,
                "include_tags": config.include_tags,
                "include_insights": config.include_insights
            }
        )
        
        # Save output to blob storage if requested
        if request.output_path:
            blob_client = await get_blob_storage_client()
            path_parts = request.output_path.split('/', 1)
            if len(path_parts) == 2:
                container_name, blob_name = path_parts
                
                output_data = {
                    "job_id": job_id,
                    "source": request.source,
                    "generated_at": results.timestamp,
                    "total_topics": results.total_topics,
                    "enhanced_topics": [topic.dict() for topic in results.enhanced_topics],
                    "enhancement_statistics": results.enhancement_statistics,
                    "config_used": results.config_used
                }
                
                blob_client_instance = blob_client.get_blob_client(
                    container=container_name,
                    blob=blob_name
                )
                blob_client_instance.upload_blob(
                    json.dumps(output_data, indent=2),
                    overwrite=True
                )
        
        # Update job with successful results
        update_job_status(
            job_id,
            "completed",
            results=results
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


@router.post("/process", response_model=JobResponse)
async def create_enrichment_job(
    request: EnhancementRequest,
    background_tasks: BackgroundTasks
):
    """
    Create a new content enrichment job.
    
    This endpoint maintains compatibility with the established API patterns
    while using the new AI enhancement engine.
    """
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
    return JobResponse(
        job_id=job_id,
        status="queued",
        message="Content enrichment started. Use job_id to check status.",
        timestamp=datetime.utcnow().isoformat(),
        source=request.source,
        topics_count=len(request.topics) if request.topics else None,
        estimated_completion=None,
        status_check_url=f"/api/content-enricher/status/{job_id}"
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def check_job_status(job_id: str):
    """Check the status of a content enrichment job using GET"""
    job_data = job_storage.get(job_id)
    if not job_data:
        raise HTTPException(
            status_code=404, 
            detail=f"Job {job_id} not found"
        )
    
    return JobStatusResponse(**job_data)


@router.post("/status", response_model=JobStatusResponse)
async def check_job_status_post(request: JobStatusRequest):
    """Check the status of a content enrichment job using POST (legacy compatibility)"""
    job_data = job_storage.get(request.job_id)
    if not job_data:
        raise HTTPException(
            status_code=404, 
            detail=f"Job {request.job_id} not found"
        )
    
    return JobStatusResponse(**job_data)


@router.get("/result/{job_id}", response_model=JobResultResponse)
async def get_job_result(job_id: str):
    """Get the results of a completed content enrichment job"""
    job_data = job_storage.get(job_id)
    if not job_data:
        raise HTTPException(
            status_code=404, 
            detail=f"Job {job_id} not found"
        )
    
    if job_data["status"] not in ["completed", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed. Status: {job_data['status']}"
        )
    
    return JobResultResponse(
        job_id=job_id,
        status=job_data["status"],
        results=EnhancementResult(**job_data["results"]) if job_data.get("results") else None,
        error=job_data.get("error"),
        generated_at=job_data["updated_at"]
    )


@router.get("/docs")
async def get_api_documentation():
    """API documentation endpoint"""
    return {
        "service": "Content Enricher",
        "version": "2.0.0",
        "description": "AI-powered content enhancement with summaries, key insights, tags, and sentiment analysis",
        "endpoints": {
            "POST /process": {
                "description": "Create content enrichment job",
                "features": [
                    "AI-generated summaries using OpenAI",
                    "Key insights extraction", 
                    "Automatic tag generation",
                    "Sentiment analysis",
                    "Fallback to rule-based enhancement when OpenAI unavailable"
                ],
                "example_request": {
                    "source": "reddit",
                    "blob_path": "ranked-content/20250813_reddit_technology.json",
                    "config": {
                        "openai_model": "gpt-3.5-turbo",
                        "include_sentiment": True,
                        "include_tags": True,
                        "include_insights": True,
                        "max_tokens": 500
                    }
                }
            },
            "GET /status/{job_id}": "Check job status (preferred)",
            "POST /status": "Check job status (legacy compatibility)",
            "GET /result/{job_id}": "Get enhancement results",
            "GET /health": "Health check",
            "GET /docs": "This documentation"
        },
        "enhancement_features": {
            "ai_powered": {
                "model": "OpenAI GPT-3.5-turbo or GPT-4",
                "capabilities": [
                    "Intelligent content summarization",
                    "Key insights extraction",
                    "Contextual tag generation", 
                    "Sentiment analysis"
                ]
            },
            "fallback_system": {
                "description": "Rule-based enhancement when OpenAI unavailable",
                "features": [
                    "Keyword-based tagging",
                    "Basic sentiment analysis",
                    "Title-based summarization"
                ]
            },
            "rate_limiting": "Built-in rate limiting for OpenAI API compliance",
            "error_handling": "Graceful degradation with detailed error reporting"
        },
        "input_formats": {
            "supported": ["Direct topics array", "Azure Blob Storage JSON"],
            "blob_formats": ["topics array", "ranked_topics array"]
        }
    }

"""
Content Ranker Router

FastAPI router for content ranking with async job processing.
Maintains the same API contract as the original Azure Function while using
pure functions and pluggable storage abstraction.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from core.ranking_model import (
    RankingRequest, JobResponse, JobStatusRequest, JobStatusResponse,
    RankingResults, RankedTopic
)
from core.ranking_engine import rank_topics, RankingConfig


# Router instance
router = APIRouter(prefix="/api/content-ranker", tags=["content-ranker"])

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


async def process_ranking_job(
    job_id: str,
    request: RankingRequest
):
    """
    Process content ranking asynchronously.
    
    This function handles the async processing while delegating
    the actual ranking to pure functions.
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
            
            topics_data = blob_data.get('topics', [])
        else:
            raise ValueError("Either 'topics' or 'blob_path' must be provided")
        
        # Create ranking configuration
        config = RankingConfig()
        if request.config:
            # Update config with provided values
            for key, value in request.config.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        # Perform ranking
        ranking_result = rank_topics(topics_data, config)
        
        # Convert to API response format
        ranked_topics = []
        for topic in ranking_result.ranked_topics:
            ranked_topic = RankedTopic(
                title=topic.get('title', ''),
                content=topic.get('content', ''),
                source_url=topic.get('url', ''),
                score=topic.get('score', 0),
                author=topic.get('author', ''),
                created_utc=topic.get('created_utc', ''),
                num_comments=topic.get('num_comments', 0),
                subreddit=topic.get('subreddit', ''),
                engagement_score=topic.get('engagement_score', 0.0),
                monetization_score=topic.get('monetization_score', 0.0),
                recency_score=topic.get('recency_score', 0.0),
                title_quality_score=topic.get('title_quality_score', 0.0),
                final_score=topic.get('final_score', 0.0),
                ranking_position=topic.get('ranking_position', 0)
            )
            ranked_topics.append(ranked_topic)
        
        results = RankingResults(
            total_topics=ranking_result.total_topics,
            ranked_topics=ranked_topics,
            processing_time_seconds=ranking_result.processing_time_seconds,
            timestamp=ranking_result.timestamp.isoformat(),
            config_used={
                "engagement_weight": config.engagement_weight,
                "monetization_weight": config.monetization_weight,
                "recency_weight": config.recency_weight,
                "title_quality_weight": config.title_quality_weight,
                "minimum_score_threshold": config.minimum_score_threshold,
                "max_topics_output": config.max_topics_output
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
                    "total_topics": results.total_topics,
                    "ranked_topics": [topic.dict() for topic in results.ranked_topics],
                    "metadata": {
                        "processing_time_seconds": results.processing_time_seconds,
                        "timestamp": results.timestamp,
                        "config_used": results.config_used
                    }
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
            results=results.dict()
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
        "service": "content-ranker",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/process", response_model=JobResponse)
async def create_ranking_job(
    request: RankingRequest,
    background_tasks: BackgroundTasks
):
    """
    Create a new content ranking job.
    
    This endpoint maintains compatibility with the original ContentRanker API
    while using the new pure functions architecture.
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
        process_ranking_job,
        job_id,
        request
    )
    
    # Return job ticket
    return JobResponse(
        job_id=job_id,
        status="queued",
        message="Content ranking started. Use job_id to check status.",
        timestamp=datetime.utcnow().isoformat(),
        source=request.source,
        topics_count=len(request.topics) if request.topics else None,
        estimated_completion=None,
        status_check_example={
            "method": "POST",
            "url": "/api/content-ranker/status",
            "body": {
                "action": "status",
                "job_id": job_id
            }
        }
    )


@router.post("/status", response_model=JobStatusResponse)
async def check_job_status(request: JobStatusRequest):
    """Check the status of a content ranking job"""
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
    
    return JobStatusResponse(**job_data)


@router.get("/docs")
async def get_api_documentation():
    """API documentation endpoint"""
    return {
        "service": "Content Ranker",
        "version": "2.0.0",
        "description": "Rank and score content based on engagement, monetization potential, recency, and title quality",
        "endpoints": {
            "POST /process": {
                "description": "Create content ranking job",
                "supported_sources": ["reddit"],
                "example_request": {
                    "source": "reddit",
                    "blob_path": "hot-topics/20250813_reddit_technology.json",
                    "config": {
                        "engagement_weight": 0.4,
                        "monetization_weight": 0.3,
                        "recency_weight": 0.2,
                        "title_quality_weight": 0.1,
                        "minimum_score_threshold": 0.1,
                        "max_topics_output": 50
                    }
                }
            },
            "POST /status": {
                "description": "Check job status",
                "example_request": {
                    "action": "status",
                    "job_id": "uuid-here"
                }
            },
            "GET /health": "Health check",
            "GET /docs": "This documentation"
        },
        "ranking_algorithm": {
            "components": {
                "engagement_score": "Based on Reddit score and comments with logarithmic scaling",
                "monetization_score": "Based on high-value keywords and SEO indicators",
                "recency_score": "Exponential decay based on post age",
                "title_quality_score": "Based on length, readability, and format"
            },
            "configurable_weights": {
                "engagement_weight": "Default: 0.4",
                "monetization_weight": "Default: 0.3", 
                "recency_weight": "Default: 0.2",
                "title_quality_weight": "Default: 0.1"
            },
            "features": [
                "Duplicate detection with similarity threshold",
                "Configurable minimum score threshold",
                "Configurable maximum output limit",
                "Detailed scoring breakdown for each topic"
            ]
        }
    }

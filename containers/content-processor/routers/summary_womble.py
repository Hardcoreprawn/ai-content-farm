"""
Summary Womble Router

FastAPI router for content collection with async job processing.
Maintains the same API contract as the original Azure Function while using
pure functions and pluggable content collectors.
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
from azure.keyvault.secrets import SecretClient

from core.content_model import CollectionRequest, CollectionResult
from collectors.reddit_collector import RedditCollector


# Request/Response Models
class ContentCollectionRequest(BaseModel):
    """HTTP request model for content collection"""
    source: str = Field(..., description="Content source (reddit, rss, etc.)")
    targets: list[str] = Field(...,
                               description="Source-specific targets (subreddits, URLs, etc.)")
    limit: int = Field(
        25, ge=1, le=100, description="Number of items to collect per target")
    time_period: str = Field(
        "hot", description="Time period or sorting method")
    filters: Optional[Dict[str, Any]] = Field(
        None, description="Content filters")


class JobStatusRequest(BaseModel):
    """Request model for job status check"""
    action: str = Field(..., description="Action to perform (status)")
    job_id: str = Field(..., description="Job ID to check")


class JobResponse(BaseModel):
    """Response model for job creation"""
    job_id: str
    status: str
    message: str
    timestamp: str
    source: str
    topics_requested: list[str]
    limit: int
    status_check_example: Dict[str, Any]


class JobStatusResponse(BaseModel):
    """Response model for job status"""
    job_id: str
    status: str
    updated_at: str
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    results: Optional[Dict[str, Any]] = None


# Router setup
router = APIRouter(prefix="/api/summary-womble", tags=["content-collection"])

# In-memory job storage (TODO: replace with proper storage)
job_storage: Dict[str, Dict[str, Any]] = {}


async def get_reddit_credentials() -> Dict[str, str]:
    """
    Retrieve Reddit API credentials from environment variables or Azure Key Vault.
    
    Tries environment variables first (for local development), then falls back
    to Azure Key Vault (for production).
    
    Returns:
        Dict containing client_id, client_secret, and user_agent
        
    Raises:
        HTTPException: If credentials cannot be retrieved
    """
    # Try environment variables first (local development)
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")
    
    if client_id and client_secret and user_agent:
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "user_agent": user_agent
        }
    
    # Fall back to Azure Key Vault (production)
    try:
        # Initialize Azure Key Vault client
        credential = DefaultAzureCredential()
        
        # Note: In production, this should be configurable
        # For now, using staging Key Vault name
        vault_url = "https://ai-content-app-kvt0t36m.vault.azure.net/"
        client = SecretClient(vault_url=vault_url, credential=credential)
        
        # Retrieve secrets
        client_id = client.get_secret("reddit-client-id").value
        client_secret = client.get_secret("reddit-client-secret").value
        user_agent = client.get_secret("reddit-user-agent").value
        
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "user_agent": user_agent
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Reddit credentials from environment or Key Vault: {str(e)}"
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


async def process_content_collection(
    job_id: str,
    request: CollectionRequest,
    credentials: Dict[str, str]
):
    """
    Process content collection asynchronously.

    This function handles the async processing while delegating
    the actual collection to pure functions.
    """
    try:
        # Perform content collection
        update_job_status(job_id, "processing")
        
        if request.source == "reddit":
            # Use Reddit collector
            collector = RedditCollector(
                client_id=credentials["client_id"],
                client_secret=credentials["client_secret"],
                user_agent=credentials["user_agent"]
            )
            result = collector.collect(request)
        else:
            # Default behavior for unknown sources
            result = CollectionResult(
                request=request,
                items=[],
                success=False,
                error=f"Unsupported source: {request.source}"
            )

        # Convert result to response format
        if result.success:
            topics_response = []
            for item in result.items:
                topics_response.append({
                    "title": item.title,
                    "content": item.content,
                    "source_url": item.url,
                    "score": item.score or 0,
                    "author": item.author or "unknown",
                    "created_utc": item.created_at.isoformat() if item.created_at else "",
                    "num_comments": item.comments_count or 0,
                    "subreddit": item.metadata.get("subreddit", "") if item.metadata else ""
                })

            # Update job with successful results
            update_job_status(
                job_id,
                "completed",
                results={
                    "total_collected": len(result.items),
                    "source": result.request.source,
                    "timestamp": datetime.utcnow().isoformat(),
                    "filters_applied": result.request.filters,
                    "topics": topics_response,
                    "metadata": result.metadata
                }
            )
        else:
            # Handle collection failure
            update_job_status(
                job_id,
                "failed", 
                error=result.error or "Content collection failed"
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
        "service": "summary-womble",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/process", response_model=JobResponse)
async def create_content_collection_job(
    request: ContentCollectionRequest,
    background_tasks: BackgroundTasks
):
    """
    Create a new content collection job.

    This endpoint maintains compatibility with the original SummaryWomble API
    while using the new pure functions architecture.
    """
    # Generate job ID
    job_id = str(uuid.uuid4())

    # Create collection request
    collection_request = CollectionRequest(
        source=request.source,
        targets=request.targets,
        limit=request.limit,
        time_period=request.time_period,
        filters=request.filters
    )

    # Get credentials from Key Vault or environment
    try:
        credentials = await get_reddit_credentials()
    except HTTPException as e:
        # Return error if credentials can't be retrieved
        raise e

    # Create initial job status
    update_job_status(job_id, "queued")

    # Start background processing
    background_tasks.add_task(
        process_content_collection,
        job_id,
        collection_request,
        credentials
    )

    # Return job ticket
    return JobResponse(
        job_id=job_id,
        status="queued",
        message="Content processing started. Use job_id to check status.",
        timestamp=datetime.utcnow().isoformat(),
        source=request.source,
        topics_requested=request.targets,
        limit=request.limit,
        status_check_example={
            "method": "POST",
            "url": "/api/summary-womble/status",
            "body": {
                "action": "status",
                "job_id": job_id
            }
        }
    )


@router.post("/status", response_model=JobStatusResponse)
async def check_job_status(request: JobStatusRequest):
    """Check the status of a content collection job"""
    if request.action != "status":
        raise HTTPException(
            status_code=400, detail="Only 'status' action is supported")

    job_data = job_storage.get(request.job_id)
    if not job_data:
        raise HTTPException(
            status_code=404, detail=f"Job {request.job_id} not found")

    return JobStatusResponse(**job_data)


@router.get("/docs")
async def get_api_documentation():
    """API documentation endpoint"""
    return {
        "service": "Summary Womble Content Collector",
        "version": "2.0.0",
        "description": "Collect content from various sources (Reddit, RSS, APIs) with async job processing",
        "endpoints": {
            "POST /process": {
                "description": "Create content collection job",
                "supported_sources": ["reddit"],
                "example_request": {
                    "source": "reddit",
                    "targets": ["technology", "programming"],
                    "limit": 25,
                    "time_period": "hot"
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
        "content_sources": {
            "reddit": {
                "targets": "List of subreddit names (without /r/ prefix)",
                "time_periods": ["hot", "new", "top", "rising"],
                "filters": {
                    "min_score": "Minimum post score",
                    "min_comments": "Minimum number of comments",
                    "title_keywords": "Keywords that must appear in title",
                    "exclude_keywords": "Keywords to exclude from title"
                }
            }
        }
    }

"""
Content Ranker Router

FastAPI router for content ranking with async job processing.
Maintains compatibility with the original Azure Function API contract while using
pure functions and async processing.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from core.ranking_model import (
    ContentRankingRequest, 
    JobStatusRequest, 
    JobResponse, 
    JobStatusResponse
)

from core.ranking_engine import process_content_ranking


# Router setup
router = APIRouter(prefix="/api/content-ranker", tags=["content-ranking"])

# In-memory job storage (TODO: replace with proper storage)
job_storage: Dict[str, Dict[str, Any]] = {}

# Default ranking configuration
DEFAULT_RANKING_CONFIG = {
    'min_score_threshold': 100,
    'min_comments_threshold': 10,
    'weights': {
        'engagement': 0.3,
        'recency': 0.2,
        'monetization': 0.3,
        'title_quality': 0.2
    }
}


async def get_storage_client() -> BlobServiceClient:
    """
    Create Azure Blob Storage client with Managed Identity or environment variables.
    
    Returns:
        BlobServiceClient configured for the environment
        
    Raises:
        HTTPException: If storage cannot be configured
    """
    # Try environment variable first (local development)
    storage_account_name = os.getenv("STORAGE_ACCOUNT_NAME")
    
    if not storage_account_name:
        # Fallback to default from Azure Functions pattern
        storage_account_name = os.getenv("OUTPUT_STORAGE_ACCOUNT")
    
    if not storage_account_name:
        raise HTTPException(
            status_code=500,
            detail="Storage account not configured. Set STORAGE_ACCOUNT_NAME or OUTPUT_STORAGE_ACCOUNT environment variable."
        )

    try:
        # Use Managed Identity for Azure or connection string for local dev
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if connection_string:
            return BlobServiceClient.from_connection_string(connection_string)
        else:
            credential = DefaultAzureCredential()
            return BlobServiceClient(
                account_url=f"https://{storage_account_name}.blob.core.windows.net",
                credential=credential
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create storage client: {str(e)}"
        )


def parse_blob_path(blob_path: str) -> tuple[str, str]:
    """Parse blob path into container and blob name"""
    if not blob_path:
        raise ValueError("Blob path is required")
    
    parts = blob_path.split('/', 1)
    if len(parts) != 2:
        raise ValueError("Path must be in format 'container/blob-name'")
    
    return parts[0], parts[1]  # container, blob_name


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
    request: ContentRankingRequest
):
    """
    Process content ranking asynchronously.

    This function handles the async processing while delegating
    the actual ranking to pure functions.
    """
    try:
        update_job_status(job_id, "processing")
        
        # Determine processing mode: blob-based or direct content
        if request.input_blob_path:
            # Blob-based processing (traditional mode)
            try:
                storage_client = await get_storage_client()
                
                # Parse input path
                input_container, input_blob_name = parse_blob_path(request.input_blob_path)
                
                # Read input blob
                blob_client = storage_client.get_blob_client(
                    container=input_container, blob=input_blob_name)
                blob_content = blob_client.download_blob().readall().decode('utf-8')
                content_data = json.loads(blob_content)
                
            except Exception as e:
                update_job_status(
                    job_id,
                    "failed",
                    error=f"Failed to read input blob: {str(e)}"
                )
                return
                
        elif request.content_data:
            # Direct content processing (new mode)
            content_data = request.content_data
        else:
            update_job_status(
                job_id,
                "failed",
                error="Either input_blob_path or content_data must be provided"
            )
            return

        # Prepare ranking configuration
        ranking_config = {**DEFAULT_RANKING_CONFIG}
        if request.ranking_config:
            ranking_config.update(request.ranking_config)

        # Process ranking using pure functions
        ranking_result = process_content_ranking(content_data, ranking_config)
        
        # Handle output
        if request.output_blob_path:
            # Write to blob storage
            try:
                storage_client = await get_storage_client()
                output_container, output_blob_name = parse_blob_path(request.output_blob_path)
                
                # Ensure output container exists
                try:
                    container_client = storage_client.get_container_client(output_container)
                    container_client.create_container()
                except Exception:
                    # Container might already exist
                    pass
                
                # Write output blob
                output_json = json.dumps(ranking_result, indent=2)
                output_blob_client = storage_client.get_blob_client(
                    container=output_container, blob=output_blob_name)
                output_blob_client.upload_blob(output_json, overwrite=True)
                
                result_data = {
                    "output_path": request.output_blob_path,
                    "total_ranked": ranking_result["metadata"]["total_topics"],
                    "summary": ranking_result["metadata"]
                }
                
            except Exception as e:
                update_job_status(
                    job_id,
                    "failed",
                    error=f"Failed to write output blob: {str(e)}"
                )
                return
        else:
            # Return results directly
            result_data = ranking_result

        # Update job with successful results
        update_job_status(
            job_id,
            "completed",
            results=result_data
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
    request: ContentRankingRequest,
    background_tasks: BackgroundTasks
):
    """
    Create a new content ranking job.

    This endpoint maintains compatibility with the original Azure Function API
    while using the new pure functions architecture and async processing.
    """
    # Validate request
    if not request.input_blob_path and not request.content_data:
        raise HTTPException(
            status_code=400,
            detail="Either input_blob_path or content_data must be provided"
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())

    # Create initial job status
    update_job_status(job_id, "queued")

    # Start background processing
    background_tasks.add_task(
        process_ranking_job,
        job_id,
        request
    )

    # Determine request type for response
    request_type = "blob_processing" if request.input_blob_path else "direct_content"

    # Return job ticket
    return JobResponse(
        job_id=job_id,
        status="queued",
        message="Content ranking started. Use job_id to check status.",
        timestamp=datetime.utcnow().isoformat(),
        request_type=request_type,
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
        "service": "Content Ranker Service",
        "version": "2.0.0",
        "description": "Rank content topics using configurable algorithms with async job processing",
        "endpoints": {
            "POST /process": {
                "description": "Create content ranking job",
                "input_modes": {
                    "blob_processing": "Provide input_blob_path and output_blob_path for traditional blob-based processing",
                    "direct_content": "Provide content_data for direct content processing (results returned in status)"
                },
                "example_blob_request": {
                    "input_blob_path": "raw-data/topics_20250813.json",
                    "output_blob_path": "ranked-data/ranked_topics_20250813.json",
                    "ranking_config": {
                        "weights": {
                            "engagement": 0.4,
                            "recency": 0.2,
                            "monetization": 0.3,
                            "title_quality": 0.1
                        }
                    }
                },
                "example_direct_request": {
                    "content_data": {
                        "topics": [
                            {
                                "title": "Sample Topic",
                                "score": 1500,
                                "num_comments": 50,
                                "created_utc": 1723521600
                            }
                        ]
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
        "ranking_algorithms": {
            "engagement": "Reddit score and comment count based ranking",
            "recency": "Time-based freshness scoring with exponential decay",
            "monetization": "Commercial value based on high-value keywords",
            "title_quality": "SEO potential and readability scoring"
        },
        "configuration": {
            "weights": "Customize scoring weights for each algorithm (sum should equal 1.0)",
            "thresholds": {
                "min_score_threshold": "Minimum Reddit score required",
                "min_comments_threshold": "Minimum comment count required"
            }
        }
    }
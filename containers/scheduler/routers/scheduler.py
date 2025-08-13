"""
Scheduler Router

FastAPI router for workflow orchestration and scheduling.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import httpx

# Router instance
router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])

# In-memory workflow storage
workflow_storage: Dict[str, Dict[str, Any]] = {}


class WorkflowRequest(BaseModel):
    """HTTP request model for workflow execution"""
    workflow_type: str = Field(..., description="Type of workflow (hot-topics, ranking, enrichment)")
    config: Optional[Dict[str, Any]] = Field(None, description="Workflow configuration")


class WorkflowResponse(BaseModel):
    """Response for workflow creation"""
    workflow_id: str
    status: str
    message: str
    timestamp: str
    workflow_type: str


class WorkflowStatusResponse(BaseModel):
    """Response for workflow status check"""
    workflow_id: str
    status: str
    updated_at: str
    workflow_type: str
    steps: List[Dict[str, Any]]
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def update_workflow_status(
    workflow_id: str,
    status: str,
    steps: List[Dict[str, Any]] = None,
    progress: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
):
    """Update workflow status in storage"""
    workflow_storage[workflow_id] = {
        "workflow_id": workflow_id,
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
        "steps": steps or [],
        "progress": progress,
        "error": error
    }


async def execute_hot_topics_workflow(workflow_id: str, config: Dict[str, Any]):
    """Execute hot topics collection workflow"""
    try:
        steps = [
            {"step": "collect", "status": "pending", "service": "content-processor"},
            {"step": "rank", "status": "pending", "service": "content-ranker"},
            {"step": "enrich", "status": "pending", "service": "content-enricher"},
            {"step": "publish", "status": "pending", "service": "cms-publisher"}
        ]
        
        update_workflow_status(workflow_id, "processing", steps)
        
        # Step 1: Collect content
        steps[0]["status"] = "processing"
        update_workflow_status(workflow_id, "processing", steps)
        
        async with httpx.AsyncClient() as client:
            # Call content processor
            collect_response = await client.post(
                "http://content-processor:8000/api/summary-womble/process",
                json={
                    "source": "reddit",
                    "targets": config.get("targets", ["technology"]),
                    "limit": config.get("limit", 10)
                }
            )
            
            if collect_response.status_code == 200:
                collect_job = collect_response.json()
                steps[0]["status"] = "completed"
                steps[0]["job_id"] = collect_job["job_id"]
                
                # Wait for collection to complete (simplified)
                await asyncio.sleep(5)
                
                # Step 2: Rank content
                steps[1]["status"] = "processing"
                update_workflow_status(workflow_id, "processing", steps)
                
                rank_response = await client.post(
                    "http://content-ranker:8001/api/content-ranker/process",
                    json={
                        "source": "reddit",
                        "topics": [{"title": "Sample topic", "score": 100, "num_comments": 10}]  # Placeholder
                    }
                )
                
                if rank_response.status_code == 200:
                    rank_job = rank_response.json()
                    steps[1]["status"] = "completed"
                    steps[1]["job_id"] = rank_job["job_id"]
                    
                    # Step 3: Enrich content
                    steps[2]["status"] = "processing"
                    update_workflow_status(workflow_id, "processing", steps)
                    
                    enrich_response = await client.post(
                        "http://content-enricher:8002/api/content-enricher/process",
                        json={
                            "source": "reddit",
                            "topics": [{"title": "Sample topic", "content": "Sample content"}]  # Placeholder
                        }
                    )
                    
                    if enrich_response.status_code == 200:
                        enrich_job = enrich_response.json()
                        steps[2]["status"] = "completed"
                        steps[2]["job_id"] = enrich_job["job_id"]
                        
                        # Step 4: Publish (placeholder)
                        steps[3]["status"] = "completed"
                        steps[3]["note"] = "CMS publisher not yet implemented"
                        
                        update_workflow_status(workflow_id, "completed", steps)
                    else:
                        raise Exception(f"Enrichment failed: {enrich_response.text}")
                else:
                    raise Exception(f"Ranking failed: {rank_response.text}")
            else:
                raise Exception(f"Collection failed: {collect_response.text}")
                
    except Exception as e:
        update_workflow_status(workflow_id, "failed", steps, error=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "scheduler",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/workflows", response_model=WorkflowResponse)
async def create_workflow(
    request: WorkflowRequest,
    background_tasks: BackgroundTasks
):
    """Create and execute a new workflow"""
    workflow_id = str(uuid.uuid4())
    
    # Initialize workflow
    update_workflow_status(workflow_id, "queued", [])
    
    # Start workflow execution based on type
    if request.workflow_type == "hot-topics":
        background_tasks.add_task(
            execute_hot_topics_workflow,
            workflow_id,
            request.config or {}
        )
    else:
        update_workflow_status(
            workflow_id, 
            "failed", 
            [], 
            error=f"Unknown workflow type: {request.workflow_type}"
        )
    
    return WorkflowResponse(
        workflow_id=workflow_id,
        status="queued",
        message=f"Workflow {request.workflow_type} started",
        timestamp=datetime.utcnow().isoformat(),
        workflow_type=request.workflow_type
    )


@router.get("/workflows/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(workflow_id: str):
    """Get workflow status"""
    workflow_data = workflow_storage.get(workflow_id)
    if not workflow_data:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow {workflow_id} not found"
        )
    
    return WorkflowStatusResponse(
        workflow_type="hot-topics",  # Default for now
        **workflow_data
    )


@router.get("/workflows")
async def list_workflows():
    """List all workflows"""
    return {
        "workflows": list(workflow_storage.values()),
        "total": len(workflow_storage)
    }


@router.get("/docs")
async def get_api_documentation():
    """API documentation endpoint"""
    return {
        "service": "Scheduler",
        "version": "2.0.0",
        "description": "Workflow orchestration and scheduling for content processing pipeline",
        "workflows": {
            "hot-topics": {
                "description": "Complete content collection, ranking, enrichment, and publishing workflow",
                "steps": [
                    "Collect content from sources",
                    "Rank and score content",
                    "Enrich with AI summaries",
                    "Publish to CMS"
                ]
            }
        },
        "endpoints": {
            "POST /workflows": "Create and execute workflow",
            "GET /workflows/{id}": "Get workflow status",
            "GET /workflows": "List all workflows",
            "GET /health": "Health check",
            "GET /docs": "This documentation"
        }
    }

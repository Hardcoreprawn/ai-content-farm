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

from core.scheduler_model import (
    WorkflowRequest, WorkflowResponse, WorkflowStatusResponse, 
    WorkflowType, WorkflowStatus, WorkflowExecutionContext
)
from core.scheduler_engine import (
    get_workflow_definition, execute_workflow, DEFAULT_SERVICES
)

# Router instance
router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])

# In-memory workflow storage
workflow_storage: Dict[str, Dict[str, Any]] = {}


def update_workflow_status(
    workflow_id: str,
    status: str,
    steps: List[Dict[str, Any]] = None,
    progress: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    output_data: Optional[Dict[str, Any]] = None
):
    """Update workflow status in storage"""
    workflow_storage[workflow_id] = {
        "workflow_id": workflow_id,
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
        "steps": steps or [],
        "progress": progress,
        "error": error,
        "output_data": output_data
    }


async def execute_workflow_background(
    workflow_id: str,
    workflow_type: WorkflowType,
    config: Dict[str, Any],
    input_data: Dict[str, Any]
):
    """Execute workflow in background using the scheduler engine"""
    try:
        # Update status to processing
        update_workflow_status(workflow_id, "processing")
        
        # Get workflow definition
        workflow_definition = get_workflow_definition(workflow_type, config)
        
        # Execute the workflow
        result = await execute_workflow(
            workflow_definition,
            input_data,
            DEFAULT_SERVICES
        )
        
        # Convert steps to dict format for storage
        steps_dict = []
        for step in result.steps_executed:
            steps_dict.append({
                "step_id": step.step_id,
                "name": step.name,
                "service": step.service,
                "status": step.status.value,
                "started_at": step.started_at,
                "completed_at": step.completed_at,
                "duration_seconds": step.duration_seconds,
                "error_message": step.error_message
            })
        
        # Update workflow with results
        final_status = "completed" if result.status == WorkflowStatus.COMPLETED else "failed"
        error_msg = "; ".join(result.errors) if result.errors else None
        
        update_workflow_status(
            workflow_id,
            final_status,
            steps=steps_dict,
            progress={
                "execution_time": result.execution_time,
                "steps_total": len(result.steps_executed),
                "steps_completed": len([s for s in result.steps_executed if s.status.value == "completed"]),
                "errors": result.errors,
                "warnings": result.warnings
            },
            error=error_msg,
            output_data=result.output_data
        )
        
    except Exception as e:
        # Update workflow with error
        update_workflow_status(
            workflow_id,
            "failed",
            error=str(e)
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "scheduler",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "active_workflows": len([w for w in workflow_storage.values() if w.get("status") == "processing"])
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
    
    # Prepare input data
    input_data = request.input_data or {}
    
    # Start workflow execution
    try:
        workflow_definition = get_workflow_definition(request.workflow_type, request.config or {})
        
        background_tasks.add_task(
            execute_workflow_background,
            workflow_id,
            request.workflow_type,
            request.config or {},
            input_data
        )
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            status=WorkflowStatus.QUEUED,
            message=f"Workflow {request.workflow_type.value} started",
            timestamp=datetime.utcnow().isoformat(),
            workflow_type=request.workflow_type,
            steps_total=len(workflow_definition.steps),
            priority=request.priority
        )
        
    except Exception as e:
        update_workflow_status(
            workflow_id, 
            "failed", 
            [], 
            error=f"Failed to start workflow: {str(e)}"
        )
        raise HTTPException(status_code=400, detail=str(e))


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
        workflow_type=WorkflowType.HOT_TOPICS,  # Would need to store this
        progress=workflow_data.get("progress", {}),
        steps=workflow_data.get("steps", []),
        started_at=workflow_data.get("started_at"),
        completed_at=workflow_data.get("completed_at"),
        duration_seconds=workflow_data.get("duration_seconds"),
        output_data=workflow_data.get("output_data"),
        **{k: v for k, v in workflow_data.items() if k not in ["progress", "steps", "started_at", "completed_at", "duration_seconds", "output_data"]}
    )


@router.get("/workflows")
async def list_workflows():
    """List all workflows"""
    return {
        "workflows": list(workflow_storage.values()),
        "total": len(workflow_storage),
        "active": len([w for w in workflow_storage.values() if w.get("status") == "processing"])
    }


# Convenience endpoints for specific workflow types

@router.post("/hot-topics")
async def create_hot_topics_workflow(
    background_tasks: BackgroundTasks,
    targets: List[str] = ["technology"],
    limit: int = 25,
    enable_enrichment: bool = True,
    enable_site_generation: bool = False
):
    """Create a hot topics workflow with simplified parameters"""
    request = WorkflowRequest(
        workflow_type=WorkflowType.HOT_TOPICS,
        config={
            "targets": targets,
            "limit": limit,
            "enable_enrichment": enable_enrichment,
            "enable_site_generation": enable_site_generation
        }
    )
    return await create_workflow(request, background_tasks)


@router.post("/topic-ranking")
async def create_topic_ranking_workflow(
    background_tasks: BackgroundTasks,
    topics: List[Dict[str, Any]],
    source: str = "reddit"
):
    """Create a topic ranking workflow"""
    request = WorkflowRequest(
        workflow_type=WorkflowType.TOPIC_RANKING,
        config={"source": source},
        input_data={"topics": topics}
    )
    return await create_workflow(request, background_tasks)


@router.post("/content-enrichment")
async def create_content_enrichment_workflow(
    background_tasks: BackgroundTasks,
    topics: List[Dict[str, Any]],
    source: str = "reddit",
    enable_ai_summary: bool = True,
    enable_sentiment_analysis: bool = True
):
    """Create a content enrichment workflow"""
    request = WorkflowRequest(
        workflow_type=WorkflowType.CONTENT_ENRICHMENT,
        config={
            "source": source,
            "enrichment_config": {
                "enable_ai_summary": enable_ai_summary,
                "enable_sentiment_analysis": enable_sentiment_analysis
            }
        },
        input_data={"topics": topics}
    )
    return await create_workflow(request, background_tasks)


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Alias for workflow status (for compatibility)"""
    return await get_workflow_status(job_id)


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
                    "Enrich with AI summaries (optional)",
                    "Generate static site (optional)"
                ]
            },
            "topic-ranking": {
                "description": "Rank existing topics using multiple scoring algorithms",
                "steps": ["Score and rank topics"]
            },
            "content-enrichment": {
                "description": "Enhance content with AI summaries and metadata",
                "steps": ["AI enhancement and categorization"]
            }
        },
        "endpoints": {
            "POST /workflows": "Create and execute workflow",
            "GET /workflows/{id}": "Get workflow status",
            "GET /workflows": "List all workflows",
            "POST /hot-topics": "Quick hot topics workflow",
            "POST /topic-ranking": "Quick ranking workflow",
            "POST /content-enrichment": "Quick enrichment workflow",
            "GET /health": "Health check",
            "GET /docs": "This documentation"
        }
    }

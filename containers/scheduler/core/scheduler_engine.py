"""
Scheduler Engine - Pure Functions

Workflow orchestration engine using functional programming principles.
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from .scheduler_model import (
    WorkflowDefinition, WorkflowStep, WorkflowType, WorkflowStatus, 
    WorkflowStepStatus, ServiceDefinition, WorkflowExecutionContext,
    WorkflowExecutionResult
)


# Service definitions for the Container Apps environment
DEFAULT_SERVICES = {
    "content-processor": ServiceDefinition(
        name="content-processor",
        base_url="http://content-processor:8000",
        health_endpoint="/health",
        endpoints={
            "process": "/api/summary-womble/process",
            "status": "/api/summary-womble/status"
        }
    ),
    "content-ranker": ServiceDefinition(
        name="content-ranker",
        base_url="http://content-ranker:8001",
        health_endpoint="/health",
        endpoints={
            "process": "/api/content-ranker/process",
            "status": "/api/content-ranker/status"
        }
    ),
    "content-enricher": ServiceDefinition(
        name="content-enricher",
        base_url="http://content-enricher:8002",
        health_endpoint="/health",
        endpoints={
            "process": "/api/content-enricher/process",
            "status": "/api/content-enricher/status"
        }
    ),
    "ssg": ServiceDefinition(
        name="ssg",
        base_url="http://ssg:8004",
        health_endpoint="/health",
        endpoints={
            "generate": "/api/ssg/generate",
            "status": "/api/ssg/status"
        }
    )
}


def create_hot_topics_workflow(config: Dict[str, Any]) -> WorkflowDefinition:
    """
    Create a hot topics collection workflow definition.
    
    Args:
        config: Configuration for the workflow
        
    Returns:
        WorkflowDefinition for hot topics processing
    """
    steps = [
        WorkflowStep(
            step_id="collect_content",
            name="Collect Content",
            service="content-processor",
            endpoint="/api/summary-womble/process",
            input_data={
                "source": config.get("source", "reddit"),
                "targets": config.get("targets", ["technology"]),
                "limit": config.get("limit", 25)
            }
        ),
        WorkflowStep(
            step_id="rank_content",
            name="Rank Content", 
            service="content-ranker",
            endpoint="/api/content-ranker/process",
            input_data={}  # Will be populated from previous step
        )
    ]
    
    # Add enrichment step if enabled
    if config.get("enable_enrichment", True):
        steps.append(WorkflowStep(
            step_id="enrich_content",
            name="Enrich Content",
            service="content-enricher", 
            endpoint="/api/content-enricher/process",
            input_data={}  # Will be populated from previous step
        ))
    
    # Add site generation if enabled
    if config.get("enable_site_generation", False):
        steps.append(WorkflowStep(
            step_id="generate_site",
            name="Generate Static Site",
            service="ssg",
            endpoint="/api/ssg/generate",
            input_data={
                "config": config.get("site_config", {
                    "site_title": "AI Content Farm",
                    "output_format": "markdown"
                })
            }
        ))
    
    # Set up dependencies
    dependencies = {
        "rank_content": ["collect_content"]
    }
    
    if len(steps) > 2:
        dependencies["enrich_content"] = ["rank_content"]
    
    if len(steps) > 3:
        dependencies["generate_site"] = ["enrich_content"]
    
    return WorkflowDefinition(
        workflow_type=WorkflowType.HOT_TOPICS,
        name="Hot Topics Collection and Processing",
        description="Complete pipeline from content collection to enriched output",
        steps=steps,
        dependencies=dependencies,
        timeout_minutes=config.get("timeout_minutes", 30),
        config=config
    )


def create_topic_ranking_workflow(config: Dict[str, Any]) -> WorkflowDefinition:
    """
    Create a topic ranking workflow definition.
    
    Args:
        config: Configuration for the workflow
        
    Returns:
        WorkflowDefinition for topic ranking
    """
    steps = [
        WorkflowStep(
            step_id="rank_topics",
            name="Rank Topics",
            service="content-ranker",
            endpoint="/api/content-ranker/process",
            input_data={
                "source": config.get("source", "reddit"),
                "topics": config.get("topics", []),
                "config": config.get("ranking_config", {})
            }
        )
    ]
    
    return WorkflowDefinition(
        workflow_type=WorkflowType.TOPIC_RANKING,
        name="Topic Ranking",
        description="Rank and score topics based on multiple criteria",
        steps=steps,
        dependencies={},
        timeout_minutes=config.get("timeout_minutes", 15),
        config=config
    )


def create_content_enrichment_workflow(config: Dict[str, Any]) -> WorkflowDefinition:
    """
    Create a content enrichment workflow definition.
    
    Args:
        config: Configuration for the workflow
        
    Returns:
        WorkflowDefinition for content enrichment
    """
    steps = [
        WorkflowStep(
            step_id="enrich_content",
            name="Enrich Content",
            service="content-enricher",
            endpoint="/api/content-enricher/process",
            input_data={
                "source": config.get("source", "reddit"),
                "topics": config.get("topics", []),
                "config": config.get("enrichment_config", {})
            }
        )
    ]
    
    return WorkflowDefinition(
        workflow_type=WorkflowType.CONTENT_ENRICHMENT,
        name="Content Enrichment",
        description="AI-powered content enhancement with summaries and metadata",
        steps=steps,
        dependencies={},
        timeout_minutes=config.get("timeout_minutes", 20),
        config=config
    )


def get_workflow_definition(workflow_type: WorkflowType, config: Dict[str, Any]) -> WorkflowDefinition:
    """
    Get workflow definition based on type and configuration.
    
    Args:
        workflow_type: Type of workflow to create
        config: Configuration for the workflow
        
    Returns:
        WorkflowDefinition for the requested workflow type
    """
    if workflow_type == WorkflowType.HOT_TOPICS:
        return create_hot_topics_workflow(config)
    elif workflow_type == WorkflowType.TOPIC_RANKING:
        return create_topic_ranking_workflow(config)
    elif workflow_type == WorkflowType.CONTENT_ENRICHMENT:
        return create_content_enrichment_workflow(config)
    elif workflow_type == WorkflowType.FULL_PIPELINE:
        # Full pipeline is essentially hot topics with all features enabled
        full_config = config.copy()
        full_config.update({
            "enable_enrichment": True,
            "enable_site_generation": True
        })
        return create_hot_topics_workflow(full_config)
    else:
        raise ValueError(f"Unsupported workflow type: {workflow_type}")


async def check_service_health(service: ServiceDefinition) -> bool:
    """
    Check if a service is healthy and responding.
    
    Args:
        service: Service definition to check
        
    Returns:
        True if service is healthy, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{service.base_url}{service.health_endpoint}")
            return response.status_code == 200
    except Exception:
        return False


async def call_service_endpoint(
    service: ServiceDefinition, 
    endpoint: str, 
    data: Dict[str, Any],
    timeout: Optional[int] = None
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Call a service endpoint with data.
    
    Args:
        service: Service definition
        endpoint: Endpoint path
        data: Data to send
        timeout: Optional timeout override
        
    Returns:
        Tuple of (success, response_data, error_message)
    """
    try:
        timeout_value = timeout or service.timeout_seconds
        async with httpx.AsyncClient(timeout=timeout_value) as client:
            url = f"{service.base_url}{endpoint}"
            response = await client.post(url, json=data)
            
            if response.status_code in [200, 201, 202]:
                return True, response.json(), None
            else:
                return False, None, f"HTTP {response.status_code}: {response.text}"
                
    except Exception as e:
        return False, None, str(e)


async def wait_for_job_completion(
    service: ServiceDefinition,
    job_id: str,
    max_wait_minutes: int = 10,
    poll_interval_seconds: int = 5
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Wait for an asynchronous job to complete.
    
    Args:
        service: Service definition
        job_id: Job ID to monitor
        max_wait_minutes: Maximum time to wait
        poll_interval_seconds: How often to check status
        
    Returns:
        Tuple of (success, job_result, error_message)
    """
    max_polls = (max_wait_minutes * 60) // poll_interval_seconds
    status_endpoint = service.endpoints.get("status", "/status")
    
    for _ in range(max_polls):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try different status endpoint formats
                status_data = {"action": "status", "job_id": job_id}
                response = await client.post(f"{service.base_url}{status_endpoint}", json=status_data)
                
                if response.status_code == 200:
                    job_status = response.json()
                    status = job_status.get("status", "unknown")
                    
                    if status == "completed":
                        return True, job_status, None
                    elif status == "failed":
                        return False, None, job_status.get("error", "Job failed")
                    # If queued or processing, continue polling
                    
                await asyncio.sleep(poll_interval_seconds)
                
        except Exception as e:
            # If status check fails, wait and try again
            await asyncio.sleep(poll_interval_seconds)
            continue
    
    return False, None, f"Job {job_id} timed out after {max_wait_minutes} minutes"


async def execute_workflow_step(
    step: WorkflowStep,
    context: WorkflowExecutionContext
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Execute a single workflow step.
    
    Args:
        step: Step to execute
        context: Execution context
        
    Returns:
        Tuple of (success, result_data, error_message)
    """
    service = context.services.get(step.service)
    if not service:
        return False, None, f"Service {step.service} not found in context"
    
    # Prepare input data (merge step input with context data)
    input_data = step.input_data.copy() if step.input_data else {}
    
    # If this step depends on previous steps, merge their output
    for dep_step_id in context.step_results:
        if dep_step_id in context.step_results:
            dep_result = context.step_results[dep_step_id]
            # For ranking and enrichment, pass topics from previous step
            if step.service in ["content-ranker", "content-enricher"] and "topics" in dep_result:
                input_data["topics"] = dep_result["topics"]
    
    # Call the service
    success, response_data, error = await call_service_endpoint(
        service, step.endpoint, input_data
    )
    
    if not success:
        return False, None, error
    
    # If the service returns a job ID, wait for completion
    job_id = response_data.get("job_id")
    if job_id:
        success, job_result, error = await wait_for_job_completion(service, job_id)
        if success:
            return True, job_result.get("results", job_result), None
        else:
            return False, None, error
    
    return True, response_data, None


async def execute_workflow(
    workflow_definition: WorkflowDefinition,
    input_data: Dict[str, Any],
    services: Optional[Dict[str, ServiceDefinition]] = None
) -> WorkflowExecutionResult:
    """
    Execute a complete workflow.
    
    Args:
        workflow_definition: Workflow to execute
        input_data: Initial input data
        services: Service definitions (uses defaults if not provided)
        
    Returns:
        WorkflowExecutionResult with execution details
    """
    start_time = datetime.utcnow()
    services = services or DEFAULT_SERVICES
    
    context = WorkflowExecutionContext(
        workflow_id=f"exec_{start_time.strftime('%Y%m%d_%H%M%S')}",
        workflow_type=workflow_definition.workflow_type,
        config=workflow_definition.config,
        input_data=input_data,
        services=services
    )
    
    executed_steps = []
    errors = []
    warnings = []
    output_data = {}
    
    # Execute steps in dependency order
    remaining_steps = workflow_definition.steps.copy()
    completed_step_ids = set()
    
    while remaining_steps:
        executed_any = False
        
        for step in remaining_steps.copy():
            # Check if dependencies are satisfied
            dependencies = workflow_definition.dependencies.get(step.step_id, [])
            if all(dep_id in completed_step_ids for dep_id in dependencies):
                # Execute this step
                step.status = WorkflowStepStatus.PROCESSING
                step.started_at = datetime.utcnow().isoformat()
                
                try:
                    success, result_data, error = await execute_workflow_step(step, context)
                    
                    step.completed_at = datetime.utcnow().isoformat()
                    started = datetime.fromisoformat(step.started_at.replace('Z', '+00:00'))
                    completed = datetime.fromisoformat(step.completed_at.replace('Z', '+00:00'))
                    step.duration_seconds = (completed - started).total_seconds()
                    
                    if success:
                        step.status = WorkflowStepStatus.COMPLETED
                        step.output_data = result_data
                        context.step_results[step.step_id] = result_data
                        completed_step_ids.add(step.step_id)
                    else:
                        step.status = WorkflowStepStatus.FAILED
                        step.error_message = error
                        errors.append(f"Step {step.step_id} failed: {error}")
                        
                except Exception as e:
                    step.status = WorkflowStepStatus.FAILED
                    step.error_message = str(e)
                    step.completed_at = datetime.utcnow().isoformat()
                    errors.append(f"Step {step.step_id} failed with exception: {str(e)}")
                
                executed_steps.append(step)
                remaining_steps.remove(step)
                executed_any = True
        
        if not executed_any:
            # No steps could be executed (circular dependencies or failed prerequisites)
            for step in remaining_steps:
                step.status = WorkflowStepStatus.SKIPPED
                warnings.append(f"Step {step.step_id} skipped due to unmet dependencies")
                executed_steps.append(step)
            break
    
    # Determine overall status
    if errors:
        status = WorkflowStatus.FAILED
    elif warnings:
        status = WorkflowStatus.COMPLETED  # Completed with warnings
    else:
        status = WorkflowStatus.COMPLETED
    
    # Collect output data from final step
    if executed_steps:
        final_step = executed_steps[-1]
        if final_step.output_data:
            output_data = final_step.output_data
    
    execution_time = (datetime.utcnow() - start_time).total_seconds()
    
    return WorkflowExecutionResult(
        workflow_id=context.workflow_id,
        status=status,
        steps_executed=executed_steps,
        output_data=output_data,
        execution_time=execution_time,
        errors=errors,
        warnings=warnings
    )
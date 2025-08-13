"""
Scheduler Data Models

Request/Response models for the Scheduler Container Apps service.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class WorkflowType(str, Enum):
    """Supported workflow types"""
    HOT_TOPICS = "hot-topics"
    TOPIC_RANKING = "topic-ranking"
    CONTENT_ENRICHMENT = "content-enrichment"
    FULL_PIPELINE = "full-pipeline"
    CUSTOM = "custom"


class WorkflowStepStatus(str, Enum):
    """Workflow step statuses"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(str, Enum):
    """Overall workflow statuses"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStep(BaseModel):
    """Individual step in a workflow"""
    step_id: str = Field(..., description="Unique step identifier")
    name: str = Field(..., description="Human-readable step name")
    service: str = Field(..., description="Target service name")
    endpoint: str = Field(..., description="Service endpoint to call")
    status: WorkflowStepStatus = Field(default=WorkflowStepStatus.PENDING)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    job_id: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class WorkflowDefinition(BaseModel):
    """Definition of a workflow with its steps"""
    workflow_type: WorkflowType
    name: str
    description: str
    steps: List[WorkflowStep]
    dependencies: Dict[str, List[str]] = Field(default_factory=dict)  # step_id -> [prerequisite_step_ids]
    timeout_minutes: int = 60
    retry_attempts: int = 3
    config: Dict[str, Any] = Field(default_factory=dict)


class WorkflowRequest(BaseModel):
    """HTTP request model for workflow execution"""
    workflow_type: WorkflowType = Field(..., description="Type of workflow to execute")
    config: Optional[Dict[str, Any]] = Field(None, description="Workflow configuration")
    input_data: Optional[Dict[str, Any]] = Field(None, description="Initial input data")
    priority: int = Field(default=5, description="Execution priority (1-10, higher is more important)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "workflow_type": "hot-topics",
                "config": {
                    "targets": ["technology", "programming"],
                    "limit": 10,
                    "enable_enrichment": True
                },
                "priority": 7
            }
        }


class WorkflowResponse(BaseModel):
    """Response for workflow creation"""
    workflow_id: str
    status: WorkflowStatus
    message: str
    timestamp: str
    workflow_type: WorkflowType
    estimated_completion: Optional[str] = None
    steps_total: int
    priority: int


class WorkflowStatusResponse(BaseModel):
    """Response for workflow status check"""
    workflow_id: str
    status: WorkflowStatus
    updated_at: str
    workflow_type: WorkflowType
    progress: Dict[str, Any]
    steps: List[WorkflowStep]
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    output_data: Optional[Dict[str, Any]] = None


class ServiceDefinition(BaseModel):
    """Definition of a service that can be called by workflows"""
    name: str
    base_url: str
    health_endpoint: str
    timeout_seconds: int = 30
    retry_attempts: int = 3
    endpoints: Dict[str, str] = Field(default_factory=dict)


class ScheduleRequest(BaseModel):
    """Request to schedule a workflow for later execution"""
    workflow_type: WorkflowType
    schedule_time: str = Field(..., description="ISO timestamp when to execute")
    config: Optional[Dict[str, Any]] = None
    recurrence: Optional[str] = Field(None, description="Cron expression for recurring schedules")


class ScheduleResponse(BaseModel):
    """Response for scheduled workflow"""
    schedule_id: str
    workflow_type: WorkflowType
    schedule_time: str
    status: str  # scheduled, active, cancelled
    recurrence: Optional[str] = None
    next_execution: Optional[str] = None


class WorkflowExecutionContext(BaseModel):
    """Context for workflow execution"""
    workflow_id: str
    workflow_type: WorkflowType
    config: Dict[str, Any]
    input_data: Dict[str, Any]
    services: Dict[str, ServiceDefinition]
    current_step: Optional[str] = None
    step_results: Dict[str, Any] = Field(default_factory=dict)
    global_variables: Dict[str, Any] = Field(default_factory=dict)


class WorkflowExecutionResult(BaseModel):
    """Result of workflow execution"""
    workflow_id: str
    status: WorkflowStatus
    steps_executed: List[WorkflowStep]
    output_data: Dict[str, Any]
    execution_time: float
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
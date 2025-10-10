"""
Pydantic models for site-publisher.

All data structures for requests, responses, and internal data.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    """Processing status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str
    service: str
    version: str
    timestamp: datetime


class MetricsResponse(BaseModel):
    """Metrics response model."""

    total_builds: int
    successful_builds: int
    failed_builds: int
    last_build_time: Optional[datetime] = None
    last_build_duration: Optional[float] = None
    uptime_seconds: float


class PublishRequest(BaseModel):
    """Manual publish request model."""

    trigger_source: str = "manual"
    force_rebuild: bool = False


class PublishResponse(BaseModel):
    """Publish response model."""

    status: ProcessingStatus
    message: str
    files_uploaded: int
    duration_seconds: float
    errors: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Validation result model."""

    is_valid: bool
    errors: List[str] = Field(default_factory=list)


class DownloadResult(BaseModel):
    """Result from downloading markdown files."""

    files_downloaded: int
    duration_seconds: float
    errors: List[str] = Field(default_factory=list)


class BuildResult(BaseModel):
    """Result from Hugo build."""

    success: bool
    output_files: int
    duration_seconds: float
    errors: List[str] = Field(default_factory=list)


class DeploymentResult(BaseModel):
    """Result from deployment to blob storage."""

    files_uploaded: int
    duration_seconds: float
    errors: List[str] = Field(default_factory=list)

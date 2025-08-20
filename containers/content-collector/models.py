"""
Content Collector Data Models

Pydantic models for the content collector API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class SourceConfig(BaseModel):
    """Configuration for a content source."""

    type: str = Field(..., description="Type of source (e.g., 'reddit', 'web')")
    subreddits: Optional[List[str]] = Field(
        default=None, description="List of subreddits (for Reddit)"
    )
    sites: Optional[List[str]] = Field(
        default=None, description="List of web sites (for web sources)"
    )
    limit: Optional[int] = Field(
        default=10, ge=1, le=100, description="Number of items to collect"
    )
    criteria: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Filtering criteria"
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        # Allow any type, will be handled gracefully in processing
        return v

    @model_validator(mode="after")
    def validate_source_requirements(self):
        """Validate that required fields are present based on source type."""
        if self.type == "reddit":
            if self.subreddits is None:
                raise ValueError("subreddits field is required for Reddit sources")
        elif self.type == "web":
            if self.sites is None:
                raise ValueError("sites field is required for web sources")
        return self


class CollectionRequest(BaseModel):
    """Request for collecting content."""

    sources: List[SourceConfig] = Field(..., description="Sources to collect from")
    deduplicate: bool = Field(default=True, description="Enable deduplication")
    similarity_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for deduplication",
    )
    save_to_storage: bool = Field(
        default=True, description="Save collected content to blob storage"
    )
    output_format: str = Field(default="json", description="Output format (json, csv)")


class CollectionResponse(BaseModel):
    """Response from content collection."""

    collection_id: str = Field(..., description="Unique collection identifier")
    collected_items: List[Dict[str, Any]] = Field(
        ..., description="Collected content items"
    )
    metadata: Dict[str, Any] = Field(..., description="Collection metadata")
    timestamp: str = Field(..., description="Collection timestamp")
    storage_location: Optional[str] = Field(
        default=None, description="Blob storage location if saved"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status (healthy/warning/unhealthy)")
    timestamp: str = Field(..., description="Health check timestamp")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    dependencies: Optional[Dict[str, Any]] = Field(
        default=None, description="Dependency health status"
    )
    config_issues: Optional[List[str]] = Field(
        default=None, description="Configuration issues"
    )
    environment: Optional[str] = Field(default=None, description="Environment name")


class StatusResponse(BaseModel):
    """Service status response."""

    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Status timestamp")
    uptime: float = Field(..., description="Service uptime in seconds")
    last_collection: Optional[str] = Field(
        default=None, description="Last successful collection timestamp"
    )
    stats: Dict[str, Any] = Field(..., description="Service statistics")
    config: Dict[str, Any] = Field(..., description="Service configuration")


class SourceInfo(BaseModel):
    """Information about a content source."""

    type: str = Field(..., description="Source type")
    name: str = Field(..., description="Source name")
    description: str = Field(..., description="Source description")
    status: str = Field(..., description="Source availability status")
    parameters: List[str] = Field(..., description="Required parameters")


class SourcesResponse(BaseModel):
    """Response containing available sources."""

    available_sources: List[SourceInfo] = Field(
        ..., description="Available content sources"
    )

"""Pydantic models for markdown generator API."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class MarkdownRequest(BaseModel):
    """Request model for manual markdown generation."""
    content_items: List[Dict[str, Any]] = Field(
        ...,
        description="List of ranked content items to convert to markdown"
    )
    output_dir: Optional[str] = Field(
        None,
        description="Custom output directory (optional)"
    )
    auto_notify: bool = Field(
        True,
        description="Whether to automatically notify downstream services"
    )
    template_style: Optional[str] = Field(
        None,
        description="Markdown template style (jekyll, hugo, etc.)"
    )


class ContentItem(BaseModel):
    """Model for a single content item."""
    title: str
    clean_title: Optional[str] = None
    source_url: str
    content_type: str = "article"
    ai_summary: str
    topics: List[str] = []
    sentiment: str = "neutral"
    final_score: float = Field(ge=0.0, le=1.0)
    engagement_score: float = Field(ge=0.0, le=1.0)
    source_metadata: Dict[str, Any] = {}
    published_at: Optional[str] = None


class MarkdownFile(BaseModel):
    """Model for generated markdown file information."""
    file: str
    slug: str
    title: str
    score: float
    blob_name: Optional[str] = None


class GenerationResult(BaseModel):
    """Model for markdown generation result."""
    status: str
    files_generated: int
    manifest_file: Optional[str] = None
    blob_manifest: Optional[str] = None
    output_directory: Optional[str] = None
    timestamp: str
    markdown_files: List[MarkdownFile] = []


class ServiceStatus(BaseModel):
    """Model for service status response."""
    service: str
    status: str
    version: Optional[str] = None
    content_watcher: Dict[str, Any]
    blob_storage: Dict[str, Any]
    file_statistics: Optional[Dict[str, Any]] = None
    timestamp: str
    configuration: Optional[Dict[str, Any]] = None


class HealthCheckResponse(BaseModel):
    """Model for health check response."""
    status: str
    timestamp: str
    service: str
    blob_storage_healthy: bool


class WatcherNotification(BaseModel):
    """Model for content watcher notifications."""
    event: str
    timestamp: str
    result: Dict[str, Any]

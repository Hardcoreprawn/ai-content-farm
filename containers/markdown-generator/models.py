"""
Pydantic models for markdown-generator container.

This module defines the data models used throughout the markdown generation
pipeline, including input validation, processing state, and output formats.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "ProcessingStatus",
    "ArticleMetadata",
    "MarkdownGenerationResult",
    "MarkdownGenerationRequest",
    "MarkdownGenerationBatchRequest",
    "MarkdownGenerationResponse",
    "HealthCheckResponse",
    "MetricsResponse",
]


class ProcessingStatus(str, Enum):
    """Enumeration of processing states."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ArticleMetadata(BaseModel):
    """Metadata extracted from processed article JSON."""

    title: str = Field(..., description="Article title")
    url: str = Field(
        ..., description="Original article URL"
    )  # Changed from HttpUrl to str for lenient validation
    source: str = Field(..., description="Content source (reddit, rss, etc)")
    author: Optional[str] = Field(None, description="Article author")
    published_date: Optional[datetime] = Field(None, description="Publication date")
    tags: List[str] = Field(default_factory=list, description="Article tags")
    category: Optional[str] = Field(None, description="Content category")

    # Stock image fields
    hero_image: Optional[str] = Field(None, description="Hero image URL (1080px)")
    thumbnail: Optional[str] = Field(None, description="Thumbnail URL (400px)")
    image_alt: Optional[str] = Field(None, description="Image alt text/description")
    image_credit: Optional[str] = Field(
        None, description="Photographer credit and link"
    )
    image_color: Optional[str] = Field(None, description="Dominant image color (hex)")

    @field_validator("tags", mode="before")
    @classmethod
    def ensure_list(cls, v: Any) -> List[str]:
        """Ensure tags is always a list."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return list(v)


class MarkdownGenerationRequest(BaseModel):
    """Request model for markdown generation."""

    blob_name: str = Field(
        ..., description="Name of the processed JSON blob to convert"
    )
    input_container: str = Field(
        default="processed-content",
        description="Source container for JSON files",
    )
    output_container: str = Field(
        default="markdown-content",
        description="Destination container for markdown files",
    )
    template_name: str = Field(
        default="default.md.j2",
        description=(
            "Jinja2 template to use " "(default.md.j2, with-toc.md.j2, minimal.md.j2)"
        ),
    )
    overwrite: bool = Field(
        default=False, description="Overwrite existing markdown files"
    )


class MarkdownGenerationBatchRequest(BaseModel):
    """Request model for batch markdown generation."""

    blob_names: List[str] = Field(
        ..., min_length=1, description="List of blob names to process"
    )
    input_container: str = Field(
        default="processed-content",
        description="Source container for JSON files",
    )
    output_container: str = Field(
        default="markdown-content",
        description="Destination container for markdown files",
    )
    template_name: str = Field(
        default="default.md.j2",
        description=(
            "Jinja2 template to use " "(default.md.j2, with-toc.md.j2, minimal.md.j2)"
        ),
    )
    overwrite: bool = Field(
        default=False, description="Overwrite existing markdown files"
    )


class MarkdownGenerationResult(BaseModel):
    """Result of markdown generation operation."""

    blob_name: str = Field(..., description="Name of processed blob")
    status: ProcessingStatus = Field(..., description="Processing status")
    markdown_blob_name: Optional[str] = Field(
        None, description="Name of generated markdown blob"
    )
    files_created: bool = Field(
        default=False,
        description="Whether a new markdown file was actually created (vs skipped/duplicate)",
    )
    file_created_timestamp: Optional[str] = Field(
        None, description="Timestamp when file was created (ISO-8601)"
    )
    file_hash: Optional[str] = Field(
        None,
        description="SHA256 hash of generated markdown content (for dedup detection)",
    )
    error_message: Optional[str] = Field(None, description="Error details")
    processing_time_ms: Optional[int] = Field(
        None, description="Processing duration in milliseconds"
    )


class MarkdownGenerationResponse(BaseModel):
    """API response for markdown generation."""

    status: str = Field(..., description="Overall operation status")
    message: str = Field(..., description="Human-readable message")
    data: Dict[str, Any] = Field(default_factory=dict, description="Response data")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Response metadata"
    )


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Check timestamp"
    )
    version: str = Field(..., description="Container version")
    storage_connection: bool = Field(..., description="Storage connectivity status")
    queue_connection: bool = Field(..., description="Queue connectivity status")


class MetricsResponse(BaseModel):
    """Metrics and statistics response."""

    total_processed: int = Field(default=0, description="Total articles processed")
    total_failed: int = Field(default=0, description="Total failures")
    average_processing_time_ms: float = Field(
        default=0.0, description="Average processing time"
    )
    uptime_seconds: float = Field(default=0.0, description="Container uptime")
    last_processed: Optional[datetime] = Field(
        None, description="Last processing timestamp"
    )
    rate_limit_status: Optional[Dict[str, Any]] = Field(
        None, description="Unsplash API rate limit status (if stock images enabled)"
    )

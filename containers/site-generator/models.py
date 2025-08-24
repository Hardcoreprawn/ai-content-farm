#!/usr/bin/env python3
"""
Pydantic models for Site Generator API
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class GenerationStatus(str, Enum):
    """Site generation status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NOT_FOUND = "not_found"


class SiteTheme(str, Enum):
    """Available site themes."""

    MODERN = "modern"
    CLASSIC = "classic"
    MINIMAL = "minimal"
    DARK = "dark"


class StandardResponse(BaseModel):
    """Standard API response format."""

    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Human readable message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Response metadata"
    )
    errors: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Error details"
    )


class GenerationRequest(BaseModel):
    """Request to generate a static site."""

    content_source: str = Field(
        default="ranked",
        description="Source of content: ranked, enriched, or specific blob name",
    )
    theme: SiteTheme = Field(default=SiteTheme.MODERN, description="Site theme to use")
    include_analytics: bool = Field(
        default=True, description="Include analytics tracking"
    )
    max_articles: int = Field(default=20, description="Maximum articles to include")
    site_title: Optional[str] = Field(None, description="Custom site title")
    site_description: Optional[str] = Field(None, description="Custom site description")

    @field_validator("max_articles")
    @classmethod
    def validate_max_articles(cls, v):
        if v < 1 or v > 100:
            raise ValueError("max_articles must be between 1 and 100")
        return v


class SiteInfo(BaseModel):
    """Information about a generated site."""

    site_id: str = Field(..., description="Unique site identifier")
    creation_date: datetime = Field(..., description="When the site was created")
    theme: str = Field(..., description="Theme used for the site")
    article_count: int = Field(..., description="Number of articles in the site")
    status: GenerationStatus = Field(..., description="Current generation status")
    preview_url: str = Field(..., description="URL to preview the site")
    blob_path: Optional[str] = Field(None, description="Blob storage path")


class GenerationStatusResponse(BaseModel):
    """Response for generation status requests."""

    site_id: str = Field(..., description="Site identifier")
    status: GenerationStatus = Field(..., description="Current status")
    # Make these optional to support simplified status in tests/mocks
    progress_percentage: Optional[int] = Field(
        default=None, description="Completion percentage"
    )
    current_step: Optional[str] = Field(
        default=None, description="Current processing step"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    completion_time: Optional[datetime] = Field(
        None, description="When generation completed"
    )
    # Fields used by API tests for simpler status reporting
    started_at: Optional[str] = Field(
        None, description="When generation started (RFC3339)"
    )
    progress: Optional[str] = Field(None, description="Freeform progress message")


class ContentItem(BaseModel):
    """Individual content item for site generation."""

    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Original URL")
    summary: str = Field(..., description="Article summary")
    content: Optional[str] = Field(None, description="Full article content")
    author: Optional[str] = Field(None, description="Article author")
    published_date: Optional[datetime] = Field(None, description="Publication date")
    tags: List[str] = Field(default_factory=list, description="Article tags")
    score: Optional[float] = Field(None, description="Content ranking score")
    source: str = Field(..., description="Content source (reddit, hackernews, etc.)")


class SiteMetadata(BaseModel):
    """Metadata for generated site."""

    title: str = Field(..., description="Site title")
    description: str = Field(..., description="Site description")
    generation_date: datetime = Field(..., description="When site was generated")
    theme: str = Field(..., description="Theme used")
    total_articles: int = Field(..., description="Total number of articles")
    content_sources: List[str] = Field(..., description="Content sources included")
    version: str = Field(default="1.0.0", description="Site generator version")

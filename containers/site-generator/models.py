"""
Site Generator Models

Pydantic models for request/response handling in the static site generator.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    """Request model for content generation."""

    source: str = Field(default="manual", description="Source of generation request")
    batch_size: int = Field(
        default=10, ge=1, le=100, description="Number of items to process"
    )
    theme: Optional[str] = Field(default=None, description="Site theme to use")
    force_regenerate: bool = Field(
        default=False, description="Force regeneration of existing content"
    )


class GenerationResponse(BaseModel):
    """Response model for generation operations."""

    generator_id: str
    operation_type: str
    files_generated: int
    pages_generated: Optional[int] = None
    processing_time: float
    output_location: str
    generated_files: List[str]
    errors: List[str] = []


class MarkdownFile(BaseModel):
    """Model for generated markdown file metadata."""

    filename: str
    title: str
    slug: str
    word_count: int
    generated_at: datetime
    source_article_id: str


class SiteMetrics(BaseModel):
    """Site generation metrics."""

    total_articles: int
    total_pages: int
    total_size_bytes: int
    last_build_time: float
    build_timestamp: datetime


class SiteStatus(BaseModel):
    """Current site generator status."""

    generator_id: str
    status: str  # idle, generating, error
    current_theme: str
    markdown_files_count: int
    site_metrics: Optional[SiteMetrics] = None
    last_generation: Optional[datetime] = None
    error_message: Optional[str] = None


class ArticleMetadata(BaseModel):
    """Processed article metadata for site generation."""

    topic_id: str
    title: str
    slug: str
    word_count: int
    quality_score: float
    cost: float
    source: str
    original_url: str
    generated_at: datetime
    content: str


class SiteManifest(BaseModel):
    """Complete site manifest for deployment."""

    site_id: str
    version: str
    build_timestamp: datetime
    theme: str
    total_files: int
    articles: List[ArticleMetadata]
    index_pages: List[str]
    static_assets: List[str]
    deployment_url: Optional[str] = None

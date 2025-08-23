"""
Pydantic models for content enricher API.

Request and response validation models for the content enricher service.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ContentItem(BaseModel):
    """Content item to be enriched."""

    id: str = Field(
        ..., description="Unique identifier for the content item", min_length=1
    )
    title: str = Field(..., description="Original title of the content", min_length=1)
    clean_title: str = Field(
        ..., description="Cleaned title without special characters", min_length=1
    )
    normalized_score: Optional[float] = Field(
        0.0, ge=0.0, le=1.0, description="Normalized score (0-1)"
    )
    engagement_score: Optional[float] = Field(
        0.0, ge=0.0, le=1.0, description="Engagement score (0-1)"
    )
    source_url: Optional[str] = Field(None, description="URL to the original content")
    published_at: Optional[str] = Field(
        None, description="Publication timestamp in ISO format"
    )
    content_type: Optional[str] = Field(
        "text", description="Type of content (text, link, image)"
    )
    source_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Source-specific metadata"
    )


class EnrichmentOptions(BaseModel):
    """Options for content enrichment."""

    include_summary: bool = Field(
        True, description="Whether to generate content summaries"
    )
    max_summary_length: int = Field(
        200, ge=50, le=1000, description="Maximum length of generated summaries"
    )
    classify_topics: bool = Field(
        True, description="Whether to classify content topics"
    )
    analyze_sentiment: bool = Field(
        True, description="Whether to analyze content sentiment"
    )
    calculate_trends: bool = Field(
        True, description="Whether to calculate trend scores"
    )


class EnrichmentRequest(BaseModel):
    """Request to enrich content items."""

    items: List[ContentItem] = Field(..., description="List of content items to enrich")
    options: Optional[EnrichmentOptions] = Field(
        default=None, description="Enrichment options"
    )


class EnrichmentResponse(BaseModel):
    """Response from content enrichment."""

    enriched_items: List[Dict[str, Any]] = Field(
        ..., description="List of enriched content items"
    )
    metadata: Dict[str, Any] = Field(..., description="Processing metadata")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    azure_connectivity: bool = Field(..., description="Azure connectivity status")
    openai_available: bool = Field(..., description="OpenAI API availability")

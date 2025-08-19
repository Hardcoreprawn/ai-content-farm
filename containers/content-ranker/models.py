"""
Pydantic models for Content Ranker API requests and responses.

Defines all data models used in the content ranking service.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class ContentItem(BaseModel):
    """Enriched content item to be ranked."""

    id: str = Field(..., description="Unique identifier for the content item")
    title: str = Field(..., description="Content title")
    clean_title: Optional[str] = Field(None, description="Cleaned title")
    normalized_score: Optional[float] = Field(
        0.0, ge=0.0, le=1.0, description="Normalized engagement score")
    engagement_score: Optional[float] = Field(
        0.0, ge=0.0, le=1.0, description="Engagement score")
    published_at: Optional[str] = Field(
        None, description="Publication timestamp")
    content_type: Optional[str] = Field("text", description="Content type")

    # Enrichment data
    topic_classification: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Topic classification results")
    sentiment_analysis: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Sentiment analysis results")
    trend_analysis: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Trend analysis results")
    source_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Source metadata")


class RankingOptions(BaseModel):
    """Options for content ranking."""

    weights: Optional[Dict[str, float]] = Field(
        None,
        description="Custom weights for ranking factors (engagement, recency, topic_relevance)"
    )
    target_topics: Optional[List[str]] = Field(
        None,
        description="Target topics for relevance scoring"
    )
    limit: Optional[int] = Field(
        None,
        ge=1,
        le=1000,
        description="Maximum number of items to return"
    )


class RankingRequest(BaseModel):
    """Request to rank content items."""

    items: List[ContentItem] = Field(...,
                                     description="List of enriched content items to rank")
    options: Optional[RankingOptions] = Field(
        default=None, description="Ranking options")


class RankedItem(BaseModel):
    """Content item with ranking scores."""

    # Original content (dynamic fields)
    # We'll use Dict[str, Any] to allow flexible content structure


class RankingResponse(BaseModel):
    """Response from content ranking."""

    ranked_items: List[Dict[str, Any]
                       ] = Field(..., description="Ranked content items with scores")
    metadata: Dict[str, Any] = Field(..., description="Ranking metadata")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    azure_connectivity: Optional[bool] = Field(
        None, description="Azure connectivity status")


class BatchRankingRequest(BaseModel):
    """Request for batch ranking of enriched content."""

    weights: Optional[Dict[str, float]] = Field(
        None,
        description="Custom weights for ranking factors"
    )
    target_topics: Optional[List[str]] = Field(
        None,
        description="Target topics for relevance scoring"
    )
    limit: Optional[int] = Field(
        None,
        ge=1,
        le=1000,
        description="Maximum number of items to return"
    )


class SpecificRankingRequest(BaseModel):
    """Request to rank specific content items."""

    content_items: List[Dict[str, Any]] = Field(
        ...,
        description="List of content items to rank"
    )
    weights: Optional[Dict[str, float]] = Field(
        None,
        description="Custom weights for ranking factors"
    )
    target_topics: Optional[List[str]] = Field(
        None,
        description="Target topics for relevance scoring"
    )
    limit: Optional[int] = Field(
        None,
        ge=1,
        le=1000,
        description="Maximum number of items to return"
    )

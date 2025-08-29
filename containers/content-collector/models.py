"""
Content Womble API Models

Pydantic models for request/response validation and data structures.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SourceConfig(BaseModel):
    """Configuration for a content source."""

    type: str = Field(..., description="Type of source (reddit, web, etc.)")
    subreddits: Optional[List[str]] = Field(
        None, description="List of subreddits for reddit sources"
    )
    websites: Optional[List[str]] = Field(
        None, description="List of websites for web sources"
    )
    limit: int = Field(10, description="Maximum number of items to collect")
    criteria: Dict[str, Any] = Field(
        default_factory=dict, description="Additional filtering criteria"
    )


class DiscoveryRequest(BaseModel):
    """Request model for content discovery endpoint."""

    sources: List[SourceConfig] = Field(..., description="List of sources to analyze")
    keywords: Optional[List[str]] = Field(
        None, description="Keywords to focus analysis on"
    )
    analysis_depth: str = Field(
        "standard", description="Depth of analysis: basic, standard, detailed"
    )
    include_trending: bool = Field(True, description="Include trending topic analysis")
    include_recommendations: bool = Field(
        True, description="Include research recommendations"
    )


class LegacyCollectionRequest(BaseModel):
    """Legacy request format for backward compatibility."""

    sources: List[Dict[str, Any]]
    deduplicate: bool = True
    similarity_threshold: float = 0.8
    save_to_storage: bool = True


class CollectionRequest(BaseModel):
    """Standardized request model for content collection."""

    sources: List[SourceConfig] = Field(
        ..., description="List of sources to collect from"
    )
    deduplicate: bool = Field(True, description="Remove duplicate content")
    similarity_threshold: float = Field(
        0.8, description="Similarity threshold for deduplication (0.0-1.0)"
    )
    save_to_storage: bool = Field(
        True, description="Save collected content to blob storage"
    )


class CollectionResult(BaseModel):
    """Result model for content collection operations."""

    sources_processed: int = Field(..., description="Number of sources processed")
    total_items_collected: int = Field(..., description="Total items found")
    items_saved: int = Field(..., description="Number of items successfully saved")
    storage_location: str = Field(..., description="Where the content was stored")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    summary: str = Field(..., description="Human-readable summary of collection")


class ServiceStatus(BaseModel):
    """Service status information."""

    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    status: str = Field(..., description="Current status")
    storage_healthy: bool = Field(..., description="Storage connectivity status")
    reddit_healthy: bool = Field(..., description="Reddit API connectivity status")
    last_collection: Optional[str] = Field(
        None, description="Last successful collection timestamp"
    )
    active_processes: int = Field(
        ..., description="Number of active collection processes"
    )


class TrendingTopic(BaseModel):
    """A trending topic discovered from content analysis."""

    topic: str = Field(..., description="The trending topic or keyword")
    mentions: int = Field(..., description="Number of mentions found")
    growth_rate: float = Field(..., description="Rate of growth in mentions")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)")
    related_keywords: List[str] = Field(..., description="Related keywords and phrases")
    sample_content: List[str] = Field(
        ..., description="Sample content mentioning this topic"
    )
    source_breakdown: Dict[str, int] = Field(..., description="Mentions per source")
    sentiment_score: Optional[float] = Field(
        None, description="Average sentiment score"
    )
    engagement_metrics: Dict[str, float] = Field(
        default_factory=dict, description="Engagement data"
    )


class ResearchRecommendation(BaseModel):
    """Research recommendation based on trending topics."""

    topic: TrendingTopic = Field(
        ..., description="The trending topic this recommendation is for"
    )
    research_potential: float = Field(
        ..., description="Potential value score (0.0-1.0)"
    )
    recommended_approach: str = Field(..., description="Suggested research approach")
    key_questions: List[str] = Field(..., description="Key questions to investigate")
    suggested_sources: List[str] = Field(
        ..., description="Recommended sources for research"
    )
    estimated_depth: str = Field(..., description="Estimated research depth needed")


class DiscoveryResult(BaseModel):
    """Result model for content discovery operations."""

    trending_topics: List[TrendingTopic] = Field(
        ..., description="Discovered trending topics"
    )
    research_recommendations: List[ResearchRecommendation] = Field(
        ..., description="Research suggestions"
    )
    analysis_summary: str = Field(..., description="Summary of discovery analysis")
    sources_analyzed: int = Field(..., description="Number of sources analyzed")
    total_content_analyzed: int = Field(
        ..., description="Total pieces of content analyzed"
    )
    analysis_time_ms: int = Field(..., description="Analysis processing time")
    keywords_focus: List[str] = Field(
        default_factory=list, description="Keywords that guided the analysis"
    )
    confidence_score: float = Field(..., description="Overall confidence in results")

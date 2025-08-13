"""
Content Ranking Data Models

This module defines data structures and interfaces for content ranking,
following the pure functions architecture.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


@dataclass
class ContentItem:
    """Standardized content item for ranking"""
    title: str
    content: str
    url: str
    source: str  # "reddit", "rss", "api", etc.
    source_id: str  # Original ID from source
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    score: Optional[int] = None
    comments_count: Optional[int] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize default values"""
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class RankingRequest:
    """Request parameters for content ranking"""
    content_data: Dict[str, Any]  # Raw content data (blob data or direct content)
    ranking_config: Optional[Dict[str, Any]] = None
    input_format: str = "blob"  # "blob" or "direct"
    
    def __post_init__(self):
        if self.ranking_config is None:
            self.ranking_config = {}


@dataclass 
class RankingResult:
    """Result from content ranking operation"""
    request: RankingRequest
    ranked_topics: List[Dict[str, Any]]
    success: bool
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# Pydantic models for HTTP API
class ContentRankingRequest(BaseModel):
    """HTTP request model for content ranking"""
    input_blob_path: Optional[str] = Field(None, description="Path to input blob in format 'container/blob-name'")
    output_blob_path: Optional[str] = Field(None, description="Path to output blob in format 'container/blob-name'")
    content_data: Optional[Dict[str, Any]] = Field(None, description="Direct content data (alternative to blob path)")
    ranking_config: Optional[Dict[str, Any]] = Field(None, description="Custom ranking configuration")
    
    class Config:
        schema_extra = {
            "example": {
                "input_blob_path": "raw-data/topics_20250813.json",
                "output_blob_path": "ranked-data/ranked_topics_20250813.json",
                "ranking_config": {
                    "weights": {
                        "engagement": 0.4,
                        "freshness": 0.2,
                        "monetization": 0.3,
                        "seo_potential": 0.1
                    },
                    "min_score_threshold": 100,
                    "min_comments_threshold": 10
                }
            }
        }


class JobStatusRequest(BaseModel):
    """Request model for job status check"""
    action: str = Field(..., description="Action to perform (status)")
    job_id: str = Field(..., description="Job ID to check")


class JobResponse(BaseModel):
    """Response model for job creation"""
    job_id: str
    status: str
    message: str
    timestamp: str
    request_type: str
    status_check_example: Dict[str, Any]


class JobStatusResponse(BaseModel):
    """Response model for job status"""
    job_id: str
    status: str
    updated_at: str
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    results: Optional[Dict[str, Any]] = None


class ContentRankingInterface(ABC):
    """Abstract interface for content ranking implementations"""

    @abstractmethod
    def rank_content(self, request: RankingRequest) -> RankingResult:
        """
        Rank content based on request parameters.

        This is a pure function that:
        - Takes ranking parameters and content data
        - Returns ranked content with scores
        - Does not perform any side effects (logging, storage)
        """
        pass

    @abstractmethod
    def validate_request(self, request: RankingRequest) -> tuple[bool, Optional[str]]:
        """
        Validate if the request can be processed.

        Returns:
            (is_valid, error_message)
        """
        pass


def normalize_topic_data(raw_data: Dict[str, Any], source: str = "unknown") -> ContentItem:
    """
    Pure function to normalize raw topic data into ContentItem.

    Args:
        raw_data: Raw topic data from any source
        source: Source identifier ("reddit", "blob", etc.)

    Returns:
        Normalized ContentItem
    """
    return ContentItem(
        title=str(raw_data.get("title", "")).strip(),
        content=str(raw_data.get("content", raw_data.get("selftext", ""))).strip(),
        url=str(raw_data.get("url", raw_data.get("external_url", ""))).strip(),
        source=source,
        source_id=str(raw_data.get("id", raw_data.get("reddit_id", ""))),
        author=raw_data.get("author"),
        created_at=raw_data.get("created_at"),
        score=raw_data.get("score"),
        comments_count=raw_data.get("comments_count", raw_data.get("num_comments")),
        tags=raw_data.get("tags", []),
        metadata=raw_data.get("metadata", {})
    )
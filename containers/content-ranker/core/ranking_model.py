"""
Content Ranker Data Models

Request/Response models for the ContentRanker Container Apps service.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class RankingRequest(BaseModel):
    """HTTP request model for content ranking"""
    source: str = Field(..., description="Content source (reddit, etc.)")
    topics: Optional[List[Dict[str, Any]]] = Field(None, description="Direct topic data (alternative to blob_path)")
    blob_path: Optional[str] = Field(None, description="Blob storage path to topic data")
    config: Optional[Dict[str, Any]] = Field(None, description="Custom ranking configuration")
    output_path: Optional[str] = Field(None, description="Optional output blob path")
    
    class Config:
        json_schema_extra = {
            "example": {
                "source": "reddit",
                "blob_path": "hot-topics/20250813_reddit_technology.json",
                "config": {
                    "engagement_weight": 0.4,
                    "monetization_weight": 0.3,
                    "recency_weight": 0.2,
                    "title_quality_weight": 0.1,
                    "minimum_score_threshold": 0.1,
                    "max_topics_output": 50
                }
            }
        }


class JobResponse(BaseModel):
    """Response for job creation"""
    job_id: str
    status: str
    message: str
    timestamp: str
    source: str
    topics_count: Optional[int] = None
    estimated_completion: Optional[str] = None
    status_check_example: Dict[str, Any]


class JobStatusRequest(BaseModel):
    """Request for checking job status"""
    action: str = Field(..., description="Action type (must be 'status')")
    job_id: str = Field(..., description="Job ID to check")


class RankedTopic(BaseModel):
    """Individual ranked topic with scores"""
    title: str
    content: str
    source_url: str
    score: int
    author: str
    created_utc: str
    num_comments: int
    subreddit: str
    
    # Ranking scores
    engagement_score: float
    monetization_score: float
    recency_score: float
    title_quality_score: float
    final_score: float
    ranking_position: int


class RankingResults(BaseModel):
    """Complete ranking results"""
    total_topics: int
    ranked_topics: List[RankedTopic]
    processing_time_seconds: float
    timestamp: str
    config_used: Dict[str, Any]


class JobStatusResponse(BaseModel):
    """Response for job status check"""
    job_id: str
    status: str  # queued, processing, completed, failed
    updated_at: str
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    results: Optional[RankingResults] = None

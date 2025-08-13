"""
Content Enricher Data Models

Request/Response models for the ContentEnricher Container Apps service.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class EnhancementRequest(BaseModel):
    """HTTP request model for content enrichment"""
    source: str = Field(..., description="Content source (reddit, etc.)")
    topics: Optional[List[Dict[str, Any]]] = Field(None, description="Direct topic data (alternative to blob_path)")
    blob_path: Optional[str] = Field(None, description="Blob storage path to topic data")
    config: Optional[Dict[str, Any]] = Field(None, description="Custom enhancement configuration")
    output_path: Optional[str] = Field(None, description="Optional output blob path")
    
    class Config:
        json_schema_extra = {
            "example": {
                "source": "reddit",
                "blob_path": "ranked-content/20250813_reddit_technology.json",
                "config": {
                    "openai_model": "gpt-3.5-turbo",
                    "include_sentiment": True,
                    "include_tags": True,
                    "include_insights": True,
                    "max_tokens": 500
                }
            }
        }


class EnhancedTopic(BaseModel):
    """Individual enriched topic with AI enhancements"""
    title: str
    content: Optional[str] = None
    source_url: Optional[str] = None
    author: Optional[str] = None
    created_utc: Optional[str] = None
    score: Optional[int] = None
    num_comments: Optional[int] = None
    subreddit: Optional[str] = None
    
    # Original ranking data if available
    ranking_score: Optional[float] = None
    ranking_position: Optional[int] = None
    
    # AI Enhancement data
    ai_summary: Optional[str] = None
    key_insights: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    sentiment: Optional[str] = None
    enhancement_metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_time_seconds: float = 0.0
    enhancement_success: bool = True
    enhancement_error: Optional[str] = None


class EnhancementResult(BaseModel):
    """Complete enhancement results"""
    total_topics: int
    enhanced_topics: List[EnhancedTopic]
    processing_time_seconds: float
    timestamp: str
    enhancement_statistics: Dict[str, Any]
    config_used: Dict[str, Any]


class JobResponse(BaseModel):
    """Response for job creation"""
    job_id: str
    status: str
    message: str
    timestamp: str
    source: str
    topics_count: Optional[int] = None
    estimated_completion: Optional[str] = None
    status_check_url: Optional[str] = None


class JobStatusRequest(BaseModel):
    """Request for checking job status"""
    job_id: str = Field(..., description="Job ID to check")


class JobStatusResponse(BaseModel):
    """Response for job status check"""
    job_id: str
    status: str  # queued, processing, completed, failed
    updated_at: str
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    results: Optional[EnhancementResult] = None


class JobResultRequest(BaseModel):
    """Request for getting job results"""
    job_id: str = Field(..., description="Job ID to get results for")


class JobResultResponse(BaseModel):
    """Response for job results"""
    job_id: str
    status: str
    results: Optional[EnhancementResult] = None
    error: Optional[str] = None
    generated_at: str
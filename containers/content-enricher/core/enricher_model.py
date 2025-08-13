"""
Content Enricher Data Models

Request/Response models for the ContentEnricher Container Apps service.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class EnrichmentRequest(BaseModel):
    """HTTP request model for content enrichment"""
    source: str = Field(..., description="Content source (reddit, etc.)")
    topics: Optional[List[Dict[str, Any]]] = Field(None, description="Direct topic data")
    blob_path: Optional[str] = Field(None, description="Blob storage path to topic data")
    config: Optional[Dict[str, Any]] = Field(None, description="Custom enrichment configuration")
    output_path: Optional[str] = Field(None, description="Optional output blob path")
    
    class Config:
        json_schema_extra = {
            "example": {
                "source": "reddit",
                "topics": [
                    {
                        "title": "AI breakthrough in natural language processing",
                        "content": "Researchers have developed a new model...",
                        "score": 1500,
                        "num_comments": 250,
                        "created_utc": "2024-08-13T10:00:00Z"
                    }
                ],
                "config": {
                    "enable_ai_summary": True,
                    "enable_sentiment_analysis": True,
                    "enable_categorization": True,
                    "enable_key_phrases": True,
                    "max_summary_length": 300
                }
            }
        }


class EnrichedTopic(BaseModel):
    """Enriched topic with AI-generated content"""
    # Original fields
    title: str
    content: str
    score: Optional[int] = None
    num_comments: Optional[int] = None
    created_utc: Optional[str] = None
    url: Optional[str] = None
    author: Optional[str] = None
    
    # Enrichment fields
    ai_summary: str = Field(..., description="AI-generated summary")
    category: str = Field(..., description="Content category")
    sentiment: str = Field(..., description="Sentiment analysis result")
    key_phrases: List[str] = Field(..., description="Extracted key phrases")
    reading_time: str = Field(..., description="Estimated reading time")
    quality_score: float = Field(..., description="Content quality score (0-1)")
    enrichment_timestamp: str = Field(..., description="When enrichment was performed")
    ai_model_used: Optional[str] = Field(None, description="AI model used for enrichment")


class EnrichmentJobResponse(BaseModel):
    """Response for enrichment job creation"""
    job_id: str
    status: str
    message: str
    timestamp: str
    source: str
    topics_count: Optional[int] = None
    estimated_completion: Optional[str] = None


class EnrichmentJobStatusRequest(BaseModel):
    """Request for checking enrichment job status"""
    action: str = Field(..., description="Action type (must be 'status')")
    job_id: str = Field(..., description="Job ID to check")


class EnrichmentJobStatusResponse(BaseModel):
    """Response for enrichment job status check"""
    job_id: str
    status: str  # queued, processing, completed, failed
    updated_at: str
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    results: Optional[Dict[str, Any]] = None


class EnrichmentConfig(BaseModel):
    """Configuration for content enrichment"""
    enable_ai_summary: bool = True
    enable_sentiment_analysis: bool = True
    enable_categorization: bool = True
    enable_key_phrases: bool = True
    max_summary_length: int = 300
    ai_model: str = "gpt-3.5-turbo"
    quality_scoring_enabled: bool = True
    reading_time_calculation: bool = True
    
    # Category mapping
    category_mapping: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "Technology": ["AI", "machine learning", "programming", "tech", "software"],
            "Business": ["startup", "finance", "economy", "market", "investment"],
            "Science": ["research", "study", "discovery", "scientific", "analysis"],
            "Entertainment": ["gaming", "movie", "music", "sports", "culture"],
            "General": []  # Fallback category
        }
    )
    
    # Sentiment thresholds
    sentiment_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "positive": 0.1,
            "negative": -0.1
        }
    )


class EnrichmentResult(BaseModel):
    """Result of enrichment processing"""
    source: str
    total_topics: int
    total_enriched: int
    enriched_topics: List[EnrichedTopic]
    processing_time: float
    ai_model_used: str
    config_used: EnrichmentConfig
    enrichment_timestamp: str
    errors: List[str] = Field(default_factory=list)
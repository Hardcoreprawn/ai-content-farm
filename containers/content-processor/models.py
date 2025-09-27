"""
Core data models for content processor.

Clean, functional models using Pydantic for the wake-up work queue pattern.
Focus on immutability and type safety for Azure Container Apps scaling.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class WakeUpRequest(BaseModel):
    """Request model for wake-up endpoint - what collector sends."""

    source: str = Field(
        ..., description="Source triggering wake-up (e.g., 'collector')"
    )
    batch_size: Optional[int] = Field(10, description="Max topics to process")
    priority_threshold: Optional[float] = Field(
        0.5, description="Minimum priority score"
    )
    processing_options: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional processing parameters"
    )
    debug_bypass: Optional[bool] = Field(
        False,
        description="Bypass all filtering for diagnostic purposes - opens the taps!",
    )


class ProcessBatchRequest(BaseModel):
    """Request model for manual batch processing."""

    topic_ids: List[str] = Field(..., description="Specific topic IDs to process")
    force_reprocess: Optional[bool] = Field(
        False, description="Reprocess even if complete"
    )
    processing_options: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Processing parameters"
    )


class TopicMetadata(BaseModel):
    """Immutable topic metadata from collector."""

    topic_id: str
    title: str
    source: str
    collected_at: datetime
    priority_score: float
    subreddit: Optional[str] = None
    url: Optional[str] = None
    upvotes: Optional[int] = None
    comments: Optional[int] = None


class ProcessingAttempt(BaseModel):
    """Single processing attempt with cost tracking."""

    attempt_id: str = Field(default_factory=lambda: str(uuid4()))
    processor_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str  # "processing", "completed", "failed"

    # Cost tracking
    openai_tokens_used: int = 0
    openai_cost_usd: float = 0.0
    processing_time_seconds: float = 0.0

    # Quality metrics
    quality_score: Optional[float] = None
    word_count: Optional[int] = None

    # Results
    research_sources: List[str] = Field(default_factory=list)
    article_content: Optional[str] = None
    error_message: Optional[str] = None


class TopicState(BaseModel):
    """Complete state of a topic through processing pipeline."""

    metadata: TopicMetadata
    status: str  # "pending", "processing", "completed", "failed"

    # Processing history
    attempts: List[ProcessingAttempt] = Field(default_factory=list)
    current_lease: Optional[str] = None  # processor_id holding lease
    lease_expires_at: Optional[datetime] = None

    # Cumulative metrics
    total_cost_usd: float = 0.0
    total_processing_time: float = 0.0
    best_quality_score: float = 0.0

    # Final results
    final_article: Optional[str] = None
    published_at: Optional[datetime] = None


class ProcessingResult(BaseModel):
    """Result of processing operation - functional return type."""

    success: bool
    topics_processed: int
    articles_generated: int
    total_cost: float
    processing_time: float

    # Detailed results
    completed_topics: List[str] = Field(default_factory=list)
    failed_topics: List[str] = Field(default_factory=list)
    error_messages: List[str] = Field(default_factory=list)


class ProcessorStatus(BaseModel):
    """Current processor status and metrics."""

    processor_id: str
    status: str  # "idle", "processing", "error"

    # Current operation
    current_topics: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None

    # Session metrics
    session_topics_processed: int = 0
    session_cost: float = 0.0
    session_processing_time: float = 0.0

    # System health
    azure_openai_available: bool = True
    blob_storage_available: bool = True
    last_health_check: datetime


class WakeUpResponse(BaseModel):
    """Response data for wake-up endpoint."""

    processor_id: str
    topics_found: int
    work_completed: List[Dict[str, Any]]
    total_processed: int
    total_cost: float
    processing_time_seconds: float
    next_wake_up_recommended: Optional[datetime] = None

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SourceData(BaseModel):
    """Source information for content generation"""

    name: str
    url: str
    title: str
    summary: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RankedTopic(BaseModel):
    """Ranked topic from content ranker"""

    topic: str
    sources: List[SourceData]
    rank: int
    ai_score: float
    sentiment: str
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GenerationRequest(BaseModel):
    """Request for content generation"""

    topics: List[RankedTopic]
    content_type: Literal["tldr", "blog", "deepdive"] = "tldr"
    # analytical, casual, expert, skeptical, enthusiast
    writer_personality: str = "professional"
    max_words: Optional[int] = None
    verify_sources: bool = True
    focus: Optional[str] = None


class GeneratedContent(BaseModel):
    """Generated content output"""

    topic: str
    content_type: str
    title: str
    content: str
    word_count: int
    tags: List[str]
    sources: List[SourceData]
    writer_personality: str
    verification_status: str = "pending"  # verified, unverified, failed
    fact_check_notes: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    generation_time: datetime
    ai_model: str
    quality_score: Optional[float] = None


class BatchGenerationRequest(BaseModel):
    """Batch generation request"""

    batch_id: str
    ranked_topics: List[RankedTopic]
    generation_config: Dict[str, Any] = Field(default_factory=dict)


class BatchGenerationResponse(BaseModel):
    """Batch generation response"""

    batch_id: str
    generated_content: List[GeneratedContent]
    total_articles: int
    generation_time: datetime
    stats: Dict[str, Any] = Field(default_factory=dict)


class GenerationStatus(BaseModel):
    """Generation status tracking"""

    batch_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress: float = 0.0
    total_topics: int = 0
    completed_topics: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = "healthy"
    service: str = "content-generator"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StatusResponse(BaseModel):
    """Service status response"""

    service: str = "content-generator"
    status: str = "operational"
    active_generations: int = 0
    total_generated: int = 0
    uptime: str
    blob_storage: str = "connected"
    ai_services: Dict[str, str] = Field(default_factory=dict)

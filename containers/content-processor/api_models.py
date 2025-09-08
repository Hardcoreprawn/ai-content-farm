"""
API models for Content Processor service.

Pydantic models for request/response validation.
"""

from typing import Any, Dict

from pydantic import BaseModel


class ProcessingRequest(BaseModel):
    """Request model for content processing."""

    content: str
    processing_type: str = "general"
    options: Dict[str, Any] = {}

    class Config:
        """Pydantic configuration with examples."""

        schema_extra = {
            "example": {
                "content": "Write an article about sustainable energy solutions",
                "processing_type": "article_generation",
                "options": {
                    "voice": "professional",
                    "target_audience": "general",
                    "max_length": 1000,
                },
            }
        }


class ProcessingResult(BaseModel):
    """Response model for processed content."""

    processed_content: str
    quality_score: float
    processing_metadata: Dict[str, Any]

    class Config:
        """Pydantic configuration with examples."""

        schema_extra = {
            "example": {
                "processed_content": "# Sustainable Energy Solutions\n\nSustainable energy represents...",
                "quality_score": 0.85,
                "processing_metadata": {
                    "processing_type": "article_generation",
                    "model_used": "gpt-4",
                    "region": "west_europe",
                    "processing_time": 5.2,
                    "estimated_cost": 0.0245,
                    "quality_score": 0.85,
                    "status": "completed",
                },
            }
        }

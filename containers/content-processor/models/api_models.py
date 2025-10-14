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


# NOTE: ProcessingResult removed - was duplicate/unused
# Use models.ProcessingResult for batch processing results

#!/usr/bin/env python3
"""
Content Processor - Pydantic Models

Request and response validation models for the content processor service.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class RedditPost(BaseModel):
    title: str
    score: int
    num_comments: Optional[int] = 0
    created_utc: Optional[int] = 0
    subreddit: Optional[str] = ""
    url: Optional[str] = ""
    selftext: Optional[str] = ""
    id: Optional[str] = ""


class ProcessRequest(BaseModel):
    """
    Flexible processing request that supports multiple input formats.

    Supports both:
    - Legacy format: {source: "reddit", data: [...]}
    - New format: {items: [...], source: "reddit"}
    """

    # Primary fields (new format)
    items: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="List of content items to process (new format)"
    )

    # Legacy fields (backward compatibility)
    source: Optional[str] = Field(
        default=None, description="Data source (e.g., 'reddit') - legacy format"
    )
    data: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="List of posts to process - legacy format"
    )

    # Options (flexible)
    options: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Processing options"
    )

    class Config:
        # Allow extra fields and ignore them for forward compatibility
        extra = "ignore"

    @field_validator("items", "data", mode="before")
    @classmethod
    def validate_items_or_data(cls, v):
        """Ensure we have valid item data."""
        if v is not None and not isinstance(v, list):
            raise ValueError("Items/data must be a list")
        return v

    @model_validator(mode="after")
    def validate_has_items_or_data(self):
        """Ensure we have either items or data field provided."""
        if self.items is None and self.data is None:
            raise ValueError("Either 'items' or 'data' field is required")
        return self

    def get_items(self) -> List[Dict[str, Any]]:
        """Get items from either new format or legacy format."""
        if self.items is not None:
            return self.items
        elif self.data is not None:
            return self.data
        else:
            raise ValueError("Either 'items' or 'data' field is required")

    def get_source(self) -> str:
        """Get source, defaulting to 'unknown' if not specified."""
        if self.source:
            return self.source
        # Try to infer from first item
        items = self.get_items()
        if items and len(items) > 0:
            first_item = items[0]
            if isinstance(first_item, dict):
                return first_item.get("source", "unknown")
        return "unknown"


class ProcessedItem(BaseModel):
    id: str
    title: str
    clean_title: str
    normalized_score: float
    engagement_score: float
    source_url: str
    published_at: str
    content_type: str
    source_metadata: Dict[str, Any]


class ProcessResponse(BaseModel):
    processed_items: List[ProcessedItem]
    metadata: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    service: str
    azure_connectivity: Optional[bool] = None

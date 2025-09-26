"""
Data Contracts for AI Content Farm

Shared Pydantic models ensuring consistent data structures across
all services (collector, processor, site-generator) and storage layers.

Follows schema-first design principle for end-to-end type safety.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ContentSource(str, Enum):
    """Standardized content source types."""

    REDDIT = "reddit"
    RSS = "rss"
    TWITTER = "twitter"
    WEB = "web"


class CollectionItem(BaseModel):
    """
    Standardized collection item contract.

    Used by all services for consistent data handling.
    All fields are immutable after creation for functional processing.
    """

    # Required fields
    id: str
    title: str
    source: ContentSource
    collected_at: datetime

    # Content fields
    url: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None

    # Engagement metrics
    upvotes: Optional[int] = None
    comments: Optional[int] = None
    score: Optional[float] = None

    # Source-specific fields
    subreddit: Optional[str] = None  # Reddit
    author: Optional[str] = None
    category: Optional[str] = None  # RSS

    # Processing metadata
    priority_score: Optional[float] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() + "Z"}


class CollectionMetadata(BaseModel):
    """Collection operation metadata."""

    timestamp: datetime
    collection_id: str
    total_items: int
    sources_processed: int
    processing_time_ms: int
    collector_version: str = "1.0.0"


class CollectionResult(BaseModel):
    """
    Standard collection file format.

    Contract for blob storage between collector and processor.
    """

    metadata: CollectionMetadata
    items: List[CollectionItem]

    # Schema evolution support
    schema_version: str = "2.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProcessingRequest(BaseModel):
    """
    Queue message contract for processing requests.

    Envelope pattern for type-safe queue communication.
    """

    message_id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service_name: str
    operation: str = "process"

    # Payload data
    collection_blob_path: str
    batch_size: int = 10
    priority_threshold: float = 0.5

    # Processing options
    options: Dict[str, Any] = Field(default_factory=dict)


class ProcessedContent(BaseModel):
    """Contract for processed content output."""

    topic_id: str
    original_item: CollectionItem

    # Generated content
    article_title: str
    article_content: str
    summary: str
    keywords: List[str]

    # Processing metadata
    processed_at: datetime
    processing_cost_usd: float
    tokens_used: int
    quality_score: float

    # Schema evolution
    schema_version: str = "2.0"


class DataContractError(Exception):
    """Raised when data doesn't match expected contract."""

    pass


class ContractValidator:
    """Validates data contracts at service boundaries."""

    @staticmethod
    def validate_collection_data(blob_data: Dict) -> CollectionResult:
        """
        Validate collection blob data with migration support.

        Handles schema evolution and malformed data gracefully.
        """
        try:
            # Handle legacy format
            if "schema_version" not in blob_data:
                return ContractValidator._migrate_legacy_collection(blob_data)

            return CollectionResult.parse_obj(blob_data)

        except Exception as e:
            raise DataContractError(f"Invalid collection format: {e}")

    @staticmethod
    def _migrate_legacy_collection(blob_data: Dict) -> CollectionResult:
        """Migrate legacy collection format to current contract."""

        # Extract items, handling string vs dict issues
        items = []
        raw_items = blob_data.get("items", [])

        for i, item_data in enumerate(raw_items):
            try:
                # Skip non-dict items (strings, None, etc.)
                if not isinstance(item_data, dict):
                    continue

                # Create standardized item
                items.append(
                    CollectionItem(
                        id=item_data.get("id", f"legacy_{i}"),
                        title=item_data.get("title", "Untitled"),
                        source=ContentSource(item_data.get("source", "web")),
                        collected_at=datetime.fromisoformat(
                            item_data.get(
                                "collected_at", datetime.utcnow().isoformat()
                            ).replace("Z", "+00:00")
                        ),
                        url=item_data.get("url"),
                        content=item_data.get("content"),
                        upvotes=item_data.get("ups") or item_data.get("upvotes"),
                        comments=item_data.get("num_comments")
                        or item_data.get("comments"),
                        subreddit=item_data.get("subreddit"),
                    )
                )

            except Exception as e:
                # Log but don't fail - continue processing valid items
                print(f"Skipping invalid item {i}: {e}")
                continue

        # Create metadata from available data
        metadata = CollectionMetadata(
            timestamp=datetime.utcnow(),
            collection_id=blob_data.get("collection_id", "unknown"),
            total_items=len(items),
            sources_processed=1,
            processing_time_ms=0,
        )

        return CollectionResult(
            metadata=metadata,
            items=items,
            schema_version="2.0",  # Mark as migrated
        )

    @staticmethod
    def validate_queue_message(message_data: Dict) -> ProcessingRequest:
        """Validate queue message format."""
        try:
            return ProcessingRequest.parse_obj(message_data)
        except Exception as e:
            raise DataContractError(f"Invalid queue message: {e}")

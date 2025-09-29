"""
Extended Data Contracts for AI Content Farm

Enhanced Pydantic models with provenance tracking, extensibility, and safe
forward compatibility. Allows downstream services to ignore irrelevant data
while maintaining rich metadata flow.

Design Principles:
- Required Core Fields: Essential fields that all services need
- Optional Extensions: Source-specific or processing-specific data
- Provenance Tracking: Full audit trail of data transformations
- Forward Compatibility: Safe addition of new fields without breaking changes
- Cost & Performance Tracking: AI usage, processing costs, performance metrics
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ProcessingStage(str, Enum):
    """Pipeline processing stages for provenance tracking."""

    COLLECTION = "collection"
    RANKING = "ranking"
    ENRICHMENT = "enrichment"
    PROCESSING = "processing"
    PUBLISHING = "publishing"


class ProvenanceEntry(BaseModel):
    """
    Single provenance entry tracking one processing step.

    Provides full audit trail of data transformations.
    """

    stage: ProcessingStage
    service_name: str
    service_version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Processing details
    operation: str  # e.g., "reddit_collection", "ai_enhancement", "quality_scoring"
    processing_time_ms: Optional[int] = None

    # AI/Model information (when applicable)
    ai_model: Optional[str] = None  # e.g., "gpt-4o-mini", "claude-3-sonnet"
    ai_endpoint: Optional[str] = None  # e.g., "eastus", "westus2"
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None

    # Quality and confidence metrics
    quality_score: Optional[float] = None  # 0.0 to 1.0
    confidence_score: Optional[float] = None  # 0.0 to 1.0

    # Processing parameters used
    parameters: Dict[str, Any] = Field(default_factory=dict)

    # Error handling
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class SourceMetadata(BaseModel):
    """
    Source-specific metadata that can be extended per source type.

    Allows safe addition of new source types without breaking existing code.
    """

    # Core fields all sources should have
    source_type: str  # e.g., "reddit", "rss", "twitter", "mastodon", "web"
    source_identifier: str  # e.g., subreddit name, RSS URL, Twitter handle
    collected_at: datetime

    # Engagement metrics (optional, varies by source)
    upvotes: Optional[int] = None
    downvotes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    likes: Optional[int] = None
    retweets: Optional[int] = None

    # Source-specific data (extensible)
    reddit_data: Optional[Dict[str, Any]] = None  # subreddit, flair, etc.
    rss_data: Optional[Dict[str, Any]] = None  # feed info, categories
    twitter_data: Optional[Dict[str, Any]] = None  # hashtags, mentions
    mastodon_data: Optional[Dict[str, Any]] = None  # instance, boosts, etc.
    web_data: Optional[Dict[str, Any]] = None  # scraping method, domain

    # Generic extensibility for future sources
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class ContentItem(BaseModel):
    """
    Enhanced content item with full provenance and extensibility.

    Replaces CollectionItem with backward-compatible interface.
    """

    # Required core fields (used by all downstream services)
    id: str
    title: str
    url: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None

    # Source information
    source: SourceMetadata

    # Processing scores (computed during pipeline)
    priority_score: Optional[float] = None  # Ranking priority
    quality_score: Optional[float] = None  # Content quality
    relevance_score: Optional[float] = None  # Topic relevance
    engagement_score: Optional[float] = None  # Social engagement

    # Content analysis (optional, added during processing)
    topics: List[str] = Field(default_factory=list)  # Extracted topics
    keywords: List[str] = Field(default_factory=list)  # SEO keywords
    entities: List[str] = Field(default_factory=list)  # Named entities
    # positive/negative/neutral
    sentiment: Optional[str] = None

    # Processing provenance (full audit trail)
    provenance: List[ProvenanceEntry] = Field(default_factory=list)

    # Forward compatibility
    schema_version: str = "3.0"
    extensions: Dict[str, Any] = Field(default_factory=dict)  # Future extensibility

    @field_validator("source", mode="before")
    @classmethod
    def handle_legacy_source(cls, v):
        """Convert legacy source formats to new SourceMetadata."""
        if isinstance(v, str):
            # Legacy format: just a source type string
            return SourceMetadata(
                source_type=v,
                source_identifier="unknown",
                collected_at=datetime.utcnow(),
            )
        elif isinstance(v, dict) and "source_type" not in v:
            # Legacy CollectionItem format
            return SourceMetadata(
                source_type=v.get("source", "web"),
                source_identifier=v.get("subreddit") or v.get("url", "unknown"),
                collected_at=datetime.utcnow(),
                upvotes=v.get("upvotes"),
                comments=v.get("comments"),
                reddit_data=(
                    {"subreddit": v.get("subreddit")} if v.get("subreddit") else None
                ),
            )
        return v

    def add_provenance(self, entry: ProvenanceEntry):
        """Add a provenance entry to track processing."""
        self.provenance.append(entry)

    def get_total_cost(self) -> float:
        """Calculate total processing cost from provenance."""
        return sum(entry.cost_usd or 0.0 for entry in self.provenance)

    def get_processing_time(self) -> int:
        """Calculate total processing time from provenance."""
        return sum(entry.processing_time_ms or 0 for entry in self.provenance)

    def get_last_stage(self) -> Optional[ProcessingStage]:
        """Get the last processing stage from provenance."""
        return self.provenance[-1].stage if self.provenance else None


class CollectionMetadata(BaseModel):
    """Enhanced collection metadata with provenance and cost tracking."""

    # Core metadata
    timestamp: datetime
    collection_id: str
    total_items: int
    sources_processed: int
    processing_time_ms: int
    collector_version: str = "1.0.0"

    # Collection strategy information
    # e.g., "scheduled", "discovery", "manual"
    collection_strategy: Optional[str] = None
    collection_template: Optional[str] = None  # Template used

    # Aggregate costs and metrics
    total_cost_usd: float = 0.0
    total_tokens_used: int = 0
    average_quality_score: Optional[float] = None

    # Source breakdown
    sources_breakdown: Dict[str, int] = Field(
        default_factory=dict
    )  # source_type -> count

    # Provenance for the collection operation itself
    collection_provenance: List[ProvenanceEntry] = Field(default_factory=list)


class ExtendedCollectionResult(BaseModel):
    """
    Enhanced collection result with full provenance and forward compatibility.

    Replaces CollectionResult with backward-compatible interface.
    """

    metadata: CollectionMetadata
    items: List[ContentItem]

    # Schema evolution support
    schema_version: str = "3.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Processing configuration used
    processing_config: Dict[str, Any] = Field(default_factory=dict)

    # Quality assurance
    validation_results: Dict[str, Any] = Field(default_factory=dict)

    # Forward compatibility
    extensions: Dict[str, Any] = Field(default_factory=dict)

    def add_collection_provenance(self, entry: ProvenanceEntry):
        """Add provenance entry to collection metadata."""
        self.metadata.collection_provenance.append(entry)

    def calculate_aggregate_metrics(self):
        """Calculate and update aggregate metrics from items."""
        if not self.items:
            return

        # Calculate total cost
        self.metadata.total_cost_usd = sum(item.get_total_cost() for item in self.items)

        # Calculate total tokens
        self.metadata.total_tokens_used = sum(
            sum(entry.total_tokens or 0 for entry in item.provenance)
            for item in self.items
        )

        # Calculate average quality score
        quality_scores = [
            item.quality_score for item in self.items if item.quality_score
        ]
        if quality_scores:
            self.metadata.average_quality_score = sum(quality_scores) / len(
                quality_scores
            )

        # Update sources breakdown
        for item in self.items:
            source_type = item.source.source_type
            self.metadata.sources_breakdown[source_type] = (
                self.metadata.sources_breakdown.get(source_type, 0) + 1
            )


class ProcessingRequest(BaseModel):
    """
    Enhanced processing request with extensible parameters.

    Supports new processing types without breaking existing handlers.
    """

    message_id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service_name: str
    operation: str = "process"

    # Core request data
    collection_blob_path: str
    batch_size: int = 10
    priority_threshold: float = 0.5

    # Processing configuration
    # "standard", "high_quality", "fast", etc.
    processing_type: str = "standard"
    ai_models: List[str] = Field(default_factory=lambda: ["gpt-4o-mini"])
    max_cost_usd: Optional[float] = None

    # Extensible options
    options: Dict[str, Any] = Field(default_factory=dict)

    # Source-specific processing hints
    source_specific_config: Dict[str, Any] = Field(default_factory=dict)


class ProcessedContent(BaseModel):
    """Enhanced processed content with full provenance."""

    topic_id: str
    original_item: ContentItem

    # Generated content
    article_title: str
    article_content: str
    summary: str
    keywords: List[str]

    # Processing metadata
    processed_at: datetime
    processing_stage: ProcessingStage = ProcessingStage.PROCESSING

    # Cost and performance
    processing_cost_usd: float
    tokens_used: int
    quality_score: float
    processing_time_ms: int

    # AI model information
    ai_model_used: str
    ai_endpoint: Optional[str] = None

    # Schema evolution
    schema_version: str = "3.0"

    # Forward compatibility
    extensions: Dict[str, Any] = Field(default_factory=dict)


# Backward Compatibility Aliases
# These allow existing code to continue working while migration happens
CollectionItem = ContentItem  # Alias for backward compatibility
CollectionResult = ExtendedCollectionResult  # Alias for backward compatibility


class DataContractError(Exception):
    """Raised when data doesn't match expected contract."""

    pass


class ExtendedContractValidator:
    """
    Enhanced contract validator with migration support and extensibility.

    Provides safe migration from old formats to new schema while
    preserving all data and maintaining backward compatibility.
    """

    @staticmethod
    def validate_collection_data(blob_data: Dict) -> ExtendedCollectionResult:
        """
        Validate and migrate collection data to new format.

        Handles all legacy formats and migrates them safely.
        """
        try:
            # Check schema version
            schema_version = blob_data.get("schema_version", "1.0")

            if schema_version in ["3.0"]:
                # New format - validate directly
                return ExtendedCollectionResult.parse_obj(blob_data)
            else:
                # Legacy format - migrate
                return ExtendedContractValidator._migrate_to_extended_format(blob_data)

        except Exception as e:
            raise DataContractError(f"Invalid collection format: {e}")

    @staticmethod
    def _migrate_to_extended_format(blob_data: Dict) -> ExtendedCollectionResult:
        """Migrate legacy format to extended format."""

        # Extract items with enhanced structure
        items = []
        raw_items = blob_data.get("items", [])

        for i, item_data in enumerate(raw_items):
            try:
                if not isinstance(item_data, dict):
                    continue

                # Check if this item is already in enhanced format
                source_data = item_data.get("source")
                is_enhanced_format = (
                    isinstance(source_data, dict) and "source_type" in source_data
                )

                if is_enhanced_format:
                    # Item is already in enhanced format - validate directly
                    content_item = ContentItem.parse_obj(item_data)
                else:
                    # Item is in legacy format - migrate it

                    # Handle datetime parsing more robustly
                    collected_at_str = item_data.get(
                        "collected_at", datetime.utcnow().isoformat()
                    )

                    # Clean up datetime string - handle various formats
                    if collected_at_str.endswith("Z"):
                        if "+00:00" in collected_at_str:
                            # Remove redundant Z suffix when timezone offset is present
                            collected_at_str = collected_at_str.rstrip("Z")
                        else:
                            # Replace Z with +00:00
                            collected_at_str = collected_at_str.replace("Z", "+00:00")

                    # Create source metadata from legacy fields
                    source_metadata = SourceMetadata(
                        source_type=item_data.get("source", "web"),
                        source_identifier=item_data.get("subreddit")
                        or item_data.get("url", "unknown"),
                        collected_at=datetime.fromisoformat(collected_at_str),
                        upvotes=item_data.get("ups") or item_data.get("upvotes"),
                        comments=item_data.get("num_comments")
                        or item_data.get("comments"),
                        reddit_data=(
                            {"subreddit": item_data.get("subreddit")}
                            if item_data.get("subreddit")
                            else None
                        ),
                    )

                    # Create enhanced content item
                    content_item = ContentItem(
                        id=item_data.get("id", f"migrated_{i}"),
                        title=item_data.get("title", "Untitled"),
                        url=item_data.get("url"),
                        content=item_data.get("content"),
                        summary=item_data.get("summary"),
                        source=source_metadata,
                        priority_score=item_data.get("priority_score"),
                        schema_version="3.0",
                    )

                    # Add migration provenance only for legacy items
                    migration_entry = ProvenanceEntry(
                        stage=ProcessingStage.COLLECTION,
                        service_name="migration-service",
                        operation="legacy_migration",
                        timestamp=datetime.utcnow(),
                        processing_time_ms=0,
                        parameters={
                            "original_schema": blob_data.get(
                                "schema_version", "unknown"
                            )
                        },
                    )
                    content_item.add_provenance(migration_entry)

                items.append(content_item)

            except Exception as e:
                print(f"Skipping invalid item {i}: {e}")
                continue

        # Create enhanced metadata
        metadata = CollectionMetadata(
            timestamp=datetime.utcnow(),
            collection_id=blob_data.get(
                "collection_id",
                blob_data.get("metadata", {}).get("collection_id", "unknown"),
            ),
            total_items=len(items),
            sources_processed=1,
            processing_time_ms=blob_data.get("metadata", {}).get(
                "processing_time_ms", 0
            ),
            collection_strategy="migrated",
        )

        # Create result
        result = ExtendedCollectionResult(
            metadata=metadata, items=items, schema_version="3.0"
        )

        # Calculate aggregate metrics
        result.calculate_aggregate_metrics()

        return result

    @staticmethod
    def validate_processing_request(message_data: Dict) -> ProcessingRequest:
        """Validate processing request format."""
        try:
            return ProcessingRequest.parse_obj(message_data)
        except Exception as e:
            raise DataContractError(f"Invalid processing request: {e}")

    @staticmethod
    def extract_core_fields(item: ContentItem) -> Dict[str, Any]:
        """
        Extract core fields that downstream services need.

        This allows services to safely ignore extended fields while
        getting all the data they actually use.
        """
        return {
            "id": item.id,
            "title": item.title,
            "url": item.url,
            "content": item.content,
            "summary": item.summary,
            "source": item.source.source_type,  # Legacy format
            "upvotes": item.source.upvotes,
            "comments": item.source.comments,
            "subreddit": (
                item.source.reddit_data.get("subreddit")
                if item.source.reddit_data
                else None
            ),
            "priority_score": item.priority_score,
            "collected_at": item.source.collected_at.isoformat(),
        }

    @staticmethod
    def create_safe_collection_for_downstream(
        collection: ExtendedCollectionResult,
    ) -> Dict[str, Any]:
        """
        Create a safe collection format for downstream services.

        Strips out extended fields that older services don't understand
        while preserving all essential data.
        """
        return {
            "metadata": {
                "timestamp": collection.metadata.timestamp.isoformat(),
                "collection_id": collection.metadata.collection_id,
                "total_items": collection.metadata.total_items,
                "sources_processed": collection.metadata.sources_processed,
                "processing_time_ms": collection.metadata.processing_time_ms,
                "collector_version": collection.metadata.collector_version,
            },
            "items": [
                ExtendedContractValidator.extract_core_fields(item)
                for item in collection.items
            ],
            "schema_version": "2.0",  # Report as legacy-compatible
            "created_at": collection.created_at.isoformat(),
        }

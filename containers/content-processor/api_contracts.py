"""
API Contract Definitions for Content Processor

Defines versioned contracts for all external integrations.
Contract Version: 1.0.0

Follows strict standards:
- Semantic versioning for all contracts
- Type hints for all schemas
- Comprehensive documentation
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Contract Metadata
# ============================================================================

CONTRACT_VERSION = "1.0.0"
SUPPORTED_VERSIONS = ["1.0.0"]


class ContractVersion(BaseModel):
    """Version information for API contracts."""

    version: str = Field(
        default=CONTRACT_VERSION,
        description="Semantic version of this contract",
    )
    supported_versions: List[str] = Field(
        default=SUPPORTED_VERSIONS,
        description="List of supported contract versions",
    )


# ============================================================================
# Content Collector Contracts (Upstream)
# ============================================================================


class CollectionItemContract(BaseModel):
    """Contract for collection items from content-collector.

    This defines what we expect from upstream collection files.
    Contract Version: 1.0.0
    """

    id: str = Field(..., description="Unique item identifier")
    title: str = Field(..., min_length=1, description="Item title")
    url: Optional[str] = Field(None, description="Source URL")
    upvotes: int = Field(default=0, ge=0, description="Upvote count")
    comments: int = Field(default=0, ge=0, description="Comment count")
    subreddit: Optional[str] = Field(None, description="Subreddit name")
    created_utc: Optional[float] = Field(None, description="UTC timestamp")
    selftext: Optional[str] = Field(None, description="Full text content")


class CollectionFileContract(BaseModel):
    """Contract for collection files from content-collector.

    This is the top-level structure we expect in blob storage.
    Contract Version: 1.0.0
    """

    collection_id: str = Field(..., description="Unique collection ID")
    source: Literal["reddit", "rss", "mastodon", "web"] = Field(
        ..., description="Collection source type"
    )
    collected_at: str = Field(..., description="ISO 8601 timestamp")
    items: List[CollectionItemContract] = Field(
        ..., description="List of collected items"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Collection metadata"
    )


# ============================================================================
# Markdown Generator Contracts (Downstream)
# ============================================================================


class ProvenanceEntryContract(BaseModel):
    """Contract for provenance tracking entries.

    Contract Version: 1.0.0
    """

    stage: Literal["collection", "processing", "publishing"] = Field(
        ..., description="Pipeline stage"
    )
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    source: Optional[str] = Field(
        None, description="Source identifier (e.g., 'reddit-praw')"
    )
    processor_id: Optional[str] = Field(None, description="Processor instance ID")
    version: str = Field(..., description="Component version")


class CostTrackingContract(BaseModel):
    """Contract for cost tracking data.

    Contract Version: 1.0.0
    """

    openai_tokens: int = Field(ge=0, description="Total tokens used")
    openai_cost_usd: float = Field(ge=0.0, description="Total cost in USD")
    processing_time_seconds: float = Field(ge=0.0, description="Processing time")
    model: str = Field(..., description="Model name used")


class ProcessedArticleContract(BaseModel):
    """Contract for processed articles sent to markdown-generator.

    This defines what we produce for downstream consumption.
    Contract Version: 1.0.0
    """

    article_id: str = Field(..., description="Unique article identifier")
    original_topic_id: str = Field(..., description="Original collection item ID")
    title: str = Field(..., min_length=1, description="Article title")
    seo_title: str = Field(..., max_length=60, description="SEO-optimized title")
    slug: str = Field(..., description="URL-safe slug")
    url: str = Field(..., description="Article URL path")
    filename: str = Field(..., description="Output filename")
    content: str = Field(..., min_length=100, description="Article content")
    word_count: int = Field(ge=0, description="Word count")
    quality_score: float = Field(ge=0.0, le=1.0, description="Quality score")
    metadata: Dict[str, Any] = Field(..., description="Article metadata")
    provenance: List[ProvenanceEntryContract] = Field(
        ..., description="Processing history"
    )
    costs: CostTrackingContract = Field(..., description="Cost tracking")
    contract_version: str = Field(
        default=CONTRACT_VERSION, description="Contract version"
    )


# ============================================================================
# Queue Message Contracts
# ============================================================================


class WakeUpMessageContract(BaseModel):
    """Contract for wake-up messages from content-collector.

    Contract Version: 1.0.0
    """

    source: str = Field(..., description="Message source")
    batch_size: int = Field(default=10, ge=1, description="Batch size")
    priority_threshold: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Priority threshold"
    )
    processing_options: Dict[str, Any] = Field(
        default_factory=dict, description="Processing options"
    )
    debug_bypass: bool = Field(default=False, description="Bypass validation")
    payload: Dict[str, Any] = Field(..., description="Message payload")


class MarkdownTriggerContract(BaseModel):
    """Contract for messages sent to markdown-generator.

    Contract Version: 1.0.0
    """

    trigger: Literal["content-processor"] = Field(..., description="Trigger source")
    blob_name: str = Field(..., description="Processed article blob path")
    article_id: str = Field(..., description="Article identifier")
    priority: Literal["high", "normal", "low"] = Field(
        default="normal", description="Processing priority"
    )
    timestamp: str = Field(..., description="ISO 8601 timestamp")


# ============================================================================
# Blob Storage Naming Contracts
# ============================================================================


class BlobNamingContract:
    """Naming conventions for blob storage.

    Contract Version: 1.0.0
    """

    # Collection files from content-collector
    COLLECTION_PATTERN = (
        "collections/{year}/{month}/{day}/{source}-{topic}-{timestamp}.json"
    )
    COLLECTION_PREFIX = "collections/"

    # Processed articles for markdown-generator
    PROCESSED_PATTERN = "processed-content/{year}/{month}/{day}/article-{id}.json"
    PROCESSED_PREFIX = "processed-content/"

    # Article ID format
    ARTICLE_ID_PATTERN = "{date}-{slug}"  # e.g., "20251008-ai-transforms-dev"

    @staticmethod
    def validate_collection_path(path: str) -> bool:
        """Validate collection blob path format."""
        parts = path.split("/")
        return (
            len(parts) == 5
            and parts[0] == "collections"
            and len(parts[1]) == 4  # Year
            and len(parts[2]) == 2  # Month
            and len(parts[3]) == 2  # Day
            and parts[4].endswith(".json")
        )

    @staticmethod
    def validate_processed_path(path: str) -> bool:
        """Validate processed article blob path format."""
        parts = path.split("/")
        return (
            len(parts) == 5
            and parts[0] == "processed-content"
            and len(parts[1]) == 4  # Year
            and len(parts[2]) == 2  # Month
            and len(parts[3]) == 2  # Day
            and parts[4].endswith(".json")
        )


# ============================================================================
# Version Compatibility
# ============================================================================


def check_contract_compatibility(version: str) -> bool:
    """Check if contract version is supported.

    Args:
        version: Semantic version string (e.g., "1.0.0")

    Returns:
        True if version is supported, False otherwise
    """
    return version in SUPPORTED_VERSIONS


def get_contract_info() -> Dict[str, Any]:
    """Get current contract information.

    Returns:
        Dictionary with version and compatibility info
    """
    return {
        "contract_version": CONTRACT_VERSION,
        "supported_versions": SUPPORTED_VERSIONS,
        "contracts": {
            "upstream": {
                "content_collector": {
                    "collection_file": "CollectionFileContract",
                    "collection_item": "CollectionItemContract",
                }
            },
            "downstream": {
                "markdown_generator": {
                    "processed_article": "ProcessedArticleContract",
                    "queue_message": "MarkdownTriggerContract",
                }
            },
        },
    }

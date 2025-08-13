"""
Content Source Abstraction - Pure Functions

This module defines abstract interfaces and data structures for content collection,
allowing multiple content sources (Reddit, RSS, APIs, etc.) to be processed uniformly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class ContentItem:
    """Standardized content item from any source"""
    title: str
    content: str
    url: str
    source: str  # "reddit", "rss", "api", etc.
    source_id: str  # Original ID from source
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    score: Optional[int] = None
    comments_count: Optional[int] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize default values"""
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class CollectionRequest:
    """Request parameters for content collection"""
    source: str  # "reddit", "rss", "hacker_news", etc.
    targets: List[str]  # subreddits, RSS URLs, API endpoints, etc.
    limit: int = 25
    time_period: str = "hot"  # "hot", "new", "top", "day", "week", etc.
    filters: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.filters is None:
            self.filters = {}


@dataclass
class CollectionResult:
    """Result from content collection operation"""
    request: CollectionRequest
    items: List[ContentItem]
    success: bool
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ContentCollector(ABC):
    """Abstract base class for content collectors"""

    @abstractmethod
    def collect(self, request: CollectionRequest) -> CollectionResult:
        """
        Collect content based on request parameters.

        This is a pure function that:
        - Takes collection parameters
        - Returns standardized content items
        - Does not perform any side effects (logging, storage)
        """
        pass

    @abstractmethod
    def validate_request(self, request: CollectionRequest) -> tuple[bool, Optional[str]]:
        """
        Validate if the request can be processed by this collector.

        Returns:
            (is_valid, error_message)
        """
        pass


def normalize_content_item(raw_data: Dict[str, Any], source: str) -> ContentItem:
    """
    Pure function to normalize raw content data into ContentItem.

    Args:
        raw_data: Raw data from any content source
        source: Source identifier ("reddit", "rss", etc.)

    Returns:
        Normalized ContentItem
    """
    # Default normalization - subclasses can override
    return ContentItem(
        title=str(raw_data.get("title", "")).strip(),
        content=str(raw_data.get("content", "")).strip(),
        url=str(raw_data.get("url", "")).strip(),
        source=source,
        source_id=str(raw_data.get("id", "")),
        author=raw_data.get("author"),
        created_at=raw_data.get("created_at"),
        score=raw_data.get("score"),
        comments_count=raw_data.get("comments_count"),
        tags=raw_data.get("tags", []),
        metadata=raw_data.get("metadata", {})
    )


def filter_content_items(items: List[ContentItem], filters: Dict[str, Any]) -> List[ContentItem]:
    """
    Pure function to filter content items based on criteria.

    Args:
        items: List of content items to filter
        filters: Filter criteria

    Returns:
        Filtered list of content items
    """
    if not filters:
        return items

    filtered_items = items

    # Minimum score filter
    if "min_score" in filters:
        min_score = filters["min_score"]
        filtered_items = [item for item in filtered_items
                          if item.score is None or item.score >= min_score]

    # Minimum comments filter
    if "min_comments" in filters:
        min_comments = filters["min_comments"]
        filtered_items = [item for item in filtered_items
                          if item.comments_count is None or item.comments_count >= min_comments]

    # Title keyword filter
    if "title_keywords" in filters:
        keywords = [kw.lower() for kw in filters["title_keywords"]]
        filtered_items = [item for item in filtered_items
                          if any(keyword in item.title.lower() for keyword in keywords)]

    # Exclude keywords filter
    if "exclude_keywords" in filters:
        exclude_keywords = [kw.lower() for kw in filters["exclude_keywords"]]
        filtered_items = [item for item in filtered_items
                          if not any(keyword in item.title.lower() for keyword in exclude_keywords)]

    return filtered_items


def transform_collection_result(result: CollectionResult, transformations: Dict[str, Any]) -> CollectionResult:
    """
    Pure function to transform collection results.

    Args:
        result: Original collection result
        transformations: Transformation parameters

    Returns:
        Transformed collection result
    """
    if not transformations:
        return result

    items = result.items

    # Apply filters
    if "filters" in transformations:
        items = filter_content_items(items, transformations["filters"])

    # Sort items
    if "sort_by" in transformations:
        sort_key = transformations["sort_by"]
        reverse = transformations.get("sort_desc", True)

        if sort_key == "score":
            items = sorted(items, key=lambda x: x.score or 0, reverse=reverse)
        elif sort_key == "comments":
            items = sorted(
                items, key=lambda x: x.comments_count or 0, reverse=reverse)
        elif sort_key == "created_at":
            items = sorted(
                items, key=lambda x: x.created_at or datetime.min, reverse=reverse)

    # Limit items
    if "limit" in transformations:
        items = items[:transformations["limit"]]

    return CollectionResult(
        request=result.request,
        items=items,
        success=result.success,
        error=result.error,
        metadata={**(result.metadata or {}),
                  "transformations_applied": transformations}
    )

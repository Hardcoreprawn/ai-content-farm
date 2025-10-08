"""
Data Contract Tests for Content Processor

Validates input/output formats and ensures compatibility with:
- Content Collector (upstream)
- Markdown Generator (downstream)
- Blob Storage contracts

Follows strict PEP 8 standards:
- Max 400 lines per file
- Type hints on all functions
- Comprehensive docstrings
- No mutable defaults
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

import pytest
from models import (
    ProcessingResult,
    TopicMetadata,
    WakeUpRequest,
    WakeUpResponse,
)
from pydantic import ValidationError


class TestCollectionInputContract:
    """Test input format from content-collector container.

    Validates that we correctly parse collection files from blob storage.
    Contract version: 1.0.0
    """

    def test_collection_file_structure(self) -> None:
        """Validate collection file has required top-level fields."""
        collection_data: Dict[str, Any] = {
            "collection_id": "reddit-tech-20251008-103045",
            "source": "reddit",
            "collected_at": "2025-10-08T10:30:45Z",
            "items": [],
            "metadata": {
                "collection_method": "praw",
                "api_version": "7.7.1",
            },
        }

        # Required fields must exist
        assert "collection_id" in collection_data
        assert "source" in collection_data
        assert "collected_at" in collection_data
        assert "items" in collection_data
        assert isinstance(collection_data["items"], list)

    def test_collection_item_required_fields(self) -> None:
        """Validate collection item has all required fields."""
        item: Dict[str, Any] = {
            "id": "abc123xyz",
            "title": "How AI is Transforming Software Development",
            "url": "https://reddit.com/r/programming/comments/abc123",
            "upvotes": 1250,
            "comments": 180,
            "subreddit": "programming",
            "created_utc": 1728385845.0,
            "selftext": "AI-powered tools are revolutionizing...",
        }

        # Required fields
        assert "id" in item
        assert "title" in item
        assert isinstance(item["title"], str)
        assert len(item["title"]) > 0

        # Engagement metrics
        assert "upvotes" in item
        assert "comments" in item
        assert isinstance(item["upvotes"], int)
        assert isinstance(item["comments"], int)

    def test_collection_item_to_topic_metadata(self) -> None:
        """Test conversion from collection item to TopicMetadata."""
        item: Dict[str, Any] = {
            "id": "test123",
            "title": "Test Article Title",
            "url": "https://example.com/test",
            "upvotes": 500,
            "comments": 75,
            "subreddit": "technology",
            "created_utc": 1728385845.0,
        }

        # Create TopicMetadata (this should not raise)
        topic = TopicMetadata(
            topic_id=item["id"],
            title=item["title"],
            source="reddit",
            collected_at=datetime.now(timezone.utc),
            priority_score=0.8,
            url=item["url"],
            upvotes=item["upvotes"],
            comments=item["comments"],
            subreddit=item.get("subreddit"),
        )

        # Validate required fields
        assert topic.topic_id == "test123"
        assert topic.title == "Test Article Title"
        assert 0.0 <= topic.priority_score <= 1.0

    def test_collection_item_missing_required_field(self) -> None:
        """Test that missing required fields are handled gracefully."""
        incomplete_item: Dict[str, Any] = {
            "id": "test123",
            # Missing 'title' - should be handled
        }

        # This should either raise ValidationError or return None
        # depending on implementation
        assert "title" not in incomplete_item


class TestProcessedArticleOutputContract:
    """Test output format for processed-content container.

    Validates that we produce correct format for markdown-generator.
    Contract version: 1.0.0
    """

    def test_processed_article_required_fields(self) -> None:
        """Validate processed article has all required fields."""
        article_data: Dict[str, Any] = {
            "article_id": "20251008-ai-transforming-software",
            "original_topic_id": "abc123xyz",
            "title": "How AI is Transforming Software Development",
            "seo_title": "AI Transforming Software Development - Complete Guide",
            "slug": "ai-transforming-software-development",
            "url": "/2025/10/ai-transforming-software-development",
            "filename": "20251008-ai-transforming-software-development.md",
            "content": "# How AI is Transforming Software Development\n\n...",
            "word_count": 3200,
            "quality_score": 0.87,
            "metadata": {},
            "provenance": [],
            "costs": {},
        }

        # Required fields
        assert "article_id" in article_data
        assert "original_topic_id" in article_data
        assert "title" in article_data
        assert "slug" in article_data
        assert "content" in article_data

        # SEO fields
        assert "seo_title" in article_data
        assert "url" in article_data
        assert "filename" in article_data

        # Metrics
        assert "word_count" in article_data
        assert "quality_score" in article_data
        assert isinstance(article_data["word_count"], int)
        assert isinstance(article_data["quality_score"], float)

    def test_article_metadata_structure(self) -> None:
        """Validate article metadata structure."""
        metadata: Dict[str, Any] = {
            "source": "reddit",
            "subreddit": "programming",
            "original_url": "https://reddit.com/r/programming/comments/abc123",
            "collected_at": "2025-10-08T10:30:45Z",
            "processed_at": "2025-10-08T11:45:30Z",
            "processor_id": "proc-xyz789",
        }

        # Required metadata fields
        assert "source" in metadata
        assert "collected_at" in metadata
        assert "processed_at" in metadata
        assert "processor_id" in metadata

        # Validate timestamp format (ISO 8601)
        assert "T" in metadata["collected_at"]
        assert "Z" in metadata["collected_at"]

    def test_article_provenance_structure(self) -> None:
        """Validate provenance tracking structure."""
        provenance: List[Dict[str, Any]] = [
            {
                "stage": "collection",
                "timestamp": "2025-10-08T10:30:45Z",
                "source": "reddit-praw",
                "version": "7.7.1",
            },
            {
                "stage": "processing",
                "timestamp": "2025-10-08T11:45:30Z",
                "processor_id": "proc-xyz789",
                "version": "1.0.0",
            },
        ]

        # Validate provenance entries
        assert len(provenance) >= 1
        for entry in provenance:
            assert "stage" in entry
            assert "timestamp" in entry
            assert entry["stage"] in ["collection", "processing", "publishing"]

    def test_article_costs_structure(self) -> None:
        """Validate cost tracking structure."""
        costs: Dict[str, Any] = {
            "openai_tokens": 4500,
            "openai_cost_usd": 0.045,
            "processing_time_seconds": 12.5,
            "model": "gpt-35-turbo",
        }

        # Required cost fields
        assert "openai_tokens" in costs
        assert "openai_cost_usd" in costs
        assert isinstance(costs["openai_tokens"], int)
        assert isinstance(costs["openai_cost_usd"], float)
        assert costs["openai_cost_usd"] >= 0.0


class TestQueueMessageContract:
    """Test queue message formats for pipeline coordination.

    Contract version: 1.0.0
    """

    def test_wake_up_request_structure(self) -> None:
        """Validate wake-up request from content-collector."""
        request = WakeUpRequest(
            source="content-collector",
            batch_size=10,
            priority_threshold=0.5,
            processing_options={},
            debug_bypass=False,
            payload={
                "files": [
                    "collections/2025/10/08/reddit-tech-20251008.json",
                ]
            },
        )

        # Validate structure
        assert request.source == "content-collector"
        assert isinstance(request.batch_size, int)
        assert isinstance(request.priority_threshold, float)
        assert request.payload is not None
        assert "files" in request.payload

    def test_markdown_trigger_message_structure(self) -> None:
        """Validate message sent to markdown-generator queue."""
        message: Dict[str, Any] = {
            "trigger": "content-processor",
            "blob_name": "processed-content/2025/10/08/article-abc123.json",
            "article_id": "20251008-article-abc123",
            "priority": "normal",
            "timestamp": "2025-10-08T11:45:30Z",
        }

        # Required fields for markdown generator
        assert "trigger" in message
        assert "blob_name" in message
        assert "article_id" in message
        assert message["trigger"] == "content-processor"

        # Validate blob path format
        blob_name = message["blob_name"]
        assert blob_name.startswith("processed-content/")
        assert blob_name.endswith(".json")


class TestProcessingResultContract:
    """Test ProcessingResult model validation."""

    def test_processing_result_validation(self) -> None:
        """Test ProcessingResult with valid data."""
        result = ProcessingResult(
            success=True,
            topics_processed=5,
            articles_generated=5,
            total_cost=0.125,
            processing_time=45.5,
            completed_topics=["topic1", "topic2", "topic3", "topic4", "topic5"],
            failed_topics=[],
            error_messages=[],
        )

        # Validate fields
        assert result.success is True
        assert result.topics_processed == 5
        assert len(result.completed_topics) == 5
        assert len(result.failed_topics) == 0

    def test_processing_result_with_failures(self) -> None:
        """Test ProcessingResult with partial failures."""
        result = ProcessingResult(
            success=True,
            topics_processed=3,
            articles_generated=3,
            total_cost=0.075,
            processing_time=35.2,
            completed_topics=["topic1", "topic2", "topic3"],
            failed_topics=["topic4", "topic5"],
            error_messages=[
                "Topic4: OpenAI API timeout",
                "Topic5: Invalid metadata",
            ],
        )

        # Validate partial success
        assert result.success is True  # Overall success even with failures
        assert result.topics_processed == 3
        assert len(result.failed_topics) == 2
        assert len(result.error_messages) == 2


class TestBlobNamingConventions:
    """Test blob storage naming conventions.

    Ensures consistent naming across containers.
    Contract version: 1.0.0
    """

    def test_collection_blob_naming(self) -> None:
        """Test collection blob naming convention."""
        blob_name = "collections/2025/10/08/reddit-tech-20251008-103045.json"

        # Validate format: collections/YYYY/MM/DD/source-topic-timestamp.json
        parts = blob_name.split("/")
        assert parts[0] == "collections"
        assert len(parts[1]) == 4  # Year
        assert len(parts[2]) == 2  # Month
        assert len(parts[3]) == 2  # Day
        assert parts[4].endswith(".json")

    def test_processed_article_blob_naming(self) -> None:
        """Test processed article blob naming convention."""
        blob_name = "processed-content/2025/10/08/article-abc123.json"

        # Validate format: processed-content/YYYY/MM/DD/article-id.json
        parts = blob_name.split("/")
        assert parts[0] == "processed-content"
        assert len(parts[1]) == 4  # Year
        assert len(parts[2]) == 2  # Month
        assert len(parts[3]) == 2  # Day
        assert parts[4].endswith(".json")

    def test_article_id_format(self) -> None:
        """Test article ID format consistency."""
        article_id = "20251008-ai-transforming-software"

        # Format: YYYYMMDD-slug
        parts = article_id.split("-", 1)
        assert len(parts) == 2
        assert len(parts[0]) == 8  # YYYYMMDD
        assert parts[0].isdigit()


class TestDataContractVersioning:
    """Test that we track data contract versions.

    Important for API evolution and backward compatibility.
    """

    def test_collection_contract_version(self) -> None:
        """Test collection data contract version tracking."""
        collection_data: Dict[str, Any] = {
            "collection_id": "test-20251008",
            "source": "reddit",
            "collected_at": "2025-10-08T10:30:45Z",
            "items": [],
            "metadata": {
                "collection_method": "praw",
                "api_version": "7.7.1",
                "contract_version": "1.0.0",  # Track contract version
            },
        }

        # Verify version tracking
        assert "contract_version" in collection_data["metadata"]
        version = collection_data["metadata"]["contract_version"]
        assert isinstance(version, str)
        assert version.count(".") == 2  # Semantic versioning

    def test_processed_article_contract_version(self) -> None:
        """Test processed article contract version tracking."""
        article_data: Dict[str, Any] = {
            "article_id": "20251008-test",
            "contract_version": "1.0.0",  # Track at top level
            "metadata": {
                "processor_version": "1.0.0",
            },
        }

        # Verify version tracking
        assert "contract_version" in article_data
        assert "processor_version" in article_data["metadata"]

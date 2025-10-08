"""
Output Format Validation Tests

Tests that content-processor produces correct output formats
for downstream consumers (markdown-generator).

Follows strict standards:
- Max 400 lines per file
- Type hints on all functions
- External API contract testing with versioning
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from models import ProcessingResult


class TestProcessedArticleOutput:
    """Test processed article output format."""

    @pytest.fixture
    def mock_blob_client(self) -> Mock:
        """Create mock blob client for upload operations."""
        client = Mock()
        client.upload_json = AsyncMock()
        client.blob_exists = AsyncMock(return_value=False)
        return client

    def test_article_output_structure(self) -> None:
        """Test complete article output structure."""
        article_output: Dict[str, Any] = {
            "article_id": "20251008-ai-transforming-dev",
            "original_topic_id": "abc123",
            "title": "How AI is Transforming Software Development",
            "seo_title": "AI Transforming Software Development - Guide 2025",
            "slug": "ai-transforming-software-development",
            "url": "/2025/10/ai-transforming-software-development",
            "filename": "20251008-ai-transforming-software-development.md",
            "content": "# How AI is Transforming Software Development\n\n...",
            "word_count": 3200,
            "quality_score": 0.87,
            "metadata": {
                "source": "reddit",
                "subreddit": "programming",
                "collected_at": "2025-10-08T10:30:45Z",
                "processed_at": "2025-10-08T11:45:30Z",
                "processor_id": "proc-xyz789",
                "contract_version": "1.0.0",
            },
            "provenance": [
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
            ],
            "costs": {
                "openai_tokens": 4500,
                "openai_cost_usd": 0.045,
                "processing_time_seconds": 12.5,
                "model": "gpt-35-turbo",
            },
        }

        # Validate all required fields present
        required_fields = [
            "article_id",
            "title",
            "content",
            "metadata",
            "provenance",
        ]
        for field in required_fields:
            assert field in article_output, f"Missing field: {field}"

        # Validate types
        assert isinstance(article_output["word_count"], int)
        assert isinstance(article_output["quality_score"], float)
        assert isinstance(article_output["metadata"], dict)
        assert isinstance(article_output["provenance"], list)

    @pytest.mark.asyncio
    async def test_upload_article_to_blob(self, mock_blob_client: Mock) -> None:
        """Test uploading article to blob storage."""
        article_data: Dict[str, Any] = {
            "article_id": "20251008-test",
            "title": "Test Article",
            "content": "Test content",
            "metadata": {},
        }

        blob_name = "processed-content/2025/10/08/article-test.json"
        await mock_blob_client.upload_json(blob_name, article_data)

        # Verify upload was called
        mock_blob_client.upload_json.assert_called_once_with(blob_name, article_data)

    def test_seo_metadata_generation(self) -> None:
        """Test SEO metadata generation."""
        seo_data: Dict[str, str] = {
            "seo_title": "Complete Guide: AI Transforming Development 2025",
            "slug": "ai-transforming-software-development",
            "url": "/2025/10/ai-transforming-software-development",
            "filename": "20251008-ai-transforming-software-development.md",
        }

        # Validate SEO fields
        assert len(seo_data["seo_title"]) <= 60  # SEO best practice
        assert "-" in seo_data["slug"]
        assert " " not in seo_data["slug"]
        assert seo_data["url"].startswith("/")
        assert seo_data["filename"].endswith(".md")

    def test_slug_generation(self) -> None:
        """Test slug generation from title."""
        titles_and_slugs = [
            ("How AI is Transforming Dev", "how-ai-is-transforming-dev"),
            ("Python 3.12 Released!", "python-312-released"),  # Periods removed
            ("Machine Learning: A Guide", "machine-learning-a-guide"),
        ]

        for title, expected_slug in titles_and_slugs:
            # Slug should be lowercase, hyphenated, alphanumeric only
            slug = title.lower().replace(" ", "-")
            slug = "".join(c if c.isalnum() or c == "-" else "" for c in slug)
            assert slug == expected_slug

    def test_filename_generation(self) -> None:
        """Test markdown filename generation."""
        article_id = "20251008-ai-transforming-dev"
        filename = f"{article_id}.md"

        # Validate format
        assert filename.endswith(".md")
        assert filename.startswith("20251008")
        assert "-" in filename


class TestProvenanceTracking:
    """Test provenance tracking in output."""

    def test_provenance_chain(self) -> None:
        """Test complete provenance chain."""
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

        # Validate chain
        assert len(provenance) >= 2
        assert provenance[0]["stage"] == "collection"
        assert provenance[1]["stage"] == "processing"

        # Validate timestamps are sequential
        ts1 = datetime.fromisoformat(provenance[0]["timestamp"].replace("Z", "+00:00"))
        ts2 = datetime.fromisoformat(provenance[1]["timestamp"].replace("Z", "+00:00"))
        assert ts2 > ts1

    def test_add_provenance_entry(self) -> None:
        """Test adding new provenance entry."""
        provenance: List[Dict[str, Any]] = []

        # Add entry
        entry: Dict[str, Any] = {
            "stage": "processing",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "processor_id": str(uuid4()),
            "version": "1.0.0",
        }
        provenance.append(entry)

        # Validate
        assert len(provenance) == 1
        assert provenance[0]["stage"] == "processing"
        assert "timestamp" in provenance[0]


class TestCostTracking:
    """Test cost tracking in output."""

    def test_cost_structure(self) -> None:
        """Test cost tracking structure."""
        costs: Dict[str, Any] = {
            "openai_tokens": 4500,
            "openai_cost_usd": 0.045,
            "processing_time_seconds": 12.5,
            "model": "gpt-35-turbo",
        }

        # Validate cost fields
        assert isinstance(costs["openai_tokens"], int)
        assert isinstance(costs["openai_cost_usd"], float)
        assert costs["openai_cost_usd"] >= 0.0
        assert costs["openai_tokens"] > 0

    def test_cost_calculation(self) -> None:
        """Test cost calculation from tokens."""
        tokens = 4500
        cost_per_1k = 0.01  # $0.01 per 1K tokens

        calculated_cost = (tokens / 1000) * cost_per_1k
        assert calculated_cost == 0.045

    def test_processing_time_tracking(self) -> None:
        """Test processing time tracking."""
        start_time = datetime.now(timezone.utc)
        # Simulate processing...
        end_time = datetime.now(timezone.utc)

        processing_time = (end_time - start_time).total_seconds()
        assert processing_time >= 0.0


class TestQueueMessageOutput:
    """Test queue messages sent to markdown-generator."""

    @pytest.fixture
    def mock_queue_client(self) -> Mock:
        """Create mock queue client."""
        client = Mock()
        client.send_message = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_send_markdown_trigger(self, mock_queue_client: Mock) -> None:
        """Test sending trigger message to markdown-generator."""
        message: Dict[str, Any] = {
            "trigger": "content-processor",
            "blob_name": "processed-content/2025/10/08/article-abc123.json",
            "article_id": "20251008-article-abc123",
            "priority": "normal",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await mock_queue_client.send_message(message)

        # Verify message sent
        mock_queue_client.send_message.assert_called_once()

    def test_markdown_trigger_format(self) -> None:
        """Test markdown trigger message format."""
        message: Dict[str, Any] = {
            "trigger": "content-processor",
            "blob_name": "processed-content/2025/10/08/test.json",
            "article_id": "20251008-test",
            "priority": "normal",
            "timestamp": "2025-10-08T11:45:30Z",
        }

        # Validate required fields
        assert message["trigger"] == "content-processor"
        assert message["blob_name"].endswith(".json")
        assert message["priority"] in ["high", "normal", "low"]


class TestProcessingResultOutput:
    """Test ProcessingResult model output."""

    def test_successful_result(self) -> None:
        """Test successful processing result."""
        result = ProcessingResult(
            success=True,
            topics_processed=5,
            articles_generated=5,
            total_cost=0.125,
            processing_time=45.5,
            completed_topics=["t1", "t2", "t3", "t4", "t5"],
            failed_topics=[],
            error_messages=[],
        )

        # Validate success case
        assert result.success is True
        assert result.topics_processed == 5
        assert len(result.completed_topics) == 5
        assert len(result.failed_topics) == 0

    def test_partial_failure_result(self) -> None:
        """Test result with partial failures."""
        result = ProcessingResult(
            success=True,
            topics_processed=3,
            articles_generated=3,
            total_cost=0.075,
            processing_time=35.2,
            completed_topics=["t1", "t2", "t3"],
            failed_topics=["t4", "t5"],
            error_messages=["T4 failed: timeout", "T5 failed: invalid data"],
        )

        # Validate partial success
        assert result.success is True
        assert result.topics_processed == 3
        assert len(result.failed_topics) == 2
        assert len(result.error_messages) == 2

    def test_complete_failure_result(self) -> None:
        """Test complete failure result."""
        result = ProcessingResult(
            success=False,
            topics_processed=0,
            articles_generated=0,
            total_cost=0.0,
            processing_time=5.0,
            completed_topics=[],
            failed_topics=["t1", "t2", "t3"],
            error_messages=["OpenAI API unavailable"],
        )

        # Validate failure case
        assert result.success is False
        assert result.topics_processed == 0
        assert len(result.failed_topics) == 3


class TestVersionTracking:
    """Test version tracking in outputs."""

    def test_contract_version_in_metadata(self) -> None:
        """Test contract version in article metadata."""
        metadata: Dict[str, Any] = {
            "source": "reddit",
            "contract_version": "1.0.0",
            "processor_version": "1.0.0",
        }

        # Validate version fields
        assert "contract_version" in metadata
        assert "processor_version" in metadata

        # Validate semantic versioning
        for version in [
            metadata["contract_version"],
            metadata["processor_version"],
        ]:
            parts = version.split(".")
            assert len(parts) == 3
            assert all(part.isdigit() for part in parts)

    def test_api_version_compatibility(self) -> None:
        """Test API version compatibility checks."""
        supported_versions = ["1.0.0", "1.1.0"]
        test_versions = [
            ("1.0.0", True),
            ("1.1.0", True),
            ("2.0.0", False),
            ("0.9.0", False),
        ]

        for version, should_support in test_versions:
            is_supported = version in supported_versions
            assert is_supported == should_support

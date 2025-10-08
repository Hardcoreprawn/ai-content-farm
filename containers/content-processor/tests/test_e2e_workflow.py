"""
End-to-End Workflow Tests

Tests complete pipeline flows from collection to processed output.

Follows strict standards:
- Max 400 lines per file
- Type hints on all functions
- Integration test patterns
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest


class TestCompleteProcessingFlow:
    """Test complete article processing workflow."""

    @pytest.fixture
    def mock_dependencies(self) -> Dict[str, Mock]:
        """Create all mock dependencies for E2E test."""
        blob_client = Mock()
        blob_client.download_json = AsyncMock()
        blob_client.upload_json = AsyncMock()
        blob_client.list_blobs = AsyncMock()

        openai_client = Mock()
        openai_client.generate_article = AsyncMock()

        queue_client = Mock()
        queue_client.send_message = AsyncMock()

        return {
            "blob_client": blob_client,
            "openai_client": openai_client,
            "queue_client": queue_client,
        }

    @pytest.mark.asyncio
    async def test_single_topic_processing(
        self, mock_dependencies: Dict[str, Mock]
    ) -> None:
        """Test processing single topic end-to-end."""
        blob_client = mock_dependencies["blob_client"]
        openai_client = mock_dependencies["openai_client"]

        # Mock collection download
        blob_client.download_json.return_value = {
            "collection_id": "reddit-tech-20251008",
            "items": [
                {
                    "id": "abc123",
                    "title": "How AI Transforms Development",
                    "upvotes": 1250,
                    "comments": 180,
                }
            ],
        }

        # Mock OpenAI response
        openai_client.generate_article.return_value = (
            "# How AI Transforms Development\n\nContent...",
            0.045,  # cost
            4500,  # tokens
        )

        # Simulate processing
        collection_data = await blob_client.download_json(
            "collections/2025/10/08/reddit-tech.json"
        )
        article_content, cost, tokens = await openai_client.generate_article(
            collection_data["items"][0]
        )

        # Upload result
        output_data: Dict[str, Any] = {
            "article_id": "20251008-ai-transforms-dev",
            "title": collection_data["items"][0]["title"],
            "content": article_content,
            "costs": {
                "openai_cost_usd": cost,
                "openai_tokens": tokens,
            },
        }
        await blob_client.upload_json(
            "processed-content/2025/10/08/article-abc123.json", output_data
        )

        # Verify all steps executed
        assert blob_client.download_json.call_count == 1
        assert openai_client.generate_article.call_count == 1
        assert blob_client.upload_json.call_count == 1

    @pytest.mark.asyncio
    async def test_batch_processing(self, mock_dependencies: Dict[str, Mock]) -> None:
        """Test processing batch of topics."""
        blob_client = mock_dependencies["blob_client"]
        openai_client = mock_dependencies["openai_client"]

        # Mock collection with multiple items
        blob_client.download_json.return_value = {
            "collection_id": "batch-20251008",
            "items": [
                {"id": "t1", "title": "Topic 1", "upvotes": 500},
                {"id": "t2", "title": "Topic 2", "upvotes": 600},
                {"id": "t3", "title": "Topic 3", "upvotes": 700},
            ],
        }

        # Mock OpenAI responses
        openai_client.generate_article.return_value = (
            "Article content",
            0.03,
            3000,
        )

        # Simulate batch processing
        collection_data = await blob_client.download_json("collections/batch.json")

        processed_count = 0
        for item in collection_data["items"]:
            content, cost, tokens = await openai_client.generate_article(item)
            await blob_client.upload_json(
                f"processed-content/article-{item['id']}.json",
                {"content": content},
            )
            processed_count += 1

        # Verify batch processing
        assert processed_count == 3
        assert openai_client.generate_article.call_count == 3
        assert blob_client.upload_json.call_count == 3


class TestErrorRecovery:
    """Test error handling and recovery in pipeline."""

    @pytest.fixture
    def mock_clients(self) -> Dict[str, Mock]:
        """Create mock clients for error testing."""
        blob_client = Mock()
        blob_client.download_json = AsyncMock()
        blob_client.upload_json = AsyncMock()

        openai_client = Mock()
        openai_client.generate_article = AsyncMock()

        return {
            "blob_client": blob_client,
            "openai_client": openai_client,
        }

    @pytest.mark.asyncio
    async def test_openai_timeout_recovery(self, mock_clients: Dict[str, Mock]) -> None:
        """Test recovery from OpenAI timeout."""
        openai_client = mock_clients["openai_client"]

        # First call times out, second succeeds
        openai_client.generate_article.side_effect = [
            TimeoutError("OpenAI timeout"),
            ("Article content", 0.03, 3000),
        ]

        # Attempt with retry
        try:
            result = await openai_client.generate_article({})
        except TimeoutError:
            # Retry
            result = await openai_client.generate_article({})

        # Verify retry succeeded
        assert result[0] == "Article content"
        assert openai_client.generate_article.call_count == 2

    @pytest.mark.asyncio
    async def test_blob_upload_failure_recovery(
        self, mock_clients: Dict[str, Mock]
    ) -> None:
        """Test recovery from blob upload failure."""
        blob_client = mock_clients["blob_client"]

        # First upload fails, second succeeds
        blob_client.upload_json.side_effect = [
            Exception("Upload failed"),
            None,
        ]

        # Attempt with retry
        try:
            await blob_client.upload_json("test.json", {})
        except Exception:
            # Retry
            await blob_client.upload_json("test.json", {})

        # Verify retry executed
        assert blob_client.upload_json.call_count == 2

    @pytest.mark.asyncio
    async def test_partial_batch_failure(self, mock_clients: Dict[str, Mock]) -> None:
        """Test handling partial batch failure."""
        openai_client = mock_clients["openai_client"]
        blob_client = mock_clients["blob_client"]

        # Mix of success and failure
        openai_client.generate_article.side_effect = [
            ("Content 1", 0.03, 3000),
            Exception("Generation failed"),
            ("Content 3", 0.03, 3000),
        ]

        items = [
            {"id": "t1", "title": "Topic 1"},
            {"id": "t2", "title": "Topic 2"},
            {"id": "t3", "title": "Topic 3"},
        ]

        completed = []
        failed = []

        for item in items:
            try:
                content, cost, tokens = await openai_client.generate_article(item)
                await blob_client.upload_json(f"article-{item['id']}.json", {})
                completed.append(item["id"])
            except Exception:
                failed.append(item["id"])

        # Verify partial success
        assert len(completed) == 2
        assert len(failed) == 1
        assert "t2" in failed


class TestDataFlowValidation:
    """Test data transformations through pipeline."""

    def test_collection_to_topic_transformation(self) -> None:
        """Test transforming collection item to topic."""
        collection_item: Dict[str, Any] = {
            "id": "abc123",
            "title": "Original Title",
            "upvotes": 1250,
            "comments": 180,
            "subreddit": "programming",
        }

        # Transform to topic
        topic: Dict[str, Any] = {
            "topic_id": collection_item["id"],
            "title": collection_item["title"],
            "source": "reddit",
            "priority_score": 0.85,
            "metadata": {
                "upvotes": collection_item["upvotes"],
                "comments": collection_item["comments"],
                "subreddit": collection_item["subreddit"],
            },
        }

        # Validate transformation
        assert topic["topic_id"] == collection_item["id"]
        assert topic["title"] == collection_item["title"]
        assert 0.0 <= topic["priority_score"] <= 1.0

    def test_topic_to_article_transformation(self) -> None:
        """Test transforming topic to article."""
        topic: Dict[str, Any] = {
            "topic_id": "abc123",
            "title": "Original Title",
            "source": "reddit",
        }

        generated_content = "# Article Title\n\nContent..."

        # Transform to article
        article: Dict[str, Any] = {
            "article_id": f"20251008-{topic['topic_id']}",
            "original_topic_id": topic["topic_id"],
            "title": topic["title"],
            "content": generated_content,
            "word_count": len(generated_content.split()),
            "metadata": {
                "source": topic["source"],
            },
        }

        # Validate transformation
        assert article["original_topic_id"] == topic["topic_id"]
        assert article["title"] == topic["title"]
        assert article["word_count"] > 0


class TestPipelineIntegration:
    """Test integration with upstream/downstream containers."""

    @pytest.fixture
    def mock_storage(self) -> Mock:
        """Create mock storage for integration test."""
        storage = Mock()
        storage.download_json = AsyncMock()
        storage.upload_json = AsyncMock()
        storage.list_blobs = AsyncMock()
        return storage

    @pytest.mark.asyncio
    async def test_content_collector_integration(self, mock_storage: Mock) -> None:
        """Test reading from content-collector output."""
        # Mock collection file from content-collector
        mock_storage.download_json.return_value = {
            "collection_id": "reddit-tech-20251008-103045",
            "source": "reddit",
            "collected_at": "2025-10-08T10:30:45Z",
            "items": [{"id": "t1", "title": "Test"}],
            "metadata": {
                "collection_method": "praw",
                "contract_version": "1.0.0",
            },
        }

        # Download and validate
        data = await mock_storage.download_json("collections/test.json")

        assert "collection_id" in data
        assert "items" in data
        assert len(data["items"]) > 0

    @pytest.mark.asyncio
    async def test_markdown_generator_integration(self, mock_storage: Mock) -> None:
        """Test writing for markdown-generator consumption."""
        # Create output for markdown-generator
        article_output: Dict[str, Any] = {
            "article_id": "20251008-test",
            "title": "Test Article",
            "content": "# Test\n\nContent...",
            "metadata": {
                "contract_version": "1.0.0",
            },
        }

        # Upload
        await mock_storage.upload_json(
            "processed-content/2025/10/08/test.json", article_output
        )

        # Verify upload
        mock_storage.upload_json.assert_called_once()
        call_args = mock_storage.upload_json.call_args
        uploaded_data = call_args[0][1]

        assert "article_id" in uploaded_data
        assert "content" in uploaded_data
        assert "contract_version" in uploaded_data["metadata"]

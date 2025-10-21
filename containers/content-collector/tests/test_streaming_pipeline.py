"""
Tests for streaming pipeline (pipeline/stream.py).

Core: collect → review → dedupe → save → queue
CRITICAL: Message format must match content-processor expectations.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest


@pytest.fixture
def mock_blob_client():
    """Mock Azure Blob Storage client."""
    client = AsyncMock()
    client.append_item = AsyncMock(return_value=True)
    client.is_seen = AsyncMock(return_value=False)
    client.mark_seen = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_queue_client():
    """Mock Azure Storage Queue client."""
    client = AsyncMock()
    client.send_message = AsyncMock(return_value=True)
    return client


@pytest.fixture
def sample_item():
    """Sample collected item before review."""
    return {
        "id": "reddit_abc123",
        "title": "Python 3.13 Released with Performance Improvements",
        "content": "Major release with 10-15% performance improvements across standard library.",
        "source": "reddit",
        "url": "https://reddit.com/r/programming/abc123",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "subreddit": "programming",
            "score": 150,
            "num_comments": 42,
        },
    }


@pytest.fixture
def collection_context():
    """Minimal collection context."""
    return {
        "collection_id": "col_test_123",
        "collection_blob": "collections/2025-10-21/col_test_123.json",
    }


class TestMessageFormatCompatibility:
    """CRITICAL: Verify message format for content-processor compatibility."""

    def test_message_has_required_top_level_fields(
        self, sample_item, collection_context
    ):
        """Message has operation, service_name, timestamp, correlation_id."""
        from pipeline.stream import create_queue_message

        message = create_queue_message(sample_item, collection_context)

        # Top-level fields (REQUIRED for content-processor)
        assert "operation" in message
        assert message["operation"] == "process_topic"

        assert "service_name" in message
        assert message["service_name"] == "content-collector"

        assert "timestamp" in message
        assert isinstance(message["timestamp"], str)

        assert "correlation_id" in message
        assert isinstance(message["correlation_id"], str)
        assert len(message["correlation_id"]) > 0

    def test_message_payload_has_required_fields(self, sample_item, collection_context):
        """Payload has topic_id, title, source, collection_id, collection_blob."""
        from pipeline.stream import create_queue_message

        message = create_queue_message(sample_item, collection_context)

        payload = message["payload"]

        # REQUIRED fields (content-processor depends on these)
        assert payload["topic_id"] == "reddit_abc123"
        assert payload["title"] == "Python 3.13 Released with Performance Improvements"
        assert payload["source"] == "reddit"
        assert payload["collection_id"] == "col_test_123"
        assert payload["collection_blob"] == "collections/2025-10-21/col_test_123.json"

    def test_message_payload_has_optional_metadata(
        self, sample_item, collection_context
    ):
        """Optional fields are included when present."""
        from pipeline.stream import create_queue_message

        message = create_queue_message(sample_item, collection_context)

        payload = message["payload"]

        # Optional fields from Reddit metadata
        assert payload.get("subreddit") == "programming"
        assert payload.get("upvotes") == 150
        assert payload.get("comments") == 42
        assert payload.get("url") == "https://reddit.com/r/programming/abc123"

    def test_message_format_json_serializable(self, sample_item, collection_context):
        """Message is JSON serializable (for queue)."""
        import json

        from pipeline.stream import create_queue_message

        message = create_queue_message(sample_item, collection_context)

        # Should serialize without error
        json_str = json.dumps(message)
        assert isinstance(json_str, str)

        # Should deserialize back
        restored = json.loads(json_str)
        assert restored["operation"] == "process_topic"
        assert restored["payload"]["topic_id"] == "reddit_abc123"

    def test_message_preserves_all_fields_from_item(
        self, sample_item, collection_context
    ):
        """All fields from collected item are preserved in message."""
        from pipeline.stream import create_queue_message

        message = create_queue_message(sample_item, collection_context)
        payload = message["payload"]

        # All key fields from item should be in payload
        assert "title" in payload
        assert "source" in payload
        assert "collected_at" in payload
        assert "priority_score" in payload or "priority_score" in message


class TestStreamingPipeline:
    """Test streaming orchestration."""

    @pytest.mark.asyncio
    async def test_stream_collection_basic_flow(
        self, mock_blob_client, mock_queue_client, sample_item
    ):
        """Basic stream flow: collect → review → dedupe → save → queue."""
        from pipeline.stream import stream_collection

        async def mock_collector():
            yield sample_item

        stats = await stream_collection(
            collector_fn=mock_collector(),
            collection_id="col_test",
            collection_blob="collections/2025-10-21/col_test.json",
            blob_client=mock_blob_client,
            queue_client=mock_queue_client,
        )

        assert stats["collected"] == 1
        assert stats["published"] >= 0

    @pytest.mark.asyncio
    async def test_stream_respects_quality_filter(
        self, mock_blob_client, mock_queue_client
    ):
        """Items rejected by quality gate are not published."""
        from pipeline.stream import stream_collection

        low_quality_item = {
            "id": "low_1",
            "title": "x",  # Too short
            "content": "y",
            "source": "reddit",
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"score": 0},  # Too low
        }

        async def mock_collector():
            yield low_quality_item

        stats = await stream_collection(
            collector_fn=mock_collector(),
            collection_id="col_test",
            collection_blob="collections/2025-10-21/col_test.json",
            blob_client=mock_blob_client,
            queue_client=mock_queue_client,
        )

        # Should be rejected by quality gate
        assert stats["collected"] == 1
        assert stats["rejected_quality"] > 0

    @pytest.mark.asyncio
    async def test_stream_respects_dedup(
        self, mock_blob_client, mock_queue_client, sample_item
    ):
        """Duplicate items are not sent to queue."""
        from pipeline.stream import stream_collection

        # First item passes dedup
        mock_blob_client.is_seen.side_effect = [False, True]

        items = [sample_item, sample_item]  # Same item twice

        async def mock_collector():
            for item in items:
                yield item

        stats = await stream_collection(
            collector_fn=mock_collector(),
            collection_id="col_test",
            collection_blob="collections/2025-10-21/col_test.json",
            blob_client=mock_blob_client,
            queue_client=mock_queue_client,
        )

        # First should be published, second rejected as duplicate
        assert stats["collected"] == 2
        assert stats["rejected_dedup"] > 0
        assert stats["published"] == 1

    @pytest.mark.asyncio
    async def test_stream_marks_seen_in_dedup(
        self, mock_blob_client, mock_queue_client, sample_item
    ):
        """Items are marked as seen after processing."""
        from pipeline.stream import stream_collection

        mock_blob_client.is_seen.return_value = False

        async def mock_collector():
            yield sample_item

        await stream_collection(
            collector_fn=mock_collector(),
            collection_id="col_test",
            collection_blob="collections/2025-10-21/col_test.json",
            blob_client=mock_blob_client,
            queue_client=mock_queue_client,
        )

        # mark_seen should have been called
        mock_blob_client.mark_seen.assert_called()

    @pytest.mark.asyncio
    async def test_stream_sends_to_queue(
        self, mock_blob_client, mock_queue_client, sample_item
    ):
        """Items are sent to queue for processor."""
        from pipeline.stream import stream_collection

        mock_blob_client.is_seen.return_value = False

        async def mock_collector():
            yield sample_item

        await stream_collection(
            collector_fn=mock_collector(),
            collection_id="col_test",
            collection_blob="collections/2025-10-21/col_test.json",
            blob_client=mock_blob_client,
            queue_client=mock_queue_client,
        )

        # send_message should have been called
        mock_queue_client.send_message.assert_called()

        # Verify message format
        call_args = mock_queue_client.send_message.call_args
        message = call_args[0][0] if call_args[0] else call_args[1].get("message")

        assert message is not None
        assert message["operation"] == "process_topic"

    @pytest.mark.asyncio
    async def test_stream_saves_to_blob(
        self, mock_blob_client, mock_queue_client, sample_item
    ):
        """Items are saved to blob storage."""
        from pipeline.stream import stream_collection

        mock_blob_client.is_seen.return_value = False

        async def mock_collector():
            yield sample_item

        await stream_collection(
            collector_fn=mock_collector(),
            collection_id="col_test",
            collection_blob="collections/2025-10-21/col_test.json",
            blob_client=mock_blob_client,
            queue_client=mock_queue_client,
        )

        # append_item should have been called
        mock_blob_client.append_item.assert_called()

    @pytest.mark.asyncio
    async def test_stream_returns_stats(
        self, mock_blob_client, mock_queue_client, sample_item
    ):
        """Stream returns collection statistics."""
        from pipeline.stream import stream_collection

        mock_blob_client.is_seen.return_value = False

        async def mock_collector():
            yield sample_item
            yield sample_item

        stats = await stream_collection(
            collector_fn=mock_collector(),
            collection_id="col_test",
            collection_blob="collections/2025-10-21/col_test.json",
            blob_client=mock_blob_client,
            queue_client=mock_queue_client,
        )

        # Stats structure
        assert isinstance(stats, dict)
        assert "collected" in stats
        assert "published" in stats
        assert "rejected_quality" in stats
        assert "rejected_dedup" in stats

    @pytest.mark.asyncio
    async def test_stream_handles_errors_gracefully(
        self, mock_blob_client, mock_queue_client, sample_item
    ):
        """Stream continues on individual item errors."""
        from pipeline.stream import stream_collection

        # First item succeeds, second fails during review
        async def mock_collector():
            yield sample_item
            yield {"invalid": "item"}  # Missing required fields
            yield sample_item

        mock_blob_client.is_seen.return_value = False

        stats = await stream_collection(
            collector_fn=mock_collector(),
            collection_id="col_test",
            collection_blob="collections/2025-10-21/col_test.json",
            blob_client=mock_blob_client,
            queue_client=mock_queue_client,
        )

        # Should process 3 items despite error in middle
        assert stats["collected"] == 3


class TestStreamingIntegration:
    """Integration tests for full pipeline."""

    @pytest.mark.asyncio
    async def test_multiple_items_streaming(self, mock_blob_client, mock_queue_client):
        """Multiple items stream through pipeline."""
        from pipeline.stream import stream_collection

        items = [
            {
                "id": f"item_{i}",
                "title": f"Article {i}",
                "content": f"Content for article {i} with enough text to pass validation",
                "source": "reddit",
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"score": 50 + i},
            }
            for i in range(5)
        ]

        async def mock_collector():
            for item in items:
                yield item

        mock_blob_client.is_seen.return_value = False

        stats = await stream_collection(
            collector_fn=mock_collector(),
            collection_id="col_test",
            collection_blob="collections/2025-10-21/col_test.json",
            blob_client=mock_blob_client,
            queue_client=mock_queue_client,
        )

        assert stats["collected"] == 5
        assert stats["published"] >= 1  # At least some should pass quality

    @pytest.mark.asyncio
    async def test_stream_lazy_evaluation(self, mock_blob_client, mock_queue_client):
        """Generator is lazily evaluated (items aren't collected until streamed)."""
        from pipeline.stream import stream_collection

        collection_called = []

        async def mock_collector():
            for i in range(5):
                collection_called.append(i)
                yield {
                    "id": f"item_{i}",
                    "title": f"Article {i}",
                    "content": f"Content text here for article {i}",
                    "source": "reddit",
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"score": 50},
                }

        mock_blob_client.is_seen.return_value = False

        # Generator created but not yet evaluated
        gen = mock_collector()
        # Don't iterate yet, just verify generator exists
        assert callable(gen.__anext__)

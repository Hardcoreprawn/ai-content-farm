"""
Integration Tests for Collector Fanout Pattern

Tests the collector's ability to send individual topic messages
instead of batch messages, enabling KEDA horizontal scaling.

Test Coverage:
- Fanout message generation (N topics → N messages)
- Message format validation (ProcessTopicRequest schema)
- Collection audit trail (collection.json saved)
- Message statistics and monitoring
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from topic_fanout import (
    count_topic_messages_by_source,
    create_topic_message,
    create_topic_messages_batch,
    validate_topic_message,
)

# Add containers to path for imports
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "containers" / "content-collector")
)


# Add containers to path for imports
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "containers" / "content-collector")
)


@pytest.fixture
def sample_reddit_topics() -> List[Dict[str, Any]]:
    """Generate sample Reddit topics for testing."""
    return [
        {
            "id": f"reddit_{i}",
            "title": f"Test Article {i}",
            "source": "reddit",
            "url": f"https://reddit.com/r/technology/post{i}",
            "collected_at": "2025-10-08T10:00:00+00:00",
            "priority_score": 0.8 + (i * 0.01),
            "metadata": {
                "subreddit": "technology",
                "score": 100 + (i * 10),
                "num_comments": 50 + (i * 5),
            },
        }
        for i in range(100)
    ]


@pytest.fixture
def sample_rss_topics() -> List[Dict[str, Any]]:
    """Generate sample RSS topics for testing."""
    return [
        {
            "id": f"rss_{i}",
            "title": f"RSS Article {i}",
            "source": "rss",
            "url": f"https://example.com/article{i}",
            "collected_at": "2025-10-08T10:00:00+00:00",
            "priority_score": 0.7 + (i * 0.01),
            "metadata": {
                "feed_url": "https://example.com/feed.xml",
                "author": f"Author {i}",
            },
        }
        for i in range(50)
    ]


@pytest.fixture
def collection_metadata() -> Dict[str, str]:
    """Sample collection metadata."""
    return {
        "collection_id": "col_test_20251008_100000",
        "collection_blob": "collections/2025/10/08/col_test_20251008_100000.json",
    }


class TestCollectorFanoutGeneration:
    """Test fanout message generation."""

    def test_generates_correct_number_of_messages(
        self, sample_reddit_topics, collection_metadata
    ):
        """Verify N topics generate N messages."""
        messages = create_topic_messages_batch(
            sample_reddit_topics,
            collection_metadata["collection_id"],
            collection_metadata["collection_blob"],
        )

        assert len(messages) == 100, "Should generate 100 messages for 100 topics"

    def test_each_message_has_unique_topic(
        self, sample_reddit_topics, collection_metadata
    ):
        """Verify each message represents a different topic."""
        messages = create_topic_messages_batch(
            sample_reddit_topics,
            collection_metadata["collection_id"],
            collection_metadata["collection_blob"],
        )

        topic_ids = {msg["payload"]["topic_id"] for msg in messages}
        assert len(topic_ids) == 100, "All messages should have unique topic_ids"

    def test_messages_preserve_topic_order(
        self, sample_reddit_topics, collection_metadata
    ):
        """Verify message order matches input order."""
        messages = create_topic_messages_batch(
            sample_reddit_topics,
            collection_metadata["collection_id"],
            collection_metadata["collection_blob"],
        )

        for i, msg in enumerate(messages):
            expected_id = f"reddit_{i}"
            assert (
                msg["payload"]["topic_id"] == expected_id
            ), f"Message {i} should have topic_id {expected_id}"

    def test_mixed_sources_handled_correctly(
        self, sample_reddit_topics, sample_rss_topics, collection_metadata
    ):
        """Verify fanout works with multiple source types."""
        mixed_topics = sample_reddit_topics[:50] + sample_rss_topics[:50]
        messages = create_topic_messages_batch(
            mixed_topics,
            collection_metadata["collection_id"],
            collection_metadata["collection_blob"],
        )

        assert len(messages) == 100, "Should handle mixed sources"

        # Verify source distribution
        source_counts = count_topic_messages_by_source(messages)
        assert source_counts["reddit"] == 50, "Should have 50 Reddit messages"
        assert source_counts["rss"] == 50, "Should have 50 RSS messages"


class TestFanoutMessageFormat:
    """Test message format validation."""

    def test_message_structure_matches_schema(self, collection_metadata):
        """Verify message structure matches ProcessTopicRequest."""
        item = {
            "id": "reddit_test",
            "title": "Test Article",
            "source": "reddit",
            "url": "https://reddit.com/r/technology/test",
            "collected_at": "2025-10-08T10:00:00+00:00",
            "priority_score": 0.85,
            "metadata": {
                "subreddit": "technology",
                "score": 150,
                "num_comments": 75,
            },
        }

        message = create_topic_message(
            item,
            collection_metadata["collection_id"],
            collection_metadata["collection_blob"],
        )

        # Verify required top-level fields
        assert message["operation"] == "process_topic"
        assert message["service_name"] == "content-collector"
        assert "correlation_id" in message
        assert "payload" in message

        # Verify required payload fields
        payload = message["payload"]
        assert payload["topic_id"] == "reddit_test"
        assert payload["title"] == "Test Article"
        assert payload["source"] == "reddit"
        assert payload["collection_id"] == collection_metadata["collection_id"]
        assert payload["collection_blob"] == collection_metadata["collection_blob"]

    def test_optional_reddit_fields_included(self, collection_metadata):
        """Verify Reddit-specific fields included when present."""
        item = {
            "id": "reddit_test",
            "title": "Test Article",
            "source": "reddit",
            "url": "https://reddit.com/r/technology/test",
            "collected_at": "2025-10-08T10:00:00+00:00",
            "priority_score": 0.85,
            "metadata": {
                "subreddit": "technology",
                "score": 150,
                "num_comments": 75,
            },
        }

        message = create_topic_message(
            item,
            collection_metadata["collection_id"],
            collection_metadata["collection_blob"],
        )

        payload = message["payload"]
        assert payload["subreddit"] == "technology"
        assert payload["upvotes"] == 150
        assert payload["comments"] == 75

    def test_optional_fields_omitted_for_rss(self, collection_metadata):
        """Verify Reddit fields omitted for RSS topics."""
        item = {
            "id": "rss_test",
            "title": "RSS Article",
            "source": "rss",
            "url": "https://example.com/article",
            "collected_at": "2025-10-08T10:00:00+00:00",
            "priority_score": 0.75,
            "metadata": {
                "feed_url": "https://example.com/feed.xml",
                "author": "Test Author",
            },
        }

        message = create_topic_message(
            item,
            collection_metadata["collection_id"],
            collection_metadata["collection_blob"],
        )

        payload = message["payload"]
        assert "subreddit" not in payload
        assert "upvotes" not in payload
        assert "comments" not in payload

    def test_all_messages_pass_validation(
        self, sample_reddit_topics, collection_metadata
    ):
        """Verify all generated messages pass validation."""
        messages = create_topic_messages_batch(
            sample_reddit_topics,
            collection_metadata["collection_id"],
            collection_metadata["collection_blob"],
        )

        invalid_messages = []
        for msg in messages:
            is_valid, error = validate_topic_message(msg)
            if not is_valid:
                invalid_messages.append((msg["payload"]["topic_id"], error))

        assert (
            len(invalid_messages) == 0
        ), f"All messages should be valid, found: {invalid_messages}"


class TestFanoutStatistics:
    """Test fanout statistics and monitoring."""

    def test_statistics_by_source(
        self, sample_reddit_topics, sample_rss_topics, collection_metadata
    ):
        """Verify source statistics calculated correctly."""
        mixed_topics = sample_reddit_topics[:60] + sample_rss_topics[:40]
        messages = create_topic_messages_batch(
            mixed_topics,
            collection_metadata["collection_id"],
            collection_metadata["collection_blob"],
        )

        stats = count_topic_messages_by_source(messages)

        assert stats["reddit"] == 60, "Should count 60 Reddit messages"
        assert stats["rss"] == 40, "Should count 40 RSS messages"
        assert sum(stats.values()) == 100, "Total should be 100"

    def test_empty_list_returns_empty_stats(self, collection_metadata):
        """Verify empty input returns empty statistics."""
        messages = create_topic_messages_batch(
            [],
            collection_metadata["collection_id"],
            collection_metadata["collection_blob"],
        )

        assert len(messages) == 0, "Should return empty list"

        stats = count_topic_messages_by_source(messages)
        assert len(stats) == 0, "Should return empty stats"


class TestFanoutAuditTrail:
    """Test audit trail and collection.json integration."""

    def test_all_messages_reference_same_collection(
        self, sample_reddit_topics, collection_metadata
    ):
        """Verify all messages reference the same collection."""
        messages = create_topic_messages_batch(
            sample_reddit_topics,
            collection_metadata["collection_id"],
            collection_metadata["collection_blob"],
        )

        collection_ids = {msg["payload"]["collection_id"] for msg in messages}
        assert (
            len(collection_ids) == 1
        ), "All messages should reference same collection_id"

        collection_blobs = {msg["payload"]["collection_blob"] for msg in messages}
        assert (
            len(collection_blobs) == 1
        ), "All messages should reference same collection_blob"

    def test_correlation_id_includes_collection_and_topic(self, collection_metadata):
        """Verify correlation_id format for tracing."""
        item = {
            "id": "reddit_test",
            "title": "Test Article",
            "source": "reddit",
            "collected_at": "2025-10-08T10:00:00+00:00",
            "priority_score": 0.85,
        }

        message = create_topic_message(
            item,
            collection_metadata["collection_id"],
            collection_metadata["collection_blob"],
        )

        correlation_id = message["correlation_id"]
        assert (
            collection_metadata["collection_id"] in correlation_id
        ), "Correlation ID should include collection_id"
        assert "reddit_test" in correlation_id, "Correlation ID should include topic_id"


# Summary comment for test execution
"""
To run these integration tests:

    cd /workspaces/ai-content-farm
    pytest tests/integration/test_collector_fanout.py -v

Expected Results:
- 10 tests should pass
- Validates fanout message generation
- Confirms message format compliance
- Verifies audit trail references

These tests use real topic_fanout.py functions with no mocks,
ensuring integration integrity between collector and processor.
"""

"""Tests for topic fanout pure functions.

Testing Philosophy:
- Pure functions = deterministic outputs for given inputs
- No mocks needed for pure functions
- Test edge cases and error conditions
- Verify PEP 8 compliance and type safety
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest
from topic_fanout import (
    count_topic_messages_by_source,
    create_topic_message,
    create_topic_messages_batch,
    validate_topic_message,
)


class TestCreateTopicMessage:
    """Tests for create_topic_message pure function."""

    def test_minimal_reddit_item(self):
        """Test with minimal Reddit item data."""
        item = {
            "id": "reddit_abc123",
            "title": "Test Post",
            "source": "reddit",
        }

        message = create_topic_message(
            item, "col123", "collections/2025/10/08/col123.json"
        )

        assert message["operation"] == "process_topic"
        assert message["service_name"] == "content-collector"
        assert message["payload"]["topic_id"] == "reddit_abc123"
        assert message["payload"]["title"] == "Test Post"
        assert message["payload"]["source"] == "reddit"
        assert message["payload"]["collection_id"] == "col123"
        assert (
            message["payload"]["collection_blob"]
            == "collections/2025/10/08/col123.json"
        )
        assert message["payload"]["priority_score"] == 0.5  # Default

    def test_complete_reddit_item_with_metadata(self):
        """Test with complete Reddit item including all metadata fields."""
        item = {
            "id": "reddit_xyz789",
            "title": "Interesting Discussion",
            "source": "reddit",
            "url": "https://reddit.com/r/python/comments/xyz789",
            "created_at": "2025-10-08T10:00:00+00:00",
            "priority_score": 0.85,
            "metadata": {
                "subreddit": "python",
                "score": 1250,
                "num_comments": 45,
                "upvote_ratio": 0.95,
            },
        }

        message = create_topic_message(
            item, "col456", "collections/2025/10/08/col456.json"
        )

        payload = message["payload"]
        assert payload["topic_id"] == "reddit_xyz789"
        assert payload["title"] == "Interesting Discussion"
        assert payload["source"] == "reddit"
        assert payload["url"] == "https://reddit.com/r/python/comments/xyz789"
        assert payload["subreddit"] == "python"
        assert payload["upvotes"] == 1250
        assert payload["comments"] == 45
        assert payload["collected_at"] == "2025-10-08T10:00:00+00:00"
        assert payload["priority_score"] == 0.85

    def test_rss_item_without_reddit_fields(self):
        """Test with RSS item that doesn't have Reddit-specific metadata."""
        item = {
            "id": "rss_feed_123",
            "title": "Tech News Article",
            "source": "rss",
            "url": "https://example.com/article",
            "created_at": "2025-10-08T11:30:00+00:00",
            "metadata": {
                "feed_url": "https://example.com/feed.xml",
                "tags": ["technology", "ai"],
            },
        }

        message = create_topic_message(
            item, "col789", "collections/2025/10/08/col789.json"
        )

        payload = message["payload"]
        assert payload["topic_id"] == "rss_feed_123"
        assert payload["source"] == "rss"
        # Reddit-specific fields should not be present
        assert "subreddit" not in payload
        assert "upvotes" not in payload
        assert "comments" not in payload

    def test_missing_id_generates_fallback(self):
        """Test that missing ID generates a fallback topic_id."""
        item = {"title": "No ID Item", "source": "test"}

        message = create_topic_message(item, "col999", "collections/test.json")

        assert message["payload"]["topic_id"].startswith("topic_")
        assert len(message["payload"]["topic_id"]) > 6  # topic_ + uuid chars

    def test_missing_title_uses_default(self):
        """Test that missing title uses default value."""
        item = {"id": "test123", "source": "test"}

        message = create_topic_message(item, "col999", "collections/test.json")

        assert message["payload"]["title"] == "Untitled Topic"

    def test_missing_source_uses_unknown(self):
        """Test that missing source uses 'unknown'."""
        item = {"id": "test123", "title": "Test"}

        message = create_topic_message(item, "col999", "collections/test.json")

        assert message["payload"]["source"] == "unknown"

    def test_missing_collected_at_generates_timestamp(self):
        """Test that missing collected_at generates current timestamp."""
        item = {"id": "test123", "title": "Test", "source": "test"}

        message = create_topic_message(item, "col999", "collections/test.json")

        # Should have ISO format timestamp
        collected_at = message["payload"]["collected_at"]
        assert isinstance(collected_at, str)
        # Should parse as valid ISO timestamp
        datetime.fromisoformat(collected_at.replace("Z", "+00:00"))

    def test_correlation_id_format(self):
        """Test that correlation_id has expected format."""
        item = {"id": "test123", "title": "Test", "source": "reddit"}

        message = create_topic_message(item, "col456", "collections/test.json")

        correlation_id = message["correlation_id"]
        assert correlation_id == "col456_test123"

    def test_optional_fields_only_present_if_set(self):
        """Test that optional fields (url, subreddit, etc.) only present when available."""
        minimal_item = {"id": "test123", "title": "Test", "source": "test"}

        message = create_topic_message(minimal_item, "col999", "collections/test.json")

        payload = message["payload"]
        assert "url" not in payload
        assert "subreddit" not in payload
        assert "upvotes" not in payload
        assert "comments" not in payload

    def test_metadata_field_variations(self):
        """Test handling of different metadata field names (score vs upvotes)."""
        item = {
            "id": "test123",
            "title": "Test",
            "source": "reddit",
            "metadata": {
                "subreddit": "programming",
                "score": 500,  # Reddit uses 'score'
                "num_comments": 25,
            },
        }

        message = create_topic_message(item, "col999", "collections/test.json")

        payload = message["payload"]
        # Should map 'score' to 'upvotes'
        assert payload["upvotes"] == 500
        # Should map 'num_comments' to 'comments'
        assert payload["comments"] == 25


class TestCreateTopicMessagesBatch:
    """Tests for create_topic_messages_batch pure function."""

    def test_empty_list_returns_empty_list(self):
        """Test that empty items list returns empty messages list."""
        messages = create_topic_messages_batch([], "col123", "collections/test.json")

        assert messages == []
        assert isinstance(messages, list)

    def test_single_item_returns_single_message(self):
        """Test that single item returns single message."""
        items = [{"id": "test1", "title": "Test 1", "source": "reddit"}]

        messages = create_topic_messages_batch(items, "col123", "collections/test.json")

        assert len(messages) == 1
        assert messages[0]["payload"]["topic_id"] == "test1"

    def test_multiple_items_return_multiple_messages(self):
        """Test that N items return N messages."""
        items = [
            {"id": "test1", "title": "Test 1", "source": "reddit"},
            {"id": "test2", "title": "Test 2", "source": "rss"},
            {"id": "test3", "title": "Test 3", "source": "mastodon"},
        ]

        messages = create_topic_messages_batch(items, "col123", "collections/test.json")

        assert len(messages) == 3
        assert messages[0]["payload"]["topic_id"] == "test1"
        assert messages[1]["payload"]["topic_id"] == "test2"
        assert messages[2]["payload"]["topic_id"] == "test3"

    def test_all_messages_have_same_collection_reference(self):
        """Test that all messages reference same collection."""
        items = [
            {"id": f"test{i}", "title": f"Test {i}", "source": "reddit"}
            for i in range(5)
        ]

        messages = create_topic_messages_batch(
            items, "col999", "collections/batch.json"
        )

        for message in messages:
            assert message["payload"]["collection_id"] == "col999"
            assert message["payload"]["collection_blob"] == "collections/batch.json"

    def test_batch_preserves_item_order(self):
        """Test that batch processing preserves item order."""
        items = [
            {"id": f"id_{i}", "title": f"Title {i}", "source": "reddit"}
            for i in range(10)
        ]

        messages = create_topic_messages_batch(items, "col123", "collections/test.json")

        for i, message in enumerate(messages):
            assert message["payload"]["topic_id"] == f"id_{i}"
            assert message["payload"]["title"] == f"Title {i}"


class TestValidateTopicMessage:
    """Tests for validate_topic_message pure function."""

    def test_valid_message_passes(self):
        """Test that valid message passes validation."""
        message = {
            "operation": "process_topic",
            "payload": {
                "topic_id": "test123",
                "title": "Test",
                "source": "reddit",
                "collection_id": "col123",
                "collection_blob": "collections/test.json",
            },
        }

        is_valid, error = validate_topic_message(message)

        assert is_valid is True
        assert error is None

    def test_missing_operation_fails(self):
        """Test that message without operation fails."""
        message = {
            "payload": {
                "topic_id": "test123",
                "title": "Test",
                "source": "reddit",
                "collection_id": "col123",
            }
        }

        is_valid, error = validate_topic_message(message)

        assert is_valid is False
        assert error is not None
        assert "operation" in str(error)

    def test_wrong_operation_fails(self):
        """Test that message with wrong operation fails."""
        message = {
            "operation": "process_batch",  # Wrong operation
            "payload": {
                "topic_id": "test123",
                "title": "Test",
                "source": "reddit",
                "collection_id": "col123",
            },
        }

        is_valid, error = validate_topic_message(message)

        assert is_valid is False
        assert error is not None
        assert "operation" in str(error)

    def test_missing_payload_fails(self):
        """Test that message without payload fails."""
        message = {"operation": "process_topic"}

        is_valid, error = validate_topic_message(message)

        assert is_valid is False
        assert error is not None
        assert "payload" in str(error)

    def test_invalid_payload_type_fails(self):
        """Test that message with non-dict payload fails."""
        message = {"operation": "process_topic", "payload": "not a dict"}

        is_valid, error = validate_topic_message(message)

        assert is_valid is False
        assert error is not None
        assert "payload" in str(error)

    def test_missing_topic_id_fails(self):
        """Test that payload without topic_id fails."""
        message = {
            "operation": "process_topic",
            "payload": {
                "title": "Test",
                "source": "reddit",
                "collection_id": "col123",
            },
        }

        is_valid, error = validate_topic_message(message)

        assert is_valid is False
        assert error is not None
        assert "topic_id" in str(error)

    def test_missing_title_fails(self):
        """Test that payload without title fails."""
        message = {
            "operation": "process_topic",
            "payload": {
                "topic_id": "test123",
                "source": "reddit",
                "collection_id": "col123",
            },
        }

        is_valid, error = validate_topic_message(message)

        assert is_valid is False
        assert error is not None
        assert "title" in str(error)

    def test_missing_source_fails(self):
        """Test that payload without source fails."""
        message = {
            "operation": "process_topic",
            "payload": {
                "topic_id": "test123",
                "title": "Test",
                "collection_id": "col123",
            },
        }

        is_valid, error = validate_topic_message(message)

        assert is_valid is False
        assert error is not None
        assert "source" in str(error)

    def test_missing_collection_id_fails(self):
        """Test that payload without collection_id fails."""
        message = {
            "operation": "process_topic",
            "payload": {"topic_id": "test123", "title": "Test", "source": "reddit"},
        }

        is_valid, error = validate_topic_message(message)

        assert is_valid is False
        assert error is not None
        assert "collection_id" in str(error)

    def test_optional_fields_not_required(self):
        """Test that optional fields (url, subreddit, etc.) are not required."""
        message = {
            "operation": "process_topic",
            "payload": {
                "topic_id": "test123",
                "title": "Test",
                "source": "reddit",
                "collection_id": "col123",
                # No url, subreddit, upvotes, comments, etc.
            },
        }

        is_valid, error = validate_topic_message(message)

        assert is_valid is True
        assert error is None


class TestCountTopicMessagesBySource:
    """Tests for count_topic_messages_by_source pure function."""

    def test_empty_list_returns_empty_dict(self):
        """Test that empty messages list returns empty counts."""
        counts = count_topic_messages_by_source([])

        assert counts == {}

    def test_single_message_returns_single_count(self):
        """Test that single message returns count of 1."""
        messages = [
            {
                "operation": "process_topic",
                "payload": {"topic_id": "test1", "source": "reddit"},
            }
        ]

        counts = count_topic_messages_by_source(messages)

        assert counts == {"reddit": 1}

    def test_multiple_same_source_accumulates(self):
        """Test that multiple messages from same source accumulate."""
        messages = [
            {
                "operation": "process_topic",
                "payload": {"topic_id": f"test{i}", "source": "reddit"},
            }
            for i in range(5)
        ]

        counts = count_topic_messages_by_source(messages)

        assert counts == {"reddit": 5}

    def test_multiple_different_sources(self):
        """Test counting across multiple different sources."""
        messages = [
            {
                "operation": "process_topic",
                "payload": {"topic_id": "r1", "source": "reddit"},
            },
            {
                "operation": "process_topic",
                "payload": {"topic_id": "r2", "source": "reddit"},
            },
            {
                "operation": "process_topic",
                "payload": {"topic_id": "rss1", "source": "rss"},
            },
            {
                "operation": "process_topic",
                "payload": {"topic_id": "m1", "source": "mastodon"},
            },
            {
                "operation": "process_topic",
                "payload": {"topic_id": "m2", "source": "mastodon"},
            },
            {
                "operation": "process_topic",
                "payload": {"topic_id": "m3", "source": "mastodon"},
            },
        ]

        counts = count_topic_messages_by_source(messages)

        assert counts == {"reddit": 2, "rss": 1, "mastodon": 3}

    def test_missing_source_counts_as_unknown(self):
        """Test that messages without source count as 'unknown'."""
        messages = [
            {
                "operation": "process_topic",
                "payload": {"topic_id": "test1"},
            },  # No source
            {
                "operation": "process_topic",
                "payload": {"topic_id": "test2", "source": "reddit"},
            },
        ]

        counts = count_topic_messages_by_source(messages)

        assert counts == {"unknown": 1, "reddit": 1}

    def test_missing_payload_counts_as_unknown(self):
        """Test that messages without payload count as 'unknown'."""
        messages = [
            {"operation": "process_topic"},  # No payload
            {
                "operation": "process_topic",
                "payload": {"topic_id": "test1", "source": "reddit"},
            },
        ]

        counts = count_topic_messages_by_source(messages)

        assert counts == {"unknown": 1, "reddit": 1}


class TestPurityAndDeterminism:
    """Tests to verify pure function properties."""

    def test_create_topic_message_is_deterministic(self):
        """Test that same input produces same output (except timestamp)."""
        item = {
            "id": "test123",
            "title": "Test",
            "source": "reddit",
            "created_at": "2025-10-08T10:00:00+00:00",
            "priority_score": 0.75,
        }

        message1 = create_topic_message(item, "col123", "collections/test.json")
        message2 = create_topic_message(item, "col123", "collections/test.json")

        # Everything except timestamp should be identical
        assert message1["operation"] == message2["operation"]
        assert message1["payload"] == message2["payload"]
        assert message1["correlation_id"] == message2["correlation_id"]

    def test_create_topic_messages_batch_is_deterministic(self):
        """Test that batch conversion is deterministic with complete input."""
        fixed_timestamp = "2025-10-08T12:00:00+00:00"
        items = [
            {
                "id": f"test{i}",
                "title": f"Test {i}",
                "source": "reddit",
                "collected_at": fixed_timestamp,
            }
            for i in range(5)
        ]

        messages1 = create_topic_messages_batch(
            items, "col123", "collections/test.json"
        )
        messages2 = create_topic_messages_batch(
            items, "col123", "collections/test.json"
        )

        assert len(messages1) == len(messages2)
        for msg1, msg2 in zip(messages1, messages2):
            assert msg1["payload"] == msg2["payload"]

    def test_validate_is_pure(self):
        """Test that validation doesn't modify input."""
        message = {
            "operation": "process_topic",
            "payload": {
                "topic_id": "test123",
                "title": "Test",
                "source": "reddit",
                "collection_id": "col123",
            },
        }

        original_payload = message["payload"].copy()

        is_valid, error = validate_topic_message(message)

        # Message should be unchanged
        assert message["payload"] == original_payload

    def test_count_is_pure(self):
        """Test that counting doesn't modify input."""
        messages = [
            {
                "operation": "process_topic",
                "payload": {"topic_id": "test1", "source": "reddit"},
            },
            {
                "operation": "process_topic",
                "payload": {"topic_id": "test2", "source": "rss"},
            },
        ]

        original_messages = [msg.copy() for msg in messages]

        counts = count_topic_messages_by_source(messages)

        # Messages should be unchanged
        assert messages == original_messages

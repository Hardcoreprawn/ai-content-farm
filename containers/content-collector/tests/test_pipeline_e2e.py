"""
End-to-end integration test: Full streaming pipeline.

Tests complete flow:
  Reddit/Mastodon collection → Quality review → Deduplication → Queue message

Verifies:
  1. Items flow through pipeline correctly
  2. Quality filtering rejects invalid items
  3. Deduplication prevents duplicates
  4. Queue message format matches content-processor expectations
  5. Stats tracking is accurate
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pipeline.dedup import hash_content
from pipeline.stream import create_queue_message, stream_collection
from quality.review import review_item


class MockBlobClient:
    """Mock Azure Blob Storage client for testing."""

    def __init__(self):
        """Initialize mock with empty dedup state."""
        self.deduplicated = {}  # date -> set of hashes
        self.items = []  # All appended items

    async def append_item(self, collection_id: str, item: Dict[str, Any]) -> bool:
        """Append item to collection."""
        self.items.append({"collection_id": collection_id, "item": item})
        return True

    async def download_json(self, blob_name: str) -> Dict[str, Any]:
        """Download JSON blob (dedup storage)."""
        if blob_name in self.deduplicated:
            return {"hashes": list(self.deduplicated[blob_name])}
        raise Exception(f"Blob not found: {blob_name}")

    async def upload_json(self, blob_name: str, data: Dict[str, Any]) -> bool:
        """Upload JSON blob (dedup storage)."""
        # Extract date from blob name
        if "deduplicated-content/" in blob_name:
            date_str = blob_name.split("/")[1].replace(".json", "")
            if date_str not in self.deduplicated:
                self.deduplicated[date_str] = set()
            if isinstance(data, dict) and "hashes" in data:
                self.deduplicated[date_str].update(data["hashes"])
            elif isinstance(data, list):
                self.deduplicated[date_str].update(data)
        return True


class MockQueueClient:
    """Mock Azure Storage Queue client for testing."""

    def __init__(self):
        """Initialize mock with empty queue."""
        self.messages = []

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message to queue."""
        self.messages.append(message)
        return True


class TestStreamCollectionE2E:
    """End-to-end tests for complete streaming pipeline."""

    @pytest.fixture
    def setup_clients(self):
        """Setup mock blob and queue clients."""
        return MockBlobClient(), MockQueueClient()

    @pytest.fixture
    def sample_items(self):
        """Sample items with various quality levels."""
        return [
            {
                "id": "reddit_1",
                "title": "Advanced Python Async Patterns in Production",
                "content": "Long technical article about async/await patterns, concurrency, and best practices in Python development for production systems.",
                "source": "reddit",
                "metadata": {
                    "subreddit": "programming",
                    "url": "https://reddit.com/r/programming/post1",
                    "score": 150,
                    "num_comments": 45,
                    "author": "tech_expert",
                },
            },
            {
                "id": "mastodon_1",
                "title": "Kubernetes Security Best Practices 2025",
                "content": "Comprehensive guide to securing Kubernetes deployments, covering network policies, RBAC, pod security standards, and runtime security monitoring.",
                "source": "mastodon",
                "metadata": {
                    "instance": "fosstodon.org",
                    "url": "https://fosstodon.org/@devops/123456",
                    "boosts": 89,
                    "author": "kubernetes_expert",
                },
            },
            {
                "id": "reddit_2",
                "title": "Short",  # Will be rejected (too short)
                "content": "Too short",
                "source": "reddit",
            },
            {
                "id": "reddit_3",
                # Will be rejected (not readable)
                "title": "123456789 @@@@@@@@@@",
                "content": "This has enough content to pass length check but the title is symbols"
                * 5,
                "source": "reddit",
            },
            {
                "id": "reddit_4",
                "title": "Non-technical Article About Cats",
                "content": "This is a long article about how cute cats are and their various behaviors and personality types.",
                "source": "reddit",
            },
        ]

    async def mock_collector(self, items: list) -> AsyncIterator[Dict[str, Any]]:
        """Mock async generator that yields items."""
        for item in items:
            await asyncio.sleep(0)  # Simulate async I/O
            yield item

    @pytest.mark.asyncio
    async def test_e2e_basic_flow(self, setup_clients, sample_items):
        """Test basic pipeline flow: collection → review → dedup → queue."""
        blob_client, queue_client = setup_clients

        collector_fn = self.mock_collector(sample_items[:2])

        stats = await stream_collection(
            collector_fn=collector_fn,
            collection_id="test_collection_001",
            collection_blob="collections/test_collection_001.json",
            blob_client=blob_client,
            queue_client=queue_client,
        )

        # Verify stats
        assert stats["collected"] == 2
        assert stats["published"] == 2
        assert stats["rejected_quality"] == 0
        assert stats["rejected_dedup"] == 0

        # Verify items were appended
        assert len(blob_client.items) == 2

        # Verify queue messages were sent
        assert len(queue_client.messages) == 2

    @pytest.mark.asyncio
    async def test_e2e_quality_filtering(self, setup_clients, sample_items):
        """Test quality filtering rejects low-quality items."""
        blob_client, queue_client = setup_clients

        # Use all items (includes low-quality ones)
        collector_fn = self.mock_collector(sample_items)

        stats = await stream_collection(
            collector_fn=collector_fn,
            collection_id="test_collection_002",
            collection_blob="collections/test_collection_002.json",
            blob_client=blob_client,
            queue_client=queue_client,
        )

        # First 2 items are high quality
        # Item 3 is too short (rejected)
        # Item 4 has unreadable title (rejected)
        # Item 5 is off-topic (rejected)
        assert stats["collected"] == 5
        assert stats["published"] == 2  # Only first 2 pass quality
        assert stats["rejected_quality"] == 3  # 3, 4, 5 rejected

        # Verify only good items in queue
        assert len(queue_client.messages) == 2

    @pytest.mark.asyncio
    async def test_e2e_deduplication(self, setup_clients, sample_items):
        """Test deduplication prevents duplicate items."""
        blob_client, queue_client = setup_clients

        # Create duplicate of first item
        duplicate_item = sample_items[0].copy()
        duplicate_item["id"] = "reddit_1_duplicate"

        items_with_duplicate = sample_items[:2] + [duplicate_item]

        collector_fn = self.mock_collector(items_with_duplicate)

        stats = await stream_collection(
            collector_fn=collector_fn,
            collection_id="test_collection_003",
            collection_blob="collections/test_collection_003.json",
            blob_client=blob_client,
            queue_client=queue_client,
        )

        # First 2 unique, 3rd is duplicate
        assert stats["collected"] == 3
        assert stats["published"] == 2  # Duplicate rejected
        assert stats["rejected_dedup"] == 1

        # Verify queue only has 2 messages (no duplicate)
        assert len(queue_client.messages) == 2

    @pytest.mark.asyncio
    async def test_e2e_queue_message_format(self, setup_clients):
        """Test queue message format matches content-processor expectations."""
        blob_client, queue_client = setup_clients

        item = {
            "id": "test_1",
            "title": "Advanced Test Article Title for Processing Systems",
            "content": "This is comprehensive test content about software development and technical topics. It covers best practices, design patterns, and implementation strategies for modern software systems. The article discusses how to build scalable applications with proper architecture.",
            "source": "reddit",
            "url": "https://example.com/article",
            "collected_at": "2025-10-21T12:00:00Z",
            "metadata": {
                "subreddit": "programming",
                "url": "https://reddit.com/r/programming/xyz",
                "score": 100,
                "num_comments": 25,
                "author": "test_user",
            },
        }

        items = [item]
        collector_fn = self.mock_collector(items)

        await stream_collection(
            collector_fn=collector_fn,
            collection_id="test_collection_004",
            collection_blob="collections/test_collection_004.json",
            blob_client=blob_client,
            queue_client=queue_client,
        )

        # Verify message was sent
        assert len(queue_client.messages) == 1

        message = queue_client.messages[0]

        # Verify message structure
        assert message["operation"] == "process_topic"
        assert message["service_name"] == "content-collector"
        assert "timestamp" in message
        assert "correlation_id" in message
        assert "payload" in message

        # Verify payload content
        payload = message["payload"]
        assert payload["topic_id"] == "test_1"
        assert payload["title"] == "Advanced Test Article Title for Processing Systems"
        assert payload["source"] == "reddit"
        assert payload["collection_id"] == "test_collection_004"
        assert payload["collection_blob"] == "collections/test_collection_004.json"
        assert payload["subreddit"] == "programming"
        assert payload["url"] == "https://reddit.com/r/programming/xyz"
        assert payload["upvotes"] == 100
        assert payload["comments"] == 25
        assert payload["author"] == "test_user"

    @pytest.mark.asyncio
    async def test_e2e_missing_optional_fields(self, setup_clients):
        """Test queue message handles items with minimal optional fields."""
        blob_client, queue_client = setup_clients

        minimal_item = {
            "id": "minimal_1",
            "title": "Minimal Article Title for Testing Pipeline Architecture",
            "content": "This minimal content still contains important information about technology and software development practices. It demonstrates how systems work together and what best practices mean for teams building applications.",
            "source": "mastodon",
        }

        items = [minimal_item]
        collector_fn = self.mock_collector(items)

        await stream_collection(
            collector_fn=collector_fn,
            collection_id="test_collection_005",
            collection_blob="collections/test_collection_005.json",
            blob_client=blob_client,
            queue_client=queue_client,
        )

        assert len(queue_client.messages) == 1

        message = queue_client.messages[0]
        payload = message["payload"]

        # Required fields present
        assert payload["topic_id"] == "minimal_1"
        assert (
            payload["title"]
            == "Minimal Article Title for Testing Pipeline Architecture"
        )
        assert payload["source"] == "mastodon"

        # Optional fields should use defaults or be absent
        assert payload.get("subreddit") is None
        assert payload.get("url") is None
        assert payload.get("upvotes") is None
        assert payload.get("author") is None

    @pytest.mark.asyncio
    async def test_e2e_error_recovery(self, setup_clients, sample_items):
        """Test pipeline continues on individual item errors."""
        blob_client, queue_client = setup_clients

        # Add item with missing required field
        items_with_bad = sample_items[:2].copy()
        bad_item = {"id": "bad_1"}  # Missing required fields
        items_with_bad.insert(1, bad_item)

        collector_fn = self.mock_collector(items_with_bad)

        stats = await stream_collection(
            collector_fn=collector_fn,
            collection_id="test_collection_006",
            collection_blob="collections/test_collection_006.json",
            blob_client=blob_client,
            queue_client=queue_client,
        )

        # Bad item rejected during quality review
        assert stats["collected"] == 3
        assert stats["rejected_quality"] == 1  # Bad item
        assert stats["published"] == 2  # Two good items

        # Good items still processed
        assert len(queue_client.messages) == 2

    @pytest.mark.asyncio
    async def test_e2e_stats_accuracy(self, setup_clients):
        """Test stats tracking is accurate across all scenarios."""
        blob_client, queue_client = setup_clients

        items = [
            {
                "id": "high_quality_1",
                "title": "First High Quality Technical Article",
                "content": "This is a detailed technical article with substantial content about software engineering practices and methodologies.",
                "source": "reddit",
            },
            {
                "id": "high_quality_2",
                "title": "Second High Quality Technical Article",
                "content": "Another technical article discussing advanced programming concepts and design patterns in modern software development.",
                "source": "reddit",
            },
            {
                "id": "low_quality_1",
                "title": "Bad",  # Too short - rejected
                "content": "Bad",
                "source": "reddit",
            },
        ]

        collector_fn = self.mock_collector(items)

        stats = await stream_collection(
            collector_fn=collector_fn,
            collection_id="test_collection_007",
            collection_blob="collections/test_collection_007.json",
            blob_client=blob_client,
            queue_client=queue_client,
        )

        # Verify stats total
        total_items = (
            stats["published"] + stats["rejected_quality"] + stats["rejected_dedup"]
        )
        assert total_items == stats["collected"]
        assert stats["collected"] == 3
        assert (
            stats["published"] + stats["rejected_quality"] + stats["rejected_dedup"]
            == 3
        )


class TestCreateQueueMessage:
    """Unit tests for queue message creation."""

    def test_message_has_required_fields(self):
        """Queue message contains all required fields."""
        item = {
            "id": "test_1",
            "title": "Test Article",
            "content": "Test content about technology and software",
            "source": "reddit",
        }

        message = create_queue_message(item, "coll_001", "collections/coll_001.json")

        assert message["operation"] == "process_topic"
        assert message["service_name"] == "content-collector"
        assert "timestamp" in message
        assert "correlation_id" in message
        assert "payload" in message

    def test_message_payload_format(self):
        """Queue message payload has correct structure."""
        item = {
            "id": "test_1",
            "title": "Test Article",
            "content": "Test content about technology",
            "source": "reddit",
        }

        message = create_queue_message(item, "coll_001", "collections/coll_001.json")
        payload = message["payload"]

        assert isinstance(payload, dict)
        assert "topic_id" in payload
        assert "title" in payload
        assert "source" in payload
        assert "collection_id" in payload
        assert "collection_blob" in payload

    def test_message_is_json_serializable(self):
        """Queue message can be serialized to JSON."""
        item = {
            "id": "test_1",
            "title": "Test Article",
            "content": "Test content about technology and software development",
            "source": "reddit",
            "metadata": {"score": 100},
        }

        message = create_queue_message(item, "coll_001", "collections/coll_001.json")

        # Should not raise
        json_str = json.dumps(message)
        assert json_str is not None

        # Should be deserializable
        parsed = json.loads(json_str)
        assert parsed["operation"] == "process_topic"

    def test_message_handles_missing_id(self):
        """Queue message generates ID if not provided."""
        item = {
            "title": "Test Article",
            "content": "Test content about technology",
            "source": "reddit",
        }

        message = create_queue_message(item, "coll_001", "collections/coll_001.json")
        payload = message["payload"]

        # Should have generated an ID
        assert "topic_id" in payload
        assert payload["topic_id"].startswith("topic_")


@pytest.mark.asyncio
async def test_pipeline_end_to_end_integration():
    """
    Full integration test: Real-like scenario.

    Simulates collecting 10 items from mixed sources, with realistic
    quality distribution and deduplication.
    """
    blob_client = MockBlobClient()
    queue_client = MockQueueClient()

    items = [
        {
            "id": f"item_{i}",
            "title": f"Technical Article {i}: Software Development Best Practices",
            "content": f"Long technical content about software development, engineering practices, and technology trends. Article {i} discusses important aspects.",
            "source": "reddit" if i % 2 == 0 else "mastodon",
        }
        for i in range(10)
    ]

    async def collector():
        for item in items:
            yield item

    stats = await stream_collection(
        collector_fn=collector(),
        collection_id="integration_test_001",
        collection_blob="collections/integration_test_001.json",
        blob_client=blob_client,
        queue_client=queue_client,
    )

    # All items are valid and high quality
    assert stats["collected"] == 10
    assert stats["published"] == 10
    assert stats["rejected_quality"] == 0

    # All messages should be in queue
    assert len(queue_client.messages) == 10

    # Each message should have valid structure
    for message in queue_client.messages:
        assert message["operation"] == "process_topic"
        assert message["payload"]["collection_id"] == "integration_test_001"
        assert (
            message["payload"]["collection_blob"]
            == "collections/integration_test_001.json"
        )

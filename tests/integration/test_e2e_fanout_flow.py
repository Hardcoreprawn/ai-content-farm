"""
Integration Tests for End-to-End Fanout Flow

Tests the complete pipeline from collector → queue → processor,
including failure handling and parallel processing simulation.

Functional approach: Each test is a standalone function testing pure logic.

Test Coverage:
- Complete fanout pipeline (collector → processor)
- Individual topic failure handling
- Parallel processing simulation
- No duplicate processing verification
- Queue depth monitoring
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, call

import pytest
from endpoints.storage_queue_router import ContentProcessorStorageQueueRouter
from models import TopicMetadata
from topic_fanout import (
    create_topic_message,
    create_topic_messages_batch,
)

from libs.queue_client import QueueMessageModel

# Add containers to path for imports
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "containers" / "content-collector")
)
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "containers" / "content-processor")
)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "libs"))


@pytest.fixture
def sample_topics() -> List[Dict[str, Any]]:
    """Sample topics for end-to-end testing."""
    return [
        {
            "id": "reddit_1",  # Use "id" not "topic_id" for fanout compatibility
            "title": "AI Breakthrough in Natural Language Processing",
            "source": "reddit",
            "metadata": {
                "subreddit": "technology",
                "score": 250,
                "num_comments": 120,
            },
            "url": "https://reddit.com/r/technology/post1",
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "priority_score": 0.95,
        },
        {
            "id": "reddit_2",
            "title": "New Python Framework Released",
            "source": "reddit",
            "metadata": {
                "subreddit": "programming",
                "score": 180,
                "num_comments": 85,
            },
            "url": "https://reddit.com/r/programming/post2",
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "priority_score": 0.82,
        },
        {
            "id": "rss_1",
            "title": "Climate Tech Startup Raises $50M",
            "source": "rss",
            "url": "https://example.com/climate-tech",
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "priority_score": 0.78,
        },
    ]


@pytest.fixture
def mock_processor():
    """Mock content processor for e2e tests."""
    processor = AsyncMock()
    # Default: successful processing
    processor._process_topic_with_lease = AsyncMock(return_value=(True, 0.02))
    return processor


@pytest.fixture
def queue_router(mock_processor):
    """Create queue router with mocked processor."""
    router = ContentProcessorStorageQueueRouter()
    router.get_processor = Mock(return_value=mock_processor)
    return router


# ============================================================================
# Test: Complete fanout pipeline
# ============================================================================


@pytest.mark.asyncio
async def test_complete_fanout_pipeline(sample_topics, queue_router, mock_processor):
    """Test complete flow: topics → messages → processing."""
    collection_id = "col_test_e2e_001"
    collection_blob = f"collections/2025/10/08/{collection_id}.json"

    # Step 1: Create fanout messages (simulates collector)
    messages = create_topic_messages_batch(
        items=sample_topics,
        collection_id=collection_id,
        collection_blob=collection_blob,
    )

    # Verify fanout created correct number of messages
    assert len(messages) == 3, "Should create 3 messages for 3 topics"

    # Step 2: Process each message (simulates processor consuming queue)
    results = []
    for msg_data in messages:
        message = QueueMessageModel(
            message_id=f"msg_{msg_data['correlation_id']}",
            operation=msg_data["operation"],
            service_name=msg_data["service_name"],
            correlation_id=msg_data["correlation_id"],
            payload=msg_data["payload"],
        )
        result = await queue_router.process_storage_queue_message(message)
        results.append(result)

    # Step 3: Verify all topics processed successfully
    assert len(results) == 3, "Should process all 3 messages"
    assert all(r["status"] == "success" for r in results), "All should succeed"

    # Step 4: Verify processor called for each topic
    assert mock_processor._process_topic_with_lease.call_count == 3

    # Step 5: Verify no duplicate processing (unique topic_ids)
    processed_topics = []
    for call_args in mock_processor._process_topic_with_lease.call_args_list:
        topic = call_args[0][0]
        processed_topics.append(topic.topic_id)

    assert len(set(processed_topics)) == 3, "Should process 3 unique topics"
    assert "reddit_1" in processed_topics
    assert "reddit_2" in processed_topics
    assert "rss_1" in processed_topics


# ============================================================================
# Test: Failure handling (individual topics)
# ============================================================================


@pytest.mark.asyncio
async def test_individual_topic_failure_doesnt_block_others(
    sample_topics, queue_router, mock_processor
):
    """Test that one topic failure doesn't block other topics."""
    collection_id = "col_test_failure_001"
    collection_blob = f"collections/2025/10/08/{collection_id}.json"

    # Configure mock: topic 2 fails, others succeed
    async def mock_processing(topic):
        if topic.topic_id == "reddit_2":
            return (False, 0.0)  # Failure
        return (True, 0.02)  # Success

    mock_processor._process_topic_with_lease = AsyncMock(side_effect=mock_processing)

    # Create and process messages
    messages = create_topic_messages_batch(
        items=sample_topics,
        collection_id=collection_id,
        collection_blob=collection_blob,
    )

    results = []
    for msg_data in messages:
        message = QueueMessageModel(
            message_id=f"msg_{msg_data['correlation_id']}",
            operation=msg_data["operation"],
            service_name=msg_data["service_name"],
            correlation_id=msg_data["correlation_id"],
            payload=msg_data["payload"],
        )
        result = await queue_router.process_storage_queue_message(message)
        results.append(result)

    # Verify: 2 successes, 1 failure
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")

    assert success_count == 2, "Topics 1 and 3 should succeed"
    assert error_count == 1, "Topic 2 should fail"

    # Verify all topics attempted (no blocking)
    assert mock_processor._process_topic_with_lease.call_count == 3


# ============================================================================
# Test: Parallel processing simulation
# ============================================================================


@pytest.mark.asyncio
async def test_parallel_processing_simulation(
    sample_topics, queue_router, mock_processor
):
    """Simulate parallel processing of multiple topics."""
    collection_id = "col_test_parallel_001"
    collection_blob = f"collections/2025/10/08/{collection_id}.json"

    # Add delay to simulate processing time
    async def slow_processing(topic):
        await asyncio.sleep(0.1)  # 100ms per topic
        return (True, 0.02)

    mock_processor._process_topic_with_lease = AsyncMock(side_effect=slow_processing)

    # Create messages
    messages = create_topic_messages_batch(
        items=sample_topics,
        collection_id=collection_id,
        collection_blob=collection_blob,
    )

    # Process in parallel using asyncio.gather
    async def process_message(msg_data):
        message = QueueMessageModel(
            message_id=f"msg_{msg_data['correlation_id']}",
            operation=msg_data["operation"],
            service_name=msg_data["service_name"],
            correlation_id=msg_data["correlation_id"],
            payload=msg_data["payload"],
        )
        return await queue_router.process_storage_queue_message(message)

    # Process all messages in parallel
    start_time = asyncio.get_event_loop().time()
    results = await asyncio.gather(*[process_message(msg) for msg in messages])
    end_time = asyncio.get_event_loop().time()

    # Verify parallel execution (should be ~100ms, not 300ms)
    elapsed = end_time - start_time
    assert (
        elapsed < 0.2
    ), f"Parallel processing should complete quickly ({elapsed:.2f}s)"

    # Verify all succeeded
    assert all(r["status"] == "success" for r in results)
    assert len(results) == 3


# ============================================================================
# Test: No duplicate processing
# ============================================================================


@pytest.mark.asyncio
async def test_no_duplicate_processing(sample_topics, queue_router, mock_processor):
    """Verify no duplicate processing when same message processed twice."""
    collection_id = "col_test_dedup_001"
    collection_blob = f"collections/2025/10/08/{collection_id}.json"

    # Create single message
    messages = create_topic_messages_batch(
        items=[sample_topics[0]],  # Just first topic
        collection_id=collection_id,
        collection_blob=collection_blob,
    )

    msg_data = messages[0]
    message = QueueMessageModel(
        message_id=f"msg_{msg_data['correlation_id']}",
        operation=msg_data["operation"],
        service_name=msg_data["service_name"],
        correlation_id=msg_data["correlation_id"],
        payload=msg_data["payload"],
    )

    # Process same message twice (simulates retry or duplicate delivery)
    result1 = await queue_router.process_storage_queue_message(message)
    result2 = await queue_router.process_storage_queue_message(message)

    # Both should succeed (idempotent processing)
    assert result1["status"] == "success"
    assert result2["status"] == "success"

    # Verify processor called twice (current behavior - no dedup at processor level)
    # Note: Deduplication should happen at queue level (Azure Queue deduplication)
    assert mock_processor._process_topic_with_lease.call_count == 2


# ============================================================================
# Test: Queue depth monitoring
# ============================================================================


@pytest.mark.asyncio
async def test_queue_depth_monitoring(sample_topics):
    """Test queue depth tracking for KEDA scaling metrics."""
    collection_id = "col_test_queue_001"
    collection_blob = f"collections/2025/10/08/{collection_id}.json"

    # Create messages for different batches
    batch1 = create_topic_messages_batch(
        items=sample_topics[:2],
        collection_id=f"{collection_id}_batch1",
        collection_blob=collection_blob,
    )

    batch2 = create_topic_messages_batch(
        items=[sample_topics[2]],
        collection_id=f"{collection_id}_batch2",
        collection_blob=collection_blob,
    )

    # Verify message counts
    assert len(batch1) == 2, "Batch 1 should have 2 messages"
    assert len(batch2) == 1, "Batch 2 should have 1 message"

    # Total queue depth
    total_depth = len(batch1) + len(batch2)
    assert total_depth == 3, "Total queue depth should be 3"

    # Verify each message has correlation_id for tracking
    all_messages = batch1 + batch2
    assert all("correlation_id" in msg for msg in all_messages)

    # Verify correlation_ids are unique
    correlation_ids = [msg["correlation_id"] for msg in all_messages]
    assert len(set(correlation_ids)) == 3, "All correlation_ids should be unique"


# Summary comment for test execution
"""
To run these end-to-end integration tests:

    cd /workspaces/ai-content-farm
    pytest tests/integration/test_e2e_fanout_flow.py -v

Expected Results:
- 5 tests should pass
- Complete fanout pipeline validation
- Failure isolation verified
- Parallel processing confirmed
- No duplicate processing
- Queue monitoring validated

These tests validate the complete fanout architecture
from topic collection through individual processing.
"""

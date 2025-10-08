"""
Integration Tests for Processor Queue Handler - Functional Style

Tests the processor's ability to handle individual topic messages
from the queue, including validation, processing, and error handling.

Functional approach: Each test is a standalone function testing pure logic.

Test Coverage:
- process_topic message handling
- Validation before processor initialization
- Error handling and edge cases
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock

import pytest

# Add containers to path for imports - MUST be before other imports
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / "containers" / "content-processor")
)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "libs"))

from endpoints.storage_queue_router import ContentProcessorStorageQueueRouter
from models import TopicMetadata

from libs.queue_client import QueueMessageModel


@pytest.fixture
def mock_processor():
    """Mock content processor for process_topic operations."""
    processor = AsyncMock()
    processor._process_topic_with_lease = AsyncMock(return_value=(True, 0.02))
    return processor


@pytest.fixture
def queue_router(mock_processor):
    """Create queue router with mocked processor."""
    router = ContentProcessorStorageQueueRouter()
    router.get_processor = Mock(return_value=mock_processor)
    return router


@pytest.fixture
def sample_process_topic_message() -> Dict[str, Any]:
    """Sample process_topic message with complete data."""
    return {
        "operation": "process_topic",
        "service_name": "content-collector",
        "correlation_id": "col_test_123_reddit_1",
        "payload": {
            "topic_id": "reddit_1",
            "title": "Test Article About AI",
            "source": "reddit",
            "subreddit": "technology",
            "url": "https://reddit.com/r/technology/post1",
            "upvotes": 150,
            "comments": 75,
            "collected_at": "2025-10-08T10:00:00+00:00",
            "priority_score": 0.85,
            "collection_id": "col_test_123",
            "collection_blob": "collections/2025/10/08/col_test_123.json",
        },
    }


@pytest.fixture
def minimal_process_topic_message() -> Dict[str, Any]:
    """Sample process_topic message with minimal required fields."""
    return {
        "operation": "process_topic",
        "service_name": "content-collector",
        "correlation_id": "col_test_456_rss_1",
        "payload": {
            "topic_id": "rss_1",
            "title": "Minimal RSS Article",
            "source": "rss",
            "collection_id": "col_test_456",
            "collection_blob": "collections/2025/10/08/col_test_456.json",
        },
    }


# ============================================================================
# Test: process_topic message handling
# ============================================================================


@pytest.mark.asyncio
async def test_handles_complete_topic_message(
    queue_router, mock_processor, sample_process_topic_message
):
    """Verify processor handles complete process_topic message."""
    # Create message model
    message = QueueMessageModel(
        message_id="msg_1",
        operation=sample_process_topic_message["operation"],
        service_name=sample_process_topic_message["service_name"],
        correlation_id=sample_process_topic_message["correlation_id"],
        payload=sample_process_topic_message["payload"],
    )

    # Process message
    result = await queue_router.process_storage_queue_message(message)

    # Verify processor called with correct topic
    assert mock_processor._process_topic_with_lease.called
    call_args = mock_processor._process_topic_with_lease.call_args
    topic = call_args[0][0]

    assert isinstance(topic, TopicMetadata)
    assert topic.topic_id == "reddit_1"
    assert topic.title == "Test Article About AI"
    assert topic.source == "reddit"
    assert topic.subreddit == "technology"
    assert topic.upvotes == 150
    assert topic.comments == 75

    # Verify result
    assert result["status"] == "success"
    assert result["operation"] == "topic_processed"
    assert result["result"]["success"] is True
    assert result["result"]["cost_usd"] == 0.02


@pytest.mark.asyncio
async def test_handles_minimal_topic_message(
    queue_router, mock_processor, minimal_process_topic_message
):
    """Verify processor handles minimal process_topic message."""
    message = QueueMessageModel(
        message_id="msg_2",
        operation=minimal_process_topic_message["operation"],
        service_name=minimal_process_topic_message["service_name"],
        correlation_id=minimal_process_topic_message["correlation_id"],
        payload=minimal_process_topic_message["payload"],
    )

    result = await queue_router.process_storage_queue_message(message)

    # Verify processor called
    assert mock_processor._process_topic_with_lease.called
    call_args = mock_processor._process_topic_with_lease.call_args
    topic = call_args[0][0]

    # Verify only required fields set
    assert topic.topic_id == "rss_1"
    assert topic.title == "Minimal RSS Article"
    assert topic.source == "rss"
    assert topic.subreddit is None  # Optional field not present
    assert topic.upvotes is None  # Optional field not present

    # Verify success
    assert result["status"] == "success"


# ============================================================================
# Test: Validation before processing
# ============================================================================


@pytest.mark.asyncio
async def test_validates_before_processor_initialization(queue_router, mock_processor):
    """Verify validation happens before get_processor() call."""
    # Message missing required field (title)
    message = QueueMessageModel(
        message_id="msg_invalid",
        operation="process_topic",
        service_name="content-collector",
        correlation_id="test",
        payload={
            "topic_id": "test_1",
            # Missing "title" (required)
            "source": "reddit",
            "collection_id": "col_test",
            "collection_blob": "test.json",
        },
    )

    result = await queue_router.process_storage_queue_message(message)

    # Verify processor NOT called (validation failed first)
    assert not mock_processor._process_topic_with_lease.called
    assert not queue_router.get_processor.called

    # Verify error response
    assert result["status"] == "error"
    assert "error" in result  # Response uses "error" key, not "message"
    assert "required field" in result["error"].lower()


@pytest.mark.asyncio
async def test_missing_topic_id_fails_validation(queue_router):
    """Verify missing topic_id fails validation."""
    message = QueueMessageModel(
        message_id="msg_no_id",
        operation="process_topic",
        service_name="content-collector",
        correlation_id="test",
        payload={
            "title": "Test Article",
            "source": "reddit",
            "collection_id": "col_test",
            "collection_blob": "test.json",
        },
    )

    result = await queue_router.process_storage_queue_message(message)

    assert result["status"] == "error"
    assert "error" in result
    assert "topic_id" in result["error"].lower()


@pytest.mark.asyncio
async def test_missing_source_fails_validation(queue_router):
    """Verify missing source fails validation."""
    message = QueueMessageModel(
        message_id="msg_no_source",
        operation="process_topic",
        service_name="content-collector",
        correlation_id="test",
        payload={
            "topic_id": "test_1",
            "title": "Test Article",
            "collection_id": "col_test",
            "collection_blob": "test.json",
        },
    )

    result = await queue_router.process_storage_queue_message(message)

    assert result["status"] == "error"
    assert "error" in result
    assert "source" in result["error"].lower()


# ============================================================================
# Test: Error handling
# ============================================================================


@pytest.mark.asyncio
async def test_handles_processing_failure(
    queue_router, mock_processor, sample_process_topic_message
):
    """Verify processor handles processing failures gracefully."""
    # Mock processor to return failure
    mock_processor._process_topic_with_lease.return_value = (False, 0.0)

    message = QueueMessageModel(
        message_id="msg_fail",
        operation=sample_process_topic_message["operation"],
        service_name=sample_process_topic_message["service_name"],
        correlation_id=sample_process_topic_message["correlation_id"],
        payload=sample_process_topic_message["payload"],
    )

    result = await queue_router.process_storage_queue_message(message)

    # Verify failure status returned
    assert result["status"] == "error"
    assert result["result"]["success"] is False
    assert result["result"]["cost_usd"] == 0.0


@pytest.mark.asyncio
async def test_handles_processor_exception(
    queue_router, mock_processor, sample_process_topic_message
):
    """Verify processor handles exceptions during processing."""
    # Mock processor to raise exception
    mock_processor._process_topic_with_lease.side_effect = Exception("OpenAI API error")

    message = QueueMessageModel(
        message_id="msg_exception",
        operation=sample_process_topic_message["operation"],
        service_name=sample_process_topic_message["service_name"],
        correlation_id=sample_process_topic_message["correlation_id"],
        payload=sample_process_topic_message["payload"],
    )

    result = await queue_router.process_storage_queue_message(message)

    # Verify error handled gracefully
    assert result["status"] == "error"
    assert "error" in result  # Response uses "error" key
    assert "openai" in result["error"].lower() or "error" in result["error"].lower()


# Summary comment for test execution
"""
To run these integration tests:

    cd /workspaces/ai-content-farm
    pytest tests/integration/test_processor_queue_handling.py -v

Expected Results:
- 8 tests should pass (focused on process_topic fanout pattern)
- Validates process_topic message handling (complete and minimal)
- Confirms validation before processing (3 validation tests)
- Tests error handling scenarios (failure and exception)

These tests use mocked processor but real queue handler logic,
ensuring the processor correctly interprets fanout messages from
the new parallel processing architecture.
"""

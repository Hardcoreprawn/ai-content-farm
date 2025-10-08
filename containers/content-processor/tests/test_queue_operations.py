"""
Black-box tests for queue_operations module.

Tests cover all queue operations without knowledge of implementation.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from queue_operations import (
    clear_queue,
    create_markdown_trigger_message,
    create_queue_message,
    delete_queue_message,
    generate_correlation_id,
    get_queue_properties,
    peek_queue_messages,
    receive_queue_messages,
    send_queue_message,
    should_trigger_next_stage,
)

# ============================================================================
# Test Message Creation (Pure Functions)
# ============================================================================


class TestCreateQueueMessage:
    """Test queue message creation."""

    def test_creates_basic_message(self):
        """Should create message with required fields."""
        msg = create_queue_message(
            service_name="test-service",
            operation="wake_up",
        )

        assert msg["service_name"] == "test-service"
        assert msg["operation"] == "wake_up"
        assert "timestamp" in msg
        assert "correlation_id" in msg
        assert "payload" in msg
        assert msg["payload"] == {}

    def test_includes_payload(self):
        """Should include payload data."""
        payload = {"files": ["file1.json", "file2.json"], "count": 2}
        msg = create_queue_message(
            service_name="test-service",
            operation="process",
            payload=payload,
        )

        assert msg["payload"] == payload
        assert msg["payload"]["files"] == ["file1.json", "file2.json"]

    def test_uses_provided_correlation_id(self):
        """Should use provided correlation ID."""
        corr_id = "custom-correlation-id"
        msg = create_queue_message(
            service_name="test-service",
            operation="wake_up",
            correlation_id=corr_id,
        )

        assert msg["correlation_id"] == corr_id

    def test_generates_correlation_id_if_not_provided(self):
        """Should auto-generate correlation ID."""
        msg = create_queue_message(
            service_name="test-service",
            operation="wake_up",
        )

        assert "correlation_id" in msg
        assert "test-service_" in msg["correlation_id"]
        assert len(msg["correlation_id"]) > 20

    def test_timestamp_format(self):
        """Should create ISO format timestamp."""
        msg = create_queue_message(
            service_name="test-service",
            operation="wake_up",
        )

        # Verify ISO format by parsing
        timestamp = datetime.fromisoformat(msg["timestamp"])
        assert timestamp.tzinfo is not None


class TestGenerateCorrelationId:
    """Test correlation ID generation."""

    def test_includes_service_name(self):
        """Should include service name in correlation ID."""
        corr_id = generate_correlation_id("content-processor")

        assert corr_id.startswith("content-processor_")

    def test_generates_unique_ids(self):
        """Should generate unique IDs on each call."""
        id1 = generate_correlation_id("test-service")
        id2 = generate_correlation_id("test-service")

        assert id1 != id2

    def test_format_with_uuid(self):
        """Should have service_name_uuid format."""
        corr_id = generate_correlation_id("test")
        parts = corr_id.split("_", 1)

        assert len(parts) == 2
        assert parts[0] == "test"
        assert len(parts[1]) == 36  # UUID length


class TestCreateMarkdownTriggerMessage:
    """Test markdown trigger message creation."""

    def test_creates_markdown_trigger(self):
        """Should create proper markdown trigger message."""
        files = ["article1.json", "article2.json"]
        msg = create_markdown_trigger_message(processed_files=files)

        assert msg["service_name"] == "content-processor"
        assert msg["operation"] == "wake_up"
        assert msg["payload"]["files"] == files
        assert msg["payload"]["files_count"] == 2
        assert msg["payload"]["content_type"] == "json"

    def test_includes_correlation_id(self):
        """Should use provided correlation ID."""
        corr_id = "test-correlation-id"
        msg = create_markdown_trigger_message(
            processed_files=["file.json"],
            correlation_id=corr_id,
        )

        assert msg["correlation_id"] == corr_id

    def test_includes_additional_data(self):
        """Should merge additional data into payload."""
        additional = {"priority": "high", "source": "reddit"}
        msg = create_markdown_trigger_message(
            processed_files=["file.json"],
            additional_data=additional,
        )

        assert msg["payload"]["priority"] == "high"
        assert msg["payload"]["source"] == "reddit"
        assert msg["payload"]["files"] == ["file.json"]

    def test_empty_files_list(self):
        """Should handle empty files list."""
        msg = create_markdown_trigger_message(processed_files=[])

        assert msg["payload"]["files"] == []
        assert msg["payload"]["files_count"] == 0


# ============================================================================
# Test Queue Operations (Async Functions)
# ============================================================================
class TestSendQueueMessage:
    """Test sending messages to queue."""

    @pytest.mark.asyncio
    async def test_sends_message_successfully(self):
        """Should send message and return success."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.id = "msg-123"
        mock_client.send_message = Mock(return_value=mock_response)
        mock_client.queue_name = "test-queue"

        message = {"service_name": "test", "operation": "wake_up"}
        result = await send_queue_message(mock_client, message)

        assert result["status"] == "success"
        assert result["message_id"] == "msg-123"
        assert result["queue_name"] == "test-queue"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_serializes_message_to_json(self):
        """Should convert message dict to JSON string."""
        mock_client = Mock()
        mock_response = Mock(id="msg-123")
        mock_client.send_message = Mock(return_value=mock_response)
        mock_client.queue_name = "test-queue"

        message = {"service_name": "test", "data": {"key": "value"}}
        await send_queue_message(mock_client, message)

        # Verify JSON string was sent
        call_args = mock_client.send_message.call_args[0][0]
        assert isinstance(call_args, str)
        assert json.loads(call_args) == message

    @pytest.mark.asyncio
    async def test_handles_send_failure(self):
        """Should return error on send failure."""
        mock_client = Mock()
        mock_client.send_message = Mock(side_effect=Exception("Network error"))

        message = {"service_name": "test"}
        result = await send_queue_message(mock_client, message)

        assert result["status"] == "error"
        assert "error" in result
        assert "Network error" in result["error"]


class TestReceiveQueueMessages:
    """Test receiving messages from queue."""

    @pytest.mark.asyncio
    async def test_receives_messages_successfully(self):
        """Should receive and parse messages."""
        mock_msg = Mock()
        mock_msg.id = "msg-123"
        mock_msg.content = '{"service_name": "test", "operation": "wake_up"}'
        mock_msg.pop_receipt = "receipt-abc"
        mock_msg.dequeue_count = 1
        mock_msg.insertion_time = datetime.now(timezone.utc)

        mock_client = Mock()
        mock_client.receive_messages = Mock(return_value=[mock_msg])

        messages = await receive_queue_messages(mock_client, max_messages=1)

        assert len(messages) == 1
        assert messages[0]["id"] == "msg-123"
        assert messages[0]["content"]["service_name"] == "test"
        assert messages[0]["pop_receipt"] == "receipt-abc"

    @pytest.mark.asyncio
    async def test_handles_invalid_json(self):
        """Should handle non-JSON message content."""
        mock_msg = Mock()
        mock_msg.id = "msg-123"
        mock_msg.content = "not valid json"
        mock_msg.pop_receipt = "receipt-abc"
        mock_msg.dequeue_count = 1
        mock_msg.insertion_time = datetime.now(timezone.utc)

        mock_client = Mock()
        mock_client.receive_messages = Mock(return_value=[mock_msg])

        messages = await receive_queue_messages(mock_client)

        assert len(messages) == 1
        assert "raw_content" in messages[0]["content"]
        assert messages[0]["content"]["raw_content"] == "not valid json"

    @pytest.mark.asyncio
    async def test_receives_multiple_messages(self):
        """Should receive multiple messages."""
        mock_messages = []
        for i in range(3):
            msg = Mock()
            msg.id = f"msg-{i}"
            msg.content = json.dumps({"index": i})
            msg.pop_receipt = f"receipt-{i}"
            msg.dequeue_count = 1
            msg.insertion_time = datetime.now(timezone.utc)
            mock_messages.append(msg)

        mock_client = Mock()
        mock_client.receive_messages = Mock(return_value=mock_messages)

        messages = await receive_queue_messages(mock_client, max_messages=3)

        assert len(messages) == 3
        assert messages[0]["content"]["index"] == 0
        assert messages[2]["content"]["index"] == 2

    @pytest.mark.asyncio
    async def test_handles_receive_failure(self):
        """Should return empty list on failure."""
        mock_client = Mock()
        mock_client.receive_messages = Mock(side_effect=Exception("Network error"))

        messages = await receive_queue_messages(mock_client)

        assert messages == []


class TestDeleteQueueMessage:
    """Test deleting messages from queue."""

    @pytest.mark.asyncio
    async def test_deletes_message_successfully(self):
        """Should delete message and return True."""
        mock_client = Mock()
        mock_client.delete_message = Mock()

        success = await delete_queue_message(
            mock_client,
            message_id="msg-123",
            pop_receipt="receipt-abc",
        )

        assert success is True
        mock_client.delete_message.assert_called_once_with("msg-123", "receipt-abc")

    @pytest.mark.asyncio
    async def test_handles_delete_failure(self):
        """Should return False on delete failure."""
        mock_client = Mock()
        mock_client.delete_message = Mock(side_effect=Exception("Not found"))

        success = await delete_queue_message(
            mock_client,
            message_id="msg-123",
            pop_receipt="receipt-abc",
        )

        assert success is False


class TestPeekQueueMessages:
    """Test peeking at queue messages."""

    @pytest.mark.asyncio
    async def test_peeks_messages_successfully(self):
        """Should peek at messages without dequeuing."""
        mock_msg = Mock()
        mock_msg.id = "msg-123"
        mock_msg.content = '{"service_name": "test"}'
        mock_msg.dequeue_count = 0

        mock_client = Mock()
        mock_client.peek_messages = Mock(return_value=[mock_msg])

        messages = await peek_queue_messages(mock_client, max_messages=1)

        assert len(messages) == 1
        assert messages[0]["id"] == "msg-123"
        assert messages[0]["content"]["service_name"] == "test"
        assert "pop_receipt" not in messages[0]  # Peek doesn't include receipt

    @pytest.mark.asyncio
    async def test_handles_invalid_json_in_peek(self):
        """Should handle non-JSON content in peek."""
        mock_msg = Mock()
        mock_msg.id = "msg-123"
        mock_msg.content = "invalid json"
        mock_msg.dequeue_count = 0

        mock_client = Mock()
        mock_client.peek_messages = Mock(return_value=[mock_msg])

        messages = await peek_queue_messages(mock_client)

        assert len(messages) == 1
        assert "raw_content" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_handles_peek_failure(self):
        """Should return empty list on peek failure."""
        mock_client = Mock()
        mock_client.peek_messages = Mock(side_effect=Exception("Network error"))

        messages = await peek_queue_messages(mock_client)

        assert messages == []


class TestGetQueueProperties:
    """Test getting queue properties."""

    @pytest.mark.asyncio
    async def test_gets_queue_properties(self):
        """Should retrieve queue properties."""
        mock_props = Mock()
        mock_props.approximate_message_count = 5
        mock_props.metadata = {"env": "test"}

        mock_client = Mock()
        mock_client.queue_name = "test-queue"
        mock_client.get_queue_properties = Mock(return_value=mock_props)

        props = await get_queue_properties(mock_client)

        assert props["name"] == "test-queue"
        assert props["approximate_message_count"] == 5
        assert props["metadata"]["env"] == "test"

    @pytest.mark.asyncio
    async def test_handles_empty_metadata(self):
        """Should handle None metadata."""
        mock_props = Mock()
        mock_props.approximate_message_count = 0
        mock_props.metadata = None

        mock_client = Mock()
        mock_client.queue_name = "test-queue"
        mock_client.get_queue_properties = Mock(return_value=mock_props)

        props = await get_queue_properties(mock_client)

        assert props["metadata"] == {}

    @pytest.mark.asyncio
    async def test_handles_properties_failure(self):
        """Should return error dict on failure."""
        mock_client = Mock()
        mock_client.queue_name = "test-queue"
        mock_client.get_queue_properties = Mock(side_effect=Exception("Access denied"))

        props = await get_queue_properties(mock_client)

        assert props["name"] == "test-queue"
        assert "error" in props


class TestClearQueue:
    """Test clearing queue messages."""

    @pytest.mark.asyncio
    async def test_clears_queue_successfully(self):
        """Should clear queue and return True."""
        mock_client = Mock()
        mock_client.queue_name = "test-queue"
        mock_client.clear_messages = Mock()

        success = await clear_queue(mock_client)

        assert success is True
        mock_client.clear_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_clear_failure(self):
        """Should return False on clear failure."""
        mock_client = Mock()
        mock_client.clear_messages = Mock(side_effect=Exception("Permission denied"))

        success = await clear_queue(mock_client)

        assert success is False


# ============================================================================
# Test Decision Functions (Pure)
# ============================================================================


class TestShouldTriggerNextStage:
    """Test pipeline trigger decision logic."""

    def test_triggers_when_force_is_true(self):
        """Should always trigger when force_trigger=True."""
        assert should_trigger_next_stage(files=[], force_trigger=True) is True
        assert should_trigger_next_stage(files=None, force_trigger=True) is True
        assert (
            should_trigger_next_stage(files=["file.json"], force_trigger=True) is True
        )

    def test_does_not_trigger_empty_files(self):
        """Should not trigger with empty files and no force."""
        assert should_trigger_next_stage(files=[]) is False
        assert should_trigger_next_stage(files=None) is False

    def test_triggers_when_minimum_met(self):
        """Should trigger when file count meets minimum."""
        files = ["file1.json", "file2.json", "file3.json"]
        assert should_trigger_next_stage(files, minimum_files=3) is True
        assert should_trigger_next_stage(files, minimum_files=2) is True
        assert should_trigger_next_stage(files, minimum_files=1) is True

    def test_does_not_trigger_below_minimum(self):
        """Should not trigger when below minimum."""
        files = ["file1.json", "file2.json"]
        assert should_trigger_next_stage(files, minimum_files=3) is False
        assert should_trigger_next_stage(files, minimum_files=5) is False

    def test_default_minimum_is_one(self):
        """Should default to minimum of 1 file."""
        assert should_trigger_next_stage(files=["file.json"]) is True
        assert should_trigger_next_stage(files=[]) is False


# ============================================================================
# Test Purity and Determinism
# ============================================================================


class TestPurityAndDeterminism:
    """Test that pure functions are truly pure."""

    def test_create_queue_message_deterministic(self):
        """Should produce same result with same inputs (except timestamp/correlation_id)."""
        msg1 = create_queue_message(
            service_name="test",
            operation="wake_up",
            correlation_id="fixed-id",
        )
        msg2 = create_queue_message(
            service_name="test",
            operation="wake_up",
            correlation_id="fixed-id",
        )

        # Same structure (timestamps may differ by microseconds)
        assert msg1["service_name"] == msg2["service_name"]
        assert msg1["operation"] == msg2["operation"]
        assert msg1["correlation_id"] == msg2["correlation_id"]

    def test_should_trigger_pure_function(self):
        """Should be pure - same inputs always produce same output."""
        files = ["file1.json", "file2.json"]

        result1 = should_trigger_next_stage(files, force_trigger=False, minimum_files=2)
        result2 = should_trigger_next_stage(files, force_trigger=False, minimum_files=2)

        assert result1 == result2
        assert result1 is True

    def test_functions_do_not_modify_inputs(self):
        """Should not modify input data structures."""
        files = ["file1.json", "file2.json"]
        original_files = files.copy()

        create_markdown_trigger_message(processed_files=files)

        assert files == original_files

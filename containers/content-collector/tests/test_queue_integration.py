"""
Queue Integration Tests for Content Collector

Tests for Storage Queue integration and wake-up message functionality.
"""

import os

# Import test fixtures
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from service_logic import ContentCollectorService
from test_fixtures import MockBlobStorageClient, MockQueueClient

sys.path.append(os.path.dirname(__file__))

# Add the shared libs folder to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "libs"))


@pytest.mark.unit
class TestQueueIntegration:
    """Test Storage Queue client integration."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock storage."""
        return ContentCollectorService(storage_client=MockBlobStorageClient())

    @pytest.mark.asyncio
    @patch("service_logic.send_wake_up_message")
    async def test_send_processing_request_success(self, mock_send_wake_up, service):
        """Test successful processing request sending."""
        # Mock successful wake-up message
        mock_send_wake_up.return_value = {"message_id": "test_message_123"}

        collection_result = {
            "collection_id": "test_collection",
            "collected_items": [{"id": 1}, {"id": 2}],
            "metadata": {},
            "storage_location": "test/path",
        }

        result = await service._send_processing_request(collection_result)

        assert result is True
        mock_send_wake_up.assert_called_once()

        # Verify call arguments
        call_args = mock_send_wake_up.call_args
        assert call_args[1]["queue_name"] == "content-processing-requests"
        assert call_args[1]["service_name"] == "content-collector"
        assert call_args[1]["payload"]["trigger_reason"] == "new_collection"
        assert call_args[1]["payload"]["collection_id"] == "test_collection"
        assert call_args[1]["payload"]["items_count"] == 2

    @pytest.mark.asyncio
    @patch("service_logic.send_wake_up_message")
    async def test_send_processing_request_queue_failure(
        self, mock_send_wake_up, service
    ):
        """Test processing request when queue send fails."""
        # Mock failed wake-up message
        mock_send_wake_up.side_effect = Exception("Queue unavailable")

        collection_result = {
            "collection_id": "test_collection",
            "collected_items": [{"id": 1}, {"id": 2}],
            "metadata": {},
            "storage_location": "test/path",
        }

        result = await service._send_processing_request(collection_result)

        assert result is False
        mock_send_wake_up.assert_called_once()

    @pytest.mark.asyncio
    @patch("service_logic.send_wake_up_message")
    async def test_send_processing_request_empty_items(
        self, mock_send_wake_up, service
    ):
        """Test processing request with no items to process."""
        # Mock successful wake-up message
        mock_send_wake_up.return_value = {"message_id": "test_message_123"}

        collection_result = {
            "collection_id": "test_collection",
            "collected_items": [],
            "metadata": {},
            "storage_location": "test/path",
        }

        result = await service._send_processing_request(collection_result)

        # Should still return True for empty collections (processor decides what to do)
        assert result is True
        mock_send_wake_up.assert_called_once()

        # Verify payload shows 0 items
        call_args = mock_send_wake_up.call_args
        assert call_args[1]["payload"]["items_count"] == 0

    @pytest.mark.asyncio
    @patch("service_logic.send_wake_up_message")
    async def test_send_processing_request_no_storage_location(
        self, mock_send_wake_up, service
    ):
        """Test processing request without storage location."""
        # Mock successful wake-up message
        mock_send_wake_up.return_value = {"message_id": "test_message_123"}

        collection_result = {
            "collection_id": "test_collection",
            "collected_items": [{"id": 1}],
            "metadata": {},
            "storage_location": None,
        }

        result = await service._send_processing_request(collection_result)

        assert result is True
        mock_send_wake_up.assert_called_once()

        # Verify payload includes None storage location
        call_args = mock_send_wake_up.call_args
        assert call_args[1]["payload"]["storage_location"] is None


@pytest.mark.unit
class TestQueueClientMocking:
    """Test queue client mocking functionality for other tests."""

    def test_mock_queue_client_creation(self):
        """Test mock queue client can be created."""
        client = MockQueueClient("test-queue")

        assert client.queue_name == "test-queue"
        assert not client._connected
        assert len(client._messages) == 0

    @pytest.mark.asyncio
    async def test_mock_queue_client_context_manager(self):
        """Test mock queue client as context manager."""
        async with MockQueueClient("test-queue") as client:
            assert client._connected

            # Test message sending
            result = await client.send_message({"test": "data"})
            assert "message_id" in result
            assert len(client._messages) == 1

        # Should be disconnected after context
        assert not client._connected

    @pytest.mark.asyncio
    async def test_mock_queue_client_message_operations(self):
        """Test mock queue client message operations."""
        client = MockQueueClient("test-queue")
        await client.connect()

        # Send a message
        message_data = {"operation": "test", "payload": {"key": "value"}}
        result = await client.send_message(message_data)

        assert "message_id" in result
        assert "pop_receipt" in result

        # Receive messages
        messages = await client.receive_messages()
        assert len(messages) == 1
        assert messages[0]["content"] == message_data

        # Get queue properties
        props = await client.get_queue_properties()
        assert props["approximate_message_count"] == 1
        assert props["queue_name"] == "test-queue"

        # Get health status
        health = client.get_health_status()
        assert health["status"] == "healthy"
        assert health["queue_name"] == "test-queue"

        await client.close()

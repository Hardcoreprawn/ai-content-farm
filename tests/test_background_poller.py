"""
Tests for Background Service Bus Poller

Tests the shared background polling functionality used by KEDA-scaled containers.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from libs.background_poller import BackgroundPoller
from libs.shared_models import StandardResponse


class MockServiceBusRouter:
    """Mock service bus router for testing."""

    def __init__(self, service_name="test-service", queue_name="test-queue"):
        self.service_name = service_name
        self.queue_name = queue_name
        self.call_count = 0
        self.messages_to_return = []

    async def _process_servicebus_message_impl(self, metadata):
        """Mock implementation that returns configurable responses."""
        self.call_count += 1

        if self.messages_to_return:
            # Return next configured response
            response = self.messages_to_return.pop(0)
        else:
            # Default: no messages
            response = {
                "status": "success",
                "messages_processed": 0,
                "messages_received": 0,
                "messages_failed": 0,
            }

        # Create proper response structure
        from pydantic import BaseModel

        from libs.shared_models import StandardResponse

        class MockProcessResponse(BaseModel):
            messages_processed: int = response.get("messages_processed", 0)
            messages_received: int = response.get("messages_received", 0)
            messages_failed: int = response.get("messages_failed", 0)

        return StandardResponse(
            status=response.get("status", "success"),
            message="Mock response",
            data=MockProcessResponse(**response),
            metadata=metadata,
        )


@pytest.mark.asyncio
class TestBackgroundPoller:
    """Test suite for BackgroundPoller."""

    def setup_method(self):
        """Set up test environment."""
        self.mock_router = MockServiceBusRouter()
        self.poller = BackgroundPoller(
            service_bus_router=self.mock_router,
            poll_interval=0.1,  # Fast polling for tests
            max_poll_attempts=2,
            empty_queue_sleep=0.2,
        )

    async def test_poller_initialization(self):
        """Test poller initializes correctly."""
        assert self.poller.service_bus_router == self.mock_router
        assert self.poller.poll_interval == 0.1
        assert self.poller.max_poll_attempts == 2
        assert self.poller.empty_queue_sleep == 0.2
        assert not self.poller.is_running

    async def test_start_and_stop_poller(self):
        """Test poller can be started and stopped."""
        # Start poller
        await self.poller.start()
        assert self.poller.is_running

        # Give it a moment to start polling
        await asyncio.sleep(0.05)

        # Stop poller
        await self.poller.stop()
        assert not self.poller.is_running

    async def test_poller_processes_messages(self):
        """Test poller calls service bus router to process messages."""
        # Configure mock to return some messages
        self.mock_router.messages_to_return = [
            {
                "status": "success",
                "messages_processed": 2,
                "messages_received": 2,
                "messages_failed": 0,
            },
            {
                "status": "success",
                "messages_processed": 1,
                "messages_received": 1,
                "messages_failed": 0,
            },
            {
                "status": "success",
                "messages_processed": 0,
                "messages_received": 0,
                "messages_failed": 0,
            },  # Empty queue
        ]

        # Start poller
        await self.poller.start()

        # Let it process some messages
        await asyncio.sleep(0.3)

        # Stop poller
        await self.poller.stop()

        # Should have called the router multiple times
        assert self.mock_router.call_count >= 3

    async def test_poller_handles_empty_queue(self):
        """Test poller handles empty queue correctly."""
        # Configure mock to always return empty
        self.mock_router.messages_to_return = []

        # Start poller
        await self.poller.start()

        # Let it run for a bit
        await asyncio.sleep(0.25)

        # Stop poller
        await self.poller.stop()

        # Should have made multiple attempts
        assert self.mock_router.call_count >= 2

    async def test_poller_handles_errors(self):
        """Test poller handles errors gracefully."""
        # Configure mock to return error
        self.mock_router.messages_to_return = [
            {
                "status": "error",
                "messages_processed": 0,
                "messages_received": 0,
                "messages_failed": 1,
            }
        ]

        # Start poller
        await self.poller.start()

        # Let it handle the error
        await asyncio.sleep(0.25)

        # Stop poller
        await self.poller.stop()

        # Should still be running and have attempted processing
        assert self.mock_router.call_count >= 1

    async def test_double_start_warning(self):
        """Test starting poller twice logs warning."""
        with patch("libs.background_poller.logger") as mock_logger:
            await self.poller.start()
            await self.poller.start()  # Second start should warn

            mock_logger.warning.assert_called_once_with(
                "Background poller already running"
            )

            await self.poller.stop()

    async def test_stop_without_start(self):
        """Test stopping poller that wasn't started."""
        # Should not raise exception
        await self.poller.stop()
        assert not self.poller.is_running

    async def test_metadata_updates(self):
        """Test that metadata timestamps are updated."""
        call_metadata = []

        async def capture_metadata(metadata):
            call_metadata.append(metadata.copy())
            return StandardResponse(
                status="success",
                message="Mock",
                data=Mock(messages_processed=0, messages_received=0, messages_failed=0),
                metadata=metadata,
            )

        self.mock_router._process_servicebus_message_impl = capture_metadata

        await self.poller.start()
        await asyncio.sleep(0.15)  # Let it make a few calls
        await self.poller.stop()

        # Should have captured multiple metadata calls
        assert len(call_metadata) >= 1

        # Check metadata structure
        first_call = call_metadata[0]
        assert "timestamp" in first_call
        assert "function" in first_call
        assert first_call["function"] == "test-service"

    async def test_exception_handling_in_loop(self):
        """Test polling loop handles unexpected exceptions."""

        # Mock router that raises exception
        async def raise_exception(metadata):
            raise ValueError("Test exception")

        self.mock_router._process_servicebus_message_impl = raise_exception

        with patch("libs.background_poller.logger") as mock_logger:
            await self.poller.start()
            await asyncio.sleep(0.25)  # Let it handle exception
            await self.poller.stop()

            # Should have logged the error
            mock_logger.error.assert_called()

    async def test_graceful_shutdown_timeout(self):
        """Test poller handles graceful shutdown timeout."""

        # Mock a router that never finishes
        async def slow_process(metadata):
            await asyncio.sleep(100)  # Very slow
            return StandardResponse(
                status="success",
                message="Mock",
                data=Mock(messages_processed=0),
                metadata=metadata,
            )

        self.mock_router._process_servicebus_message_impl = slow_process

        # Use a poller with very short timeout for testing
        fast_poller = BackgroundPoller(self.mock_router, poll_interval=0.1)

        with patch("libs.background_poller.logger") as mock_logger:
            await fast_poller.start()
            # Stop should timeout and cancel the task
            await fast_poller.stop()

            assert not fast_poller.is_running


@pytest.mark.unit
class TestBackgroundPollerUnit:
    """Unit tests for individual methods."""

    def test_get_current_iso_timestamp(self):
        """Test timestamp generation."""
        router = MockServiceBusRouter()
        poller = BackgroundPoller(router)

        timestamp = poller._get_current_iso_timestamp()

        # Should be valid ISO format
        assert isinstance(timestamp, str)
        assert "T" in timestamp
        assert timestamp.endswith("+00:00") or timestamp.endswith("Z")

        # Should be parseable as datetime
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None

    def test_is_running_property(self):
        """Test is_running property."""
        router = MockServiceBusRouter()
        poller = BackgroundPoller(router)

        assert not poller.is_running

        # Simulate internal state change
        poller._is_running = True
        assert poller.is_running

        poller._is_running = False
        assert not poller.is_running


# Integration test with actual Service Bus router (mocked dependencies)
@pytest.mark.integration
class TestBackgroundPollerIntegration:
    """Integration tests with real service bus router components."""

    @patch("libs.service_bus_client.ServiceBusClient")
    async def test_with_real_router(self, mock_client_class):
        """Test with actual ServiceBusRouterBase subclass."""
        from libs.service_bus_router import ServiceBusRouterBase

        class TestServiceBusRouter(ServiceBusRouterBase):
            async def process_message_payload(self, payload, operation):
                return {"status": "success", "processed": True}

        # Mock the client
        mock_client = AsyncMock()
        mock_client.receive_messages.return_value = []  # Empty queue
        mock_client_class.return_value = mock_client

        router = TestServiceBusRouter("test-service", "test-queue")
        poller = BackgroundPoller(router, poll_interval=0.1)

        await poller.start()
        await asyncio.sleep(0.15)
        await poller.stop()

        # Should have attempted to receive messages
        assert mock_client.receive_messages.called

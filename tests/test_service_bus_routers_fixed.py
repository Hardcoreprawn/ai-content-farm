"""
Test suite for Service Bus Router base implementation.

This module tests the shared Service Bus router functionality
that's used across multiple container services.
"""

import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libs.service_bus_client import ServiceBusClient
from libs.service_bus_router import ServiceBusRouterBase, ServiceBusStatusResponse
from libs.shared_models import StandardResponse


class MockServiceBusRouter(ServiceBusRouterBase):
    """Mock implementation for testing."""

    def __init__(self):
        super().__init__(
            service_name="test-service", queue_name="test-queue", prefix="/test"
        )

    async def process_message_payload(
        self, payload: Dict[str, Any], operation: str
    ) -> Dict[str, Any]:
        """Mock message processing."""
        if payload.get("should_fail"):
            return {"status": "error", "error": "Test failure"}
        return {"status": "success", "processed": True}

    def get_max_messages(self) -> int:
        """Mock max messages."""
        return 10

    def is_processing_successful(self, result: Dict[str, Any]) -> bool:
        """Mock success check."""
        return result.get("status") == "success"


class TestServiceBusRouterBase:
    """Test cases for ServiceBusRouterBase functionality."""

    def test_router_initialization(self):
        """Test router initialization with proper attributes."""
        mock_router = MockServiceBusRouter()
        assert mock_router.service_name == "test-service"
        assert mock_router.queue_name == "test-queue"
        assert mock_router.router.prefix == "/test"

    def test_get_max_messages(self):
        """Test get_max_messages method."""
        mock_router = MockServiceBusRouter()
        assert mock_router.get_max_messages() == 10

    def test_is_processing_successful_success(self):
        """Test is_processing_successful with successful result."""
        mock_router = MockServiceBusRouter()
        result = {"status": "success", "data": "processed"}
        assert mock_router.is_processing_successful(result) is True

    def test_is_processing_successful_failure(self):
        """Test is_processing_successful with failed result."""
        mock_router = MockServiceBusRouter()
        result = {"status": "error", "error": "Failed"}
        assert mock_router.is_processing_successful(result) is False

    @pytest.mark.asyncio
    async def test_process_message_payload_success(self):
        """Test process_message_payload with successful processing."""
        mock_router = MockServiceBusRouter()
        payload = {"test": "data"}
        result = await mock_router.process_message_payload(payload, "test_operation")

        assert result["status"] == "success"
        assert result["processed"] is True

    @pytest.mark.asyncio
    async def test_process_message_payload_failure(self):
        """Test process_message_payload with failure condition."""
        mock_router = MockServiceBusRouter()
        payload = {"should_fail": True, "test": "data"}
        result = await mock_router.process_message_payload(payload, "test_operation")

        assert result["status"] == "error"
        assert "error" in result


class TestServiceBusMessageProcessing:
    """Test cases for Service Bus message processing."""

    @pytest.mark.asyncio
    @patch("libs.service_bus_router.ServiceBusConfig")
    async def test_process_message_success(self, mock_config):
        """Test successful message processing."""
        # Create mock message with proper JSON content
        mock_message = MagicMock()
        mock_message.message_id = "test-message-123"
        mock_message.__str__ = lambda: json.dumps(
            {"operation": "process", "payload": {"test": "data"}}
        )

        # Create mock Service Bus client
        mock_client = AsyncMock(spec=ServiceBusClient)
        mock_client.receive_messages.return_value = [mock_message]

        # Create router and inject mock client
        router = MockServiceBusRouter()
        router._service_bus_client = mock_client

        # Test message processing
        metadata = {"service": "test"}
        result = await router._process_servicebus_message_impl(metadata)

        # Verify results
        assert result.status == "success"
        assert result.data.messages_received == 1
        assert result.data.messages_processed == 1
        assert result.data.messages_failed == 0

        # Verify Service Bus interactions
        mock_client.receive_messages.assert_called_once_with(max_messages=10)
        mock_client.complete_message.assert_called_once_with(mock_message)

    @pytest.mark.asyncio
    @patch("libs.service_bus_router.ServiceBusConfig")
    async def test_process_message_failure(self, mock_config):
        """Test message processing failure."""
        # Create mock message that will cause processing failure
        mock_message = MagicMock()
        mock_message.message_id = "test-message-456"
        mock_message.__str__ = lambda: json.dumps(
            {"operation": "process", "payload": {"should_fail": True}}
        )

        # Create mock Service Bus client
        mock_client = AsyncMock(spec=ServiceBusClient)
        mock_client.receive_messages.return_value = [mock_message]

        # Create router and inject mock client
        router = MockServiceBusRouter()
        router._service_bus_client = mock_client

        # Test message processing
        metadata = {"service": "test"}
        result = await router._process_servicebus_message_impl(metadata)

        # Verify results - overall success but message failed
        assert result.status == "success"
        assert result.data.messages_received == 1
        assert result.data.messages_processed == 0
        assert result.data.messages_failed == 1

        # Verify Service Bus interactions
        mock_client.receive_messages.assert_called_once_with(max_messages=10)
        mock_client.abandon_message.assert_called_once_with(mock_message)

    @pytest.mark.asyncio
    @patch("libs.service_bus_router.ServiceBusConfig")
    async def test_get_servicebus_status(self, mock_config):
        """Test Service Bus status endpoint."""
        # Mock Service Bus client
        mock_client = AsyncMock(spec=ServiceBusClient)
        mock_client.namespace = "test-namespace"
        mock_client.queue_name = "test-queue"

        # Create router and inject mock client
        router = MockServiceBusRouter()
        router._service_bus_client = mock_client

        # Test status retrieval
        metadata = {"service": "test"}
        result = await router._get_servicebus_status_impl(metadata)

        # Verify results
        assert result.status == "success"
        assert isinstance(result.data, ServiceBusStatusResponse)
        assert result.data.namespace == "test-namespace"
        assert result.data.queue_name == "test-queue"


class TestRouterEndpoints:
    """Test cases for router HTTP endpoints."""

    @pytest.mark.asyncio
    async def test_process_message_endpoint(self):
        """Test the process message HTTP endpoint."""
        router = MockServiceBusRouter()

        # Test endpoint exists in router
        routes = [route.path for route in router.router.routes]
        assert "/test/process-servicebus-message" in routes

    @pytest.mark.asyncio
    async def test_servicebus_status_endpoint(self):
        """Test the Service Bus status HTTP endpoint."""
        router = MockServiceBusRouter()

        # Test endpoint exists in router
        routes = [route.path for route in router.router.routes]
        assert "/test/servicebus-status" in routes

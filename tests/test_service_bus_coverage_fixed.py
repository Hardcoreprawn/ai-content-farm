"""
Service Bus Router Coverage Tests

This module provides comprehensive coverage tests for the Service Bus router
infrastructure with proper mocking and isolation.
"""

import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libs.service_bus_client import ServiceBusClient
from libs.service_bus_router import ServiceBusRouterBase, ServiceBusStatusResponse
from libs.shared_models import StandardResponse


class TestRouter(ServiceBusRouterBase):
    """Test router implementation for coverage testing."""

    def __init__(self):
        super().__init__(
            service_name="test-router", queue_name="test-queue", prefix="/test"
        )

    async def process_message_payload(
        self, payload: Dict[str, Any], operation: str
    ) -> Dict[str, Any]:
        """Test message processing."""
        return {"status": "success", "operation": operation, "payload": payload}

    def get_max_messages(self) -> int:
        """Test max messages."""
        return 5

    def is_processing_successful(self, result: Dict[str, Any]) -> bool:
        """Test success check."""
        return result.get("status") == "success"


class TestServiceBusRouterCoverage:
    """Comprehensive coverage tests for Service Bus router."""

    def test_service_bus_router_base_initialization(self):
        """Test Service Bus router initialization."""
        router = TestRouter()
        assert router.service_name == "test-router"
        assert router.queue_name == "test-queue"
        assert router.router.prefix == "/test"

    @pytest.mark.asyncio
    @patch("libs.service_bus_router.ServiceBusConfig")
    async def test_message_processing_flow(self, mock_config):
        """Test complete message processing flow."""
        # Create mock message
        mock_message = MagicMock()
        mock_message.message_id = "test-123"
        mock_message.__str__ = lambda: json.dumps(
            {"operation": "test_op", "payload": {"data": "test"}}
        )

        # Create mock Service Bus client
        mock_client = AsyncMock(spec=ServiceBusClient)
        mock_client.receive_messages.return_value = [mock_message]

        # Create router and inject mock client
        router = TestRouter()
        router._service_bus_client = mock_client

        # Test message processing
        result = await router._process_servicebus_message_impl({})

        # Verify results
        assert result.status == "success"
        assert result.data.messages_received == 1
        assert result.data.messages_processed == 1
        assert result.data.messages_failed == 0

    @pytest.mark.asyncio
    @patch("libs.service_bus_router.ServiceBusConfig")
    async def test_error_handling_in_message_processing(self, mock_config):
        """Test error handling during message processing."""
        # Create mock message with invalid JSON
        mock_message = MagicMock()
        mock_message.message_id = "test-error-123"
        mock_message.__str__ = lambda: "invalid json"

        # Create mock Service Bus client
        mock_service_bus_client = AsyncMock(spec=ServiceBusClient)
        mock_service_bus_client.receive_messages.return_value = [mock_message]

        # Create router and inject mock client
        router = TestRouter()
        router._service_bus_client = mock_service_bus_client

        # Test message processing with error
        result = await router._process_servicebus_message_impl({})

        # Verify error handling
        assert result.status == "success"  # Overall process succeeds
        assert result.data.messages_received == 1
        assert result.data.messages_processed == 0
        assert result.data.messages_failed == 1

    @pytest.mark.asyncio
    @patch("libs.service_bus_router.ServiceBusConfig")
    async def test_service_bus_status_retrieval(self, mock_config):
        """Test Service Bus status retrieval."""
        # Create mock Service Bus client
        mock_client = AsyncMock(spec=ServiceBusClient)
        mock_client.namespace = "test-namespace"
        mock_client.queue_name = "test-queue"

        # Create router and inject mock client
        router = TestRouter()
        router._service_bus_client = mock_client

        # Test status retrieval
        result = await router._get_servicebus_status_impl({})

        # Verify status response
        assert result.status == "success"
        assert isinstance(result.data, ServiceBusStatusResponse)

    def test_router_configuration_methods(self):
        """Test router configuration methods."""
        router = TestRouter()

        # Test max messages configuration
        assert router.get_max_messages() == 5

        # Test processing success check
        success_result = {"status": "success"}
        failure_result = {"status": "error"}

        assert router.is_processing_successful(success_result) is True
        assert router.is_processing_successful(failure_result) is False

    @pytest.mark.asyncio
    async def test_message_payload_processing(self):
        """Test message payload processing implementation."""
        router = TestRouter()

        # Test payload processing
        payload = {"test": "data"}
        operation = "test_operation"

        result = await router.process_message_payload(payload, operation)

        assert result["status"] == "success"
        assert result["operation"] == operation
        assert result["payload"] == payload


class TestContainerSpecificRouters:
    """Test container-specific router implementations with mocking."""

    @pytest.mark.asyncio
    @patch("libs.service_bus_router.ServiceBusClient")
    async def test_content_collector_router_isolated(self, mock_sb_client):
        """Test content collector router in isolation."""
        # This test validates the router pattern without actual collector logic

        # Create a mock router that simulates content collector behavior
        class MockContentCollectorRouter(ServiceBusRouterBase):
            def __init__(self):
                super().__init__(
                    service_name="content-collector",
                    queue_name="content-collection-queue",
                    prefix="/api/v1/content-collector",
                )

            async def process_message_payload(
                self, payload: Dict[str, Any], operation: str
            ) -> Dict[str, Any]:
                # Simulate content collection processing
                if operation == "collect_content":
                    return {"status": "success", "collected": True}
                return {"status": "error", "message": "Unknown operation"}

            def get_max_messages(self) -> int:
                return 10

            def is_processing_successful(self, result: Dict[str, Any]) -> bool:
                return result.get("status") == "success"

        router = MockContentCollectorRouter()
        assert router.service_name == "content-collector"

    @pytest.mark.asyncio
    @patch("libs.service_bus_router.ServiceBusClient")
    async def test_content_processor_router_isolated(self, mock_sb_client):
        """Test content processor router in isolation."""

        class MockContentProcessorRouter(ServiceBusRouterBase):
            def __init__(self):
                super().__init__(
                    service_name="content-processor",
                    queue_name="content-processing-queue",
                    prefix="/api/v1/content-processor",
                )

            async def process_message_payload(
                self, payload: Dict[str, Any], operation: str
            ) -> Dict[str, Any]:
                # Simulate content processing
                if operation == "process_content":
                    return {"status": "success", "processed": True}
                return {"status": "error", "message": "Unknown operation"}

            def get_max_messages(self) -> int:
                return 5

            def is_processing_successful(self, result: Dict[str, Any]) -> bool:
                return result.get("status") == "success"

        router = MockContentProcessorRouter()
        assert router.service_name == "content-processor"

    @pytest.mark.asyncio
    @patch("libs.service_bus_router.ServiceBusClient")
    async def test_site_generator_router_isolated(self, mock_sb_client):
        """Test site generator router in isolation."""

        class MockSiteGeneratorRouter(ServiceBusRouterBase):
            def __init__(self):
                super().__init__(
                    service_name="site-generator",
                    queue_name="site-generation-queue",
                    prefix="/api/v1/site-generator",
                )

            async def process_message_payload(
                self, payload: Dict[str, Any], operation: str
            ) -> Dict[str, Any]:
                # Simulate site generation
                if operation == "generate_site":
                    return {"status": "success", "generated": True}
                return {"status": "error", "message": "Unknown operation"}

            def get_max_messages(self) -> int:
                return 3

            def is_processing_successful(self, result: Dict[str, Any]) -> bool:
                return result.get("status") == "success"

        router = MockSiteGeneratorRouter()
        assert router.service_name == "site-generator"


class TestServiceBusRouterErrorScenarios:
    """Test error scenarios and edge cases."""

    @pytest.mark.asyncio
    @patch("libs.service_bus_router.ServiceBusConfig")
    async def test_service_bus_client_initialization_failure(self, mock_config):
        """Test Service Bus client initialization failure handling."""
        # Mock config to raise exception
        mock_config.from_environment.side_effect = Exception("Connection failed")

        router = TestRouter()

        # Test that client initialization is handled gracefully
        with pytest.raises(Exception):
            await router._get_service_bus_client()

    @pytest.mark.asyncio
    @patch("libs.service_bus_router.ServiceBusConfig")
    async def test_empty_message_batch_processing(self, mock_config):
        """Test processing when no messages are available."""
        # Create mock Service Bus client with no messages
        mock_client = AsyncMock(spec=ServiceBusClient)
        mock_client.receive_messages.return_value = []

        # Create router and inject mock client
        router = TestRouter()
        router._service_bus_client = mock_client

        # Test message processing with empty batch
        result = await router._process_servicebus_message_impl({})

        # Verify results
        assert result.status == "success"
        assert result.data.messages_received == 0
        assert result.data.messages_processed == 0
        assert result.data.messages_failed == 0

    def test_router_endpoint_registration(self):
        """Test that router endpoints are properly registered."""
        router = TestRouter()

        # Check that routes are registered
        routes = [route.path for route in router.router.routes]

        assert "/test/process-servicebus-message" in routes
        assert "/test/servicebus-status" in routes

        # Check route methods
        post_routes = [
            route for route in router.router.routes if "POST" in route.methods
        ]
        get_routes = [route for route in router.router.routes if "GET" in route.methods]

        assert len(post_routes) >= 1  # process-servicebus-message
        assert len(get_routes) >= 1  # servicebus-status

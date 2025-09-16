"""
Tests for ServiceBusClient queue properties functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.core.exceptions import AzureError, ServiceRequestError
from azure.servicebus.aio import ServiceBusClient as AzureServiceBusClient
from azure.servicebus.management import QueueProperties
from azure.servicebus.management.aio import ServiceBusAdministrationClient

from libs.service_bus_client import ServiceBusClient


class TestServiceBusClientQueueProperties:
    """Test queue properties functionality in ServiceBusClient."""

    @pytest.fixture
    async def service_bus_client(self):
        """Create a ServiceBusClient instance for testing."""
        client = ServiceBusClient("test-queue")
        client._client = AsyncMock(spec=AzureServiceBusClient)
        client._admin_client = AsyncMock(spec=ServiceBusAdministrationClient)
        return client

    @pytest.mark.asyncio
    async def test_get_queue_properties_success(self, service_bus_client):
        """Test successful queue properties retrieval."""
        # Mock queue properties
        mock_properties = MagicMock(spec=QueueProperties)
        mock_properties.name = "test-queue"
        mock_properties.active_message_count = 42
        mock_properties.dead_letter_message_count = 3
        mock_properties.scheduled_message_count = 1
        mock_properties.transfer_message_count = 0
        mock_properties.transfer_dead_letter_message_count = 0
        mock_properties.max_size_in_megabytes = 1024

        service_bus_client._admin_client.get_queue.return_value = mock_properties

        result = await service_bus_client.get_queue_properties()

        assert result["status"] == "healthy"
        assert result["queue_name"] == "test-queue"
        assert result["active_message_count"] == 42
        assert result["dead_letter_message_count"] == 3
        assert result["scheduled_message_count"] == 1
        assert result["transfer_message_count"] == 0
        assert result["transfer_dead_letter_message_count"] == 0
        assert result["max_size_in_megabytes"] == 1024
        assert "timestamp" in result

        service_bus_client._admin_client.get_queue.assert_called_once_with("test-queue")

    @pytest.mark.asyncio
    async def test_get_queue_properties_service_request_error(self, service_bus_client):
        """Test handling of ServiceRequestError during queue properties retrieval."""
        service_bus_client._admin_client.get_queue.side_effect = ServiceRequestError(
            "Queue not found", response=MagicMock()
        )

        result = await service_bus_client.get_queue_properties()

        assert result["status"] == "error"
        assert result["queue_name"] == "test-queue"
        assert "Queue not found" in result["error"]
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_queue_properties_azure_error(self, service_bus_client):
        """Test handling of general AzureError during queue properties retrieval."""
        service_bus_client._admin_client.get_queue.side_effect = AzureError(
            "Azure service unavailable"
        )

        result = await service_bus_client.get_queue_properties()

        assert result["status"] == "error"
        assert result["queue_name"] == "test-queue"
        assert "Azure service unavailable" in result["error"]
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_queue_properties_generic_exception(self, service_bus_client):
        """Test handling of generic exceptions during queue properties retrieval."""
        service_bus_client._admin_client.get_queue.side_effect = ValueError(
            "Unexpected error"
        )

        result = await service_bus_client.get_queue_properties()

        assert result["status"] == "error"
        assert result["queue_name"] == "test-queue"
        assert "Unexpected error" in result["error"]
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_queue_properties_admin_client_not_initialized(self):
        """Test queue properties when admin client is not initialized."""
        client = ServiceBusClient("test-queue")
        client._client = AsyncMock(spec=AzureServiceBusClient)
        # Don't set _admin_client

        result = await client.get_queue_properties()

        assert result["status"] == "error"
        assert result["queue_name"] == "test-queue"
        assert "Admin client not initialized" in result["error"]
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_queue_properties_none_properties(self, service_bus_client):
        """Test handling when queue properties return None."""
        service_bus_client._admin_client.get_queue.return_value = None

        result = await service_bus_client.get_queue_properties()

        assert result["status"] == "error"
        assert result["queue_name"] == "test-queue"
        assert "No properties returned" in result["error"]
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_queue_properties_missing_attributes(self, service_bus_client):
        """Test handling when queue properties are missing expected attributes."""
        # Mock incomplete properties object
        mock_properties = MagicMock()
        mock_properties.name = "test-queue"
        mock_properties.active_message_count = 10
        # Missing other attributes to test robustness
        del mock_properties.dead_letter_message_count

        service_bus_client._admin_client.get_queue.return_value = mock_properties

        result = await service_bus_client.get_queue_properties()

        assert result["status"] == "healthy"
        assert result["queue_name"] == "test-queue"
        assert result["active_message_count"] == 10
        # Should handle missing attributes gracefully
        assert result.get("dead_letter_message_count") is None

    @pytest.mark.asyncio
    async def test_queue_properties_integration_with_initialization(self):
        """Test that queue properties work after proper client initialization."""
        with (
            patch(
                "azure.servicebus.aio.ServiceBusClient.from_connection_string"
            ) as mock_client,
            patch(
                "azure.servicebus.management.aio.ServiceBusAdministrationClient.from_connection_string"
            ) as mock_admin,
        ):

            mock_client_instance = AsyncMock(spec=AzureServiceBusClient)
            mock_admin_instance = AsyncMock(spec=ServiceBusAdministrationClient)
            mock_client.return_value = mock_client_instance
            mock_admin.return_value = mock_admin_instance

            # Mock queue properties
            mock_properties = MagicMock(spec=QueueProperties)
            mock_properties.name = "test-queue"
            mock_properties.active_message_count = 5
            mock_properties.dead_letter_message_count = 0
            mock_admin_instance.get_queue.return_value = mock_properties

            client = ServiceBusClient("test-queue")
            await client.initialize("test-connection-string")

            result = await client.get_queue_properties()

            assert result["status"] == "healthy"
            assert result["active_message_count"] == 5
            mock_admin_instance.get_queue.assert_called_once_with("test-queue")

    @pytest.mark.asyncio
    async def test_queue_properties_timing(self, service_bus_client):
        """Test that queue properties include timing information."""
        import time

        mock_properties = MagicMock(spec=QueueProperties)
        mock_properties.name = "test-queue"
        mock_properties.active_message_count = 1

        start_time = time.time()
        service_bus_client._admin_client.get_queue.return_value = mock_properties

        result = await service_bus_client.get_queue_properties()
        end_time = time.time()

        assert result["status"] == "healthy"
        assert "timestamp" in result
        # Verify timestamp is reasonable (within test execution time)
        timestamp = result["timestamp"]
        assert start_time <= timestamp <= end_time

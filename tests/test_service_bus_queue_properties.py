"""
Tests for ServiceBusClient queue properties functionality.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.core.exceptions import AzureError, ServiceRequestError
from azure.servicebus.aio import ServiceBusClient as AzureServiceBusClient
from azure.servicebus.management import QueueRuntimeProperties

from libs.service_bus_client import ServiceBusClient, ServiceBusConfig


class TestServiceBusClientQueueProperties:
    """Test queue properties functionality in ServiceBusClient."""

    @pytest.fixture
    def service_bus_config(self):
        """Create a test ServiceBusConfig."""
        return ServiceBusConfig(namespace="test-namespace", queue_name="test-queue")

    @pytest.fixture
    async def service_bus_client(self, service_bus_config):
        """Create a ServiceBusClient instance for testing."""
        client = ServiceBusClient(service_bus_config)
        client._client = AsyncMock(spec=AzureServiceBusClient)
        return client

    @pytest.mark.asyncio
    async def test_get_queue_properties_success(self, service_bus_client):
        """Test successful queue properties retrieval."""
        # Mock queue runtime properties
        mock_properties = MagicMock(spec=QueueRuntimeProperties)
        mock_properties.active_message_count = 42
        mock_properties.dead_letter_message_count = 3
        mock_properties.scheduled_message_count = 1
        mock_properties.transfer_message_count = 0
        mock_properties.transfer_dead_letter_message_count = 0
        mock_properties.size_in_bytes = 1024
        mock_properties.created_at = datetime.now(timezone.utc)
        mock_properties.updated_at = datetime.now(timezone.utc)
        mock_properties.accessed_at = datetime.now(timezone.utc)

        with patch(
            "azure.servicebus.management.ServiceBusAdministrationClient"
        ) as mock_mgmt_client:
            mock_mgmt_instance = MagicMock()
            mock_mgmt_client.return_value = mock_mgmt_instance
            mock_mgmt_instance.get_queue_runtime_properties.return_value = (
                mock_properties
            )

            result = await service_bus_client.get_queue_properties()

            assert result["status"] == "healthy"
            assert result["queue_name"] == "test-queue"
            assert result["active_message_count"] == 42
            assert result["dead_letter_message_count"] == 3
            assert result["scheduled_message_count"] == 1
            assert result["transfer_message_count"] == 0
            assert result["transfer_dead_letter_message_count"] == 0
            assert result["total_message_count"] == 46  # Sum of all counts
            assert result["size_in_bytes"] == 1024
            assert "timestamp" in result

            mock_mgmt_instance.get_queue_runtime_properties.assert_called_once_with(
                queue_name="test-queue"
            )

    @pytest.mark.asyncio
    async def test_get_queue_properties_service_request_error(self, service_bus_client):
        """Test handling of ServiceRequestError during queue properties retrieval."""
        with patch(
            "azure.servicebus.management.ServiceBusAdministrationClient"
        ) as mock_mgmt_client:
            mock_mgmt_instance = MagicMock()
            mock_mgmt_client.return_value = mock_mgmt_instance
            mock_mgmt_instance.get_queue_runtime_properties.side_effect = (
                ServiceRequestError("Queue not found", response=MagicMock())
            )

            result = await service_bus_client.get_queue_properties()

            assert result["status"] == "error"
            assert result["queue_name"] == "test-queue"
            assert "Queue not found" in result["error"]
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_queue_properties_azure_error(self, service_bus_client):
        """Test handling of general AzureError during queue properties retrieval."""
        with patch(
            "azure.servicebus.management.ServiceBusAdministrationClient"
        ) as mock_mgmt_client:
            mock_mgmt_instance = MagicMock()
            mock_mgmt_client.return_value = mock_mgmt_instance
            mock_mgmt_instance.get_queue_runtime_properties.side_effect = AzureError(
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
        with patch(
            "azure.servicebus.management.ServiceBusAdministrationClient"
        ) as mock_mgmt_client:
            mock_mgmt_instance = MagicMock()
            mock_mgmt_client.return_value = mock_mgmt_instance
            mock_mgmt_instance.get_queue_runtime_properties.side_effect = ValueError(
                "Unexpected error"
            )

            result = await service_bus_client.get_queue_properties()

            assert result["status"] == "error"
            assert result["queue_name"] == "test-queue"
            assert "Unexpected error" in result["error"]
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_queue_properties_client_not_connected(self):
        """Test queue properties when client is not connected."""
        config = ServiceBusConfig(namespace="test-namespace", queue_name="test-queue")
        client = ServiceBusClient(config)
        # Don't mock _client to simulate unconnected state

        with patch(
            "azure.servicebus.management.ServiceBusAdministrationClient"
        ) as mock_mgmt_client:
            mock_mgmt_instance = MagicMock()
            mock_mgmt_client.return_value = mock_mgmt_instance

            mock_properties = MagicMock(spec=QueueRuntimeProperties)
            mock_properties.active_message_count = 5
            mock_properties.dead_letter_message_count = 0
            mock_properties.scheduled_message_count = 0
            mock_properties.transfer_message_count = 0
            mock_properties.transfer_dead_letter_message_count = 0
            mock_properties.size_in_bytes = 512
            mock_properties.created_at = None
            mock_properties.updated_at = None
            mock_properties.accessed_at = None
            mock_mgmt_instance.get_queue_runtime_properties.return_value = (
                mock_properties
            )

            with patch.object(
                client, "connect", new_callable=AsyncMock
            ) as mock_connect:
                result = await client.get_queue_properties()

                assert result["status"] == "healthy"
                assert result["active_message_count"] == 5
                mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_queue_properties_timing(self, service_bus_client):
        """Test that queue properties include timing information."""
        import time

        mock_properties = MagicMock(spec=QueueRuntimeProperties)
        mock_properties.active_message_count = 1
        mock_properties.dead_letter_message_count = 0
        mock_properties.scheduled_message_count = 0
        mock_properties.transfer_message_count = 0
        mock_properties.transfer_dead_letter_message_count = 0
        mock_properties.size_in_bytes = 256
        mock_properties.created_at = None
        mock_properties.updated_at = None
        mock_properties.accessed_at = None

        with patch(
            "azure.servicebus.management.ServiceBusAdministrationClient"
        ) as mock_mgmt_client:
            mock_mgmt_instance = MagicMock()
            mock_mgmt_client.return_value = mock_mgmt_instance
            mock_mgmt_instance.get_queue_runtime_properties.return_value = (
                mock_properties
            )

            start_time = time.time()
            result = await service_bus_client.get_queue_properties()
            end_time = time.time()

            assert result["status"] == "healthy"
            assert "timestamp" in result
            # Verify timestamp is reasonable (within test execution time)
            # Parse ISO timestamp to compare
            from datetime import datetime

            timestamp = datetime.fromisoformat(
                result["timestamp"].replace("Z", "+00:00")
            ).timestamp()
            assert start_time <= timestamp <= end_time

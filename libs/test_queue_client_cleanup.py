"""
Tests for queue_client credential cleanup.

Ensures DefaultAzureCredential sessions are properly closed.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from libs.queue_client import StorageQueueClient


@pytest.mark.asyncio
async def test_storage_queue_client_closes_credential():
    """Test that StorageQueueClient closes the credential on close()."""

    with (
        patch("libs.queue_client.DefaultAzureCredential") as mock_cred_class,
        patch("libs.queue_client.QueueClient") as mock_queue_class,
    ):

        # Setup mocks
        mock_credential = Mock()
        mock_credential.close = AsyncMock()
        mock_cred_class.return_value = mock_credential

        mock_queue_client = Mock()
        mock_queue_client.close = AsyncMock()
        mock_queue_client.create_queue = AsyncMock()
        mock_queue_class.return_value = mock_queue_client

        # Create and connect client
        client = StorageQueueClient(
            queue_name="test-queue", storage_account_name="testaccount"
        )

        await client.connect()

        # Verify credential was created
        assert client._credential is not None
        mock_cred_class.assert_called_once()

        # Close the client
        await client.close()

        # Verify both queue client and credential were closed
        mock_queue_client.close.assert_called_once()
        mock_credential.close.assert_called_once()


@pytest.mark.asyncio
async def test_storage_queue_client_context_manager_closes_credential():
    """Test that context manager properly closes credential."""

    with (
        patch("libs.queue_client.DefaultAzureCredential") as mock_cred_class,
        patch("libs.queue_client.QueueClient") as mock_queue_class,
    ):

        # Setup mocks
        mock_credential = Mock()
        mock_credential.close = AsyncMock()
        mock_cred_class.return_value = mock_credential

        mock_queue_client = Mock()
        mock_queue_client.close = AsyncMock()
        mock_queue_client.create_queue = AsyncMock()
        mock_queue_class.return_value = mock_queue_client

        # Use context manager
        async with StorageQueueClient(
            queue_name="test-queue", storage_account_name="testaccount"
        ) as client:
            # Verify credential was created
            assert client._credential is not None

        # Verify cleanup happened on exit
        mock_queue_client.close.assert_called_once()
        mock_credential.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_handles_none_credential_safely():
    """Test that close() safely handles cases where credential is None."""

    with (
        patch("libs.queue_client.DefaultAzureCredential"),
        patch("libs.queue_client.QueueClient"),
    ):

        client = StorageQueueClient(
            queue_name="test-queue", storage_account_name="testaccount"
        )

        # Close without connecting (credential will be None)
        await client.close()  # Should not raise exception

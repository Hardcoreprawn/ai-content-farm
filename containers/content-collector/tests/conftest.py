"""
Pytest configuration and fixtures for Content Womble tests.

Provides mocks and fixtures for isolated unit testing with modular multi-source architecture.
"""

import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add paths for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs"))


@pytest.fixture(autouse=True)
def mock_asyncio_sleep():
    """Mock asyncio.sleep globally to speed up tests."""
    with patch("asyncio.sleep", new_callable=AsyncMock):
        yield


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment with mocked dependencies for multi-source content collection."""
    # Set required environment variables for tests
    test_env = {
        "AZURE_STORAGE_ACCOUNT_NAME": "test_storage_account",
        "AZURE_STORAGE_CONNECTION_STRING": "test_connection_string",
        "ENVIRONMENT": "testing",
        "KEY_VAULT_URL": "https://test-keyvault.vault.azure.net/",
        "REDDIT_CLIENT_ID": "",
        "REDDIT_CLIENT_SECRET": "",
    }

    with patch.dict(os.environ, test_env):
        # Mock Reddit client class (not singleton function)
        with patch("reddit_client.RedditClient") as mock_reddit_class:
            mock_reddit_instance = Mock()
            mock_reddit_instance.reddit = None
            mock_reddit_instance.is_available.return_value = False
            mock_reddit_instance.get_trending_posts.return_value = []
            mock_reddit_class.return_value = mock_reddit_instance

            # Mock content collection service dependencies
            with (
                patch("libs.blob_storage.BlobStorageClient") as mock_storage_class,
                patch("content_processing.collect_content_batch") as mock_collect_batch,
                patch(
                    "service_logic.collect_content_batch"
                ) as mock_collect_batch_service,
                patch(
                    "source_collectors.SourceCollectorFactory"
                ) as mock_collector_factory,
                patch("libs.queue_client.send_wake_up_message") as mock_queue_client,
            ):
                # Setup mock storage client
                mock_storage = Mock()
                mock_storage.upload_text = Mock(return_value="mock_blob_url")
                mock_storage.upload_json = Mock(return_value="mock_blob_url")
                mock_storage.download_text = Mock(return_value='{"test": "data"}')
                mock_storage.list_blobs = Mock(return_value=[])
                mock_storage.health_check = Mock(return_value={"status": "healthy"})
                mock_storage_class.return_value = mock_storage

                # Setup mock content collection
                mock_collect_batch.return_value = {
                    "collected_items": [],
                    "metadata": {"total_collected": 0},
                }
                mock_collect_batch_service.return_value = {
                    "collected_items": [],
                    "metadata": {"total_collected": 0},
                }

                # Setup mock collector factory
                mock_collector = Mock()
                mock_collector.collect_content = AsyncMock(return_value=[])
                mock_collector_factory.create_collector.return_value = mock_collector

                # Setup mock queue client
                mock_queue_client.return_value = {"message_id": "test_message_123"}

                yield {
                    "storage": mock_storage,
                    "storage_class": mock_storage_class,
                    "reddit_class": mock_reddit_class,
                    "reddit_instance": mock_reddit_instance,
                    "collect_batch": mock_collect_batch,
                    "queue_client": mock_queue_client,
                }


@pytest.fixture
def mock_reddit_client():
    """Provide a mock Reddit client for individual tests."""
    client = Mock()
    client.reddit = None
    client.is_available.return_value = False
    client.get_trending_posts.return_value = []
    return client


@pytest.fixture
def mock_storage_client():
    """Provide a mock storage client for individual tests."""
    storage = Mock()
    storage.upload_text = Mock(return_value="mock://blob/test.txt")
    storage.upload_json = Mock(return_value="mock://blob/test.json")
    storage.download_text = Mock(return_value='{"test": "data"}')
    storage.list_blobs = Mock(return_value=[])
    storage.health_check = Mock(return_value={"status": "healthy"})
    return storage


@pytest.fixture
def mock_content_collector_service(mock_storage_client):
    """Provide a mock content collector service for individual tests."""
    service = Mock()
    service.collect_and_store_content = AsyncMock(
        return_value={
            "sources_processed": 1,
            "total_items_collected": 5,
            "items_saved": 5,
            "storage_location": "container://test/data.json",
            "processing_time_ms": 1000,
        }
    )
    service.health_check = Mock(return_value={"status": "healthy", "uptime": "1h 30m"})
    return service

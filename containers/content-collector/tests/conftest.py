"""
Pytest configuration and fixtures for Content Womble tests.

Provides mocks and fixtures for isolated unit testing of the standardized API.
"""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment with mocked dependencies and required env vars."""
    # Set required environment variables for tests
    test_env = {
        "AZURE_STORAGE_ACCOUNT_NAME": "test_storage_account",
        "AZURE_STORAGE_CONNECTION_STRING": "test_connection_string",
        "ENVIRONMENT": "testing",  # This makes Reddit client go to local mode
        "KEY_VAULT_URL": "https://test-keyvault.vault.azure.net/",
        # Set empty Reddit credentials so it falls back to anonymous mode
        "REDDIT_CLIENT_ID": "",
        "REDDIT_CLIENT_SECRET": "",
    }

    with patch.dict(os.environ, test_env):
        # Mock the Reddit client function that replaced the module-level variable
        with patch("endpoints.get_reddit_client") as mock_get_reddit_client:
            mock_reddit_client = Mock()
            mock_reddit_client.reddit = None
            mock_reddit_client.is_available.return_value = False
            mock_get_reddit_client.return_value = mock_reddit_client

            # Mock Azure storage and other external dependencies
            with (
                patch("libs.blob_storage.BlobStorageClient") as mock_storage_class,
                patch("service_logic.ContentCollectorService") as mock_service_class,
                patch("endpoints.get_blob_client") as mock_get_blob,
                patch("endpoints.get_collector_service") as mock_get_service,
            ):  # Setup mock storage client
                mock_storage = Mock()
                mock_storage.upload_text = Mock(return_value="mock_blob_url")
                mock_storage.upload_json = Mock(return_value="mock_blob_url")
                mock_storage.download_text = Mock(return_value='{"test": "data"}')
                mock_storage.list_blobs = Mock(return_value=[])
                mock_storage.health_check = Mock(return_value={"status": "healthy"})
                mock_storage.test_connection = Mock(
                    return_value={"status": "connected", "bearer_token_valid": True}
                )
                mock_storage_class.return_value = mock_storage
                mock_get_blob.return_value = mock_storage

                # Setup mock service
                mock_service = Mock()
                mock_service.collect_and_store_content = AsyncMock(
                    return_value={
                        "sources_processed": 1,
                        "total_items_collected": 5,
                        "items_saved": 5,
                        "storage_location": "container://test/data.json",
                        "processing_time_ms": 1000,
                    }
                )
                mock_service.health_check = Mock(
                    return_value={"status": "healthy", "uptime": "1h 30m"}
                )
                mock_service_class.return_value = mock_service
                mock_get_service.return_value = mock_service

                yield {
                    "storage": mock_storage,
                    "service": mock_service,
                    "storage_class": mock_storage_class,
                    "service_class": mock_service_class,
                }

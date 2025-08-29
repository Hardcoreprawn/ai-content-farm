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
        "ENVIRONMENT": "test",
        "KEY_VAULT_URL": "https://test-keyvault.vault.azure.net/",
    }

    with patch.dict(os.environ, test_env):
        # Mock Azure storage and other external dependencies
        with patch("libs.blob_storage.BlobStorageClient") as mock_storage_class, patch(
            "service_logic.ContentCollectorService"
        ) as mock_service_class, patch(
            "endpoints.get_blob_client"
        ) as mock_get_blob, patch(
            "endpoints.get_collector_service"
        ) as mock_get_service:  # Setup mock storage client
            mock_storage = Mock()
            mock_storage.upload_text = Mock(return_value="mock_blob_url")
            mock_storage.upload_json = Mock(return_value="mock_blob_url")
            mock_storage.download_text = Mock(return_value='{"test": "data"}')
            mock_storage.list_blobs = Mock(return_value=[])
            mock_storage.health_check = Mock(return_value={"status": "healthy"})
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
                    "summary": "Collected 5 items from 1 Reddit source",
                }
            )
            mock_service.get_status = Mock(
                return_value={
                    "service": "content-womble",
                    "version": "2.0.0",
                    "environment": "test",
                    "reddit_available": True,
                    "storage_available": True,
                    "last_collection": None,
                    "total_collections": 0,
                }
            )
            mock_service_class.return_value = mock_service
            mock_get_service.return_value = mock_service

            yield

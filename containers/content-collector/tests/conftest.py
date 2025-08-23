"""
Pytest configuration and fixtures for content-collector tests.

Provides mocks and fixtures for isolated unit testing.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_blob_storage():
    """Create a mock blob storage client."""
    mock_storage = Mock()
    mock_storage.upload_text = Mock(return_value="mock_blob_url")
    mock_storage.upload_json = Mock(return_value="mock_blob_url")
    mock_storage.download_text = Mock(return_value='{"test": "data"}')
    mock_storage.list_blobs = Mock(return_value=[])
    return mock_storage


@pytest.fixture
def mock_reddit_api():
    """Create a mock Reddit API response."""
    return [
        {
            "id": "test_id_1",
            "title": "Test Post 1",
            "url": "https://reddit.com/r/test/test1",
            "score": 100,
            "num_comments": 10,
            "created_utc": 1629800000,
            "author": "test_author",
            "selftext": "Test content",
            "subreddit": "test",
        },
        {
            "id": "test_id_2",
            "title": "Test Post 2",
            "url": "https://reddit.com/r/test/test2",
            "score": 50,
            "num_comments": 5,
            "created_utc": 1629800100,
            "author": "test_author2",
            "selftext": "More test content",
            "subreddit": "test",
        },
    ]


@pytest.fixture(autouse=True)
def setup_test_environment(mock_blob_storage, mock_reddit_api):
    """Set up test environment with mocked dependencies."""
    # Patch external dependencies
    with patch("collector.fetch_from_subreddit", return_value=mock_reddit_api), patch(
        "main.collector_service"
    ) as mock_service:

        # Mock the service methods with smarter responses
        mock_service.storage = mock_blob_storage

        def smart_collect_response(*args, **kwargs):
            """Smart mock that responds based on request content."""
            # Extract request data from args or kwargs
            sources_data = []
            if args and len(args) > 0:
                sources_data = args[0]
            elif "sources_data" in kwargs:
                sources_data = kwargs["sources_data"]

            # Handle empty sources
            if not sources_data or len(sources_data) == 0:
                return {
                    "collection_id": "empty_collection",
                    "collected_items": [],
                    "metadata": {
                        "total_collected": 0,
                        "total_sources": 0,
                        "processing_time": 0.1,
                        "timestamp": "2025-08-23T12:00:00Z",
                    },
                    "timestamp": "2025-08-23T12:00:00Z",
                    "storage_location": None,
                }

            # Handle invalid source types
            has_valid_sources = any(
                source.get("type") == "reddit" for source in sources_data
            )
            if not has_valid_sources:
                return {
                    "collection_id": "invalid_sources",
                    "collected_items": [],
                    "metadata": {
                        "total_collected": 0,
                        "total_sources": len(sources_data),
                        "processing_time": 0.1,
                        "timestamp": "2025-08-23T12:00:00Z",
                        "errors": 1,
                    },
                    "timestamp": "2025-08-23T12:00:00Z",
                    "storage_location": None,
                }

            # Default successful response
            return {
                "collection_id": "test_collection_123",
                "collected_items": [
                    {
                        "id": "test_id_1",
                        "title": "Test Post 1",
                        "url": "https://reddit.com/r/test/test1",
                        "score": 100,
                        "source": "reddit",
                        "metadata": {"comments": 10, "created_utc": 1629800000},
                    },
                    {
                        "id": "test_id_2",
                        "title": "Test Post 2",
                        "url": "https://reddit.com/r/test/test2",
                        "score": 50,
                        "source": "reddit",
                        "metadata": {"comments": 5, "created_utc": 1629800100},
                    },
                ],
                "metadata": {
                    "total_collected": 2,
                    "total_sources": 1,
                    "processing_time": 1.5,
                    "timestamp": "2025-08-23T12:00:00Z",
                },
                "timestamp": "2025-08-23T12:00:00Z",
                "storage_location": "mock://blob/collection_test_123.json",
            }

        mock_service.collect_and_store_content = AsyncMock(
            side_effect=smart_collect_response
        )
        mock_service.get_stats = Mock(
            return_value={
                "total_collections": 1,
                "successful_collections": 1,
                "failed_collections": 0,
                "last_collection": "test_collection_123",
            }
        )

        yield

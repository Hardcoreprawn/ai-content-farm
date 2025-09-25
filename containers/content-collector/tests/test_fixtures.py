"""
Test Fixtures for Content Collector - LEGACY

DEPRECATED: Complex test fixtures for legacy adaptive collectors
Status: PENDING REMOVAL - Replaced by simple fixtures in conftest.py

Contains complex mock objects and fixtures for the legacy collector system.
New simplified tests use simpler fixtures from conftest.py.

Shared test fixtures and mock objects for content collector tests.
Extracted to reduce test file size and improve maintainability.

Uses Azure Storage Queue SDK-level mocks for realistic testing.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest

# Add the shared libs folder to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "libs"))

# Import the new SDK-level mocks from shared libs
try:
    from azure_queue_mocks import (
        create_mock_queue_client,
        setup_mock_queue_with_messages,
    )
except ImportError:
    # Fallback if import fails - create minimal mocks
    def create_mock_queue_client(queue_name: str = "test-queue"):
        from unittest.mock import AsyncMock

        mock = AsyncMock()
        mock.queue_name = queue_name
        return mock

    async def setup_mock_queue_with_messages(
        queue_name: str, messages: Optional[List] = None
    ):
        return create_mock_queue_client(queue_name)


class MockBlobStorageClient:
    """Legacy mock blob storage client for testing without Azure dependencies.

    Note: This is deprecated in favor of using unittest.mock.Mock directly
    with SimplifiedBlobClient. New tests should use the simplified approach.
    """

    def __init__(self):
        self.uploaded_files = {}
        self.call_history = []

    async def upload_text(
        self,
        container_name: str,
        blob_name: str,
        content: str,
        content_type: str = "text/plain",
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Mock upload_text method."""
        self.call_history.append(
            {
                "method": "upload_text",
                "container_name": container_name,
                "blob_name": blob_name,
                "content_length": len(content),
                "content_type": content_type,
                "metadata": metadata,
            }
        )

        self.uploaded_files[f"{container_name}/{blob_name}"] = {
            "content": content,
            "content_type": content_type,
            "metadata": metadata or {},
            "uploaded_at": datetime.now(timezone.utc),
        }

        return f"mock://blob/{blob_name}"

    async def upload_json(
        self,
        container_name: str,
        blob_name: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Mock upload_json method."""
        content = json.dumps(data, indent=2, ensure_ascii=False)
        return await self.upload_text(
            container_name, blob_name, content, "application/json", metadata
        )

    async def download_text(self, container_name: str, blob_name: str) -> str:
        """Mock download_text method."""
        self.call_history.append(
            {
                "method": "download_text",
                "container_name": container_name,
                "blob_name": blob_name,
            }
        )

        key = f"{container_name}/{blob_name}"
        if key in self.uploaded_files:
            return self.uploaded_files[key]["content"]
        return '{"mock": "data"}'

    async def list_blobs(
        self, container_name: str, prefix: str = ""
    ) -> List[Dict[str, Any]]:
        """Mock list_blobs method."""
        self.call_history.append(
            {"method": "list_blobs", "container_name": container_name, "prefix": prefix}
        )

        # Return mock blob list
        blobs = []
        for key in self.uploaded_files:
            if key.startswith(f"{container_name}/"):
                blob_name = key[len(container_name) + 1 :]
                if not prefix or blob_name.startswith(prefix):
                    blobs.append(
                        {
                            "name": blob_name,
                            "size": len(self.uploaded_files[key]["content"]),
                            "last_modified": self.uploaded_files[key]["uploaded_at"],
                        }
                    )

        return blobs

    def test_connection(self):
        """Mock test_connection method."""
        return {"status": "connected", "account_name": "test_account"}


class MockQueueClient:
    """Mock Azure Storage Queue client for testing."""

    def __init__(self, queue_name: str):
        self.queue_name = queue_name
        self._messages = []
        self._connected = False

    async def connect(self) -> None:
        """Mock connection."""
        self._connected = True

    async def close(self) -> None:
        """Mock close."""
        self._connected = False

    async def send_message(self, message: Any, **kwargs) -> Dict[str, Any]:
        """Mock message sending."""
        message_id = str(uuid4())
        self._messages.append(
            {
                "id": message_id,
                "content": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return {
            "message_id": message_id,
            "pop_receipt": f"receipt_{message_id}",
            "time_next_visible": None,
            "insertion_time": datetime.now(timezone.utc),
            "expiration_time": None,
        }

    async def receive_messages(self, max_messages: Optional[int] = None) -> List[Any]:
        """Mock message receiving."""
        return self._messages[:max_messages] if max_messages else self._messages

    async def complete_message(self, message) -> None:
        """Mock message completion."""
        pass

    async def get_queue_properties(self) -> Dict[str, Any]:
        """Mock queue properties."""
        return {
            "approximate_message_count": len(self._messages),
            "metadata": {},
            "queue_name": self.queue_name,
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Mock health status."""
        return {
            "status": "healthy" if self._connected else "not_connected",
            "queue_name": self.queue_name,
        }

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


@pytest.fixture
def mock_storage():
    """Provide a mock blob storage client."""
    return MockBlobStorageClient()


@pytest.fixture
def mock_queue_client():
    """Provide a mock Azure Storage Queue client with SDK-level compatibility."""
    return create_mock_queue_client("content-processing-requests")


@pytest.fixture
async def mock_queue_with_messages():
    """Provide a mock queue client with pre-populated test messages."""
    test_messages = [
        {
            "service_name": "content-collector",
            "operation": "wake_up",
            "payload": {"test": "data1"},
        },
        {
            "service_name": "test-service",
            "operation": "process",
            "payload": {"test": "data2"},
        },
    ]
    return await setup_mock_queue_with_messages("test-queue", test_messages)


@pytest.fixture
def sample_collection_data():
    """Provide sample collection data for testing."""
    return {
        "collection_id": "test_collection_20230815_120000",
        "metadata": {
            "timestamp": "2023-08-15T12:00:00Z",
            "total_items": 2,
            "processing_time_seconds": 1.5,
            "source": "reddit",
        },
        "items": [
            {
                "title": "Test Article 1",
                "url": "https://example.com/article1",
                "source": "reddit",
                "content": "Sample content for article 1",
            },
            {
                "title": "Test Article 2",
                "url": "https://example.com/article2",
                "source": "reddit",
                "content": "Sample content for article 2",
            },
        ],
    }


@pytest.fixture
def sample_sources_data():
    """Provide sample sources configuration for testing."""
    return [
        {
            "type": "reddit",
            "config": {"subreddit": "technology", "sort": "hot", "time_filter": "week"},
            "criteria": {"min_score": 100, "max_age_hours": 168},
        }
    ]


@pytest.fixture
def mock_reddit_response():
    """Provide mock Reddit API response data."""
    return {
        "collected_items": [
            {
                "title": "Amazing Technology Breakthrough",
                "url": "https://reddit.com/r/technology/post1",
                "score": 150,
                "created_utc": 1692086400,
                "subreddit": "technology",
                "author": "tech_user",
                "num_comments": 25,
                "content": "This is about an amazing technology breakthrough...",
            },
            {
                "title": "Future of AI Development",
                "url": "https://reddit.com/r/technology/post2",
                "score": 200,
                "created_utc": 1692000000,
                "subreddit": "technology",
                "author": "ai_researcher",
                "num_comments": 45,
                "content": "Discussion about the future of AI development...",
            },
        ],
        "metadata": {
            "source": "reddit",
            "subreddit": "technology",
            "collected_at": "2023-08-15T12:00:00Z",
            "total_found": 2,
        },
    }


@pytest.fixture
def mock_wake_up_response():
    """Provide mock wake-up message response data."""
    return {
        "message_id": str(uuid4()),
        "pop_receipt": str(uuid4()),
        "time_next_visible": datetime.now(timezone.utc),
        "insertion_time": datetime.now(timezone.utc),
        "expiration_time": datetime.now(timezone.utc),
    }


@pytest.fixture
def expected_wake_up_message():
    """Provide expected wake-up message structure."""
    return {
        "service_name": "content-collector",
        "operation": "wake_up",
        "payload": {
            "trigger_reason": "new_collection",
            "collection_id": "test_collection_20230815_120000",
            "items_count": 2,
            "storage_location": "collected-content/collections/2023/08/15/test_collection_20230815_120000.json",
            "message": "Content collected for test_collection_20230815_120000, processor should scan storage",
        },
    }

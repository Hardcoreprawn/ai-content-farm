import os
import sys
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import Mock

import pytest

import libs.blob_mock as blob_mock  # type: ignore[import-untyped]

root = Path(__file__).parent
# Ensure this container directory is first on sys.path so tests importing
# top-level modules like `main` and `processor` resolve to the local files.
sys.path.insert(0, str(root))

# Also add repo root so shared `libs` package is importable during tests
repo_root = root.parent.parent
sys.path.insert(0, str(repo_root))

# Set up test environment detection
os.environ["PYTEST_CURRENT_TEST"] = "true"

# Standardized fast-test environment flags
os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("BLOB_STORAGE_MOCK", "true")

# Set up Azurite connection for integration tests only
if "integration" in os.environ.get("PYTEST_CURRENT_TEST", ""):
    os.environ["AZURE_STORAGE_CONNECTION_STRING"] = (
        "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"  # pragma: allowlist secret
        "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    )


@pytest.fixture(autouse=True)
def _isolate_mock_blob_storage() -> Generator[None, None, None]:
    """Ensure mock blob storage state is isolated per test when in mock mode."""
    if os.getenv("BLOB_STORAGE_MOCK", "false").lower() == "true":
        try:
            blob_mock._MOCK_BLOBS.clear()
            blob_mock._MOCK_CONTAINERS.clear()
        except Exception:
            pass
    yield


@pytest.fixture
def sample_reddit_post() -> Dict[str, Any]:
    """Sample Reddit post data for testing."""
    return {
        "id": "test_post_123",
        "title": "Revolutionary AI breakthrough changes everything",
        "selftext": "Scientists at leading university have developed groundbreaking AI system...",
        "score": 1247,
        "num_comments": 89,
        "created_utc": 1692800000,
        "subreddit": "technology",
        "author": "tech_researcher",
        "url": "https://example.com/ai-breakthrough",
        "upvote_ratio": 0.94,
    }


@pytest.fixture
def sample_collection_data(sample_reddit_post) -> Dict[str, Any]:
    """Sample collection data for testing."""
    return {
        "collection_id": "test_collection_20250823",
        "metadata": {
            "total_collected": 1,
            "timestamp": "2025-08-23T10:00:00Z",
            "collection_version": "1.0.0",
        },
        "items": [sample_reddit_post],
    }


@pytest.fixture
def mock_blob_storage() -> Mock:
    """Mock simplified blob storage client for fast unit tests."""
    from unittest.mock import Mock

    mock_client = Mock()
    mock_client.upload_json = Mock(return_value=True)
    mock_client.download_json = Mock(return_value={"test": "data"})
    mock_client.upload_text = Mock(return_value=True)
    mock_client.download_text = Mock(return_value="test content")
    mock_client.list_blobs = Mock(return_value=[])
    mock_client.delete_blob = Mock(return_value=True)
    return mock_client


@pytest.fixture
def mock_openai_client() -> Any:
    """Mock OpenAI client for fast unit tests."""
    from tests.contracts.openai_api_contract import (
        MockOpenAIClient,  # type: ignore[import-not-found]
    )

    return MockOpenAIClient()

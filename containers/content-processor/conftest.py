import os
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

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
def _isolate_mock_blob_storage():
    """Ensure mock blob storage state is isolated per test when in mock mode."""
    if os.getenv("BLOB_STORAGE_MOCK", "false").lower() == "true":
        try:
            import libs.blob_storage as _bs

            if hasattr(_bs, "_MOCK_BLOBS"):
                _bs._MOCK_BLOBS.clear()
            if hasattr(_bs, "_MOCK_CONTAINERS"):
                _bs._MOCK_CONTAINERS.clear()
        except Exception:
            pass
    yield


@pytest.fixture
def sample_reddit_post():
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
def sample_collection_data(sample_reddit_post):
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
def mock_blob_storage():
    """Mock blob storage client for fast unit tests."""
    from tests.contracts.blob_storage_contract import MockBlobStorageClient

    return MockBlobStorageClient()


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for fast unit tests."""
    from tests.contracts.openai_api_contract import MockOpenAIClient

    return MockOpenAIClient()

"""
Pytest configuration and fixtures for content-ranker tests.

Provides mocks and fixtures for isolated unit testing.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure this container directory is first on sys.path so tests importing
# top-level modules resolve to the local files.
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

# Also add repo root so shared `libs` package is importable during tests
repo_root = root.parent.parent
sys.path.insert(0, str(repo_root))

# Set up environment for testing
os.environ["ENVIRONMENT"] = "local"
os.environ["BLOB_STORAGE_MOCK"] = "true"

# Set up Azurite connection for testing (required for blob storage client init)
os.environ["AZURE_STORAGE_CONNECTION_STRING"] = (
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
)


@pytest.fixture
def mock_blob_storage():
    """Create a mock blob storage client."""
    mock_storage = Mock()
    mock_storage.upload_text = Mock(return_value="mock_blob_url")
    mock_storage.upload_json = Mock(return_value="mock_blob_url")
    mock_storage.download_text = Mock(return_value='{"test": "data"}')
    mock_storage.list_blobs = Mock(return_value=[])
    mock_storage.download_json = Mock(return_value={"test": "data"})
    mock_storage.health_check = Mock(return_value=True)
    return mock_storage


@pytest.fixture
def mock_ranker_service(mock_blob_storage):
    """Create a mock content ranker service."""
    with patch("service_logic.BlobStorageClient", return_value=mock_blob_storage):
        from service_logic import ContentRankerService

        return ContentRankerService()


@pytest.fixture
def test_client(mock_ranker_service):
    """Create a test client for the FastAPI app."""
    with patch("main.ranker_service", mock_ranker_service):
        from main import app

        return TestClient(app)


@pytest.fixture(autouse=True)
def _isolate_mock_blob_storage():
    """Isolate mock blob storage between tests."""
    if os.getenv("BLOB_STORAGE_MOCK", "false").lower() == "true":
        import libs.blob_storage as _bs

        if hasattr(_bs, "_MOCK_BLOBS"):
            _bs._MOCK_BLOBS.clear()
        if hasattr(_bs, "_MOCK_CONTAINERS"):
            _bs._MOCK_CONTAINERS.clear()
    yield

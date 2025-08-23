"""
Content Enricher Test Configuration

Provides shared test fixtures and configuration for pytest.
Includes Azurite integration for blob storage testing.
"""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure this container directory is first on sys.path so tests importing
# top-level modules like `main` and `enricher` resolve to the local files.
root = Path(__file__).parent
sys.path.insert(0, str(root))

# Also add repo root so shared `libs` package is importable during tests
repo_root = root.parent.parent
sys.path.insert(0, str(repo_root))


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment with Azurite connection string."""
    # Configure Azurite connection string for local testing
    azurite_connection = (
        "DefaultEndpointsProtocol=http;"
        "AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
        "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    )

    # Set environment variables for testing
    os.environ["AZURE_STORAGE_CONNECTION_STRING"] = azurite_connection
    os.environ["ENVIRONMENT"] = "local"

    yield

    # Cleanup is handled automatically by Azurite


@pytest.fixture
def sample_content():
    """Fixture providing sample content for testing."""
    return {
        "id": "test_id_123",
        "title": "Test Article Title",
        "content": "This is a test article with some content for enrichment testing.",
        "url": "https://example.com/test-article",
        "published_at": "2024-01-15T10:30:00Z",
        "source": "test_source",
        "author": "Test Author",
        "metadata": {"word_count": 100, "estimated_read_time": "1 min"},
    }


@pytest.fixture
def test_client():
    """Create a FastAPI test client."""
    # Import here to avoid circular imports
    from main import app

    return TestClient(app)

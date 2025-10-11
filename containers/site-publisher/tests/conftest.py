"""
Pytest configuration for site-publisher tests.

Provides shared fixtures and test configuration.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

# Add parent directory to path so we can import from site-publisher modules
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def mock_blob_client():
    """Provide a mocked Azure Blob Service Client."""
    mock_client = AsyncMock()
    mock_client.get_container_client = Mock(return_value=AsyncMock())
    return mock_client


@pytest.fixture
def mock_settings():
    """
    Provide mock settings for tests.

    Note: Pylance may show "Settings is unknown import symbol" but this is
    a false positive. The import works at runtime because we add parent dir
    to sys.path at the top of this file.
    """
    from config import Settings  # type: ignore[attr-defined]

    return Settings(  # type: ignore[call-arg]  # Pydantic loads from kwargs in tests
        azure_storage_account_name="teststorage",
        markdown_container="markdown-content",
        output_container="$web",
        backup_container="$web-backup",
        queue_name="site-publishing-requests",
        hugo_base_url="https://test.example.com",
    )


@pytest.fixture
def sample_markdown_content():
    """Provide sample markdown content for testing with valid YAML frontmatter."""
    return """---
title: "Test Article"
url: "https://example.com/test-article"
source: "test"
date: 2025-10-10
tags: ["test", "sample"]
---

# Test Article

This is a test article for site-publisher.

## Content

Sample content here.
"""


@pytest.fixture
def mock_blob_properties():
    """Provide mock blob properties for testing."""
    mock_blob = Mock()
    mock_blob.name = "test-article.md"
    mock_blob.size = 1024
    return mock_blob


@pytest.fixture
def mock_container_client():
    """Provide a mocked container client with common operations."""
    mock_client = AsyncMock()
    mock_client.get_blob_client = Mock(return_value=AsyncMock())
    mock_client.list_blobs = AsyncMock()
    mock_client.delete_blob = AsyncMock()
    return mock_client


@pytest.fixture
def sample_hugo_config():
    """Provide sample Hugo configuration content."""
    return """
baseURL = "https://test.example.com/"
languageCode = "en-us"
title = "Test Site"
theme = "PaperMod"

[params]
    description = "Test site description"
"""


# Configure pytest
pytest_plugins = ["pytest_asyncio"]

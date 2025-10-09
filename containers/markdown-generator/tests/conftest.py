"""
Test fixtures and configuration for markdown-generator tests.
"""

import json
from typing import Any, Dict
from unittest.mock import Mock

import pytest
from azure.storage.blob import BlobServiceClient
from markdown_processor import MarkdownProcessor

from config import Settings


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    return Settings(
        azure_storage_account_name="teststorage",
        storage_connection_string="DefaultEndpointsProtocol=https;"
        "AccountName=teststorage;EndpointSuffix=core.windows.net",
        input_container="test-input",
        output_container="test-output",
        queue_name="test-queue",
        applicationinsights_connection_string=None,
    )


@pytest.fixture
def sample_article_data() -> Dict[str, Any]:
    """Create sample article data for testing."""
    return {
        "title": "Test Article",
        "url": "https://example.com/article",
        "source": "test-source",
        "author": "Test Author",
        "published_date": "2025-10-07T12:00:00Z",
        "category": "technology",
        "tags": ["test", "article"],
        "summary": "This is a test summary.",
        "content": "This is the main content of the test article.",
        "key_points": [
            "First key point",
            "Second key point",
            "Third key point",
        ],
    }


@pytest.fixture
def expected_markdown_content() -> str:
    """Create expected markdown output for testing."""
    return """---
title: "Test Article"
url: https://example.com/article
source: test-source
author: "Test Author"
published_date: 2025-10-07T12:00:00+00:00
category: technology
tags: [test, article]
generated_date: 2025-10-07T12:00:00Z
---

# Test Article

## Summary

This is a test summary.

## Content

This is the main content of the test article.

## Key Points

- First key point
- Second key point
- Third key point

---

**Source:** [https://example.com/article](https://example.com/article)
"""


@pytest.fixture
def mock_blob_service_client(sample_article_data: Dict[str, Any]) -> Mock:
    """Create mock BlobServiceClient for testing."""
    mock_client = Mock(spec=BlobServiceClient)

    # Mock container client
    mock_container_client = Mock()
    mock_client.get_container_client.return_value = mock_container_client

    # Mock blob client for reading
    mock_read_blob_client = Mock()
    mock_download_blob = Mock()
    mock_download_blob.readall.return_value = json.dumps(sample_article_data).encode(
        "utf-8"
    )
    mock_read_blob_client.download_blob.return_value = mock_download_blob

    # Mock blob client for writing
    mock_write_blob_client = Mock()
    mock_write_blob_client.exists.return_value = False
    mock_write_blob_client.upload_blob.return_value = None

    # Setup container client to return appropriate blob clients
    def get_blob_client(blob_name: str) -> Mock:
        if blob_name.endswith(".json"):
            return mock_read_blob_client
        else:
            return mock_write_blob_client

    mock_container_client.get_blob_client = Mock(side_effect=get_blob_client)

    # Mock account info for health checks
    mock_client.get_account_information.return_value = {"account_kind": "StorageV2"}

    return mock_client


@pytest.fixture
def markdown_processor(
    mock_blob_service_client: Mock, mock_settings: Settings
) -> MarkdownProcessor:
    """Create MarkdownProcessor instance with mocked dependencies."""
    return MarkdownProcessor(mock_blob_service_client, mock_settings)

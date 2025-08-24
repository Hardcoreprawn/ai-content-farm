"""Test configuration for markdown generator service."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure this container directory is first on sys.path so tests importing
# top-level modules resolve to the local files.
root = Path(__file__).parent
sys.path.insert(0, str(root))

# Also add repo root so shared `libs` package is importable during tests
repo_root = root.parent.parent
sys.path.insert(0, str(repo_root))

# Set up environment for testing
os.environ["ENVIRONMENT"] = "local"
os.environ["BLOB_STORAGE_MOCK"] = "true"

# Note: Do not set pytest_plugins here; it's deprecated to define in non-top-level conftest.


@pytest.fixture(scope="session", autouse=True)
def mock_environment():
    """Mock environment variables for testing."""
    with patch.dict(
        os.environ,
        {
            "AZURE_STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;",
            "RANKED_CONTENT_CONTAINER": "ranked-content",
            "GENERATED_CONTENT_CONTAINER": "generated-content",
            "WATCH_INTERVAL": "30",
            "MAX_CONTENT_ITEMS": "50",
            "ENVIRONMENT": "local",
            "BLOB_STORAGE_MOCK": "true",
        },
    ):
        yield


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


@pytest.fixture
def sample_content_items():
    """Sample content items for testing."""
    return [
        {
            "title": "Test Article 1",
            "clean_title": "Test Article 1",
            "source_url": "https://example.com/article1",
            "content_type": "article",
            "ai_summary": "This is a comprehensive summary of test article 1 with detailed information.",
            "topics": ["technology", "artificial intelligence", "machine learning"],
            "sentiment": "positive",
            "final_score": 0.85,
            "engagement_score": 0.78,
            "source_metadata": {
                "site_name": "Tech News Today",
                "author": "John Doe",
                "published_date": "2024-01-01",
            },
            "published_at": "2024-01-01T12:00:00Z",
        },
        {
            "title": "Business Innovation Trends",
            "clean_title": "Business Innovation Trends",
            "source_url": "https://business.example.com/innovation",
            "content_type": "article",
            "ai_summary": "An analysis of emerging business innovation trends and their market impact.",
            "topics": ["business", "innovation", "market trends"],
            "sentiment": "neutral",
            "final_score": 0.72,
            "engagement_score": 0.65,
            "source_metadata": {"site_name": "Business Weekly", "author": "Jane Smith"},
            "published_at": "2024-01-02T08:30:00Z",
        },
        {
            "title": "Climate Change Research Updates",
            "source_url": "https://science.example.com/climate",
            "ai_summary": "Latest research findings on climate change impacts and mitigation strategies.",
            "topics": ["climate", "environment", "research"],
            "sentiment": "concerned",
            "final_score": 0.68,
            "engagement_score": 0.71,
            "source_metadata": {"site_name": "Science Daily"},
        },
    ]


@pytest.fixture
def sample_markdown_files():
    """Sample markdown file data for testing."""
    return [
        {
            "slug": "test-article-1",
            "title": "Test Article 1",
            "score": 0.85,
            "content": """---
title: "Test Article 1"
slug: "test-article-1"
date: "2024-01-01"
---

# Test Article 1

This is the content of test article 1.""",
            "rank": 1,
        },
        {
            "slug": "business-innovation-trends",
            "title": "Business Innovation Trends",
            "score": 0.72,
            "content": """---
title: "Business Innovation Trends"
slug: "business-innovation-trends" 
date: "2024-01-01"
---

# Business Innovation Trends

Content about business innovation.""",
            "rank": 2,
        },
    ]


@pytest.fixture
def sample_generation_manifest():
    """Sample generation manifest for testing."""
    return {
        "generated_at": "2024-01-01T12:00:00Z",
        "timestamp": "20240101_120000",
        "total_posts": 2,
        "generator": "markdown-generator",
        "version": "1.0.0",
        "template_style": "jekyll",
        "index_content": "# AI Curated Content Index\n\nGenerated content index.",
        "generation_settings": {"max_content_items": 50, "template_style": "jekyll"},
    }


# Configure asyncio for tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

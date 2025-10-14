"""
Shared test fixtures and configuration for content-processor tests.

Provides comprehensive mocking for Azure services to enable local testing
without requiring actual Azure credentials.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_blob_client():
    """Mock Azure Blob Storage client with all required methods."""
    with patch("libs.simplified_blob_client.SimplifiedBlobClient") as mock_class:
        mock_instance = MagicMock()

        # Connection testing - must return dict, not coroutine
        mock_instance.test_connection = MagicMock(return_value={"status": "healthy"})

        # Blob operations
        mock_instance.download_json = AsyncMock(
            return_value={"items": [], "metadata": {"source": "test"}}
        )
        mock_instance.upload_json = AsyncMock(return_value=True)
        mock_instance.list_blobs = AsyncMock(return_value=[])

        # Container operations
        mock_instance.ensure_container = AsyncMock(return_value=True)

        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client with realistic article generation."""
    with patch("openai_client.OpenAIClient") as mock_class:
        mock_instance = MagicMock()

        # Connection testing
        mock_instance.test_connection = AsyncMock(return_value=True)

        # Article generation with realistic data
        async def mock_generate_article(
            topic_title="", target_word_count=3000, **kwargs
        ):
            return (
                f"# {topic_title}\n\nThis is a comprehensive test article about {topic_title}...",
                0.25,  # cost in dollars
                1500,  # tokens used
            )

        mock_instance.generate_article = mock_generate_article

        # Cost calculation
        async def mock_calculate_cost(total_tokens=0, prompt_tokens=0):
            input_tokens = prompt_tokens
            output_tokens = total_tokens - prompt_tokens
            # GPT-4 pricing: $0.01/1k input, $0.03/1k output
            cost = (input_tokens * 0.01 / 1000) + (output_tokens * 0.03 / 1000)
            return cost

        mock_instance._calculate_cost = mock_calculate_cost

        # Prompt building
        def mock_build_prompt(
            topic_title, research_content="", target_word_count=3000, **kwargs
        ):
            return f"Write a {target_word_count} word article about: {topic_title}\n\nResearch: {research_content}"

        mock_instance._build_article_prompt = mock_build_prompt

        # Mock article generation for when client is None
        def mock_generate_mock_article(title):
            return f"# {title}\n\nThis is a mock article about {title}. " * 10

        mock_instance._generate_mock_article = mock_generate_mock_article

        # Close method
        mock_instance.close = AsyncMock()

        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_processor_storage():
    """Mock processor storage service."""
    mock_storage = MagicMock()

    # Storage connectivity
    mock_storage.test_storage_connectivity = AsyncMock(return_value=True)

    # Save operations return (success, blob_name)
    mock_storage.save_processed_article = AsyncMock(
        return_value=(True, "processed-content/2025/01/test-article-123.json")
    )

    # Close method
    mock_storage.close = AsyncMock()

    return mock_storage


@pytest.fixture
def mock_article_generation():
    """Mock article generation service."""
    mock_service = MagicMock()

    # Generate article from topic
    async def mock_generate(topic_metadata, **kwargs):
        return {
            "article_content": f"# {topic_metadata.title}\n\nComprehensive content...",
            "article_result": {
                "title": topic_metadata.title,
                "content": "Comprehensive content...",
                "metadata": {
                    "word_count": 1500,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            },
            "word_count": 1500,
            "quality_score": 0.85,
            "cost": 0.25,
        }

    mock_service.generate_article_from_topic = mock_generate

    # Close method
    mock_service.close = AsyncMock()

    return mock_service


@pytest.fixture
def sample_topic_metadata():
    """Sample topic metadata for testing."""
    from models import TopicMetadata

    return TopicMetadata(
        topic_id="test-topic-001",
        title="How AI is Transforming Software Development",
        source="reddit",
        collected_at=datetime.now(timezone.utc),
        priority_score=0.85,
        subreddit="programming",
        upvotes=1250,
        comments=89,
        url="https://reddit.com/r/programming/test",
    )


@pytest.fixture
def sample_article_result():
    """Sample article result for testing."""
    return {
        "title": "How AI is Transforming Software Development",
        "content": "# How AI is Transforming Software Development\n\nComprehensive article content...",
        "metadata": {
            "word_count": 1500,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": "reddit",
            "quality_score": 0.85,
        },
        "cost": 0.25,
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests requiring Azure services",
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (no external dependencies)"
    )

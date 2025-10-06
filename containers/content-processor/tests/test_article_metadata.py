"""
Test Article Metadata Data Contract

Tests verify that article_result contains the correct metadata fields
when metadata is successfully generated. We test the DATA CONTRACT,
not the OpenAI API behavior (which is non-deterministic).

These tests use mocked metadata generation to verify field integration.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from models import TopicMetadata
from services.article_generation import ArticleGenerationService


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client that simulates successful article generation."""
    client = MagicMock()
    client.model_name = "gpt-3.5-turbo"
    client.generate_article = AsyncMock(
        return_value=("This is a test article content about technology.", 0.0015, 500)
    )
    return client


@pytest.fixture
def sample_topic():
    """Sample topic metadata for testing."""
    return TopicMetadata(
        topic_id="test-123",
        title="Test Topic About Technology",
        url="https://example.com/test",
        source="reddit",
        priority_score=0.85,
        collected_at=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        upvotes=100,
        comments=50,
    )


@pytest.fixture
def japanese_topic():
    """Japanese topic that needs translation."""
    return TopicMetadata(
        topic_id="test-456",
        title="米政権内の対中強硬派に焦り",
        url="https://example.com/japan",
        source="reddit",
        priority_score=0.90,
        collected_at=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        upvotes=200,
        comments=75,
    )


@pytest.fixture
def hashtag_topic():
    """Topic with excessive hashtags."""
    return TopicMetadata(
        topic_id="test-789",
        title="Gem.coop #Gem.coop #technology #blockchain #innovation",
        url="https://example.com/hashtag",
        source="reddit",
        priority_score=0.75,
        collected_at=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        upvotes=50,
        comments=25,
    )


@pytest.mark.asyncio
async def test_metadata_fields_in_article_result(mock_openai_client, sample_topic):
    """
    Test DATA CONTRACT: When metadata is generated, article_result includes all required fields.

    This verifies field integration, not OpenAI behavior.
    """
    with patch(
        "services.article_generation.MetadataGenerator"
    ) as mock_metadata_generator:
        # Mock metadata generator to return valid data contract
        mock_gen = MagicMock()
        mock_gen.generate_metadata = AsyncMock(
            return_value={
                "original_title": "Test Topic About Technology",
                "title": "Test Topic About Technology",
                "slug": "test-topic-about-technology",
                "filename": "2025-01-15-test-topic-about-technology.html",
                "url": "/articles/2025-01-15-test-topic-about-technology.html",
                "cost_usd": 0.0001,
                "tokens_used": 50,
            }
        )
        mock_metadata_generator.return_value = mock_gen

        # Create service after patching
        service = ArticleGenerationService(openai_client=mock_openai_client)

        result = await service.generate_article_from_topic(
            sample_topic, processor_id="test-proc", session_id="test-session"
        )

        # DATA CONTRACT: Result must include article_result
        assert result is not None, "Service should return result"
        assert "article_result" in result, "Result should contain article_result"

        article_result = result["article_result"]

        # DATA CONTRACT: All metadata fields must be present
        required_fields = [
            "original_title",
            "title",
            "slug",
            "filename",
            "url",
            "metadata_cost",
            "metadata_tokens",
            "total_cost",
        ]
        for field in required_fields:
            assert field in article_result, f"article_result must include '{field}'"

        # DATA CONTRACT: Metadata values flow through unchanged
        assert article_result["original_title"] == "Test Topic About Technology"
        assert article_result["slug"] == "test-topic-about-technology"
        assert (
            article_result["filename"] == "2025-01-15-test-topic-about-technology.html"
        )
        assert (
            article_result["url"]
            == "/articles/2025-01-15-test-topic-about-technology.html"
        )

        # DATA CONTRACT: Cost tracking works correctly
        assert article_result["metadata_cost"] == 0.0001
        assert article_result["metadata_tokens"] == 50
        assert article_result["total_cost"] == 0.0016  # 0.0015 + 0.0001


@pytest.mark.asyncio
async def test_original_vs_translated_title_preserved(
    mock_openai_client, japanese_topic
):
    """
    Test DATA CONTRACT: original_title and title fields are both preserved.

    This verifies we maintain both the original (possibly non-English) title
    and the translated/SEO-optimized title in the output.
    """
    with patch(
        "services.article_generation.MetadataGenerator"
    ) as mock_metadata_generator:
        # Simulate metadata with translation (original != translated)
        mock_gen = MagicMock()
        mock_gen.generate_metadata = AsyncMock(
            return_value={
                "original_title": "米政権内の対中強硬派に焦り",
                "title": "US Administration Hawks on China Show Concern",
                "slug": "us-administration-hawks-on-china-show-concern",
                "filename": "2025-01-15-us-administration-hawks-on-china-show-concern.html",
                "url": "/articles/2025-01-15-us-administration-hawks-on-china-show-concern.html",
                "cost_usd": 0.0001,
                "tokens_used": 75,
            }
        )
        mock_metadata_generator.return_value = mock_gen

        service = ArticleGenerationService(openai_client=mock_openai_client)

        result = await service.generate_article_from_topic(
            japanese_topic, processor_id="test-proc", session_id="test-session"
        )

        assert result is not None, "Service should return result"
        article_result = result["article_result"]

        # DATA CONTRACT: Both original and translated titles preserved
        assert (
            article_result["original_title"] == "米政権内の対中強硬派に焦り"
        ), "original_title must preserve input"
        assert (
            article_result["title"] == "US Administration Hawks on China Show Concern"
        ), "title must contain translated/optimized version"

        # DATA CONTRACT: They can be different
        assert (
            article_result["original_title"] != article_result["title"]
        ), "Should support translation"


@pytest.mark.asyncio
async def test_slug_url_filename_relationship(mock_openai_client, hashtag_topic):
    """
    Test DATA CONTRACT: slug, filename, and url fields have correct relationships.

    Verifies that:
    - filename = YYYY-MM-DD-{slug}.html
    - url = /articles/{filename}
    """
    with patch(
        "services.article_generation.MetadataGenerator"
    ) as mock_metadata_generator:
        # Simulate metadata generation output
        mock_gen = MagicMock()
        mock_gen.generate_metadata = AsyncMock(
            return_value={
                "original_title": "Gem.coop #Gem.coop #technology #blockchain #innovation",
                "title": "Gem Coop Technology and Blockchain Innovation",
                "slug": "gem-coop-technology-and-blockchain-innovation",
                "filename": "2025-01-15-gem-coop-technology-and-blockchain-innovation.html",
                "url": "/articles/2025-01-15-gem-coop-technology-and-blockchain-innovation.html",
                "cost_usd": 0.0001,
                "tokens_used": 60,
            }
        )
        mock_metadata_generator.return_value = mock_gen

        service = ArticleGenerationService(openai_client=mock_openai_client)

        result = await service.generate_article_from_topic(
            hashtag_topic, processor_id="test-proc", session_id="test-session"
        )

        assert result is not None, "Service should return result"
        article_result = result["article_result"]

        # DATA CONTRACT: slug in filename
        slug = article_result["slug"]
        filename = article_result["filename"]
        assert slug in filename, "filename must contain slug"

        # DATA CONTRACT: filename format
        assert filename.endswith(".html"), "filename must end with .html"
        parts = filename.replace(".html", "").split("-", 3)
        assert len(parts) == 4, "filename must be YYYY-MM-DD-slug.html format"

        # DATA CONTRACT: url = /articles/{filename}
        url = article_result["url"]
        assert url.startswith("/articles/"), "url must start with /articles/"
        assert url.endswith(filename), "url must end with filename"


@pytest.mark.asyncio
async def test_provenance_includes_metadata_step(mock_openai_client, sample_topic):
    """
    Test DATA CONTRACT: Provenance chain includes metadata_generation step.

    Verifies cost tracking and operation logging in provenance.
    """
    # Add enhanced metadata to topic to enable provenance tracking
    sample_topic.enhanced_metadata = {
        "source_metadata": None,
        "quality_score": 0.85,
        "provenance_entries": [],
    }

    with patch(
        "services.article_generation.MetadataGenerator"
    ) as mock_metadata_generator:
        mock_gen = MagicMock()
        mock_gen.generate_metadata = AsyncMock(
            return_value={
                "original_title": "Test Topic",
                "title": "Test Topic",
                "slug": "test-topic",
                "filename": "2025-01-15-test-topic.html",
                "url": "/articles/2025-01-15-test-topic.html",
                "cost_usd": 0.0001,
                "tokens_used": 50,
            }
        )
        mock_metadata_generator.return_value = mock_gen

        service = ArticleGenerationService(openai_client=mock_openai_client)

        result = await service.generate_article_from_topic(
            sample_topic, processor_id="test-proc", session_id="test-session"
        )

        assert result is not None, "Service should return result"
        article_result = result["article_result"]

        # DATA CONTRACT: provenance_chain must exist when enhanced_metadata present
        assert (
            "provenance_chain" in article_result
        ), "provenance_chain required for enhanced topics"

        provenance = article_result["provenance_chain"]

        # DATA CONTRACT: metadata_generation step must be recorded
        assert (
            "metadata_generation" in provenance
        ), "provenance must include metadata_generation step"

        metadata_step = provenance["metadata_generation"]
        assert metadata_step["operation"] == "metadata_generation"
        assert metadata_step["cost_usd"] == 0.0001
        assert metadata_step["tokens_used"] == 50


@pytest.mark.asyncio
async def test_cost_aggregation(mock_openai_client, sample_topic):
    """
    Test DATA CONTRACT: total_cost = article cost + metadata cost.

    Verifies cost tracking aggregates correctly.
    """
    with patch(
        "services.article_generation.MetadataGenerator"
    ) as mock_metadata_generator:
        mock_gen = MagicMock()
        mock_gen.generate_metadata = AsyncMock(
            return_value={
                "original_title": "Test",
                "title": "Test",
                "slug": "test-article",
                "filename": "2025-01-15-test-article.html",
                "url": "/articles/2025-01-15-test-article.html",
                "cost_usd": 0.0001,
                "tokens_used": 50,
            }
        )
        mock_metadata_generator.return_value = mock_gen

        service = ArticleGenerationService(openai_client=mock_openai_client)

        result = await service.generate_article_from_topic(
            sample_topic, processor_id="test-proc", session_id="test-session"
        )

        assert result is not None, "Service should return result"
        article_result = result["article_result"]

        # DATA CONTRACT: All cost fields present
        assert "cost" in article_result, "Article generation cost required"
        assert "metadata_cost" in article_result, "Metadata cost required"
        assert "total_cost" in article_result, "Total cost required"

        # DATA CONTRACT: Cost calculation correct
        article_cost = article_result["cost"]
        metadata_cost = article_result["metadata_cost"]
        total_cost = article_result["total_cost"]

        assert article_cost == 0.0015, "Mock article cost"
        assert metadata_cost == 0.0001, "Mock metadata cost"
        assert (
            total_cost == article_cost + metadata_cost
        ), "total_cost must be sum of components"
        assert total_cost == 0.0016, "Expected combined cost"

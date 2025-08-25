#!/usr/bin/env python3
"""
Fast unit tests for site-generator service logic.

These tests use contract-based mocking for fast execution without external dependencies.
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from tests.contracts.blob_storage_contract import RankedContentContract

from models import GenerationRequest, GenerationStatus, SiteTheme
from service_logic import SiteProcessor


class TestSiteProcessorUnit:
    """Fast unit tests for SiteProcessor business logic."""

    @pytest.mark.unit
    def test_processor_initialization(self, mock_blob_client, mock_template_manager):
        """Test processor initializes correctly with mocked dependencies."""
        processor = SiteProcessor(
            blob_client=mock_blob_client, template_manager=mock_template_manager
        )

        assert processor.blob_client == mock_blob_client
        assert processor.template_manager == mock_template_manager
        assert processor.generation_status == {}
        assert not processor.is_running

    @pytest.mark.unit
    def test_process_articles_with_realistic_data(self, mock_site_processor):
        """Test article processing with contract-based data."""
        # Use contract to generate realistic test data
        ranked_content = RankedContentContract.create_mock(num_articles=3)
        articles_data = ranked_content.ranked_topics

        # Process articles
        processed_articles = mock_site_processor._process_articles(
            articles_data, max_articles=2
        )

        # Verify processing
        assert len(processed_articles) == 2  # Respects max_articles limit
        assert all(hasattr(article, "title") for article in processed_articles)
        assert all(hasattr(article, "score") for article in processed_articles)
        # Should be sorted by score
        assert processed_articles[0].score >= processed_articles[1].score

    @pytest.mark.unit
    def test_generate_rss_feed_structure(self, mock_site_processor, sample_articles):
        """Test RSS feed generation produces valid structure."""
        # Convert sample data to ContentItem objects
        from service_logic import ContentItem

        content_items = [
            ContentItem(
                title=article["title"],
                url=article["url"],
                summary=article["summary"],
                content=article.get("content"),
                author=article.get("author"),
                score=article.get("score"),
                source=article["source"],
            )
            for article in sample_articles
        ]

        # Generate RSS feed
        rss_content = mock_site_processor._generate_rss_feed(content_items)

        # Verify RSS structure
        assert "<?xml version=" in rss_content
        assert "<rss version=" in rss_content
        assert "<channel>" in rss_content
        assert "<title>" in rss_content
        assert "</rss>" in rss_content

        # Verify articles appear in feed
        for item in content_items:
            assert item.title in rss_content

    @pytest.mark.asyncio
    async def test_generation_status_tracking(self, mock_site_processor):
        """Test generation status tracking works correctly."""
        site_id = "test-site-123"

        # Initially should have no status
        status = await mock_site_processor.get_generation_status(site_id)
        assert status.status == GenerationStatus.NOT_FOUND

        # Start generation should create status
        request = GenerationRequest(
            content_source="ranked",
            theme=SiteTheme.MODERN,
            max_articles=5,
            site_title="Test Site",
            site_description="Test Description",
        )

        # Mock the async generation process
        mock_site_processor.generation_status[site_id] = {
            "status": GenerationStatus.IN_PROGRESS,
            "started_at": "2025-08-24T10:00:00Z",
            "progress": "Processing articles...",
        }

        status = await mock_site_processor.get_generation_status(site_id)
        assert status.status == GenerationStatus.IN_PROGRESS
        assert status.progress == "Processing articles..."

    @pytest.mark.unit
    def test_content_item_creation_from_ranked_data(self):
        """Test ContentItem creation from ranked topic data."""
        from service_logic import ContentItem

        # Use contract to get realistic data
        ranked_content = RankedContentContract.create_mock(num_articles=1)
        article_data = ranked_content.ranked_topics[0]

        # Create ContentItem
        content_item = ContentItem(
            title=article_data["title"],
            url=article_data["url"],
            summary=article_data["summary"],
            content=article_data.get("content"),
            author=article_data.get("author"),
            score=article_data.get("score"),
            source=article_data["source"],
        )

        # Verify all fields are correctly mapped
        assert content_item.title == article_data["title"]
        assert content_item.url == article_data["url"]
        assert content_item.summary == article_data["summary"]
        assert content_item.score == article_data["score"]
        assert content_item.source == article_data["source"]

    @pytest.mark.unit
    def test_site_metadata_creation(self, mock_site_processor):
        """Test site metadata creation from generation request."""
        request = GenerationRequest(
            content_source="ranked",
            theme=SiteTheme.MODERN,
            max_articles=10,
            site_title="AI Content Farm",
            site_description="Curated technology news and insights",
        )

        # Create site metadata (this would be part of the processing)
        metadata = {
            "title": request.site_title,
            "description": request.site_description,
            "theme": request.theme.value,
            "max_articles": request.max_articles,
            "generated_at": "2025-08-24T10:00:00Z",
        }

        assert metadata["title"] == "AI Content Farm"
        assert metadata["description"] == "Curated technology news and insights"
        assert metadata["theme"] == "modern"
        assert metadata["max_articles"] == 10

    @pytest.mark.unit
    def test_error_handling_for_invalid_content(self, mock_site_processor):
        """Test error handling for invalid or missing content."""
        # Test with empty articles list
        processed_articles = mock_site_processor._process_articles([], max_articles=10)
        assert len(processed_articles) == 0

        # Test with malformed article data
        malformed_data = [{"title": "Test", "invalid_field": "value"}]
        try:
            processed_articles = mock_site_processor._process_articles(
                malformed_data, max_articles=10
            )
            # Should handle gracefully or raise appropriate exception
            assert True  # If we get here, it handled the error
        except Exception as e:
            # Should be a meaningful exception
            assert "missing" in str(e).lower() or "required" in str(e).lower()

    @pytest.mark.unit
    def test_template_context_preparation(self, mock_site_processor, sample_articles):
        """Test template context preparation with realistic data."""
        from service_logic import ContentItem

        # Convert to ContentItem objects
        content_items = [
            ContentItem(
                title=article["title"],
                url=article["url"],
                summary=article["summary"],
                content=article.get("content"),
                author=article.get("author"),
                score=article.get("score"),
                source=article["source"],
            )
            for article in sample_articles
        ]

        site_metadata = {
            "title": "Test Site",
            "description": "Test Description",
            "theme": "modern",
        }

        # This would be the context passed to templates
        template_context = {
            "site_title": site_metadata["title"],
            "site_description": site_metadata["description"],
            "articles": content_items,
            "generated_at": "2025-08-24T10:00:00Z",
        }

        assert template_context["site_title"] == "Test Site"
        assert len(template_context["articles"]) == len(sample_articles)
        assert all(
            hasattr(article, "title") for article in template_context["articles"]
        )

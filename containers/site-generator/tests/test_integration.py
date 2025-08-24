#!/usr/bin/env python3
"""
Fast integration tests for site-generator.

These tests validate component integration using contracts instead of real external services.
Designed to complete in under 5 seconds total.

⚠️  Slow real-file tests are marked with @pytest.mark.slow and only run when requested.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from models import GenerationRequest, GenerationStatus, SiteTheme
from service_logic import SiteProcessor

from tests.contracts.blob_storage_contract import RankedContentContract
from tests.contracts.template_contract import TemplateContract


class TestSiteGeneratorIntegration:
    """Fast integration tests using contract-based mocking."""

    @pytest.mark.asyncio
    async def test_end_to_end_site_generation_flow(self, mock_site_processor):
        """Test complete site generation workflow with realistic data."""
        # Use contract to create realistic ranked content
        ranked_content = RankedContentContract.create_mock(num_articles=5)

        # Mock blob client to return our contract data
        mock_site_processor.blob_client.download_json = Mock(
            return_value=ranked_content.__dict__
        )

        # Create realistic generation request
        request = GenerationRequest(
            content_source="ranked",
            theme=SiteTheme.MODERN,
            max_articles=3,
            site_title="AI Content Farm - Integration Test",
            site_description="Fast integration test for site generation",
        )

        site_id = "integration-test-site"

        # Execute site generation
        await mock_site_processor.generate_site(site_id, request)

        # Verify site was processed
        status = await mock_site_processor.get_generation_status(site_id)
        assert status.site_id == site_id

        # Verify blob storage interactions
        assert mock_site_processor.blob_client.download_json.called
        assert mock_site_processor.blob_client.upload_text.called

    def test_content_processing_pipeline_integration(self, mock_site_processor):
        """Test content flows correctly through processing pipeline."""
        # Create contract-based test data
        ranked_content = RankedContentContract.create_mock(num_articles=4)
        articles_data = ranked_content.ranked_topics

        # Process through the pipeline
        processed_articles = mock_site_processor._process_articles(
            articles_data, max_articles=3
        )

        # Verify pipeline behavior
        assert len(processed_articles) == 3  # Respects max_articles
        assert all(hasattr(article, "title") for article in processed_articles)
        assert all(hasattr(article, "score") for article in processed_articles)

        # Verify articles are sorted by score (highest first)
        scores = [article.score for article in processed_articles]
        assert scores == sorted(scores, reverse=True)

    def test_template_rendering_integration(self, mock_site_processor, sample_articles):
        """Test template rendering with realistic content."""
        from service_logic import ContentItem

        # Convert sample articles to ContentItem objects
        content_items = [
            ContentItem(
                title=article["title"],
                url=article["url"],
                summary=article["summary"],
                content=article.get("content"),
                author=article.get("author"),
                score=article.get("score"),
                source=article["source"],
                published_date=article.get("published_date", "2025-08-24T10:00:00Z"),
            )
            for article in sample_articles
        ]

        # Test index page rendering
        index_html = mock_site_processor.template_manager.render_template(
            "index.html",
            site_title="Integration Test Site",
            site_description="Testing template integration",
            articles=content_items,
        )

        # Verify template output contains expected content
        assert "Integration Test Site" in index_html
        assert len(content_items) > 0  # Should have articles
        assert "<html>" in index_html

        # Test RSS feed rendering
        rss_xml = mock_site_processor.template_manager.render_template(
            "feed.xml",
            site_title="Integration Test Site",
            site_description="Testing RSS integration",
            articles=content_items,
        )

        assert "<?xml version=" in rss_xml
        assert "<rss" in rss_xml
        assert "Integration Test Site" in rss_xml

    def test_data_flow_consistency(self, mock_site_processor):
        """Test data maintains consistency as it flows through components."""
        # Create contract data with specific values to track
        ranked_content = RankedContentContract.create_mock(num_articles=2)
        original_title = ranked_content.ranked_topics[0]["title"]
        original_score = ranked_content.ranked_topics[0]["score"]

        # Process the data
        processed_articles = mock_site_processor._process_articles(
            ranked_content.ranked_topics, max_articles=5
        )

        # Verify data consistency is maintained
        assert len(processed_articles) == 2
        assert processed_articles[0].title == original_title
        assert processed_articles[0].score == original_score

        # Generate RSS and verify data flows through
        rss_content = mock_site_processor._generate_rss_feed(processed_articles)

        assert original_title in rss_content

    def test_performance_characteristics_integration(self, mock_site_processor):
        """Test performance characteristics meet expectations."""
        import time

        # Test processing performance with realistic data
        ranked_content = RankedContentContract.create_mock(num_articles=10)

        start_time = time.time()
        processed_articles = mock_site_processor._process_articles(
            ranked_content.ranked_topics, max_articles=5
        )
        processing_time = time.time() - start_time

        # Should process quickly with mocked dependencies
        assert processing_time < 0.1  # Under 100ms
        assert len(processed_articles) == 5

        # Test RSS generation performance
        start_time = time.time()
        rss_content = mock_site_processor._generate_rss_feed(processed_articles)
        rss_time = time.time() - start_time

        assert rss_time < 0.1  # Under 100ms
        assert len(rss_content) > 100  # Should generate meaningful content


# ============================================================================
# SLOW TESTS (20+ minutes) - Only run when explicitly requested with pytest -m slow
# ============================================================================


@pytest.mark.slow
class TestPhase1BIntegrationSlow:
    """Integration tests for Phase 1B: Real Content Processing"""

    @pytest.fixture
    def real_ranked_content(self):
        """Load real ranked content from test file."""
        content_file = Path("/workspaces/ai-content-farm/test_ranked_content.json")
        with open(content_file, "r") as f:
            real_content = json.load(f)

        # Convert to expected format
        return {
            "ranked_topics": real_content["items"],
            "metadata": {
                "generated_at": "2025-08-19T10:30:00Z",
                "total_items": len(real_content["items"]),
                "source": "content-ranker",
            },
        }

    @pytest.fixture
    def mock_processor(self, real_ranked_content):
        """Create processor with mocked blob operations for integration testing."""
        processor = SiteProcessor()

        # Mock blob client methods properly
        processor.blob_client.download_json = Mock(return_value=real_ranked_content)
        processor.blob_client.upload_text = Mock(return_value=True)
        processor.blob_client.upload_json = Mock(return_value=True)
        processor.blob_client.list_blobs = Mock(
            return_value=[
                {"name": "test-ranked-content.json", "last_modified": datetime.now()}
            ]
        )
        processor.blob_client.ensure_container = Mock(return_value=True)

        # Mock template manager to avoid file system dependencies
        processor.template_manager.render_template = Mock(
            return_value="<html><body>Mock Site</body></html>"
        )
        processor.template_manager.get_static_assets = Mock(
            return_value={"style.css": "body { font-family: sans-serif; }"}
        )

        return processor

    @pytest.mark.asyncio
    async def test_real_content_processing(self, mock_processor, real_ranked_content):
        """Test processing real ranked content into ContentItem objects."""
        print("\n🧪 Testing real content processing...")

        # Test content processing
        processed_articles = mock_processor._process_articles(
            real_ranked_content["ranked_topics"], max_articles=10
        )

        assert len(processed_articles) > 0, "Should process at least some articles"
        print(f"✅ Processed {len(processed_articles)} articles from real content")

        # Verify article structure
        first_article = processed_articles[0]
        assert hasattr(first_article, "title"), "Article should have title"
        assert hasattr(first_article, "score"), "Article should have score"
        assert hasattr(first_article, "source"), "Article should have source"
        assert hasattr(first_article, "summary"), "Article should have summary"

        print(f"📖 Sample article: {first_article.title}")
        print(f"   Score: {first_article.score}")
        print(f"   Source: {first_article.source}")

    @pytest.mark.asyncio
    async def test_full_site_generation_with_real_content(
        self, mock_processor, real_ranked_content
    ):
        """Test complete site generation workflow with real content."""
        print("\n🚀 Testing full site generation with real content...")

        # Create realistic generation request
        request = GenerationRequest(
            content_source="ranked",
            theme=SiteTheme.MODERN,
            max_articles=10,
            site_title="AI Content Farm - Latest Tech News",
            site_description="Curated technology news and insights powered by AI",
        )

        # Generate site
        site_id = "real-content-integration-test"
        await mock_processor.generate_site(site_id, request)

        # Verify generation was attempted
        assert (
            site_id in mock_processor.generation_status
        ), "Site should be in generation status"

        status = await mock_processor.get_generation_status(site_id)
        print(f"✅ Site generation completed with status: {status.status}")

        # The important test: verify that real content was processed properly
        processed_articles = mock_processor._process_articles(
            real_ranked_content["ranked_topics"], request.max_articles
        )

        assert len(processed_articles) > 0, "Should have processed real articles"
        assert (
            processed_articles[0].title
            == real_ranked_content["ranked_topics"][0]["title"]
        ), "Should preserve real article titles"
        assert (
            processed_articles[0].score
            == real_ranked_content["ranked_topics"][0]["score"]
        ), "Should preserve real article scores"

        print("🎉 Real content integration test PASSED!")

    @pytest.mark.asyncio
    async def test_rss_feed_generation_with_real_content(
        self, mock_processor, real_ranked_content
    ):
        """Test RSS feed generation with real content."""
        print("\n📡 Testing RSS feed generation with real content...")

        # Process real content into ContentItem objects
        processed_articles = mock_processor._process_articles(
            real_ranked_content["ranked_topics"], max_articles=5
        )

        # Generate RSS feed
        rss_content = mock_processor._generate_rss_feed(processed_articles)

        # Verify RSS structure
        assert "<rss" in rss_content, "Should contain RSS tag"
        assert "<channel>" in rss_content, "Should contain channel tag"
        assert "<item>" in rss_content, "Should contain item tags"

        # Verify real content titles appear in RSS
        first_article_title = processed_articles[0].title
        assert (
            first_article_title in rss_content
        ), "Real article titles should appear in RSS"

        print(f"✅ RSS feed generated with {len(processed_articles)} real articles")

    def test_content_item_validation_with_real_data(self, real_ranked_content):
        """Test that real ranked content validates against ContentItem model."""
        print("\n🔍 Testing ContentItem validation with real data...")

        from service_logic import ContentItem

        # Take first item from real content
        real_item = real_ranked_content["ranked_topics"][0]

        # Create ContentItem (this will validate the structure)
        content_item = ContentItem(
            title=real_item["title"],
            url=real_item["url"],
            summary=real_item["summary"],
            content=real_item.get("content"),
            author=real_item.get("author"),
            score=real_item.get("score"),
            source=real_item["source"],
        )

        assert content_item.title == real_item["title"]
        assert content_item.url == real_item["url"]
        assert content_item.score == real_item["score"]

        print(f"✅ Real content validates against ContentItem model")
        print(f"   Title: {content_item.title}")
        print(f"   Score: {content_item.score}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

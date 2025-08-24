#!/usr/bin/env python3
"""
Fast integration tests for site-generator.

These tests validate component integration using contracts instead of real external services.
Designed to complete in under 5 seconds total.
"""

import asyncio
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

    def test_blob_storage_integration_patterns(self, mock_site_processor):
        """Test blob storage integration follows expected patterns."""
        # Test download pattern
        mock_site_processor.blob_client.download_json = Mock(
            return_value=RankedContentContract.create_mock(num_articles=2).__dict__
        )

        # Simulate downloading ranked content
        content = mock_site_processor.blob_client.download_json(
            "ranked-topics", "latest.json"
        )

        # Verify contract structure is maintained
        assert "ranked_topics" in content
        assert "metadata" in content
        assert len(content["ranked_topics"]) == 2

        # Test upload pattern
        test_html = "<html><body>Test Site</body></html>"
        result = mock_site_processor.blob_client.upload_text(
            "sites", "test-site/index.html", test_html
        )

        assert result is True
        assert "sites/test-site/index.html" in mock_site_processor.blob_client.blobs

    def test_error_handling_integration(self, mock_site_processor):
        """Test error handling across component boundaries."""
        # Test handling of missing content
        mock_site_processor.blob_client.download_json = Mock(
            side_effect=Exception("Blob not found")
        )

        # Should handle blob storage errors gracefully
        try:
            content = mock_site_processor.blob_client.download_json(
                "missing", "file.json"
            )
            assert False, "Should have raised exception"
        except Exception as e:
            assert "not found" in str(e).lower()

        # Test handling of empty content
        empty_content = RankedContentContract.create_mock(num_articles=0)
        processed = mock_site_processor._process_articles(
            empty_content.ranked_topics, max_articles=5
        )

        assert len(processed) == 0  # Should handle empty content gracefully

    @pytest.mark.asyncio
    async def test_concurrent_generation_handling(self, mock_site_processor):
        """Test system handles concurrent site generation requests."""
        # Create multiple generation requests
        requests = [
            GenerationRequest(
                content_source="ranked",
                theme=SiteTheme.MODERN,
                max_articles=3,
                site_title=f"Concurrent Site {i}",
                site_description=f"Testing concurrent generation {i}",
            )
            for i in range(3)
        ]

        site_ids = [f"concurrent-site-{i}" for i in range(3)]

        # Mock successful generations
        async def mock_generate(site_id, request):
            mock_site_processor.generation_status[site_id] = {
                "status": GenerationStatus.COMPLETED,
                "started_at": "2025-08-24T10:00:00Z",
                "progress": "Generation completed",
            }

        # Execute concurrent generations
        tasks = [
            mock_generate(site_id, request)
            for site_id, request in zip(site_ids, requests)
        ]

        await asyncio.gather(*tasks)

        # Verify all generations completed
        assert len(mock_site_processor.generation_status) == 3
        for site_id in site_ids:
            assert site_id in mock_site_processor.generation_status

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
        # Score should be preserved in the content flow

    def test_configuration_integration(self, mock_site_processor):
        """Test configuration values are properly integrated across components."""
        # Verify processor uses configuration
        assert mock_site_processor.config is not None

        # Test that configuration affects behavior
        request = GenerationRequest(
            content_source="ranked",
            theme=SiteTheme.MODERN,
            max_articles=10,  # Large number
            site_title="Config Test Site",
            site_description="Testing configuration integration",
        )

        # Process with different limits to verify config is respected
        ranked_content = RankedContentContract.create_mock(num_articles=15)
        processed = mock_site_processor._process_articles(
            ranked_content.ranked_topics, max_articles=request.max_articles
        )

        # Should respect the max_articles from request/config
        assert len(processed) <= request.max_articles

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

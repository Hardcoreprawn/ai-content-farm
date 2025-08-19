#!/usr/bin/env python3
"""
Phase 1B Integration Test: Real Content Processing

Tests SSG with actual ranked content to validate end-to-end functionality.
"""

import json
import pytest
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
from service_logic import SiteProcessor
from models import GenerationRequest, SiteTheme


class TestPhase1BIntegration:
    """Integration tests for Phase 1B: Real Content Processing"""

    @pytest.fixture
    def real_ranked_content(self):
        """Load real ranked content from test file."""
        content_file = Path(
            "/workspaces/ai-content-farm/test_ranked_content.json")
        with open(content_file, 'r') as f:
            real_content = json.load(f)

        # Convert to expected format
        return {
            'ranked_topics': real_content['items'],
            'metadata': {
                'generated_at': '2025-08-19T10:30:00Z',
                'total_items': len(real_content['items']),
                'source': 'content-ranker'
            }
        }

    @pytest.fixture
    def mock_processor(self, real_ranked_content):
        """Create processor with mocked blob operations for integration testing."""
        processor = SiteProcessor()

        # Mock blob client methods properly
        processor.blob_client.download_json = Mock(
            return_value=real_ranked_content)
        processor.blob_client.upload_text = Mock(return_value=True)
        processor.blob_client.upload_json = Mock(return_value=True)
        processor.blob_client.list_blobs = Mock(return_value=[{
            'name': 'test-ranked-content.json',
            'last_modified': datetime.now()
        }])
        processor.blob_client.ensure_container = Mock(return_value=True)

        # Mock template manager to avoid file system dependencies
        processor.template_manager.render_template = Mock(
            return_value="<html><body>Mock Site</body></html>")
        processor.template_manager.get_static_assets = Mock(
            return_value={"style.css": "body { font-family: sans-serif; }"})

        return processor

    @pytest.mark.asyncio
    async def test_real_content_processing(self, mock_processor, real_ranked_content):
        """Test processing real ranked content into ContentItem objects."""
        print("\n🧪 Testing real content processing...")

        # Test content processing
        processed_articles = mock_processor._process_articles(
            real_ranked_content['ranked_topics'],
            max_articles=10
        )

        assert len(
            processed_articles) > 0, "Should process at least some articles"
        print(
            f"✅ Processed {len(processed_articles)} articles from real content")

        # Verify article structure
        first_article = processed_articles[0]
        assert hasattr(first_article, 'title'), "Article should have title"
        assert hasattr(first_article, 'score'), "Article should have score"
        assert hasattr(first_article, 'source'), "Article should have source"
        assert hasattr(first_article, 'summary'), "Article should have summary"

        print(f"📖 Sample article: {first_article.title}")
        print(f"   Score: {first_article.score}")
        print(f"   Source: {first_article.source}")

    @pytest.mark.asyncio
    async def test_full_site_generation_with_real_content(self, mock_processor, real_ranked_content):
        """Test complete site generation workflow with real content."""
        print("\n🚀 Testing full site generation with real content...")

        # Create realistic generation request
        request = GenerationRequest(
            content_source='ranked',
            theme=SiteTheme.MODERN,
            max_articles=10,
            site_title='AI Content Farm - Latest Tech News',
            site_description='Curated technology news and insights powered by AI'
        )

        # Generate site
        site_id = 'real-content-integration-test'
        await mock_processor.generate_site(site_id, request)

        # Verify generation was attempted
        assert site_id in mock_processor.generation_status, "Site should be in generation status"

        status = await mock_processor.get_generation_status(site_id)
        print(f"✅ Site generation completed with status: {status.status}")

        # The important test: verify that real content was processed properly
        processed_articles = mock_processor._process_articles(
            real_ranked_content['ranked_topics'],
            request.max_articles
        )

        assert len(processed_articles) > 0, "Should have processed real articles"
        assert processed_articles[0].title == real_ranked_content[
            'ranked_topics'][0]['title'], "Should preserve real article titles"
        assert processed_articles[0].score == real_ranked_content[
            'ranked_topics'][0]['score'], "Should preserve real article scores"

        print("🎉 Real content integration test PASSED!")

    @pytest.mark.asyncio
    async def test_rss_feed_generation_with_real_content(self, mock_processor, real_ranked_content):
        """Test RSS feed generation with real content."""
        print("\n📡 Testing RSS feed generation with real content...")

        # Process real content into ContentItem objects
        processed_articles = mock_processor._process_articles(
            real_ranked_content['ranked_topics'],
            max_articles=5
        )

        # Generate RSS feed
        rss_content = mock_processor._generate_rss_feed(processed_articles)

        # Verify RSS structure
        assert "<rss" in rss_content, "Should contain RSS tag"
        assert "<channel>" in rss_content, "Should contain channel tag"
        assert "<item>" in rss_content, "Should contain item tags"

        # Verify real content titles appear in RSS
        first_article_title = processed_articles[0].title
        assert first_article_title in rss_content, "Real article titles should appear in RSS"

        print(
            f"✅ RSS feed generated with {len(processed_articles)} real articles")

    def test_content_item_validation_with_real_data(self, real_ranked_content):
        """Test that real ranked content validates against ContentItem model."""
        print("\n🔍 Testing ContentItem validation with real data...")

        from service_logic import ContentItem

        # Take first item from real content
        real_item = real_ranked_content['ranked_topics'][0]

        # Create ContentItem (this will validate the structure)
        content_item = ContentItem(
            title=real_item['title'],
            url=real_item['url'],
            summary=real_item['summary'],
            content=real_item.get('content'),
            author=real_item.get('author'),
            score=real_item.get('score'),
            source=real_item['source']
        )

        assert content_item.title == real_item['title']
        assert content_item.url == real_item['url']
        assert content_item.score == real_item['score']

        print(f"✅ Real content validates against ContentItem model")
        print(f"   Title: {content_item.title}")
        print(f"   Score: {content_item.score}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

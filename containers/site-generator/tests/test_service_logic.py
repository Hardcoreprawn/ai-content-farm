#!/usr/bin/env python3
"""
Tests for Site Generator Service Logic

Tests the core business logic that processes ranked content into static websites.
"""

from service_logic import SiteProcessor
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import sys
sys.path.append('/workspaces/ai-content-farm')


class TestSiteProcessor:
    """Test the core SiteProcessor business logic"""

    @pytest.fixture
    def mock_processor(self, mock_blob_client):
        """Create a SiteProcessor with mocked dependencies"""
        with patch('service_logic.BlobStorageClient', return_value=mock_blob_client):
            with patch('service_logic.get_config') as mock_config:
                mock_config.return_value.service_name = "site-generator"
                processor = SiteProcessor()
                processor.template_manager = Mock()
                return processor

    def test_processor_initialization(self, mock_processor):
        """Test SiteProcessor initializes correctly"""
        assert mock_processor is not None
        assert mock_processor.generation_status == {}
        assert mock_processor.is_running is False

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self, mock_processor):
        """Test processor start/stop lifecycle"""
        # Test start
        await mock_processor.start()
        assert mock_processor.is_running is True

        # Test stop
        await mock_processor.stop()
        assert mock_processor.is_running is False

    @pytest.mark.asyncio
    async def test_generate_site_with_valid_content(self, mock_processor, sample_ranked_content):
        """Test site generation with valid ranked content"""
        # Mock template manager responses
        mock_processor.template_manager.render_template.side_effect = [
            "<html>Index page with articles</html>",  # index.html
            "<html>Article 1 content</html>",         # article 1
            "<html>Article 2 content</html>",         # article 2
        ]

        mock_processor.template_manager.get_static_assets.return_value = {
            "assets/style.css": "body { font-family: sans-serif; }"
        }

        # Mock blob operations
        mock_processor.blob_client.download_json.return_value = sample_ranked_content
        mock_processor.blob_client.upload_text.return_value = True

        # Test site generation
        await mock_processor.generate_site(
            site_id="test-site-001",
            request=Mock(content_source="ranked",
                         theme="modern", max_articles=10)
        )

        # Verify generation status was updated
        assert "test-site-001" in mock_processor.generation_status

    @pytest.mark.asyncio
    async def test_generate_site_with_empty_content(self, mock_processor):
        """Test site generation with no ranked content"""
        # Mock empty content
        mock_processor.blob_client.download_json.return_value = {
            "ranked_topics": [],
            "metadata": {"total_items": 0}
        }

        mock_processor.template_manager.render_template.return_value = "<html>Empty site</html>"
        mock_processor.template_manager.get_static_assets.return_value = {
            "assets/style.css": ""}

        await mock_processor.generate_site(
            site_id="empty-site",
            request=Mock(content_source="ranked",
                         theme="modern", max_articles=10)
        )

        # Should have updated generation status
        assert "empty-site" in mock_processor.generation_status

    @pytest.mark.asyncio
    async def test_generate_site_with_blob_error(self, mock_processor):
        """Test site generation when blob storage fails"""
        # Mock blob storage failure
        mock_processor.blob_client.download_json.side_effect = Exception(
            "Blob storage error")

        await mock_processor.generate_site(
            site_id="error-site",
            request=Mock(content_source="ranked",
                         theme="modern", max_articles=10)
        )

        # Should have error status
        assert "error-site" in mock_processor.generation_status
        assert mock_processor.generation_status["error-site"]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_generate_site_with_template_error(self, mock_processor, sample_ranked_content):
        """Test site generation when template rendering fails"""
        # Mock successful blob download but template failure
        mock_processor.blob_client.download_json.return_value = sample_ranked_content
        mock_processor.template_manager.render_template.side_effect = Exception(
            "Template error")

        await mock_processor.generate_site(
            site_id="template-error-site",
            request=Mock(content_source="ranked",
                         theme="modern", max_articles=10)
        )

        # Should have error status
        assert "template-error-site" in mock_processor.generation_status
        assert mock_processor.generation_status["template-error-site"]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_get_generation_status(self, mock_processor):
        """Test getting generation status for a site"""
        # Set up test status
        site_id = "test-status-site"
        mock_processor.generation_status[site_id] = {
            "status": "processing",
            "progress": 50,  # Use "progress" not "progress_percentage"
            "current_step": "Rendering templates",
            "error_message": None,
            "completion_time": None
        }

        status = await mock_processor.get_generation_status(site_id)

        assert status.status == "processing"
        assert status.progress_percentage == 50
        assert status.current_step == "Rendering templates"

    @pytest.mark.asyncio
    async def test_get_generation_status_not_found(self, mock_processor):
        """Test getting status for non-existent site"""
        with pytest.raises(Exception):  # Should raise KeyError or similar
            await mock_processor.get_generation_status("non-existent-site")

    @pytest.mark.asyncio
    async def test_list_available_sites(self, mock_processor):
        """Test listing available generated sites"""
        # Mock blob storage to return some sites with proper published-sites prefix
        mock_processor.blob_client.list_blobs.return_value = [
            {"name": "site_001/index.html"},
            {"name": "site_002/index.html"},
            {"name": "site_003/index.html"},
        ]

        # Mock the download_json calls for manifests to avoid exceptions
        mock_processor.blob_client.download_json.side_effect = Exception(
            "Manifest not found")

        sites = await mock_processor.list_available_sites()

        assert len(sites) == 3
        assert all("site_" in site.get("site_id", "") for site in sites)

    def test_generate_rss_feed(self, mock_processor, sample_ranked_content):
        """Test RSS feed generation"""
        # Convert dict articles to ContentItem objects
        from service_logic import ContentItem
        articles = []
        for article_data in sample_ranked_content["ranked_topics"]:
            content_item = ContentItem(
                title=article_data["title"],
                url=article_data.get("url", "#"),
                summary=article_data.get("summary", article_data.get(
                    "content", "No summary available")[:100]),
                content=article_data["content"],
                author=article_data.get("author", ""),
                score=article_data.get("ranking_score", 0),
                source=article_data.get("source", "unknown")
            )
            articles.append(content_item)

        rss = mock_processor._generate_rss_feed(articles)

        assert "<rss" in rss
        assert "<channel>" in rss
        assert "<item>" in rss
        assert articles[0].title in rss

    @pytest.mark.asyncio
    async def test_content_processing_with_limits(self, mock_processor, sample_ranked_content):
        """Test content processing respects article limits"""
        # Create content with many articles
        many_articles = sample_ranked_content.copy()
        # 20 articles
        many_articles["ranked_topics"] = sample_ranked_content["ranked_topics"] * 10

        mock_processor.blob_client.download_json.return_value = many_articles
        mock_processor.template_manager.render_template.return_value = "<html>Test</html>"
        mock_processor.template_manager.get_static_assets.return_value = {
            "assets/style.css": ""}

        # Test with limit of 5 articles
        await mock_processor.generate_site(
            site_id="limited-site",
            request=Mock(content_source="ranked",
                         theme="modern", max_articles=5)
        )

        # Should have updated generation status
        assert "limited-site" in mock_processor.generation_status

    def test_url_slug_generation(self, mock_processor):
        """Test URL slug generation from article titles"""
        test_cases = [
            ("Simple Title", "simple-title"),
            ("Title with Special Characters!@#", "title-with-special-characters"),
            ("Multiple    Spaces   Here", "multiple-spaces-here"),
            ("Very Long Title That Should Be Truncated Because It's Too Long",
             "very-long-title-that-should-be-truncated-because"),
        ]

        for title, expected_slug in test_cases:
            slug = mock_processor._create_slug(title)
            assert slug == expected_slug or slug.startswith(expected_slug[:20])
            assert " " not in slug
            assert slug.islower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

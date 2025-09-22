"""
Integration Tests for Simplified Content Processing - ACTIVE

CURRENT ARCHITECTURE: Integration tests for simplified content processing pipeline
Status: ACTIVE - Tests the complete collection workflow

Tests the complete collection pipeline using simplified collectors.
These tests replace the complex adaptive strategy tests with simpler, more reliable tests.

Test Coverage:
- Reddit collection integration with content_processing_simple
- Mastodon collection integration with content_processing_simple
- Multi-source collection workflows
- Content deduplication functionality
- Error handling in the processing pipeline
- Mock-based integration testing

Tests the complete collection pipeline using simplified collectors.
These tests replace the complex adaptive strategy tests with simpler, more reliable tests.
"""

from unittest.mock import AsyncMock, patch

import pytest
from content_processing_simple import collect_content_batch, deduplicate_content


class TestContentProcessingIntegration:
    """Integration tests for the simplified content processing pipeline."""

    @pytest.mark.asyncio
    async def test_reddit_collection_integration(self, sample_reddit_data):
        """Test complete Reddit collection pipeline."""

        sources = [{"type": "reddit", "subreddits": ["programming"], "limit": 5}]

        # Mock the collector's get_json method
        with patch(
            "collectors.simple_reddit.SimpleRedditCollector.get_json",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = sample_reddit_data

            result = await collect_content_batch(sources)

            assert result["metadata"]["total_sources"] == 1
            assert result["metadata"]["sources_processed"] == 1
            # Based on sample data
            assert result["metadata"]["reddit_count"] == 2
            assert result["metadata"]["reddit_status"] == "success"

            # Check item structure
            items = result["collected_items"]
            assert len(items) == 2

            item = items[0]
            assert item["source_type"] == "reddit"
            assert "source_config" in item
            assert item["id"] == "reddit_test123"
            assert item["source"] == "reddit"

    @pytest.mark.asyncio
    async def test_mastodon_collection_integration(self, sample_mastodon_data):
        """Test complete Mastodon collection pipeline."""

        sources = [
            {
                "type": "mastodon",
                "instances": ["mastodon.social"],
                "hashtags": ["technology"],
                "limit": 3,
            }
        ]

        # Mock the collector's get_json method
        with patch(
            "collectors.simple_mastodon.SimpleMastodonCollector.get_json",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = sample_mastodon_data

            result = await collect_content_batch(sources)

            assert result["metadata"]["total_sources"] == 1
            assert result["metadata"]["sources_processed"] == 1
            # Based on sample data
            assert result["metadata"]["mastodon_count"] == 1
            assert result["metadata"]["mastodon_status"] == "success"

            # Check item structure
            items = result["collected_items"]
            assert len(items) == 1

            item = items[0]
            assert item["source_type"] == "mastodon"
            assert "source_config" in item
            assert item["id"] == "mastodon_mastodon.social_post123"
            assert item["source"] == "mastodon"

    @pytest.mark.asyncio
    async def test_multi_source_collection(
        self, sample_reddit_data, sample_mastodon_data
    ):
        """Test collection from multiple sources."""

        sources = [
            {"type": "reddit", "subreddits": ["programming"], "limit": 2},
            {
                "type": "mastodon",
                "instances": ["mastodon.social"],
                "hashtags": ["technology"],
                "limit": 2,
            },
        ]

        # Mock both collectors
        with (
            patch(
                "collectors.simple_reddit.SimpleRedditCollector.get_json",
                new_callable=AsyncMock,
            ) as mock_reddit,
            patch(
                "collectors.simple_mastodon.SimpleMastodonCollector.get_json",
                new_callable=AsyncMock,
            ) as mock_mastodon,
        ):

            mock_reddit.return_value = sample_reddit_data
            mock_mastodon.return_value = sample_mastodon_data

            result = await collect_content_batch(sources)

            assert result["metadata"]["total_sources"] == 2
            assert result["metadata"]["sources_processed"] == 2
            assert result["metadata"]["reddit_count"] == 2
            assert result["metadata"]["mastodon_count"] == 1
            assert result["metadata"]["total_items"] == 3

            # Check we have items from both sources
            items = result["collected_items"]
            source_types = {item["source_type"] for item in items}
            assert "reddit" in source_types
            assert "mastodon" in source_types


class TestDeduplication:
    """Test content deduplication functionality."""

    @pytest.mark.asyncio
    async def test_deduplicate_identical_content(self):
        """Test deduplication of identical content."""

        items = [
            {
                "id": "item1",
                "title": "Same Title",
                "content": "Same content",
                "source": "reddit",
            },
            {
                "id": "item2",
                "title": "Same Title",
                "content": "Same content",
                "source": "mastodon",
            },
            {
                "id": "item3",
                "title": "Different Title",
                "content": "Different content",
                "source": "reddit",
            },
        ]

        unique_items = await deduplicate_content(items)

        # Should have 2 unique items (first duplicate removed)
        assert len(unique_items) == 2
        assert unique_items[0]["id"] == "item1"
        assert unique_items[1]["id"] == "item3"

        # Should add content_hash to items
        assert "content_hash" in unique_items[0]
        assert "content_hash" in unique_items[1]

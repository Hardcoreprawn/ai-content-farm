#!/usr/bin/env python3
"""
Integration Tests - Content Ranker Algorithms

Tests the ranking algorithms and scoring functionality.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytest
import pytest_asyncio
from ranker import calculate_composite_score, rank_content_items
from service_logic import ContentRankerService

from libs.blob_storage import BlobContainers, BlobStorageClient


@pytest.mark.asyncio
class TestContentRankingAlgorithms:
    """Test suite for Content Ranker Algorithm Integration."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_service(self):
        """Setup test environment."""
        self.ranker_service = ContentRankerService()
        self.blob_client = BlobStorageClient()

        # Ensure containers exist
        await self.ranker_service.ensure_containers()

        # Clean up any existing test data
        await self._cleanup_test_data()

    async def _cleanup_test_data(self):
        """Clean up test data from blob storage."""
        try:
            # List and delete enriched test content
            enriched_blobs = self.blob_client.list_blobs(
                BlobContainers.ENRICHED_CONTENT
            )
            for blob_info in enriched_blobs:
                if blob_info["name"].startswith("enriched_test_"):
                    self.blob_client.delete_blob(
                        BlobContainers.ENRICHED_CONTENT, blob_info["name"]
                    )

            # List and delete ranked test content
            ranked_blobs = self.blob_client.list_blobs(BlobContainers.RANKED_CONTENT)
            for blob_info in ranked_blobs:
                if blob_info["name"].startswith("ranked_test_"):
                    self.blob_client.delete_blob(
                        BlobContainers.RANKED_CONTENT, blob_info["name"]
                    )
        except Exception as e:
            print(f"Cleanup warning: {e}")

    def _create_test_enriched_content(self):
        """Create test enriched content for ranking."""
        base_time = datetime.now()
        return [
            {
                "id": "test_001",
                "title": "High-Scoring Tech Article",
                "url": "https://example.com/tech/high-score",
                "subreddit": "technology",
                "score": 500,
                "num_comments": 100,
                "created_utc": (base_time - timedelta(hours=2)).isoformat(),
                "engagement_metrics": {
                    "upvote_ratio": 0.95,
                    "awards_received": 5,
                    "comment_engagement": 0.8,
                },
                "content_analysis": {
                    "readability_score": 8.5,
                    "technical_depth": 7.0,
                    "novelty_score": 8.0,
                },
                "enrichment": {
                    "summary": "High-quality technical article about emerging tech trends.",
                    "key_points": ["Innovation", "Technology", "Future trends"],
                    "credibility_score": 9.0,
                    "processing_timestamp": base_time.isoformat(),
                },
            },
            {
                "id": "test_002",
                "title": "Medium-Scoring Science Article",
                "url": "https://example.com/science/medium-score",
                "subreddit": "science",
                "score": 250,
                "num_comments": 50,
                "created_utc": (base_time - timedelta(hours=6)).isoformat(),
                "engagement_metrics": {
                    "upvote_ratio": 0.85,
                    "awards_received": 2,
                    "comment_engagement": 0.6,
                },
                "content_analysis": {
                    "readability_score": 7.0,
                    "technical_depth": 8.5,
                    "novelty_score": 6.0,
                },
                "enrichment": {
                    "summary": "Detailed scientific study with interesting findings.",
                    "key_points": ["Research", "Scientific method", "Data analysis"],
                    "credibility_score": 8.5,
                    "processing_timestamp": base_time.isoformat(),
                },
            },
            {
                "id": "test_003",
                "title": "Low-Scoring General Article",
                "url": "https://example.com/general/low-score",
                "subreddit": "general",
                "score": 50,
                "num_comments": 10,
                "created_utc": (base_time - timedelta(hours=12)).isoformat(),
                "engagement_metrics": {
                    "upvote_ratio": 0.70,
                    "awards_received": 0,
                    "comment_engagement": 0.3,
                },
                "content_analysis": {
                    "readability_score": 6.0,
                    "technical_depth": 3.0,
                    "novelty_score": 4.0,
                },
                "enrichment": {
                    "summary": "Basic article with limited depth and engagement.",
                    "key_points": ["General topic", "Basic information"],
                    "credibility_score": 6.0,
                    "processing_timestamp": base_time.isoformat(),
                },
            },
        ]

    @pytest.mark.integration
    async def test_content_ranking_algorithms(self):
        """Test ranking algorithms with enriched content."""
        # Create and upload test content
        test_content = self._create_test_enriched_content()

        for item in test_content:
            blob_name = f"enriched_{item['id']}.json"
            self.blob_client.upload_json(
                BlobContainers.ENRICHED_CONTENT, blob_name, item
            )

        # Rank the content
        ranked_content = await self.ranker_service.rank_content_batch()

        # Should return ranked items
        assert len(ranked_content) >= 3

        # Find our test items
        test_items = [item for item in ranked_content if item["id"].startswith("test_")]
        assert len(test_items) == 3

        # Verify they're sorted by rank score
        for i in range(len(test_items) - 1):
            assert (
                test_items[i]["final_rank_score"]
                >= test_items[i + 1]["final_rank_score"]
            )

        # High-scoring item should rank higher
        high_scoring = next(item for item in test_items if item["id"] == "test_001")
        low_scoring = next(item for item in test_items if item["id"] == "test_003")
        assert high_scoring["final_rank_score"] > low_scoring["final_rank_score"]

    @pytest.mark.integration
    async def test_ranking_scores_calculation(self):
        """Test individual ranking score calculations."""
        test_content = self._create_test_enriched_content()

        # Test composite score calculation
        for item in test_content:
            score = calculate_composite_score(item)
            assert isinstance(score, (int, float))
            assert 0 <= score <= 100

        # High-scoring content should have higher composite score
        high_item = test_content[0]  # test_001
        low_item = test_content[2]  # test_003

        high_score = calculate_composite_score(high_item)
        low_score = calculate_composite_score(low_item)
        assert high_score > low_score

    @pytest.mark.integration
    async def test_specific_content_ranking(self):
        """Test ranking specific content items."""
        # Create and upload test content
        test_content = self._create_test_enriched_content()

        for item in test_content:
            blob_name = f"enriched_{item['id']}.json"
            self.blob_client.upload_json(
                BlobContainers.ENRICHED_CONTENT, blob_name, item
            )

        # Rank specific content
        specific_items = ["test_001", "test_003"]
        ranked_content = await self.ranker_service.rank_specific_content(specific_items)

        # Should return only requested items
        assert len(ranked_content) == 2
        returned_ids = [item["id"] for item in ranked_content]
        assert "test_001" in returned_ids
        assert "test_003" in returned_ids
        assert "test_002" not in returned_ids

        # Should be ranked properly
        assert (
            ranked_content[0]["final_rank_score"]
            >= ranked_content[1]["final_rank_score"]
        )

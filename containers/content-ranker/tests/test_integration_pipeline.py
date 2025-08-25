#!/usr/bin/env python3
"""
Integration Tests - Content Ranker Pipeline

Tests the complete pipeline, service integration, and end-to-end functionality.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytest
import pytest_asyncio
from service_logic import ContentRankerService

from libs.blob_storage import BlobContainers, BlobStorageClient


@pytest.mark.asyncio
class TestContentRankerPipeline:
    """Test suite for Content Ranker Pipeline Integration."""

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
        ]

    @pytest.mark.integration
    async def test_enriched_content_retrieval(self):
        """Test retrieving enriched content from blob storage."""
        # Create and upload test content
        test_content = self._create_test_enriched_content()

        for item in test_content:
            blob_name = f"enriched_{item['id']}.json"
            self.blob_client.upload_json(
                BlobContainers.ENRICHED_CONTENT, blob_name, item
            )

        # Test retrieving all content
        retrieved_content = await self.ranker_service.get_enriched_content()

        # Should find our test content
        test_items = [
            item for item in retrieved_content if item["id"].startswith("test_")
        ]
        assert len(test_items) == 2

        # Test retrieving specific content
        specific_content = await self.ranker_service.get_enriched_content("test_001")
        assert len(specific_content) == 1
        assert specific_content[0]["id"] == "test_001"

    @pytest.mark.integration
    async def test_batch_ranking_pipeline(self):
        """Test the complete batch ranking pipeline."""
        # Create and upload test content
        test_content = self._create_test_enriched_content()

        for item in test_content:
            blob_name = f"enriched_{item['id']}.json"
            self.blob_client.upload_json(
                BlobContainers.ENRICHED_CONTENT, blob_name, item
            )

        # Run batch ranking
        ranked_content = await self.ranker_service.rank_content_batch()

        # Verify results
        assert len(ranked_content) >= 2

        # Check that ranked content is stored
        ranked_blobs = self.blob_client.list_blobs(BlobContainers.RANKED_CONTENT)
        ranked_blob_names = [blob["name"] for blob in ranked_blobs]

        # Should have batch results
        batch_files = [name for name in ranked_blob_names if "batch_" in name]
        assert len(batch_files) > 0

    @pytest.mark.integration
    async def test_service_status(self):
        """Test service status endpoint."""
        status = await self.ranker_service.get_ranking_status()

        # Should return status information
        assert "service" in status
        assert status["service"] == "content-ranker"
        assert "status" in status
        assert "containers" in status

        # Should list expected containers
        containers = status["containers"]
        assert BlobContainers.ENRICHED_CONTENT in containers
        assert BlobContainers.RANKED_CONTENT in containers

    @pytest.mark.integration
    async def test_error_handling(self):
        """Test error handling in ranking operations."""
        # Test ranking non-existent content
        result = await self.ranker_service.rank_specific_content(["non_existent_id"])
        assert isinstance(result, list)
        assert len(result) == 0

        # Test getting non-existent content
        result = await self.ranker_service.get_enriched_content("non_existent_id")
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.integration
    async def test_ranking_metadata_preservation(self):
        """Test that enrichment metadata is preserved through ranking."""
        # Create and upload test content
        test_content = self._create_test_enriched_content()

        for item in test_content:
            blob_name = f"enriched_{item['id']}.json"
            self.blob_client.upload_json(
                BlobContainers.ENRICHED_CONTENT, blob_name, item
            )

        # Rank the content
        ranked_content = await self.ranker_service.rank_content_batch()

        # Find our test items
        test_items = [item for item in ranked_content if item["id"].startswith("test_")]

        for item in test_items:
            # Check that original metadata is preserved
            assert "enrichment" in item
            assert "content_analysis" in item
            assert "engagement_metrics" in item

            # Check that ranking metadata is added
            assert "final_rank_score" in item
            assert "ranking_timestamp" in item

    @pytest.mark.integration
    async def test_pipeline_end_to_end(self):
        """Test complete enriched → ranked pipeline end-to-end."""
        # Create and upload test content
        test_content = self._create_test_enriched_content()

        for item in test_content:
            blob_name = f"enriched_{item['id']}.json"
            self.blob_client.upload_json(
                BlobContainers.ENRICHED_CONTENT, blob_name, item
            )

        # Run the complete pipeline
        ranked_content = await self.ranker_service.rank_content_batch()

        # Verify pipeline results
        assert len(ranked_content) >= 2

        # Check that all stages completed
        for item in ranked_content:
            if item["id"].startswith("test_"):
                # Should have original enriched data
                assert "enrichment" in item
                assert "content_analysis" in item

                # Should have ranking data
                assert "final_rank_score" in item
                assert "ranking_timestamp" in item

                # Score should be valid
                assert isinstance(item["final_rank_score"], (int, float))
                assert item["final_rank_score"] >= 0

        # Verify content is properly stored in ranked container
        ranked_blobs = self.blob_client.list_blobs(BlobContainers.RANKED_CONTENT)
        assert len(ranked_blobs) > 0

        # Verify we can retrieve the ranked content
        batch_files = [
            blob for blob in ranked_blobs if blob["name"].startswith("batch_")
        ]
        assert len(batch_files) > 0

        # Load and verify a batch file
        latest_batch = max(batch_files, key=lambda x: x["name"])
        batch_content = self.blob_client.download_json(
            BlobContainers.RANKED_CONTENT, latest_batch["name"]
        )

        assert isinstance(batch_content, list)
        assert len(batch_content) >= 2

        # Verify test items are in the batch
        batch_test_items = [
            item for item in batch_content if item["id"].startswith("test_")
        ]
        assert len(batch_test_items) == 2

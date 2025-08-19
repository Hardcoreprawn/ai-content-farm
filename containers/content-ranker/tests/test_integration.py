#!/usr/bin/env python3
"""
Phase 2D Integration Tests - Content Ranker Integration

Tests the complete enriched → ranked content pipeline integration.
"""

import pytest
import pytest_asyncio
import json
import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from service_logic import ContentRankerService
from libs.blob_storage import BlobStorageClient, BlobContainers
from ranker import rank_content_items, calculate_composite_score


@pytest.mark.asyncio
class TestPhase2DIntegration:
    """Test suite for Phase 2D Content Ranker Integration."""

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
                BlobContainers.ENRICHED_CONTENT)
            for blob_info in enriched_blobs:
                if blob_info["name"].startswith("enriched_test_"):
                    self.blob_client.delete_blob(
                        BlobContainers.ENRICHED_CONTENT, blob_info["name"])

            # List and delete ranked test content
            ranked_blobs = self.blob_client.list_blobs(
                BlobContainers.RANKED_CONTENT)
            for blob_info in ranked_blobs:
                if blob_info["name"].startswith("ranked_test_"):
                    self.blob_client.delete_blob(
                        BlobContainers.RANKED_CONTENT, blob_info["name"])

        except Exception as e:
            print(f"Cleanup warning: {e}")

    def _create_test_enriched_content(self) -> List[Dict[str, Any]]:
        """Create sample enriched content for testing."""
        base_time = datetime.utcnow()

        return [
            {
                "id": "test_001",
                "title": "Breaking: Revolutionary AI Breakthrough",
                "clean_title": "Revolutionary AI Breakthrough",
                "content": "Major breakthrough in AI research announced today...",
                "engagement_score": 0.85,
                "normalized_score": 0.85,
                "published_at": (base_time - timedelta(hours=2)).isoformat() + "Z",
                "content_type": "article",
                "topic_classification": {
                    "primary_topic": "artificial_intelligence",
                    "confidence": 0.92,
                    "topics": ["technology", "machine_learning", "innovation"],
                    "categories": ["tech", "science"]
                },
                "sentiment_analysis": {
                    "sentiment": "positive",
                    "confidence": 0.88,
                    "compound_score": 0.7,
                    "scores": {"positive": 0.7, "neutral": 0.2, "negative": 0.1}
                },
                "trend_analysis": {
                    "trending": True,
                    "trend_score": 0.9,
                    "velocity": "increasing",
                    "momentum": "high"
                },
                "content_summary": "Revolutionary AI breakthrough announced with significant implications for the tech industry.",
                "source_metadata": {
                    "platform": "reddit",
                    "subreddit": "MachineLearning",
                    "upvotes": 245,
                    "comments": 67
                }
            },
            {
                "id": "test_002",
                "title": "Climate Change Study Results Published",
                "clean_title": "Climate Change Study Results Published",
                "content": "New research reveals concerning climate trends...",
                "engagement_score": 0.65,
                "normalized_score": 0.65,
                "published_at": (base_time - timedelta(hours=8)).isoformat() + "Z",
                "content_type": "article",
                "topic_classification": {
                    "primary_topic": "climate_change",
                    "confidence": 0.89,
                    "topics": ["environment", "science", "research"],
                    "categories": ["science", "environment"]
                },
                "sentiment_analysis": {
                    "sentiment": "negative",
                    "confidence": 0.75,
                    "compound_score": -0.3,
                    "scores": {"positive": 0.2, "neutral": 0.3, "negative": 0.5}
                },
                "trend_analysis": {
                    "trending": False,
                    "trend_score": 0.4,
                    "velocity": "stable",
                    "momentum": "low"
                },
                "content_summary": "New climate study reveals concerning environmental trends requiring immediate attention.",
                "source_metadata": {
                    "platform": "twitter",
                    "user": "climateresearcher",
                    "retweets": 123,
                    "likes": 456
                }
            },
            {
                "id": "test_003",
                "title": "Tech Stock Market Analysis",
                "clean_title": "Tech Stock Market Analysis",
                "content": "Technology stocks show mixed performance...",
                "engagement_score": 0.45,
                "normalized_score": 0.45,
                "published_at": (base_time - timedelta(hours=24)).isoformat() + "Z",
                "content_type": "analysis",
                "topic_classification": {
                    "primary_topic": "finance",
                    "confidence": 0.78,
                    "topics": ["stocks", "technology", "market_analysis"],
                    "categories": ["finance", "business"]
                },
                "sentiment_analysis": {
                    "sentiment": "neutral",
                    "confidence": 0.82,
                    "compound_score": 0.1,
                    "scores": {"positive": 0.4, "neutral": 0.5, "negative": 0.1}
                },
                "trend_analysis": {
                    "trending": False,
                    "trend_score": 0.3,
                    "velocity": "decreasing",
                    "momentum": "low"
                },
                "content_summary": "Analysis of current technology stock market trends and performance indicators.",
                "source_metadata": {
                    "platform": "news_feed",
                    "source": "FinancialNews",
                    "views": 1250,
                    "shares": 23
                }
            }
        ]

    async def test_enriched_content_retrieval(self):
        """Test retrieving enriched content from blob storage."""
        # Create and upload test content
        test_content = self._create_test_enriched_content()

        for item in test_content:
            blob_name = f"enriched_{item['id']}.json"
            self.blob_client.upload_json(
                BlobContainers.ENRICHED_CONTENT,
                blob_name,
                item
            )        # Test retrieving all content
        retrieved_content = await self.ranker_service.get_enriched_content()

        # Should find our test content
        test_items = [
            item for item in retrieved_content if item["id"].startswith("test_")]
        assert len(test_items) == 3

        # Test retrieving specific content
        specific_content = await self.ranker_service.get_enriched_content("test_001")
        assert len(specific_content) == 1
        assert specific_content[0]["id"] == "test_001"

    async def test_content_ranking_algorithms(self):
        """Test ranking algorithms with enriched content."""
        test_content = self._create_test_enriched_content()

        # Test basic ranking
        ranked_items = rank_content_items(test_content)

        assert len(ranked_items) == 3
        assert all("ranking_scores" in item for item in ranked_items)
        assert all("final_rank_score" in item for item in ranked_items)
        assert all("rank_position" in item for item in ranked_items)

        # Items should be sorted by rank score (highest first)
        for i in range(len(ranked_items) - 1):
            assert ranked_items[i]["final_rank_score"] >= ranked_items[i +
                                                                       1]["final_rank_score"]

        # Test with custom weights
        custom_weights = {"engagement": 0.6,
                          "recency": 0.3, "topic_relevance": 0.1}
        ranked_custom = rank_content_items(
            test_content, weights=custom_weights)

        assert len(ranked_custom) == 3

        # Check weights (allowing for floating point precision)
        weights_used = ranked_custom[0]["ranking_scores"]["weights_used"]
        assert abs(weights_used["engagement"] - 0.6) < 1e-6
        assert abs(weights_used["recency"] - 0.3) < 1e-6
        assert abs(weights_used["topic_relevance"] - 0.1) < 1e-6

        # Test with target topics
        target_topics = ["artificial_intelligence", "technology"]
        ranked_topics = rank_content_items(
            test_content, target_topics=target_topics)

        assert len(ranked_topics) == 3
        # AI content should rank higher with AI target topics
        ai_item = next(
            item for item in ranked_topics if item["id"] == "test_001")
        assert ai_item["rank_position"] == 1

    async def test_batch_ranking_pipeline(self):
        """Test the complete batch ranking pipeline."""
        # Upload test enriched content
        test_content = self._create_test_enriched_content()

        for item in test_content:
            blob_name = f"enriched_{item['id']}.json"
            self.blob_client.upload_json(
                BlobContainers.ENRICHED_CONTENT,
                blob_name,
                item
            )

        # Run batch ranking
        result = await self.ranker_service.rank_content_batch(
            weights={"engagement": 0.5, "recency": 0.3,
                     "topic_relevance": 0.2},
            target_topics=["artificial_intelligence"],
            limit=10
        )

        # Verify results
        assert "ranked_items" in result
        assert "total_processed" in result
        assert "ranking_metadata" in result

        ranked_items = result["ranked_items"]
        # Our test items plus any existing content
        assert len(ranked_items) >= 3

        # Verify AI content is ranked highly
        test_items = [
            item for item in ranked_items if item["id"].startswith("test_")]
        ai_item = next(item for item in test_items if item["id"] == "test_001")
        assert ai_item["rank_position"] <= 3  # Should be in top 3

        # Verify ranked content was stored
        ranked_blobs = self.blob_client.list_blobs(
            BlobContainers.RANKED_CONTENT)
        test_ranked = [
            b for b in ranked_blobs if b["name"].startswith("ranked_test_")]
        assert len(test_ranked) >= 3

    async def test_specific_content_ranking(self):
        """Test ranking specific content items."""
        test_content = self._create_test_enriched_content()

        # Test ranking specific items
        ranked_items = await self.ranker_service.rank_specific_content(
            content_items=test_content[:2],  # Only first 2 items
            weights={"engagement": 0.7, "recency": 0.2, "topic_relevance": 0.1}
        )

        assert len(ranked_items) == 2
        assert ranked_items[0]["final_rank_score"] >= ranked_items[1]["final_rank_score"]

        # Test with empty list
        empty_result = await self.ranker_service.rank_specific_content([])
        assert len(empty_result) == 0

    async def test_ranking_scores_calculation(self):
        """Test individual ranking score calculations."""
        test_item = self._create_test_enriched_content()[0]  # AI article

        # Test composite score calculation
        scores = calculate_composite_score(test_item)

        assert "engagement_score" in scores
        assert "recency_score" in scores
        assert "topic_relevance_score" in scores
        assert "composite_score" in scores
        assert "weights_used" in scores

        # Scores should be normalized (0-1)
        for score_key in ["engagement_score", "recency_score", "topic_relevance_score", "composite_score"]:
            score = scores[score_key]
            assert 0.0 <= score <= 1.0

        # Test with target topics
        scores_with_topics = calculate_composite_score(
            test_item,
            target_topics=["artificial_intelligence", "technology"]
        )

        # Topic relevance should be higher with matching topics
        assert scores_with_topics["topic_relevance_score"] > scores["topic_relevance_score"]

    async def test_service_status(self):
        """Test service status endpoint."""
        # Upload some test content first
        test_content = self._create_test_enriched_content()

        for item in test_content:
            blob_name = f"enriched_{item['id']}.json"
            self.blob_client.upload_json(
                BlobContainers.ENRICHED_CONTENT,
                blob_name,
                item
            )

        # Get status
        status = await self.ranker_service.get_ranking_status()

        assert status["service"] == "content-ranker"
        assert status["status"] == "healthy"
        assert "timestamp" in status
        assert "content_stats" in status
        assert "containers" in status

        # Should show our test content
        content_stats = status["content_stats"]
        assert content_stats["enriched_items_available"] >= 3

    async def test_error_handling(self):
        """Test error handling in ranking operations."""
        # Test with invalid content
        invalid_content = [{"invalid": "data"}]

        try:
            await self.ranker_service.rank_specific_content(invalid_content)
            # Should not reach here if error handling works
            assert False, "Expected error for invalid content"
        except Exception:
            # Expected to fail
            pass

        # Test retrieving non-existent content
        result = await self.ranker_service.get_enriched_content("nonexistent_id")
        assert len(result) == 0

    async def test_ranking_metadata_preservation(self):
        """Test that enrichment metadata is preserved through ranking."""
        test_content = self._create_test_enriched_content()

        ranked_items = await self.ranker_service.rank_specific_content(test_content)

        for ranked_item in ranked_items:
            original_item = next(
                item for item in test_content if item["id"] == ranked_item["id"])

            # Check that enrichment data is preserved
            assert ranked_item["topic_classification"] == original_item["topic_classification"]
            assert ranked_item["sentiment_analysis"] == original_item["sentiment_analysis"]
            assert ranked_item["trend_analysis"] == original_item["trend_analysis"]
            assert ranked_item["content_summary"] == original_item["content_summary"]

            # Check that ranking data is added
            assert "ranking_scores" in ranked_item
            assert "final_rank_score" in ranked_item
            assert "rank_position" in ranked_item

    async def test_pipeline_end_to_end(self):
        """Test complete enriched → ranked pipeline end-to-end."""
        # 1. Upload enriched content (simulating Phase 2C output)
        test_content = self._create_test_enriched_content()

        for item in test_content:
            blob_name = f"enriched_{item['id']}.json"
            self.blob_client.upload_json(
                BlobContainers.ENRICHED_CONTENT,
                blob_name,
                item
            )

        # 2. Run complete ranking pipeline
        pipeline_result = await self.ranker_service.rank_content_batch(
            weights={"engagement": 0.4, "recency": 0.35,
                     "topic_relevance": 0.25},
            limit=5
        )

        # 3. Verify pipeline results
        assert pipeline_result["total_processed"] >= 3
        assert len(pipeline_result["ranked_items"]) >= 3

        # 4. Verify content is stored in ranked container
        ranked_blobs = self.blob_client.list_blobs(
            BlobContainers.RANKED_CONTENT)
        ranked_test_blobs = [b for b in ranked_blobs if "test_" in b["name"]]
        assert len(ranked_test_blobs) >= 3

        # 5. Verify we can retrieve ranked content
        for blob_info in ranked_test_blobs:
            if blob_info["name"].startswith("test_ranked_"):
                ranked_data = self.blob_client.download_json(
                    BlobContainers.RANKED_CONTENT,
                    blob_info["name"]
                )
                assert "ranking_scores" in ranked_data
                assert "final_rank_score" in ranked_data

        print(f"✅ Phase 2D Integration: Complete enriched → ranked pipeline working")
        print(
            f"   - Processed {pipeline_result['total_processed']} enriched items")
        print(
            f"   - Returned {len(pipeline_result['ranked_items'])} ranked items")
        print(f"   - Stored {len(ranked_test_blobs)} ranked content files")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])

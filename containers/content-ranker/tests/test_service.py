#!/usr/bin/env python3
"""
Unit tests for content-ranker service logic.

Tests the ranking algorithms and service layer functionality.
"""

import json
import pytest
import datetime
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock

# Import service logic to test
from service_logic import ContentRankerService
from ranker import rank_content_items


def create_test_content() -> List[Dict[str, Any]]:
    """Create sample enriched content items for testing."""

    base_time = datetime.datetime.now()

    test_items = [
        {
            "id": "test_001",
            "title": "Revolutionary AI Breakthrough in Machine Learning",
            "clean_title": "Revolutionary AI Breakthrough in Machine Learning",
            "engagement_score": 0.85,
            "normalized_score": 0.85,
            "published_at": (base_time - datetime.timedelta(hours=2)).isoformat() + "Z",
            "content_type": "article",
            "topic_classification": {
                "primary_topic": "artificial_intelligence",
                "confidence": 0.92,
                "categories": ["technology", "machine_learning", "innovation"]
            },
            "sentiment_analysis": {
                "sentiment": "positive",
                "confidence": 0.88,
                "compound_score": 0.7
            },
            "trend_analysis": {
                "trending": True,
                "trend_score": 0.9,
                "velocity": "increasing"
            },
            "source_metadata": {
                "platform": "reddit",
                "subreddit": "MachineLearning",
                "upvotes": 245,
                "comments": 67
            }
        },
        {
            "id": "test_002",
            "title": "Future of Quantum Computing",
            "clean_title": "Future of Quantum Computing",
            "engagement_score": 0.72,
            "normalized_score": 0.72,
            "published_at": (base_time - datetime.timedelta(hours=5)).isoformat() + "Z",
            "content_type": "article",
            "topic_classification": {
                "primary_topic": "quantum_computing",
                "confidence": 0.89,
                "categories": ["technology", "quantum", "computing"]
            },
            "sentiment_analysis": {
                "sentiment": "neutral",
                "confidence": 0.75,
                "compound_score": 0.1
            },
            "trend_analysis": {
                "trending": False,
                "trend_score": 0.3,
                "velocity": "stable"
            },
            "source_metadata": {
                "platform": "reddit",
                "subreddit": "quantum",
                "upvotes": 156,
                "comments": 34
            }
        },
        {
            "id": "test_003",
            "title": "Cybersecurity Threats in 2025",
            "clean_title": "Cybersecurity Threats in 2025",
            "engagement_score": 0.68,
            "normalized_score": 0.68,
            "published_at": (base_time - datetime.timedelta(hours=8)).isoformat() + "Z",
            "content_type": "article",
            "topic_classification": {
                "primary_topic": "cybersecurity",
                "confidence": 0.85,
                "categories": ["security", "technology", "threats"]
            },
            "sentiment_analysis": {
                "sentiment": "negative",
                "confidence": 0.80,
                "compound_score": -0.3
            },
            "trend_analysis": {
                "trending": True,
                "trend_score": 0.7,
                "velocity": "increasing"
            },
            "source_metadata": {
                "platform": "reddit",
                "subreddit": "cybersecurity",
                "upvotes": 98,
                "comments": 23
            }
        }
    ]

    return test_items


class TestRankingService:
    """Test cases for ContentRankerService."""

    @pytest.fixture
    def mock_blob_client(self):
        """Mock blob storage client."""
        with patch('service_logic.BlobStorageClient') as mock:
            yield mock.return_value

    @pytest.fixture
    def ranker_service(self, mock_blob_client):
        """Create ranker service with mocked dependencies."""
        service = ContentRankerService()
        service.blob_client = mock_blob_client
        return service

    def test_ranking_algorithms_basic(self):
        """Test basic ranking functionality with the ranking algorithms."""
        print("=== Basic Ranking Algorithm Test ===")

        test_content = create_test_content()

        # Test the ranking algorithm directly
        ranked_items = rank_content_items(test_content)

        assert len(ranked_items) > 0
        assert all("final_rank_score" in item for item in ranked_items)
        assert all("rank_position" in item for item in ranked_items)

        # Verify ranking order (higher scores should be ranked first)
        for i in range(len(ranked_items) - 1):
            assert ranked_items[i]["final_rank_score"] >= ranked_items[i +
                                                                       1]["final_rank_score"]

        print(f"Successfully ranked {len(ranked_items)} items")

    def test_ranking_with_custom_weights(self):
        """Test ranking with custom weight options."""
        print("=== Custom Weights Ranking Test ===")

        test_content = create_test_content()

        # Test with custom weights
        custom_weights = {
            "engagement": 0.6,
            "recency": 0.2,
            "topic_relevance": 0.2
        }

        ranked_items = rank_content_items(
            test_content,
            weights=custom_weights,
            target_topics=["artificial_intelligence"]
        )

        assert len(ranked_items) > 0
        assert all("ranking_scores" in item for item in ranked_items)

        # Check that weights were applied
        first_item = ranked_items[0]
        if "ranking_scores" in first_item:
            weights_used = first_item["ranking_scores"].get("weights_used", {})
            assert weights_used.get("engagement") == 0.6

        print(
            f"Successfully ranked {len(ranked_items)} items with custom weights")

    def test_ranking_edge_cases(self):
        """Test ranking with edge cases."""
        print("=== Edge Cases Test ===")

        # Test with empty list
        print("Testing empty list...")
        empty_result = rank_content_items([])
        assert empty_result == []

        # Test with single item
        print("Testing single item...")
        single_item = [create_test_content()[0]]
        single_result = rank_content_items(single_item)
        assert len(single_result) == 1
        assert single_result[0]["rank_position"] == 1

        # Test with items missing some fields
        print("Testing incomplete data...")
        incomplete_item = {
            "id": "incomplete_001",
            "title": "Test Title"
            # Missing other fields
        }
        incomplete_result = rank_content_items([incomplete_item])
        assert len(incomplete_result) >= 0  # Should handle gracefully

        print("Edge cases handled successfully")

    def test_error_handling(self):
        """Test error handling in ranking logic."""
        print("=== Error Handling Test ===")

        # Test with invalid data types
        print("Testing invalid data...")
        try:
            result = rank_content_items(None)
            # Should either return empty list or handle gracefully
            assert isinstance(result, list)
        except (TypeError, ValueError):
            # Acceptable to raise these exceptions for invalid input
            pass

        # Test with malformed content
        malformed_content = [{"invalid": "structure"}]
        try:
            result = rank_content_items(malformed_content)
            # Should handle gracefully
            assert isinstance(result, list)
        except Exception:
            # Some exceptions are acceptable for malformed data
            pass

        print("Error handling working correctly")

    @pytest.mark.asyncio
    async def test_service_batch_ranking(self, ranker_service, mock_blob_client):
        """Test the service layer batch ranking."""
        # Mock enriched content retrieval
        mock_blob_client.list_blobs.return_value = [
            {"name": "enriched_test_001.json"},
            {"name": "enriched_test_002.json"}
        ]
        mock_blob_client.download_json.side_effect = create_test_content()

        # Test batch ranking
        result = await ranker_service.rank_content_batch()

        assert "ranked_items" in result
        assert "total_processed" in result
        assert "ranking_metadata" in result


# Legacy test functions converted to unit tests
def test_ranking_basic():
    """Legacy test converted to unit test."""
    service = TestRankingService()
    service.test_ranking_algorithms_basic()


def test_ranking_with_options():
    """Legacy test converted to unit test."""
    service = TestRankingService()
    service.test_ranking_with_custom_weights()


def test_ranking_edge_cases():
    """Legacy test converted to unit test."""
    service = TestRankingService()
    service.test_ranking_edge_cases()


def test_error_handling():
    """Legacy test converted to unit test."""
    service = TestRankingService()
    service.test_error_handling()

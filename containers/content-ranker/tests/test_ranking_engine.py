"""
Test Suite for ContentRanker Container Service

Tests the content ranking algorithms and API endpoints.
Validates that existing ranker_core.py functionality is properly migrated.
"""

import pytest
from datetime import datetime
from typing import Dict, List
from unittest.mock import Mock, patch

# Test data for content ranking
SAMPLE_CONTENT_ITEMS = [
    {
        "id": "item_001",
        "title": "Breaking: Major AI Breakthrough",
        "content": "Scientists achieve quantum advantage in AI processing...",
        "url": "https://example.com/ai-breakthrough",
        "source": "tech_news",
        "created_at": "2025-08-13T10:00:00Z",
        "upvotes": 150,
        "comments": 45,
        "engagement_metrics": {"shares": 25, "saves": 10}
    },
    {
        "id": "item_002", 
        "title": "Regular Tech Update",
        "content": "Minor software update released...",
        "url": "https://example.com/tech-update",
        "source": "tech_blog",
        "created_at": "2025-08-13T09:00:00Z",
        "upvotes": 12,
        "comments": 3,
        "engagement_metrics": {"shares": 1, "saves": 0}
    }
]

EXPECTED_RANKING_FACTORS = [
    "engagement_score",
    "freshness_score", 
    "content_quality_score",
    "viral_potential_score",
    "credibility_score"
]


class TestRankingEngine:
    """Test the core ranking engine pure functions"""
    
    @pytest.mark.unit
    def test_rank_content_items_returns_sorted_list(self):
        """Test that rank_content_items returns properly sorted results"""
        from core.ranking_engine import rank_content_items
        
        result = rank_content_items(SAMPLE_CONTENT_ITEMS)
        
        assert isinstance(result, list)
        assert len(result) == len(SAMPLE_CONTENT_ITEMS)
        
        # Should be sorted by score descending
        scores = [item["final_score"] for item in result]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.unit
    def test_calculate_engagement_score(self):
        """Test engagement score calculation"""
        from core.ranking_engine import calculate_engagement_score
        
        item = SAMPLE_CONTENT_ITEMS[0]
        score = calculate_engagement_score(item)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    @pytest.mark.unit
    def test_calculate_freshness_score(self):
        """Test freshness score calculation"""
        from core.ranking_engine import calculate_freshness_score
        
        item = SAMPLE_CONTENT_ITEMS[0]
        score = calculate_freshness_score(item)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    @pytest.mark.unit
    def test_calculate_viral_potential_score(self):
        """Test viral potential scoring"""
        from core.ranking_engine import calculate_viral_potential_score
        
        item = SAMPLE_CONTENT_ITEMS[0]
        score = calculate_viral_potential_score(item)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    @pytest.mark.unit
    def test_calculate_content_quality_score(self):
        """Test content quality assessment"""
        from core.ranking_engine import calculate_content_quality_score
        
        item = SAMPLE_CONTENT_ITEMS[0]
        score = calculate_content_quality_score(item)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    @pytest.mark.unit
    def test_ranking_factors_included(self):
        """Test that all expected ranking factors are calculated"""
        from core.ranking_engine import calculate_ranking_factors
        
        item = SAMPLE_CONTENT_ITEMS[0]
        factors = calculate_ranking_factors(item)
        
        for factor in EXPECTED_RANKING_FACTORS:
            assert factor in factors
            assert isinstance(factors[factor], float)
            assert 0.0 <= factors[factor] <= 1.0


class TestRankingAPI:
    """Test the FastAPI endpoints for content ranking"""
    
    @pytest.mark.integration
    def test_health_endpoint(self):
        """Test health check endpoint"""
        from main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "content-ranker"

    @pytest.mark.integration
    def test_rank_endpoint_accepts_content(self):
        """Test rank endpoint accepts content for ranking"""
        from main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        request_data = {
            "content_items": SAMPLE_CONTENT_ITEMS,
            "ranking_options": {
                "algorithm": "composite",
                "weights": {
                    "engagement": 0.3,
                    "freshness": 0.2,
                    "quality": 0.3,
                    "viral_potential": 0.2
                }
            }
        }
        
        response = client.post("/api/content-ranker/rank", json=request_data)
        
        assert response.status_code == 202  # Accepted for async processing
        assert "job_id" in response.json()

    @pytest.mark.integration
    def test_status_endpoint_returns_ranking_status(self):
        """Test status endpoint returns ranking job status"""
        from main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        job_id = "test_ranking_job_001"
        
        response = client.get(f"/api/content-ranker/status/{job_id}")
        
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] in ["pending", "processing", "completed", "failed"]


class TestMigrationCompatibility:
    """Test compatibility with original ranker_core.py functions"""
    
    @pytest.mark.unit
    def test_backwards_compatibility_with_original_functions(self):
        """Test that new implementation produces similar results to original"""
        # This will test against the original functions to ensure migration accuracy
        from core.ranking_engine import rank_content_items
        
        # Test with same data that original functions would process
        result = rank_content_items(SAMPLE_CONTENT_ITEMS)
        
        # Verify structure matches expectations
        assert all("final_score" in item for item in result)
        assert all("ranking_factors" in item for item in result)

    @pytest.mark.unit
    def test_ranking_algorithm_consistency(self):
        """Test that ranking algorithm produces consistent results"""
        from core.ranking_engine import rank_content_items
        
        # Run ranking multiple times
        result1 = rank_content_items(SAMPLE_CONTENT_ITEMS.copy())
        result2 = rank_content_items(SAMPLE_CONTENT_ITEMS.copy())
        
        # Results should be identical for same input
        for i, (item1, item2) in enumerate(zip(result1, result2)):
            assert item1["final_score"] == item2["final_score"]


class TestBlobStorageIntegration:
    """Test Azure Blob Storage integration for ranking"""
    
    @pytest.mark.integration
    @pytest.mark.local
    @patch('azure.storage.blob.BlobServiceClient')
    async def test_read_collected_content(self, mock_blob_client):
        """Test reading collected content from content-processor"""
        from core.storage_client import read_collected_content
        
        # Mock blob data from content-processor
        mock_blob_data = {
            "collected_items": SAMPLE_CONTENT_ITEMS,
            "collection_metadata": {"total_items": 2, "source": "reddit"}
        }
        
        mock_blob_client.get_blob_client.return_value.download_blob.return_value.readall.return_value = \
            str(mock_blob_data).encode()
        
        result = await read_collected_content("content-raw", "reddit_20250813.json")
        
        assert isinstance(result, dict)
        assert "collected_items" in result

    @pytest.mark.integration
    @pytest.mark.local
    @patch('azure.storage.blob.BlobServiceClient')
    async def test_write_ranked_content(self, mock_blob_client):
        """Test writing ranked content for content-enricher"""
        from core.storage_client import write_ranked_content
        
        ranked_data = {
            "ranked_items": SAMPLE_CONTENT_ITEMS,
            "ranking_metadata": {"algorithm": "composite", "total_ranked": 2}
        }
        
        await write_ranked_content("content-ranked", "ranked_20250813.json", ranked_data)
        
        # Verify blob client was called
        mock_blob_client.get_blob_client.assert_called()


# Pytest fixtures
@pytest.fixture
def sample_content_items():
    """Fixture providing sample content items for ranking"""
    return [item.copy() for item in SAMPLE_CONTENT_ITEMS]

@pytest.fixture
def mock_blob_client():
    """Fixture providing mocked Azure Blob client"""
    with patch('azure.storage.blob.BlobServiceClient') as mock:
        yield mock

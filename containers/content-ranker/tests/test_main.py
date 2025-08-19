"""
Tests for Content Ranker FastAPI endpoints.

Tests the API interface of the content ranker service including
health checks, status endpoints, and ranking operations.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime

# Import the FastAPI app
from main import app

# Create test client
client = TestClient(app)


class TestContentRankerAPI:
    """Test cases for Content Ranker API endpoints."""

    def test_root_endpoint(self):
        """Test the root endpoint returns service information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert data["service"] == "content-ranker"

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert data["service"] == "content-ranker"

    @patch('main.ranker_service')
    def test_status_endpoint(self, mock_service):
        """Test the status endpoint with service information."""
        # Mock service status as async
        mock_service.get_ranking_status = AsyncMock(return_value={
            "service": "content-ranker",
            "status": "healthy",
            "version": "1.0.0",
            "containers": ["enriched-content", "ranked-content"]
        })

        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "content-ranker"
        assert data["status"] == "healthy"

    @patch('main.ranker_service')
    def test_rank_enriched_endpoint_success(self, mock_service):
        """Test successful enriched content ranking."""
        # Mock successful ranking
        mock_service.rank_content_batch = AsyncMock(return_value={
            "ranked_items": [
                {"id": "test_001", "rank_score": 0.95, "rank_position": 1},
                {"id": "test_002", "rank_score": 0.87, "rank_position": 2}
            ],
            "total_processed": 2,
            "ranking_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "weights": {"engagement": 0.5, "recency": 0.3, "topic_relevance": 0.2}
            }
        })

        request_data = {
            "weights": {"engagement": 0.5, "recency": 0.3, "topic_relevance": 0.2},
            "target_topics": ["artificial_intelligence"],
            "limit": 10
        }

        response = client.post("/rank/enriched", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "ranked_items" in data
        assert "total_processed" in data
        assert len(data["ranked_items"]) == 2

    @patch('main.ranker_service')
    def test_rank_batch_endpoint_success(self, mock_service):
        """Test successful batch ranking."""
        # Mock successful batch ranking
        mock_service.rank_content_batch = AsyncMock(return_value={
            "ranked_items": [
                {"id": "test_001", "rank_score": 0.95, "rank_position": 1}
            ],
            "total_processed": 1,
            "ranking_metadata": {
                "timestamp": datetime.utcnow().isoformat()
            }
        })

        request_data = {
            "weights": {"engagement": 0.6, "recency": 0.4}
        }

        response = client.post("/rank/batch", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "ranked_items" in data
        assert "total_processed" in data

    def test_rank_specific_content_success(self):
        """Test ranking specific content items."""
        test_content = [
            {
                "id": "test_001",
                "title": "AI Technology Trends",
                "content": "Latest developments in AI",
                "timestamp": "2025-08-19T10:00:00Z",
                "enrichment": {
                    "sentiment": {"compound": 0.8},
                    "topics": ["artificial_intelligence", "technology"],
                    "summary": "AI trends discussion"
                }
            }
        ]

        request_data = {
            "content_items": test_content,
            "weights": {"engagement": 0.5, "recency": 0.5}
        }

        response = client.post("/rank", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "ranked_items" in data
        assert len(data["ranked_items"]) > 0

    @patch('main.ranker_service')
    def test_rank_enriched_endpoint_error(self, mock_service):
        """Test error handling in enriched content ranking."""
        # Mock service error
        mock_service.rank_content_batch = AsyncMock(
            side_effect=Exception("Service error"))

        request_data = {
            "weights": {"engagement": 0.5, "recency": 0.5}
        }

        response = client.post("/rank/enriched", json=request_data)
        assert response.status_code == 500

    def test_rank_specific_content_validation_error(self):
        """Test that invalid data is handled gracefully."""
        # Invalid request data (missing required fields)
        request_data = {
            "content_items": [{"invalid": "data"}],
            "weights": {"engagement": 0.5}
        }

        response = client.post("/rank", json=request_data)
        # The service handles invalid data gracefully, returning empty results
        assert response.status_code == 200
        data = response.json()
        assert "ranked_items" in data

    def test_rank_specific_content_empty_list(self):
        """Test ranking with empty content list."""
        request_data = {
            "content_items": [],
            "weights": {"engagement": 0.5, "recency": 0.5}
        }

        response = client.post("/rank", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["ranked_items"] == []

    @patch('main.ranker_service')
    def test_status_endpoint_error(self, mock_service):
        """Test status endpoint when service has issues."""
        # Mock service error
        mock_service.get_status.side_effect = Exception("Service unavailable")

        response = client.get("/status")
        assert response.status_code == 500

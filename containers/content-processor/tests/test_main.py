#!/usr/bin/env python3
"""
API Contract Tests for Content Processor

Test FastAPI endpoints with contract-based mocks for fast, reliable testing.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# This import will fail initially - we'll create main.py to make it pass
try:
    from main import app

    client = TestClient(app)
except ImportError:
    client = None


class TestHealthEndpoint:
    """Test health check endpoint - must work for container orchestration"""

    @patch("config.check_azure_connectivity", return_value=True)
    def test_health_endpoint_exists(self, mock_azure_check):
        """Health endpoint must return 200 OK"""
        if client is None:
            pytest.skip("main.py not implemented yet")
        response = client.get("/health")
        assert response.status_code == 200

    @patch("config.check_azure_connectivity", return_value=True)
    def test_health_endpoint_format(self, mock_azure_check):
        """Health endpoint must return service status"""
        if client is None:
            pytest.skip("main.py not implemented yet")
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "service" in data
        assert data["service"] == "content-processor"


class TestProcessEndpoint:
    """Test the core /process endpoint - the main business function"""

    @pytest.fixture
    def sample_reddit_data(self):
        """Sample Reddit data for testing"""
        return {
            "source": "reddit",
            "data": [
                {
                    "title": "Amazing AI breakthrough in computer vision",
                    "score": 1250,
                    "num_comments": 89,
                    "created_utc": 1692000000,
                    "subreddit": "MachineLearning",
                    "url": "https://reddit.com/r/MachineLearning/comments/test123",
                    "selftext": "Researchers have developed a new model that...",
                }
            ],
            "options": {"format": "structured"},
        }

    @patch("service_logic.ContentProcessorService")
    def test_process_endpoint_exists(self, mock_service_class, sample_reddit_data):
        """Process endpoint must exist and accept POST requests"""
        if client is None:
            pytest.skip("main.py not implemented yet")

        # Mock the service to return quickly
        mock_service = mock_service_class.return_value
        mock_service.process_collected_content = AsyncMock(
            return_value={
                "processed_items": [{"title": "Processed: Amazing AI breakthrough"}],
                "metadata": {"total_processed": 1},
            }
        )

        response = client.post("/process", json=sample_reddit_data)
        # Should not be 404 - endpoint must exist
        assert response.status_code != 404

    @patch("service_logic.ContentProcessorService")
    def test_process_valid_reddit_data(self, mock_service_class, sample_reddit_data):
        """Process endpoint must handle valid Reddit data"""
        if client is None:
            pytest.skip("main.py not implemented yet")

        # Mock the service to return realistic data fast
        mock_service = mock_service_class.return_value
        mock_service.process_collected_content = AsyncMock(
            return_value={
                "processed_items": [{"title": "Processed: Amazing AI breakthrough"}],
                "metadata": {"total_processed": 1},
            }
        )

        response = client.post("/process", json=sample_reddit_data)
        assert response.status_code == 200

        data = response.json()
        assert "processed_items" in data
        assert "metadata" in data
        assert len(data["processed_items"]) > 0

    def test_process_invalid_data_returns_422(self):
        """Process endpoint must reject invalid data"""
        if client is None:
            pytest.skip("main.py not implemented yet")
        response = client.post("/process", json={})
        assert response.status_code == 422

    def test_process_missing_source_field(self):
        """Process endpoint must require 'source' field"""
        if client is None:
            pytest.skip("main.py not implemented yet")
        invalid_data = {"data": [], "options": {}}
        response = client.post("/process", json=invalid_data)
        assert response.status_code == 422

    @patch("service_logic.ContentProcessorService")
    def test_processed_item_structure(self, mock_service_class, sample_reddit_data):
        """Processed items must have required fields"""
        if client is None:
            pytest.skip("main.py not implemented yet")

        # Mock service with realistic response structure
        mock_service = mock_service_class.return_value
        mock_service.process_collected_content = AsyncMock(
            return_value={
                "processed_items": [
                    {
                        "id": "test_post_123",
                        "title": "Processed: Amazing AI breakthrough",
                        "score": 1250,
                        "engagement_score": 0.85,
                        "content_type": "text",
                    }
                ],
                "metadata": {"total_processed": 1},
            }
        )

        response = client.post("/process", json=sample_reddit_data)
        assert response.status_code == 200

        data = response.json()
        processed_item = data["processed_items"][0]

        # Required fields for content pipeline
        assert "id" in processed_item
        assert "title" in processed_item
        assert "clean_title" in processed_item
        assert "normalized_score" in processed_item
        assert "engagement_score" in processed_item
        assert "source_url" in processed_item
        assert "published_at" in processed_item
        assert "content_type" in processed_item


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_malformed_json_returns_422(self):
        """Malformed JSON must return 422 Unprocessable Entity"""
        if client is None:
            pytest.skip("main.py not implemented yet")
        # Send malformed JSON as string
        response = client.post(
            "/process",
            content="{'invalid': json}",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    @patch("service_logic.ContentProcessorService")
    def test_large_payload_handling(self, mock_service_class):
        """Must handle reasonably large payloads"""
        if client is None:
            pytest.skip("main.py not implemented yet")

        # Mock service to handle large payload quickly
        mock_service = mock_service_class.return_value
        mock_service.process_collected_content = AsyncMock(
            return_value={
                "processed_items": [
                    {"title": f"Processed item {i}"} for i in range(100)
                ],
                "metadata": {"total_processed": 100},
            }
        )

        # Create large but reasonable payload (100 items)
        large_data = {
            "source": "reddit",
            "data": [
                {
                    "title": f"Test post {i}",
                    "score": i * 10,
                    "num_comments": i,
                    "created_utc": 1692000000 + i,
                    "subreddit": "test",
                    "url": f"https://reddit.com/test{i}",
                    "selftext": f"Content {i}",
                }
                for i in range(100)
            ],
            "options": {"format": "structured"},
        }
        response = client.post("/process", json=large_data)
        # Should handle large payload gracefully
        # 413 = Payload Too Large is acceptable
        assert response.status_code in [200, 413]

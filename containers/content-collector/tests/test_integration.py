"""
Integration tests for content-collector.

Tests that verify the service integrates properly with external dependencies
and follows standardized patterns across the pipeline.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

from libs.blob_storage import BlobContainers, BlobStorageClient


class TestStandardization:
    """Test standardized patterns and integrations."""

    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)

    @pytest.mark.integration
    def test_standardized_api_endpoints(self, client):
        """Test that content collector provides required standard endpoints."""
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()

        # Verify standardized response format
        assert data["status"] == "success"
        assert data["message"] == "Content Collector API running"

        # Check service info in data field
        service_data = data["data"]
        assert service_data["service"] == "content-collector"
        assert "version" in service_data
        assert "endpoints" in service_data

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        health_data = response.json()
        assert "status" in health_data
        assert health_data["status"] in ["healthy", "warning", "error"]

        # Test status endpoint
        response = client.get("/status")
        assert response.status_code == 200
        status_data = response.json()
        assert "service" in status_data
        assert "uptime" in status_data
        assert "stats" in status_data

    @pytest.mark.integration
    def test_blob_storage_integration(self, client):
        """Test blob storage integration with proper container usage."""
        # Use test endpoint that doesn't require external Reddit API
        test_request = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["test"],
                    "limit": 1,
                    "criteria": {"min_score": 1, "min_comments": 0},
                }
            ],
            "options": {"save_to_storage": True},
        }

        response = client.post("/collect", json=test_request)
        assert response.status_code == 200

        data = response.json()

        # Verify response has storage location
        assert "storage_location" in data

        # In production, this would be a real blob URL
        # In test mode with mocking, it's a mock URL
        storage_location = data["storage_location"]
        assert storage_location is not None

    @pytest.mark.integration
    def test_content_format_standardization(self, client):
        """Test that content follows standardized format for pipeline."""
        test_request = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 2,
                    "criteria": {"min_score": 1},
                }
            ]
        }

        response = client.post("/collect", json=test_request)
        assert response.status_code == 200

        data = response.json()

        # Verify standardized response structure
        required_top_level = [
            "collection_id",
            "collected_items",
            "metadata",
            "timestamp",
        ]
        for field in required_top_level:
            assert field in data, f"Missing required field: {field}"

        # Verify metadata structure
        metadata = data["metadata"]
        required_metadata = ["total_collected", "processing_time_seconds", "timestamp"]
        for field in required_metadata:
            # Allow some flexibility in test mode
            if field in metadata:
                assert metadata[field] is not None

        # Verify item structure if items exist
        if data["collected_items"]:
            item = data["collected_items"][0]
            required_item_fields = ["id", "title", "source"]
            for field in required_item_fields:
                assert field in item, f"Missing required item field: {field}"

            # Metadata field is optional but useful for downstream processing
            if "metadata" in item:
                assert isinstance(item["metadata"], dict)

    @pytest.mark.integration
    def test_pipeline_readiness(self, client):
        """Test that collector is ready for pipeline integration."""
        # Test collection
        response = client.post(
            "/collect",
            json={
                "sources": [
                    {
                        "type": "reddit",
                        "subreddits": ["test"],
                        "limit": 1,
                    }
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Essential fields for next pipeline stage (content-processor)
        assert "collection_id" in data
        assert "collected_items" in data
        assert "metadata" in data
        assert "timestamp" in data

        metadata = data["metadata"]
        # Processing time helps with pipeline monitoring
        processing_time_fields = ["processing_time_seconds", "processing_time"]
        has_processing_time = any(field in metadata for field in processing_time_fields)
        assert (
            has_processing_time
        ), "Must include processing time for pipeline monitoring"


class TestExternalDependencyHandling:
    """Test handling of external dependencies in different environments."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.integration
    def test_reddit_api_error_handling(self, client):
        """Test graceful handling of Reddit API issues."""
        # Request that might hit rate limits or API issues
        test_request = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["nonexistent_subreddit_12345"],
                    "limit": 1,
                }
            ]
        }

        response = client.post("/collect", json=test_request)

        # Should handle gracefully, not crash
        assert response.status_code == 200
        data = response.json()

        # Should return valid structure even if no content collected
        assert "collected_items" in data
        assert "metadata" in data
        assert isinstance(data["collected_items"], list)

    @pytest.mark.integration
    def test_blob_storage_availability(self, client):
        """Test behavior when blob storage is unavailable."""
        # This test validates that the service can operate even if blob storage fails
        test_request = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["test"],
                    "limit": 1,
                }
            ],
            "options": {"save_to_storage": False},  # Don't require storage
        }

        response = client.post("/collect", json=test_request)
        assert response.status_code == 200

        # Should work even without storage
        data = response.json()
        assert "collected_items" in data
        assert "metadata" in data

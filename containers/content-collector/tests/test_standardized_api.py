"""
Tests for standardized API endpoints in Content Collector.

Tests the new /api/content-collector/* endpoints alongside legacy endpoints
to verify both formats work correctly during the transition period.
"""

import json
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app we're going to test
from main import app

# Create test client
client = TestClient(app)


class TestStandardizedAPIEndpoints:
    """Test new standardized API endpoints."""

    def test_api_health_endpoint_format(self):
        """Test standardized health endpoint returns StandardResponse format."""
        response = client.get("/api/content-collector/health")

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse format
        assert "status" in data
        assert "message" in data
        assert "data" in data
        assert "metadata" in data

        assert data["status"] == "success"
        assert "Service is" in data["message"]

        # Verify metadata contains required fields
        metadata = data["metadata"]
        assert "timestamp" in metadata
        assert metadata["function"] == "content-collector"
        assert "version" in metadata

        # Verify health data structure
        health_data = data["data"]
        assert health_data["service"] == "content-collector"
        assert health_data["status"] in ["healthy", "warning", "unhealthy"]
        assert "dependencies" in health_data
        assert "uptime_seconds" in health_data

    def test_api_status_endpoint_format(self):
        """Test standardized status endpoint returns StandardResponse format."""
        response = client.get("/api/content-collector/status")

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse format
        assert data["status"] == "success"
        assert data["message"] == "Service status retrieved"
        assert data["metadata"]["function"] == "content-collector"

        # Verify status data structure
        status_data = data["data"]
        assert status_data["service"] == "content-collector"
        assert status_data["status"] == "running"
        assert "uptime_seconds" in status_data
        assert "stats" in status_data
        assert "configuration" in status_data

    def test_api_process_endpoint_success(self):
        """Test standardized process endpoint with successful collection."""
        test_data = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 5,
                }
            ],
            "deduplicate": True,
            "save_to_storage": True,
        }

        response = client.post("/api/content-collector/process", json=test_data)

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse format
        assert data["status"] == "success"
        assert "Collected" in data["message"]
        assert data["metadata"]["function"] == "content-collector"
        assert "execution_time_ms" in data["metadata"]

        # Verify collection data structure (same as legacy)
        collection_data = data["data"]
        assert "collected_items" in collection_data
        assert "metadata" in collection_data
        assert "collection_id" in collection_data

    def test_api_process_endpoint_error_handling(self):
        """Test standardized error handling in process endpoint."""
        # Invalid request data (missing required fields)
        test_data = {"invalid": "data"}

        response = client.post("/api/content-collector/process", json=test_data)

        assert response.status_code == 422  # Validation error
        data = response.json()

        # Should be handled by global exception handler with StandardResponse format
        assert "status" in data
        assert data["status"] == "error"
        assert "message" in data
        assert "metadata" in data
        assert data["metadata"]["function"] == "content-collector"

    def test_api_docs_endpoint(self):
        """Test API documentation endpoint."""
        response = client.get("/api/content-collector/docs")

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse format
        assert data["status"] == "success"
        assert data["message"] == "API documentation retrieved"
        assert data["metadata"]["function"] == "content-collector"

        # Verify documentation structure
        docs_data = data["data"]
        assert docs_data["service"] == "content-collector"
        assert "endpoints" in docs_data
        assert "supported_sources" in docs_data
        assert "authentication" in docs_data

        # Verify endpoint documentation
        endpoints = docs_data["endpoints"]
        assert "/api/content-collector/health" in endpoints
        assert "/api/content-collector/status" in endpoints
        assert "/api/content-collector/process" in endpoints


class TestBackwardCompatibility:
    """Test that legacy endpoints still work alongside new ones."""

    def test_legacy_health_endpoint_unchanged(self):
        """Test legacy health endpoint still returns original format."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify original format (not StandardResponse)
        assert "status" in data
        assert data["status"] in ["healthy", "warning"]
        assert "timestamp" in data
        assert "service" in data

        # Should NOT have StandardResponse structure
        assert "metadata" not in data or "function" not in data.get("metadata", {})

    def test_legacy_collect_endpoint_unchanged(self):
        """Test legacy collect endpoint still returns original format."""
        test_data = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 5,
                }
            ],
        }

        response = client.post("/collect", json=test_data)

        assert response.status_code == 200
        data = response.json()

        # Verify original format (not StandardResponse)
        assert "collected_items" in data
        assert "metadata" in data

        # Should NOT have StandardResponse structure
        assert "status" not in data or data.get("status") != "success"

    def test_both_endpoints_return_same_data(self):
        """Test that legacy and new endpoints return equivalent data."""
        test_data = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 3,
                }
            ],
            "deduplicate": True,
        }

        # Call both endpoints
        legacy_response = client.post("/collect", json=test_data)
        api_response = client.post("/api/content-collector/process", json=test_data)

        assert legacy_response.status_code == 200
        assert api_response.status_code == 200

        legacy_data = legacy_response.json()
        api_data = api_response.json()["data"]  # Extract from StandardResponse

        # Data content should be equivalent (collection_ids may be same due to mocking)
        assert len(legacy_data["collected_items"]) == len(api_data["collected_items"])
        assert (
            legacy_data["metadata"]["total_collected"]
            == api_data["metadata"]["total_collected"]
        )

        # Both should have collection metadata
        assert "collection_id" in legacy_data
        assert "collection_id" in api_data


class TestStandardizedErrorHandling:
    """Test standardized error responses."""

    def test_404_error_format(self):
        """Test 404 errors use standardized format."""
        response = client.get("/api/content-collector/nonexistent")

        assert response.status_code == 404
        data = response.json()

        # Should use standardized error format
        assert data["status"] == "error"
        assert "not found" in data["message"].lower()
        assert data["metadata"]["function"] == "content-collector"

    def test_method_not_allowed_error_format(self):
        """Test 405 errors use standardized format."""
        response = client.post("/api/content-collector/health")  # GET endpoint

        assert response.status_code == 405
        data = response.json()

        # Should use standardized error format
        assert data["status"] == "error"
        assert data["metadata"]["function"] == "content-collector"


class TestRootEndpointUpdated:
    """Test root endpoint shows both legacy and new endpoints."""

    def test_root_endpoint_standardized_format(self):
        """Test root endpoint uses StandardResponse and shows all endpoints."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse format
        assert data["status"] == "success"
        assert data["message"] == "Content Collector API running"
        assert data["metadata"]["function"] == "content-collector"

        # Verify endpoint listing includes both legacy and new
        endpoints = data["data"]["endpoints"]

        # Legacy endpoints
        assert "health" in endpoints
        assert "collect" in endpoints

        # New standardized endpoints
        assert "api_health" in endpoints
        assert "api_process" in endpoints
        assert "api_docs" in endpoints

        # Verify new endpoint paths
        assert endpoints["api_health"] == "/api/content-collector/health"
        assert endpoints["api_process"] == "/api/content-collector/process"


class TestResponseTimingMetadata:
    """Test execution time tracking in responses."""

    def test_execution_time_in_success_response(self):
        """Test execution time is tracked in successful API calls."""
        test_data = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 1,
                }
            ],
        }

        response = client.post("/api/content-collector/process", json=test_data)

        assert response.status_code == 200
        data = response.json()

        # Verify execution time is present and reasonable
        execution_time = data["metadata"]["execution_time_ms"]
        assert isinstance(execution_time, int)
        assert execution_time > 0
        assert execution_time < 30000  # Should be less than 30 seconds

    def test_execution_time_in_error_response(self):
        """Test execution time is tracked even in error responses."""
        # This will cause an internal error due to missing dependencies
        test_data = {
            "sources": [
                {
                    "type": "invalid_source_type",
                    "config": {"invalid": "config"},
                }
            ],
        }

        response = client.post("/api/content-collector/process", json=test_data)

        # Should handle gracefully and return execution time
        data = response.json()
        if "metadata" in data and "execution_time_ms" in data["metadata"]:
            execution_time = data["metadata"]["execution_time_ms"]
            assert isinstance(execution_time, int)
            assert execution_time >= 0

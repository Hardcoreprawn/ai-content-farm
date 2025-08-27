#!/usr/bin/env python3
"""
Standardized API Tests for Content Processor

Tests for the standardized API endpoints following the FastAPI-native patterns.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from main import app


class TestStandardizedAPIEndpoints:
    """Test standardized API endpoints format."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_api_health_endpoint_format(self, client):
        """Test standardized health endpoint returns proper format."""
        response = client.get("/api/content-processor/health")
        assert response.status_code == 200

        data = response.json()

        # Check StandardResponse structure
        assert "status" in data
        assert "message" in data
        assert "data" in data
        assert "errors" in data
        assert "metadata" in data

        # Check successful response
        assert data["status"] == "success"
        assert "healthy" in data["message"].lower()
        assert data["errors"] is None

        # Check service metadata
        metadata = data["metadata"]
        assert metadata["function"] == "content-processor"
        assert "timestamp" in metadata

    def test_api_status_endpoint_format(self, client):
        """Test standardized status endpoint returns proper format."""
        response = client.get("/api/content-processor/status")
        assert response.status_code == 200

        data = response.json()

        # Check StandardResponse structure
        assert "status" in data
        assert "message" in data
        assert "data" in data
        assert "errors" in data
        assert "metadata" in data

        # Check successful response
        assert data["status"] == "success"
        assert "status retrieved successfully" in data["message"].lower()
        assert data["errors"] is None

        # Check status data structure
        status_data = data["data"]
        assert status_data["service"] == "content-processor"
        assert "stats" in status_data
        assert "pipeline" in status_data

    def test_api_process_endpoint_success(self, client):
        """Test standardized process endpoint with valid request."""
        request_data = {
            "items": [
                {
                    "title": "Test Reddit Post",
                    "score": 100,
                    "num_comments": 25,
                    "created_utc": 1640995200,
                    "subreddit": "test",
                    "url": "https://reddit.com/r/test/comments/abc123",
                    "selftext": "This is a test post content",
                    "id": "abc123",
                }
            ],
            "source": "reddit",
        }

        response = client.post("/api/content-processor/process", json=request_data)
        assert response.status_code == 200

        data = response.json()

        # Check StandardResponse structure
        assert "status" in data
        assert "message" in data
        assert "data" in data
        assert "errors" in data
        assert "metadata" in data

        # Check successful response
        assert data["status"] == "success"
        assert "Successfully processed" in data["message"]
        assert data["errors"] is None

        # Check processing data
        processing_data = data["data"]
        assert "processed_items" in processing_data
        assert "metadata" in processing_data

        # Verify processing metadata
        proc_metadata = processing_data["metadata"]
        assert proc_metadata["source"] == "reddit"
        assert proc_metadata["items_received"] == 1

    def test_api_process_endpoint_legacy_format(self, client):
        """Test standardized process endpoint with legacy request format."""
        request_data = {
            "data": [
                {
                    "title": "Test Reddit Post",
                    "score": 100,
                    "num_comments": 25,
                    "created_utc": 1640995200,
                    "subreddit": "test",
                    "url": "https://reddit.com/r/test/comments/abc123",
                    "selftext": "This is a test post content",
                    "id": "abc123",
                }
            ],
            "source": "reddit",
        }

        response = client.post("/api/content-processor/process", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert "Successfully processed" in data["message"]

    def test_api_process_endpoint_error_handling(self, client):
        """Test standardized process endpoint error handling."""
        # Test with empty items
        invalid_request = {"items": [], "source": "reddit"}

        response = client.post("/api/content-processor/process", json=invalid_request)
        assert (
            response.status_code == 200
        )  # FastAPI-native returns 200 with error status

        data = response.json()
        assert data["status"] == "error"
        assert "No items provided" in data["message"]

        # Test with malformed request
        malformed_request = {
            # Missing both items and data
            "source": "reddit"
        }

        response = client.post("/api/content-processor/process", json=malformed_request)
        assert response.status_code == 422  # Validation error

    def test_api_docs_endpoint(self, client):
        """Test standardized docs endpoint."""
        response = client.get("/api/content-processor/docs")
        assert response.status_code == 200

        data = response.json()

        # Check StandardResponse structure
        assert "status" in data
        assert "message" in data
        assert "data" in data
        assert "errors" in data
        assert "metadata" in data

        # Check successful response
        assert data["status"] == "success"
        assert "documentation retrieved successfully" in data["message"].lower()
        assert data["errors"] is None

        # Check docs data structure
        docs_data = data["data"]
        assert docs_data["service"] == "content-processor"
        assert "endpoints" in docs_data
        assert "legacy_endpoints" in docs_data

        # Verify standardized endpoints are documented
        endpoints = docs_data["endpoints"]
        assert "health" in endpoints
        assert "status" in endpoints
        assert "process" in endpoints
        assert "docs" in endpoints


class TestBackwardCompatibility:
    """Test that legacy endpoints remain unchanged."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_legacy_health_endpoint_unchanged(self, client):
        """Test that legacy health endpoint still works."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        # Legacy format should still work
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]
        assert "service" in data

    def test_legacy_process_endpoint_unchanged(self, client):
        """Test that legacy process endpoint still works."""
        request_data = {
            "items": [
                {
                    "title": "Test Reddit Post",
                    "score": 100,
                    "num_comments": 25,
                    "created_utc": 1640995200,
                    "subreddit": "test",
                    "url": "https://reddit.com/r/test/comments/abc123",
                    "selftext": "This is a test post content",
                    "id": "abc123",
                }
            ],
            "source": "reddit",
        }

        response = client.post("/process", json=request_data)
        assert response.status_code == 200

        data = response.json()
        # Legacy format should work
        assert "processed_items" in data
        assert "metadata" in data

    def test_legacy_root_endpoint_unchanged(self, client):
        """Test that legacy root endpoint still works."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "service" in data
        assert data["service"] == "content-processor"
        assert "endpoints" in data


class TestStandardizedErrorHandling:
    """Test standardized error response formats."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_404_error_format(self, client):
        """Test 404 errors return proper format."""
        response = client.get("/api/content-processor/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed_error_format(self, client):
        """Test method not allowed errors."""
        response = client.post("/api/content-processor/health")
        assert response.status_code == 405

    def test_validation_error_format(self, client):
        """Test validation errors return proper format."""
        # Send invalid JSON structure
        response = client.post(
            "/api/content-processor/process", json={"invalid": "structure"}
        )
        assert response.status_code == 422


class TestResponseMetadata:
    """Test that response metadata is included."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_metadata_in_success_response(self, client):
        """Test metadata is included in successful responses."""
        response = client.get("/api/content-processor/health")
        assert response.status_code == 200

        data = response.json()
        metadata = data["metadata"]
        assert "timestamp" in metadata
        assert "function" in metadata
        assert metadata["function"] == "content-processor"

    def test_metadata_in_error_response(self, client):
        """Test metadata is included in error responses."""
        invalid_request = {"items": [], "source": "reddit"}

        response = client.post("/api/content-processor/process", json=invalid_request)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "error"
        metadata = data["metadata"]
        assert "timestamp" in metadata
        assert "function" in metadata

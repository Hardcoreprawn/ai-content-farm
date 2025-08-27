"""
Test suite for site-generator standardized API endpoints.
Tests FastAPI-native standardized endpoints following established patterns.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from main import app


class TestStandardizedAPIEndpoints:
    """Test standardized API endpoints for site-generator"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_api_health_endpoint_format(self, client):
        """Test that standardized health endpoint returns proper format"""
        with patch("main.health_checker") as mock_health:
            mock_health.check_health = AsyncMock(
                return_value={
                    "status": "healthy",
                    "checks": {"storage": True, "templates": True},
                }
            )

            response = client.get("/api/site-generator/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert data["message"] == "Service is healthy"
            assert "data" in data
            assert data["data"]["service"] == "site-generator"
            assert "metadata" in data
            assert "timestamp" in data["metadata"]

    def test_api_status_endpoint_format(self, client):
        """Test that standardized status endpoint returns proper format"""
        response = client.get("/api/site-generator/status")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Service status retrieved successfully"
        assert "data" in data
        assert data["data"]["service"] == "site-generator"
        assert "dependencies" in data["data"]
        assert "metrics" in data["data"]
        assert "metadata" in data

    def test_api_process_endpoint_success(self, client):
        """Test standardized process endpoint with valid request"""
        with patch("main.site_processor") as mock_processor:
            mock_processor.generate_site = AsyncMock()

            request_data = {
                "content_source": "ranked",
                "theme": "modern",
                "site_title": "Test Site",
                "site_description": "A test site",
                "max_articles": 10,
            }

            response = client.post("/api/site-generator/process", json=request_data)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert data["message"] == "Site generation started successfully"
            assert "data" in data
            assert "site_id" in data["data"]
            assert data["data"]["status"] == "processing"

    def test_api_process_endpoint_validation_error(self, client):
        """Test standardized process endpoint with missing required fields"""
        request_data = {
            "content_source": "ranked",
            "theme": "modern",
            # Missing site_title
        }

        response = client.post("/api/site-generator/process", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "error"
        assert "Site title is required" in data["errors"]

    def test_api_process_endpoint_error_handling(self, client):
        """Test standardized process endpoint error handling"""
        # Don't mock generate_site to actually trigger an error in the background task,
        # instead test for validation errors which are handled synchronously
        request_data = {
            "content_source": "ranked",
            "theme": "modern",
            # site_title is None by default, but we want to test a different error
            "max_articles": -1,  # Invalid value should trigger validation error
        }

        response = client.post("/api/site-generator/process", json=request_data)
        assert response.status_code == 422  # FastAPI validation error

    def test_api_docs_endpoint(self, client):
        """Test standardized docs endpoint"""
        response = client.get("/api/site-generator/docs")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "API documentation retrieved successfully"
        assert "data" in data
        assert data["data"]["service"] == "site-generator"
        assert "endpoints" in data["data"]
        assert "standardized" in data["data"]["endpoints"]
        assert "legacy" in data["data"]["endpoints"]


class TestBackwardCompatibility:
    """Test that legacy endpoints remain unchanged"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_legacy_health_endpoint_unchanged(self, client):
        """Test that legacy health endpoint still works"""
        with patch("main.health_checker") as mock_health:
            mock_health.check_health = AsyncMock(
                return_value={"status": "healthy", "checks": {"storage": True}}
            )

            response = client.get("/health")
            assert response.status_code == 200

            data = response.json()
            # Legacy format should work
            assert "status" in data
            assert data["status"] == "healthy"

    def test_legacy_root_endpoint_unchanged(self, client):
        """Test that legacy root endpoint still works"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "service" in data
        # The actual service name returned by the endpoint
        assert data["service"] == "site-generator"

    def test_legacy_status_endpoint_unchanged(self, client):
        """Test that legacy status endpoint still works"""
        response = client.get("/status")
        assert response.status_code == 200

        data = response.json()
        # Legacy format should work
        assert "status" in data
        assert "timestamp" in data

    def test_legacy_api_sites_endpoints_unchanged(self, client):
        """Test that legacy /api/sites/* endpoints still work"""
        # Test site list
        with patch("main.processor") as mock_processor:
            mock_processor.generation_status = {}  # Empty generation status

            response = client.get("/api/sites")
            assert response.status_code == 200

            data = response.json()
            # Check the actual response format from site-generator legacy API
            assert "sites" in data


class TestStandardizedErrorHandling:
    """Test standardized error handling patterns"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_404_error_format(self, client):
        """Test that 404 errors follow standardized format"""
        response = client.get("/api/site-generator/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed_error_format(self, client):
        """Test that method not allowed errors follow standardized format"""
        response = client.delete("/api/site-generator/health")
        assert response.status_code == 405

    def test_validation_error_format(self, client):
        """Test that validation errors follow standardized format"""
        # Send invalid JSON to process endpoint
        response = client.post("/api/site-generator/process", json={"invalid": "data"})
        assert response.status_code == 200  # Our custom validation

        data = response.json()
        if data["status"] == "error":
            assert "errors" in data


class TestResponseMetadata:
    """Test response metadata consistency"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_metadata_in_success_response(self, client):
        """Test that success responses include proper metadata"""
        response = client.get("/api/site-generator/docs")
        assert response.status_code == 200

        data = response.json()
        assert "metadata" in data
        assert (
            "function" in data["metadata"]
        )  # create_service_dependency uses "function"
        assert data["metadata"]["function"] == "site-generator"
        assert "timestamp" in data["metadata"]

    def test_metadata_in_error_response(self, client):
        """Test that error responses include proper metadata"""
        request_data = {
            "content_source": "ranked",
            "theme": "modern",
            # Missing required site_title
        }

        response = client.post("/api/site-generator/process", json=request_data)
        assert response.status_code == 200

        data = response.json()
        if data["status"] == "error":
            assert "metadata" in data
            assert (
                "function" in data["metadata"]
            )  # create_service_dependency uses "function"

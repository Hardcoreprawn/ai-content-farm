"""
API Compliance Tests for Content Collector

Tests FastAPI compliance using the shared standard test library.
These tests should be consistent across all services.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

from libs.standard_tests import StandardAPITestSuite


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_suite(client):
    """Create standard API test suite."""
    return StandardAPITestSuite(client, "content-womble")


@pytest.mark.unit
class TestStandardAPICompliance:
    """Standard API compliance tests using shared library."""

    def test_openapi_spec_compliance(self, test_suite):
        """Test OpenAPI 3.x specification compliance."""
        result = test_suite.test_openapi_spec_compliance()
        assert result is not None

    def test_swagger_ui_documentation(self, test_suite):
        """Test Swagger UI documentation availability."""
        test_suite.test_swagger_ui_documentation()

    def test_redoc_documentation(self, test_suite):
        """Test ReDoc documentation availability."""
        test_suite.test_redoc_documentation()

    def test_health_endpoint_standard_format(self, test_suite):
        """Test health endpoint follows standard format."""
        test_suite.test_health_endpoint_standard_format()

    def test_status_endpoint_standard_format(self, test_suite):
        """Test status endpoint follows standard format."""
        test_suite.test_status_endpoint_standard_format()

    def test_root_endpoint_standard_format(self, test_suite):
        """Test root endpoint follows standard format."""
        test_suite.test_root_endpoint_standard_format()

    def test_404_error_format(self, test_suite):
        """Test 404 errors follow standard format."""
        test_suite.test_404_error_format()

    def test_method_not_allowed_error_format(self, test_suite):
        """Test 405 errors follow standard format."""
        test_suite.test_method_not_allowed_error_format()

    def test_response_timing_metadata(self, test_suite):
        """Test response timing metadata is included."""
        test_suite.test_response_timing_metadata()


@pytest.mark.unit
class TestStandardizedAPIEndpoints:
    """Test standardized API endpoints."""

    def test_health_endpoint_format(self, client):
        """Test health endpoint response format."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "message" in data
        assert "metadata" in data

    def test_status_endpoint_format(self, client):
        """Test status endpoint response format."""
        response = client.get("/status")
        assert response.status_code in [200, 503]  # May be unhealthy in test

        data = response.json()
        assert "status" in data
        assert "message" in data
        assert "metadata" in data

    def test_collections_endpoint_success(self, client):
        """Test collections endpoint with valid request."""
        request_data = {
            "sources": [{"type": "reddit", "subreddits": ["test"], "limit": 1}],
            "deduplicate": True,
            "save_to_storage": False,
        }

        response = client.post("/collections", json=request_data)
        # May return error due to missing credentials, but should have proper format
        assert response.status_code in [200, 500]

        data = response.json()
        assert "status" in data
        assert "message" in data
        assert "metadata" in data

    def test_collections_endpoint_error_handling(self, client):
        """Test collections endpoint error handling."""
        # Invalid request - missing required fields
        response = client.post("/collections", json={})
        assert response.status_code == 422

        data = response.json()
        assert "status" in data
        assert data["status"] == "error"
        assert "errors" in data

    def test_openapi_spec_endpoint(self, client):
        """Test OpenAPI specification endpoint."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        spec = response.json()
        assert "openapi" in spec
        assert spec["openapi"].startswith("3.")
        assert spec["info"]["title"] == "Content Womble API"

    def test_swagger_ui_docs_endpoint(self, client):
        """Test Swagger UI documentation endpoint."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "swagger" in response.text.lower()

    def test_redoc_docs_endpoint(self, client):
        """Test ReDoc documentation endpoint."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "redoc" in response.text.lower()


@pytest.mark.unit
class TestStandardizedErrorHandling:
    """Test standardized error handling."""

    def test_404_error_format(self, client):
        """Test 404 error response format."""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

        data = response.json()
        assert data["status"] == "error"
        assert "available_endpoints" in data["data"]
        assert "documentation" in data["data"]

    def test_method_not_allowed_error_format(self, client):
        """Test 405 error response format."""
        response = client.post("/health")  # Health only accepts GET
        assert response.status_code == 405

        data = response.json()
        assert data["status"] == "error"
        assert "requested_method" in data["data"]


@pytest.mark.unit
class TestRootEndpointUpdated:
    """Test root endpoint standardized format."""

    def test_root_endpoint_standardized_format(self, client):
        """Test root endpoint follows standardized response format."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert "service" in data["data"]
        assert data["data"]["service"] == "content-womble"


@pytest.mark.unit
class TestResponseTimingMetadata:
    """Test response timing metadata."""

    def test_execution_time_in_success_response(self, client):
        """Test execution time is included in success responses."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "metadata" in data
        assert "execution_time_ms" in data["metadata"]
        assert isinstance(data["metadata"]["execution_time_ms"], (int, float))

    def test_execution_time_in_error_response(self, client):
        """Test execution time is included in error responses."""
        response = client.get("/nonexistent")
        assert response.status_code == 404

        data = response.json()
        assert "metadata" in data
        assert "execution_time_ms" in data["metadata"]
        assert isinstance(data["metadata"]["execution_time_ms"], (int, float))

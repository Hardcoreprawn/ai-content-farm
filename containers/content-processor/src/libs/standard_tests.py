"""
Standard Test Utilities for FastAPI Services

Provides reusable test patterns and assertions for FastAPI applications
following OpenAPI 3.0 standards and content platform conventions.
"""

from typing import Any, Dict, List, Optional, Union

import pytest
from fastapi.testclient import TestClient

from .shared_models import StandardResponse


class StandardAPITestSuite:
    """
    Reusable test suite for standard FastAPI endpoints.

    This class provides common test patterns that should be consistent
    across all services in the content platform.
    """

    def __init__(self, client: TestClient, service_name: str):
        """
        Initialize the test suite.

        Args:
            client: FastAPI TestClient instance
            service_name: Name of the service being tested
        """
        self.client = client
        self.service_name = service_name

    def test_openapi_spec_compliance(self) -> Dict[str, Any]:
        """Test OpenAPI 3.x specification endpoint compliance."""
        response = self.client.get("/openapi.json")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        spec = response.json()

        # Verify OpenAPI 3.x specification structure
        assert "openapi" in spec
        assert spec["openapi"].startswith("3.")
        assert "info" in spec
        assert "paths" in spec

        # Verify service information
        info = spec["info"]
        assert "title" in info
        assert "description" in info
        assert "version" in info

        return spec

    def test_swagger_ui_documentation(self) -> None:
        """Test Swagger UI documentation endpoint."""
        response = self.client.get("/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Verify it's actually the Swagger UI HTML page
        html_content = response.text
        assert "swagger-ui" in html_content.lower()
        assert any(
            tag in html_content.lower()
            for tag in ["<!doctype html>", "<!DOCTYPE html>"]
        )

    def test_redoc_documentation(self) -> None:
        """Test ReDoc documentation endpoint."""
        response = self.client.get("/redoc")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Verify it's actually the ReDoc HTML page
        html_content = response.text
        assert "redoc" in html_content.lower()
        assert any(
            tag in html_content.lower()
            for tag in ["<!doctype html>", "<!DOCTYPE html>"]
        )

    def test_health_endpoint_standard_format(self) -> None:
        """Test health endpoint follows StandardResponse format."""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse structure
        self._assert_standard_response_format(data)
        assert data["status"] in ["success", "error"]  # Health can report errors

        # Message should mention health
        assert "health" in data["message"].lower()

        # Verify health-specific data structure (when available)
        health_data = data["data"]
        if health_data:  # Data might be empty on error
            # Status field is common in health checks
            if "status" in health_data:
                assert health_data["status"] in ["healthy", "unhealthy", "degraded"]

    def test_status_endpoint_standard_format(self) -> None:
        """Test status endpoint follows StandardResponse format."""
        response = self.client.get("/status")

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse structure
        self._assert_standard_response_format(data)
        assert data["status"] in ["success", "error"]

        # Verify status-specific data structure (when available)
        status_data = data["data"]
        if status_data:  # Data might be empty on error
            # Service field is common in status checks
            if "service" in status_data:
                assert isinstance(status_data["service"], str)

    def test_root_endpoint_standard_format(self) -> None:
        """Test root endpoint follows StandardResponse format."""
        response = self.client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse structure
        self._assert_standard_response_format(data)
        assert data["status"] == "success"

    def test_404_error_format(self) -> None:
        """Test 404 errors follow StandardResponse format."""
        response = self.client.get("/nonexistent-endpoint")

        assert response.status_code == 404
        data = response.json()

        # Verify StandardResponse structure for errors
        self._assert_standard_response_format(data)
        assert data["status"] == "error"
        assert "404" in data["message"] or "not found" in data["message"].lower()

    def test_method_not_allowed_error_format(self) -> None:
        """Test 405 Method Not Allowed errors follow StandardResponse format."""
        # Try POST on an endpoint that only accepts GET
        response = self.client.post("/health")

        assert response.status_code == 405
        data = response.json()

        # Verify StandardResponse structure for errors
        self._assert_standard_response_format(data)
        assert data["status"] == "error"
        assert (
            "405" in data["message"] or "method not allowed" in data["message"].lower()
        )

    def test_response_timing_metadata(self) -> None:
        """Test that responses include execution timing metadata."""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify timing metadata exists
        metadata = data.get("metadata", {})
        assert "execution_time_ms" in metadata
        assert isinstance(metadata["execution_time_ms"], (int, float))
        assert metadata["execution_time_ms"] >= 0

    def verify_required_endpoints_documented(
        self, required_endpoints: List[str]
    ) -> None:
        """
        Verify that all required endpoints are documented in OpenAPI spec.

        Args:
            required_endpoints: List of endpoint paths that must be documented
        """
        spec = self.test_openapi_spec_compliance()
        paths = spec["paths"]

        for endpoint in required_endpoints:
            assert (
                endpoint in paths
            ), f"Required endpoint {endpoint} not documented in OpenAPI spec"

    def _assert_standard_response_format(self, data: Dict[str, Any]) -> None:
        """Assert that response follows StandardResponse format."""
        # Required fields
        assert "status" in data
        assert "message" in data
        assert "data" in data
        assert "errors" in data
        assert "metadata" in data

        # Type validation
        assert data["status"] in ["success", "error"]
        assert isinstance(data["message"], str)
        # Errors can be null or a list
        assert data["errors"] is None or isinstance(data["errors"], list)
        assert isinstance(data["metadata"], dict)

        # Metadata should contain function name
        assert "function" in data["metadata"]


def create_standard_test_class(
    service_name: str, required_endpoints: Optional[List[str]] = None
):
    """
    Factory function to create a standard test class for a service.

    Args:
        service_name: Name of the service
        required_endpoints: List of endpoints that must be documented in OpenAPI spec

    Returns:
        A test class with all standard tests
    """

    class TestStandardAPI:
        """Standard API compliance tests."""

        @classmethod
        def setup_class(cls, client: TestClient):
            """Setup the test suite with a TestClient."""
            cls.test_suite = StandardAPITestSuite(client, service_name)

        def test_openapi_spec_compliance(self):
            """Test OpenAPI specification compliance."""
            self.test_suite.test_openapi_spec_compliance()

        def test_swagger_ui_documentation(self):
            """Test Swagger UI documentation."""
            self.test_suite.test_swagger_ui_documentation()

        def test_redoc_documentation(self):
            """Test ReDoc documentation."""
            self.test_suite.test_redoc_documentation()

        def test_health_endpoint_format(self):
            """Test health endpoint format."""
            self.test_suite.test_health_endpoint_standard_format()

        def test_status_endpoint_format(self):
            """Test status endpoint format."""
            self.test_suite.test_status_endpoint_standard_format()

        def test_root_endpoint_format(self):
            """Test root endpoint format."""
            self.test_suite.test_root_endpoint_standard_format()

        def test_404_error_format(self):
            """Test 404 error format."""
            self.test_suite.test_404_error_format()

        def test_method_not_allowed_error_format(self):
            """Test 405 error format."""
            self.test_suite.test_method_not_allowed_error_format()

        def test_response_timing_metadata(self):
            """Test response timing metadata."""
            self.test_suite.test_response_timing_metadata()

        def test_required_endpoints_documented(self):
            """Test required endpoints are documented."""
            if required_endpoints:
                self.test_suite.verify_required_endpoints_documented(required_endpoints)

    return TestStandardAPI


# Convenience functions for common test patterns
def assert_standard_response(
    data: Dict[str, Any], expected_status: str = "success"
) -> None:
    """Assert that a response follows StandardResponse format."""
    # Inline assertion to avoid creating test suite without client
    # Required fields
    assert "status" in data
    assert "message" in data
    assert "data" in data
    assert "errors" in data
    assert "metadata" in data

    # Type validation
    assert data["status"] in ["success", "error"]
    assert isinstance(data["message"], str)
    assert data["errors"] is None or isinstance(data["errors"], list)
    assert isinstance(data["metadata"], dict)

    # Metadata should contain function name
    assert "function" in data["metadata"]

    # Check expected status
    assert data["status"] == expected_status


def assert_openapi_compliance(
    client: TestClient, required_endpoints: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Assert OpenAPI compliance and return the spec.

    Args:
        client: FastAPI TestClient
        required_endpoints: List of endpoints that must be documented

    Returns:
        The OpenAPI specification dictionary
    """
    test_suite = StandardAPITestSuite(client, "")
    spec = test_suite.test_openapi_spec_compliance()

    if required_endpoints:
        test_suite.verify_required_endpoints_documented(required_endpoints)

    return spec

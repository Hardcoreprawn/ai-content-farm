"""
DEPRECATED: Standardized API Tests for Content Collector

This file has been refactored into smaller, focused test files:
- test_api_compliance.py: Standard FastAPI compliance tests
- test_reddit_client.py: Reddit client functionality and security
- test_source_collectors.py: Source collector factory tests
- test_discovery.py: Discovery engine and analysis tests
- test_models.py: Data model validation tests

This file remains temporarily for backward compatibility and will be removed
once all tests are verified to work in their new locations.
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


# Keep just the core standardized tests that use the shared library
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

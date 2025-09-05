"""
Standardized API Tests for Site Generator

Tests the site generator API endpoints for compliance with standardized formats
and response structures used across all containers.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from libs.standard_tests import StandardAPITestSuite

# Add the containers path and libs path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "libs"))

# Import the shared test suite

# Mock dependencies before importing main
with patch("site_generator.BlobStorageClient"), patch(
    "main.SiteGenerator"
) as mock_site_gen_class:
    mock_site_gen_instance = AsyncMock()
    mock_site_gen_instance.generator_id = "test_generator_123"
    mock_site_gen_instance.check_blob_connectivity.return_value = True
    mock_site_gen_class.return_value = mock_site_gen_instance
    from main import app


class TestStandardAPICompliance:
    """Test site generator API compliance with standard format."""

    @pytest.fixture
    def test_suite(self):
        """Create standardized test suite."""
        client = TestClient(app)
        return StandardAPITestSuite(client, "site-generator")

    def test_openapi_spec_compliance(self, test_suite):
        """Test OpenAPI specification compliance."""
        test_suite.test_openapi_spec_compliance()

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
        """Test 404 error responses follow standard format."""
        test_suite.test_404_error_format()

    def test_method_not_allowed_error_format(self, test_suite):
        """Test 405 error responses follow standard format."""
        test_suite.test_method_not_allowed_error_format()

    def test_response_timing_metadata(self, test_suite):
        """Test response timing metadata is included."""
        test_suite.test_response_timing_metadata()

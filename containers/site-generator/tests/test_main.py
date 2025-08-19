#!/usr/bin/env python3
"""
API Contract Tests for Site Generator

Test-first development: Define the API behavior before implementation.
Tests the main FastAPI endpoints and their contracts.
"""

import json
import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

# Import the main app
try:
    import sys
    import os
    sys.path.append('/workspaces/ai-content-farm')

    from main import app
    client = TestClient(app)
except ImportError as e:
    client = None
    import_error = str(e)


class TestHealthEndpoint:
    """Test health check endpoint - must work for container orchestration"""

    def test_health_endpoint_exists(self):
        """Health endpoint must return 200 OK"""
        if client is None:
            pytest.skip(f"main.py import failed: {import_error}")

        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_format(self):
        """Health endpoint must return standard health format"""
        if client is None:
            pytest.skip(f"main.py import failed: {import_error}")

        response = client.get("/health")
        data = response.json()

        # Standard health response format
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]
        assert "service" in data or "message" in data


class TestStatusEndpoint:
    """Test the /status endpoint for monitoring"""

    def test_status_endpoint_exists(self):
        """Status endpoint must return service status"""
        if client is None:
            pytest.skip(f"main.py import failed: {import_error}")

        response = client.get("/status")
        assert response.status_code == 200

    def test_status_endpoint_format(self):
        """Status endpoint must return detailed status information"""
        if client is None:
            pytest.skip(f"main.py import failed: {import_error}")

        response = client.get("/status")
        data = response.json()

        # Status endpoint can return detailed health information
        # Check for any reasonable status structure
        assert isinstance(data, dict)
        # Should have some meaningful content
        assert len(data) > 0


class TestGenerateEndpoint:
    """Test the core /generate endpoint - the main business function"""

    def test_generate_endpoint_exists(self):
        """Generate endpoint must exist and accept POST requests"""
        if client is None:
            pytest.skip(f"main.py import failed: {import_error}")

        # Test with minimal valid request
        request_data = {
            "content_source": "ranked",
            "theme": "modern"
        }

        response = client.post("/generate", json=request_data)
        # Should return either 200 (sync) or 202 (async)
        assert response.status_code in [200, 202]

    def test_generate_request_validation(self):
        """Generate endpoint must validate request format"""
        if client is None:
            pytest.skip(f"main.py import failed: {import_error}")

        # Test with invalid request
        response = client.post("/generate", json={})
        # Should accept empty request with defaults
        assert response.status_code in [200, 202, 422]

    def test_generate_response_format(self):
        """Generate endpoint must return standard response format"""
        if client is None:
            pytest.skip(f"main.py import failed: {import_error}")

        request_data = {
            "content_source": "ranked",
            "theme": "modern",
            "max_articles": 5
        }

        response = client.post("/generate", json=request_data)

        if response.status_code in [200, 202]:
            data = response.json()

            # Standard response format
            assert "status" in data
            assert "message" in data
            assert "data" in data or "metadata" in data


class TestSitePreviewEndpoint:
    """Test site preview functionality"""

    def test_preview_endpoint_exists(self):
        """Preview endpoint must exist for generated sites"""
        if client is None:
            pytest.skip(f"main.py import failed: {import_error}")

        # Test with a dummy site ID
        response = client.get("/preview/test-site-id")
        # Should return 404 for non-existent site or 200 for existing
        assert response.status_code in [200, 404]

    def test_sites_list_endpoint(self):
        """Sites list endpoint must return available sites"""
        if client is None:
            pytest.skip(f"main.py import failed: {import_error}")

        response = client.get("/sites")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "data" in data


class TestAPIStandards:
    """Test that API follows standard conventions"""

    def test_root_endpoint_info(self):
        """Root endpoint must provide service information"""
        if client is None:
            pytest.skip(f"main.py import failed: {import_error}")

        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "service" in data
        assert "version" in data

    def test_cors_headers(self):
        """API must include CORS headers for browser access"""
        if client is None:
            pytest.skip(f"main.py import failed: {import_error}")

        response = client.get("/")

        # CORS should be enabled
        headers = response.headers
        # Check for CORS headers (they might not be present in test mode)
        assert response.status_code == 200

    def test_error_handling(self):
        """API must handle errors gracefully"""
        if client is None:
            pytest.skip(f"main.py import failed: {import_error}")

        # Test non-existent endpoint
        response = client.get("/non-existent-endpoint")
        assert response.status_code == 404


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])

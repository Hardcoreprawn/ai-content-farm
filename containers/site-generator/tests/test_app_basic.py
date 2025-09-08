"""
Basic application tests

Tests FastAPI application setup and health checks.
Focused on core application functionality.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add the containers path to import the main module
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

# Mock dependencies before importing main
with patch("site_generator.BlobStorageClient"), patch(
    "main.SiteGenerator"
) as mock_site_gen_class:
    mock_site_gen_instance = AsyncMock()
    mock_site_gen_instance.generator_id = "test_generator_123"
    mock_site_gen_class.return_value = mock_site_gen_instance
    from main import app


class TestFastAPIApp:
    """Test FastAPI application setup and basic functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_app_initialization(self):
        """Test that app is properly initialized."""
        assert app.title == "AI Content Farm - Site Generator"
        assert app.version == "1.0.0"
        assert app.description == "Python-based JAMStack static site generator"

    def test_health_endpoint_success(self, client):
        """Test health endpoint returns success."""
        with patch("main.get_site_generator") as mock_get_gen:
            # Mock the site generator instance
            mock_gen = MagicMock()
            mock_get_gen.return_value = mock_gen

            # Mock the async method to return a successful connectivity check
            mock_gen.check_blob_connectivity.return_value = asyncio.Future()
            mock_gen.check_blob_connectivity.return_value.set_result(
                {
                    "status": "healthy",
                    "connection_type": "mock",
                    "message": "Mock storage client is working",
                }
            )

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            # Check the standard response format
            assert data["status"] == "success"  # Top-level status
            assert data["data"]["status"] == "healthy"  # Health status in data
            assert data["data"]["service"] == "site-generator"
            assert "version" in data["data"]
            assert "timestamp" in data["metadata"]

    def test_health_endpoint_failure(self, client):
        """Test health endpoint with service failure."""
        with patch("main.get_site_generator") as mock_get_gen:
            # Mock the site generator instance
            mock_gen = MagicMock()
            mock_get_gen.return_value = mock_gen

            # Mock the async method to return unhealthy status
            mock_gen.check_blob_connectivity.return_value = {
                "status": "error",
                "message": "Connection failed",
            }

            response = client.get("/health")

            # Standard health endpoint always returns 200 with health info
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"  # Top-level status is always success
            # Check that the health data shows the dependency is unhealthy
            assert "dependencies" in data["data"]
            assert "blob_storage" in data["data"]["dependencies"]
            # The dependency should be marked as false/unhealthy
            assert data["data"]["dependencies"]["blob_storage"] is False

    def test_docs_endpoint(self, client):
        """Test that docs endpoint is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_endpoint(self, client):
        """Test that OpenAPI schema is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data

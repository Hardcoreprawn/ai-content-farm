"""
Basic application tests

Tests FastAPI application setup and health checks.
Focused on core application functionality.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

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
        with patch("main.site_generator") as mock_gen:
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
        with patch("main.site_generator") as mock_gen:
            # Mock the async method to raise an exception
            mock_gen.check_blob_connectivity.side_effect = Exception(
                "Connection failed"
            )

            response = client.get("/health")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "error"
            # Check the standard response format
            assert "unavailable" in data["message"]
            assert "errors" in data
            assert data["errors"] is not None

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

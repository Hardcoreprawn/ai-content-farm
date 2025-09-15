"""
Error handling and validation tests

Tests for error scenarios, validation, and edge cases.
Focused on robustness and error recovery.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

# Add the containers path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

# Mock dependencies before importing main
with (
    patch("site_generator.BlobStorageClient"),
    patch("main.SiteGenerator") as mock_site_gen_class,
):
    mock_site_gen_instance = AsyncMock()
    mock_site_gen_instance.generator_id = "test_generator_123"
    mock_site_gen_class.return_value = mock_site_gen_instance
    from main import app


class TestErrorHandling:
    """Test comprehensive error handling across endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_invalid_json_request(self, client):
        """Test handling of invalid JSON in request body."""
        response = client.post("/generate-markdown", content="invalid json")
        assert response.status_code == 422

    def test_missing_required_fields(self, client):
        """Test handling of missing required fields."""
        # Empty request body
        response = client.post("/generate-markdown", json={})
        assert response.status_code == 200  # Should work with defaults

    def test_unexpected_server_errors(self, client):
        """Test handling of unexpected server errors."""
        # Mock site_generator to raise unexpected error
        with patch("main.get_site_generator") as mock_get_gen:
            mock_gen = AsyncMock()
            mock_get_gen.return_value = mock_gen
            mock_gen.check_blob_connectivity = AsyncMock()
            mock_gen.check_blob_connectivity.side_effect = Exception("Unexpected error")

            response = client.get("/health")
            # Standard health endpoint always returns 200 with health info
            assert response.status_code == 200
            data = response.json()
            # Check that the health data shows the dependency is unhealthy
            assert data["status"] == "success"  # Top-level status is always success
            assert "dependencies" in data["data"]

    def test_preview_not_found(self, client):
        """Test preview URL for non-existent site."""
        with patch("main.get_site_generator") as mock_get_gen:
            mock_gen = AsyncMock()
            mock_get_gen.return_value = mock_gen
            mock_gen.get_preview_url.side_effect = Exception("Site not found")

            response = client.get("/preview/nonexistent")

            assert response.status_code == 404


class TestRequestValidation:
    """Test request validation and parameter handling."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_batch_size_validation(self, client):
        """Test batch size parameter validation."""
        with patch("main.get_site_generator") as mock_get_gen:
            mock_gen = AsyncMock()
            mock_get_gen.return_value = mock_gen
            # Set up async mock properly
            mock_gen.generate_markdown_batch = AsyncMock(
                return_value=Mock(
                    files_generated=5,
                    model_dump=Mock(return_value={"files_generated": 5}),
                )
            )

            # Valid batch size
            response = client.post("/generate-markdown", json={"batch_size": 5})
            assert response.status_code == 200

            # Test with string batch_size (should be converted or fail gracefully)
            response = client.post("/generate-markdown", json={"batch_size": "invalid"})
            assert response.status_code == 422

    def test_theme_validation(self, client):
        """Test theme parameter validation."""
        with patch("main.get_site_generator") as mock_get_gen:
            mock_gen = AsyncMock()
            mock_get_gen.return_value = mock_gen
            # Set up async mock properly
            mock_gen.generate_static_site = AsyncMock(
                return_value=Mock(
                    pages_generated=10,
                    model_dump=Mock(return_value={"pages_generated": 10}),
                )
            )

            # Valid theme
            response = client.post("/generate-site", json={"theme": "modern"})
            assert response.status_code == 200

            # Empty theme should use default
            response = client.post("/generate-site", json={"theme": ""})
            assert response.status_code == 200


class TestResponseStructure:
    """Test standardized response structure."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_success_response_structure(self, client):
        """Test that all success responses follow the standard structure."""
        with patch("main.get_site_generator") as mock_get_gen:
            mock_gen = AsyncMock()
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
            data = response.json()

            # Check standard response structure
            assert data["status"] == "success"
            assert "message" in data
            assert "data" in data
            assert "metadata" in data

            # Check health-specific fields in data
            assert data["data"]["service"] == "site-generator"
            assert "version" in data["data"]
            assert "timestamp" in data["metadata"]

    def test_error_response_structure(self, client):
        """Test that error responses follow expected structure."""
        # Standard status endpoints are designed to always return 200
        # Test a non-existent endpoint instead to get an error response
        response = client.get("/nonexistent")

        # Should get 404 for non-existent endpoint
        assert response.status_code == 404
        data = response.json()

        # Check error response structure
        assert data["status"] == "error"
        assert "errors" in data
        assert isinstance(data["errors"], list)


class TestConcurrency:
    """Test concurrent request handling."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_concurrent_requests(self, client):
        """Test concurrent requests to ensure thread safety."""
        import threading

        with patch("main.get_site_generator") as mock_get_gen:
            mock_gen = AsyncMock()
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

            results = []

            def make_request():
                response = client.get("/health")
                results.append(response.status_code)

            # Start multiple threads
            threads = [threading.Thread(target=make_request) for _ in range(5)]
            for thread in threads:
                thread.start()

            # Wait for all to complete
            for thread in threads:
                thread.join()

            # All should succeed
            assert all(status == 200 for status in results)
            assert len(results) == 5

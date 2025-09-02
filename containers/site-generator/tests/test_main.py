"""
Test suite for main application module.

Tests main application entry point and core functionality.
Follows project standards for test coverage (~70%).
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from models import GenerationRequest, GenerationResponse, SiteMetrics, SiteStatus
from pydantic import ValidationError

# Add the containers path to import the main module
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))


# Add the containers path to import the main app
sys.path.insert(0, "/workspaces/ai-content-farm/containers/site-generator")

# Mock the SiteGenerator before importing main to avoid Azure dependency
with patch("site_generator.BlobStorageClient"), patch(
    "main.SiteGenerator"
) as mock_site_gen_class:

    # Create a mock instance
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

    @pytest.fixture
    def mock_site_generator(self):
        """Mock site generator for testing."""
        mock_gen = AsyncMock()
        mock_gen.generator_id = "test_generator_123"
        return mock_gen

    def test_app_metadata(self, client):
        """Test app metadata is correctly configured."""
        response = client.get("/docs")
        assert response.status_code == 200

        # Check OpenAPI documentation is available
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_data = response.json()
        assert openapi_data["info"]["title"] == "AI Content Farm - Site Generator"
        assert openapi_data["info"]["version"] == "1.0.0"
        assert (
            openapi_data["info"]["description"]
            == "Python-based JAMStack static site generator"
        )


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_site_generator(self):
        """Mock site generator for testing."""
        mock_gen = AsyncMock()
        mock_gen.generator_id = "test_gen_health"
        mock_gen.check_blob_connectivity.return_value = True
        return mock_gen

    def test_health_check_success(self, client, mock_site_generator):
        """Test successful health check."""
        with patch("main.site_generator", mock_site_generator):
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "healthy"
            assert data["service"] == "site-generator"
            assert data["version"] == "1.0.0"
            assert "timestamp" in data
            assert data["blob_storage_available"] is True
            assert "containers" in data
            assert "source" in data["containers"]
            assert "markdown" in data["containers"]
            assert "static" in data["containers"]

    def test_health_check_blob_failure(self, client):
        """Test health check with blob storage failure."""
        mock_gen = AsyncMock()
        mock_gen.check_blob_connectivity.side_effect = Exception("Connection failed")

        with patch("main.site_generator", mock_gen):
            response = client.get("/health")

            assert response.status_code == 503
            data = response.json()

            assert data["status"] == "unhealthy"
            assert data["error"] == "Service temporarily unavailable"
            assert "timestamp" in data

    def test_api_health_check_endpoint(self, client, mock_site_generator):
        """Test standardized API health check endpoint."""
        with patch("main.site_generator", mock_site_generator):
            response = client.get("/api/site-generator/health")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "healthy"
            assert data["service"] == "site-generator"


class TestStatusEndpoint:
    """Test status endpoint functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_status(self):
        """Mock status response."""
        return SiteStatus(
            generator_id="status_test_123",
            status="idle",
            current_theme="minimal",
            markdown_files_count=25,
            site_metrics=SiteMetrics(
                total_articles=25,
                total_pages=8,
                total_size_bytes=512000,
                last_build_time=5.5,
                build_timestamp=datetime.now(timezone.utc),
            ),
            last_generation=datetime.now(timezone.utc),
        )

    def test_status_success(self, client, mock_status):
        """Test successful status retrieval."""
        mock_gen = AsyncMock()
        mock_gen.generator_id = "status_test_123"
        mock_gen.get_status.return_value = mock_status

        with patch("main.site_generator", mock_gen):
            response = client.get("/api/site-generator/status")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "success"
            assert data["message"] == "Status retrieved successfully"
            assert "data" in data
            assert data["data"]["generator_id"] == "status_test_123"
            assert data["data"]["status"] == "idle"
            assert data["data"]["current_theme"] == "minimal"
            assert data["data"]["markdown_files_count"] == 25
            assert data["errors"] is None
            assert "metadata" in data
            assert data["metadata"]["function"] == "site-generator"
            assert data["metadata"]["generator_id"] == "status_test_123"

    def test_status_failure(self, client):
        """Test status endpoint error handling."""
        mock_gen = AsyncMock()
        mock_gen.get_status.side_effect = Exception("Status retrieval failed")

        with patch("main.site_generator", mock_gen):
            response = client.get("/api/site-generator/status")

            assert response.status_code == 500
            data = response.json()
            assert "Status retrieval failed" in data["detail"]


class TestMarkdownGenerationEndpoint:
    """Test markdown generation endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_generation_response(self):
        """Mock generation response."""
        return GenerationResponse(
            generator_id="markdown_test_456",
            operation_type="markdown_generation",
            files_generated=3,
            processing_time=2.5,
            output_location="blob://markdown-content",
            generated_files=["article-1.md", "article-2.md", "article-3.md"],
        )

    def test_generate_markdown_success(self, client, mock_generation_response):
        """Test successful markdown generation."""
        mock_gen = AsyncMock()
        mock_gen.generator_id = "markdown_test_456"
        mock_gen.generate_markdown_batch.return_value = mock_generation_response

        request_data = {
            "source": "test_source",
            "batch_size": 5,
            "force_regenerate": True,
        }

        with patch("main.site_generator", mock_gen):
            response = client.post(
                "/api/site-generator/generate-markdown", json=request_data
            )

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "success"
            assert "Generated 3 markdown files" in data["message"]
            assert data["data"]["generator_id"] == "markdown_test_456"
            assert data["data"]["operation_type"] == "markdown_generation"
            assert data["data"]["files_generated"] == 3
            assert len(data["data"]["generated_files"]) == 3
            assert data["errors"] is None

    def test_generate_markdown_validation_error(self, client):
        """Test markdown generation with invalid request data."""
        invalid_request = {
            "source": "test",
            "batch_size": 150,  # Too large
            "force_regenerate": "not_a_boolean",
        }

        response = client.post(
            "/api/site-generator/generate-markdown", json=invalid_request
        )
        assert response.status_code == 422  # Validation error

    def test_generate_markdown_processing_error(self, client):
        """Test markdown generation processing failure."""
        mock_gen = AsyncMock()
        mock_gen.generate_markdown_batch.side_effect = Exception("Processing failed")

        request_data = {"source": "test_source", "batch_size": 5}

        with patch("main.site_generator", mock_gen):
            response = client.post(
                "/api/site-generator/generate-markdown", json=request_data
            )

            assert response.status_code == 500
            data = response.json()
            assert "Processing failed" in data["detail"]

    def test_generate_markdown_default_values(self, client, mock_generation_response):
        """Test markdown generation with default request values."""
        mock_gen = AsyncMock()
        mock_gen.generate_markdown_batch.return_value = mock_generation_response

        # Minimal request - should use defaults
        request_data = {"source": "minimal_test"}

        with patch("main.site_generator", mock_gen):
            response = client.post(
                "/api/site-generator/generate-markdown", json=request_data
            )

            assert response.status_code == 200

            # Verify the mock was called with default values
            mock_gen.generate_markdown_batch.assert_called_once_with(
                source="minimal_test",
                batch_size=10,  # Default value
                force_regenerate=False,  # Default value
            )


class TestSiteGenerationEndpoint:
    """Test static site generation endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_site_response(self):
        """Mock site generation response."""
        return GenerationResponse(
            generator_id="site_test_789",
            operation_type="site_generation",
            files_generated=15,
            pages_generated=5,
            processing_time=8.2,
            output_location="blob://static-sites",
            generated_files=["index.html", "archive.html", "style.css"],
        )

    def test_generate_site_success(self, client, mock_site_response):
        """Test successful site generation."""
        mock_gen = AsyncMock()
        mock_gen.generator_id = "site_test_789"
        mock_gen.generate_static_site.return_value = mock_site_response

        request_data = {"theme": "modern", "force_regenerate": True}

        with patch("main.site_generator", mock_gen):
            response = client.post(
                "/api/site-generator/generate-site", json=request_data
            )

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "success"
            assert "Generated static site with 5 pages" in data["message"]
            assert data["data"]["operation_type"] == "site_generation"
            assert data["data"]["pages_generated"] == 5

    def test_generate_site_default_theme(self, client, mock_site_response):
        """Test site generation with default theme."""
        mock_gen = AsyncMock()
        mock_gen.generate_static_site.return_value = mock_site_response

        request_data = {"force_regenerate": False}

        with patch("main.site_generator", mock_gen):
            response = client.post(
                "/api/site-generator/generate-site", json=request_data
            )

            assert response.status_code == 200

            # Verify default theme was used
            mock_gen.generate_static_site.assert_called_once_with(
                theme="minimal", force_rebuild=False  # Default theme
            )


class TestWakeUpEndpoint:
    """Test wake-up endpoint functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_responses(self):
        """Mock responses for wake-up workflow."""
        markdown_response = GenerationResponse(
            generator_id="wakeup_test",
            operation_type="markdown_generation",
            files_generated=2,
            processing_time=1.5,
            output_location="blob://markdown",
            generated_files=["new-article-1.md", "new-article-2.md"],
        )

        site_response = GenerationResponse(
            generator_id="wakeup_test",
            operation_type="site_generation",
            files_generated=5,
            pages_generated=3,
            processing_time=3.0,
            output_location="blob://static",
            generated_files=["index.html", "article-1.html", "article-2.html"],
        )

        return markdown_response, site_response

    def test_wake_up_with_new_content(self, client, mock_responses):
        """Test wake-up with new content generation."""
        markdown_response, site_response = mock_responses

        mock_gen = AsyncMock()
        mock_gen.generator_id = "wakeup_test"
        mock_gen.generate_markdown_batch.return_value = markdown_response
        mock_gen.generate_static_site.return_value = site_response

        with patch("main.site_generator", mock_gen):
            response = client.post("/api/site-generator/wake-up")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "success"
            assert "Wake-up complete: 2 markdown files, site updated" in data["message"]
            assert "data" in data
            assert data["data"]["markdown_result"]["files_generated"] == 2
            assert data["data"]["site_result"]["pages_generated"] == 3
            assert "wake_up_time" in data["data"]

    def test_wake_up_no_new_content(self, client):
        """Test wake-up with no new content."""
        # Mock no new markdown files
        markdown_response = GenerationResponse(
            generator_id="wakeup_no_content",
            operation_type="markdown_generation",
            files_generated=0,
            processing_time=0.5,
            output_location="blob://markdown",
            generated_files=[],
        )

        mock_gen = AsyncMock()
        mock_gen.generate_markdown_batch.return_value = markdown_response

        with patch("main.site_generator", mock_gen):
            response = client.post("/api/site-generator/wake-up")

            assert response.status_code == 200
            data = response.json()

            assert (
                "Wake-up complete: 0 markdown files, site unchanged" in data["message"]
            )
            assert data["data"]["site_result"] is None

            # Verify site generation wasn't called
            mock_gen.generate_static_site.assert_not_called()

    def test_wake_up_failure(self, client):
        """Test wake-up endpoint error handling."""
        mock_gen = AsyncMock()
        mock_gen.generate_markdown_batch.side_effect = Exception("Wake-up failed")

        with patch("main.site_generator", mock_gen):
            response = client.post("/api/site-generator/wake-up")

            assert response.status_code == 500
            data = response.json()
            assert "Wake-up failed" in data["detail"]


class TestPreviewEndpoint:
    """Test preview URL endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_preview_success(self, client):
        """Test successful preview URL generation."""
        mock_gen = AsyncMock()
        mock_gen.get_preview_url.return_value = "https://preview.example.com/site_123"

        with patch("main.site_generator", mock_gen):
            response = client.get("/api/site-generator/preview/site_123")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "success"
            assert data["message"] == "Preview URL retrieved"
            assert data["data"]["site_id"] == "site_123"
            assert data["data"]["preview_url"] == "https://preview.example.com/site_123"
            assert "expires_at" in data["data"]

    def test_preview_not_found(self, client):
        """Test preview URL for non-existent site."""
        mock_gen = AsyncMock()
        mock_gen.get_preview_url.side_effect = Exception("Site not found")

        with patch("main.site_generator", mock_gen):
            response = client.get("/api/site-generator/preview/nonexistent")

            assert response.status_code == 404
            data = response.json()
            assert "Site not found" in data["detail"]


class TestErrorHandling:
    """Test comprehensive error handling across endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_invalid_json_request(self, client):
        """Test handling of invalid JSON in request body."""
        response = client.post(
            "/api/site-generator/generate-markdown", data="invalid json"
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, client):
        """Test handling of missing required fields."""
        # Empty request body
        response = client.post("/api/site-generator/generate-markdown", json={})
        assert response.status_code == 422

    def test_unexpected_server_errors(self, client):
        """Test handling of unexpected server errors."""
        # Mock site_generator to raise unexpected error
        with patch("main.site_generator", side_effect=Exception("Unexpected error")):
            response = client.get("/health")
            assert response.status_code == 503


class TestRequestResponseStructure:
    """Test standardized request/response structure."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_success_response_structure(self, client):
        """Test that all success responses follow the standard structure."""
        mock_gen = AsyncMock()
        mock_gen.generator_id = "structure_test"
        mock_gen.check_blob_connectivity.return_value = True

        with patch("main.site_generator", mock_gen):
            response = client.get("/health")
            data = response.json()

            # All API responses should have these fields
            required_fields = ["status", "service", "version", "timestamp"]
            for field in required_fields:
                assert field in data

    def test_api_response_metadata(self, client):
        """Test that API responses include proper metadata."""
        mock_status = SiteStatus(
            generator_id="metadata_test",
            status="idle",
            current_theme="minimal",
            markdown_files_count=0,
        )

        mock_gen = AsyncMock()
        mock_gen.generator_id = "metadata_test"
        mock_gen.get_status.return_value = mock_status

        with patch("main.site_generator", mock_gen):
            response = client.get("/api/site-generator/status")
            data = response.json()

            # API responses should include metadata
            assert "metadata" in data
            metadata = data["metadata"]
            assert metadata["function"] == "site-generator"
            assert metadata["version"] == "1.0.0"
            assert metadata["generator_id"] == "metadata_test"
            assert "timestamp" in metadata

    def test_error_response_structure(self, client):
        """Test that error responses follow expected structure."""
        mock_gen = AsyncMock()
        mock_gen.get_status.side_effect = Exception("Test error")

        with patch("main.site_generator", mock_gen):
            response = client.get("/api/site-generator/status")

            assert response.status_code == 500
            data = response.json()

            # FastAPI error responses include detail
            assert "detail" in data


class TestAppConfiguration:
    """Test application configuration and initialization."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_app_initialization(self):
        """Test that app is properly initialized."""
        assert app.title == "AI Content Farm - Site Generator"
        assert app.version == "1.0.0"
        assert app.description == "Python-based JAMStack static site generator"

    def test_app_routes_registered(self, client):
        """Test that all expected routes are registered by calling them."""
        # Test routes by making requests instead of inspecting route objects
        expected_routes = [
            ("/health", 200),
            ("/api/site-generator/health", 200),
            ("/docs", 200),
            ("/openapi.json", 200),
        ]

        with patch("main.site_generator") as mock_gen:
            mock_gen.check_blob_connectivity.return_value = True

            for route_path, expected_status in expected_routes:
                response = client.get(route_path)
                assert (
                    response.status_code == expected_status
                ), f"Route {route_path} failed with status {response.status_code}"

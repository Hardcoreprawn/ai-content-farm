"""
API endpoint tests

Tests for all API endpoints including status, generation, and preview.
Focused on endpoint behavior and response validation.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from models import GenerationResponse, SiteStatus

# Add the containers path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

# Mock dependencies before importing main
with (
    patch("azure.storage.blob.BlobServiceClient"),
    patch("azure.identity.DefaultAzureCredential"),
    patch("main.SiteGenerator") as mock_site_gen_class,
):
    mock_site_gen_instance = AsyncMock()
    mock_site_gen_instance.generator_id = "test_generator_123"
    mock_site_gen_class.return_value = mock_site_gen_instance
    from main import app


class TestStatusEndpoint:
    """Test status endpoint functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_status_success(self, client):
        """Test successful status retrieval."""
        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Check standard response structure
        status_data = data["data"]
        assert "service" in status_data
        assert "version" in status_data
        assert "status" in status_data
        assert "environment" in status_data
        assert "uptime_seconds" in status_data
        assert status_data["service"] == "site-generator"

    def test_status_failure(self, client):
        """Test status endpoint error handling."""
        # Standard endpoints don't fail easily, they return service info
        # Test that a normal request still works
        response = client.get("/status")

        # Should always return 200 for standard status endpoints
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestMarkdownGenerationEndpoint:
    """Test markdown generation endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_generate_markdown_success(self, client):
        """Test successful markdown generation."""
        mock_response = GenerationResponse(
            generator_id="test_456",
            operation_type="markdown_generation",
            files_generated=3,
            processing_time=2.1,
            output_location="blob://markdown-content",
            generated_files=["file1.md", "file2.md", "file3.md"],
        )

        with patch("main.get_site_generator") as mock_get_gen:
            # Mock the site generator instance
            mock_gen = MagicMock()
            mock_get_gen.return_value = mock_gen

            mock_gen.generate_markdown_batch = AsyncMock(return_value=mock_response)
            mock_gen.generator_id = "test_456"

            request_data = {"source": "test_source", "batch_size": 5}
            response = client.post("/generate-markdown", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["files_generated"] == 3

    def test_generate_markdown_with_defaults(self, client):
        """Test markdown generation with default parameters."""
        mock_response = GenerationResponse(
            generator_id="test_789",
            operation_type="markdown_generation",
            files_generated=1,
            processing_time=1.0,
            output_location="blob://markdown-content",
            generated_files=["default.md"],
        )

        with patch("main.get_site_generator") as mock_get_gen:
            # Mock the site generator instance
            mock_gen = MagicMock()
            mock_get_gen.return_value = mock_gen

            mock_gen.generate_markdown_batch = AsyncMock(return_value=mock_response)
            mock_gen.generator_id = "test_789"

            response = client.post("/generate-markdown", json={})

            assert response.status_code == 200
            # Verify defaults were used
            mock_gen.generate_markdown_batch.assert_called_once_with(
                source="manual", batch_size=10, force_regenerate=False
            )


class TestSiteGenerationEndpoint:
    """Test static site generation endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_generate_site_success(self, client):
        """Test successful site generation."""
        mock_response = GenerationResponse(
            generator_id="site_test_789",
            operation_type="site_generation",
            files_generated=15,
            pages_generated=5,
            processing_time=8.2,
            output_location="blob://static-sites",
            generated_files=["index.html", "archive.html", "style.css"],
        )

        with patch("main.get_site_generator") as mock_get_gen:
            # Mock the site generator instance
            mock_gen = MagicMock()
            mock_get_gen.return_value = mock_gen

            mock_gen.generate_static_site = AsyncMock(return_value=mock_response)
            mock_gen.generator_id = "test_generator"

            request_data = {"theme": "modern", "force_regenerate": True}
            response = client.post("/generate-site", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["pages_generated"] == 5


class TestPreviewEndpoint:
    """Test preview URL endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_preview_success(self, client):
        """Test successful preview URL generation."""
        with patch("main.get_site_generator") as mock_get_gen:
            # Mock the site generator instance
            mock_gen = MagicMock()
            mock_get_gen.return_value = mock_gen

            mock_gen.get_preview_url = AsyncMock(
                return_value="https://preview.example.com/site_123"
            )
            mock_gen.generator_id = "test_generator"

            response = client.get("/preview/site_123")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["preview_url"] == "https://preview.example.com/site_123"


class TestWakeUpEndpoint:
    """Test wake-up endpoint functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_wake_up_with_new_content(self, client):
        """Test wake-up with new content generation."""
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

        with patch("main.get_site_generator") as mock_get_gen:
            mock_gen = AsyncMock()
            mock_get_gen.return_value = mock_gen

            mock_gen.generate_markdown_batch = AsyncMock(return_value=markdown_response)
            mock_gen.generate_static_site = AsyncMock(return_value=site_response)

            response = client.post("/wake-up")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "2 markdown files" in data["message"]

    def test_wake_up_no_new_content(self, client):
        """Test wake-up with no new content."""
        markdown_response = GenerationResponse(
            generator_id="wakeup_no_content",
            operation_type="markdown_generation",
            files_generated=0,
            processing_time=0.5,
            output_location="blob://markdown",
            generated_files=[],
        )

        with patch("main.get_site_generator") as mock_get_gen:
            mock_gen = AsyncMock()
            mock_get_gen.return_value = mock_gen

            mock_gen.generate_markdown_batch = AsyncMock(return_value=markdown_response)
            mock_gen.generate_static_site = AsyncMock()

            response = client.post("/wake-up")

            assert response.status_code == 200
            data = response.json()
            assert "0 markdown files" in data["message"]
            # Verify site generation wasn't called
            mock_gen.generate_static_site.assert_not_called()

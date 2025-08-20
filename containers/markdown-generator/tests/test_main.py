"""Tests for main FastAPI application."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mock the dependencies before importing the main app
mock_blob_client = MagicMock()
mock_generator = MagicMock()
mock_watcher = MagicMock()
mock_health_checker = MagicMock()

with patch("main.BlobStorageClient", return_value=mock_blob_client), patch(
    "main.MarkdownGenerator", return_value=mock_generator
), patch("main.ContentWatcher", return_value=mock_watcher), patch(
    "main.HealthChecker", return_value=mock_health_checker
), patch(
    "main.start_content_watcher", new_callable=AsyncMock
), patch(
    "config.config.validate_required_settings"
):
    from main import app

client = TestClient(app)


class TestMainApplication:
    """Test the main FastAPI application endpoints."""

    def test_root_endpoint(self):
        """Test the root endpoint returns service information."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "markdown-generator"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
        assert "endpoints" in data

    @patch("main.health_checker")
    def test_health_check_healthy(self, mock_health):
        """Test health check endpoint when service is healthy."""
        mock_health.check_health = AsyncMock(
            return_value={
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "markdown-generator",
                "checks": {},
            }
        )

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "markdown-generator"

    @patch("main.health_checker")
    def test_health_check_unhealthy(self, mock_health):
        """Test health check endpoint when service is unhealthy."""
        mock_health.check_health = AsyncMock(
            return_value={
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "markdown-generator",
                "error": "Blob storage unavailable",
            }
        )

        response = client.get("/health")
        assert response.status_code == 503

        data = response.json()
        assert data["status"] == "unhealthy"

    @patch("main.health_checker")
    def test_status_endpoint(self, mock_health):
        """Test the status endpoint."""
        mock_health.get_service_status = AsyncMock(
            return_value={
                "service": "markdown-generator",
                "status": "running",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "content_watcher": {"watching": True},
                "blob_storage": {"healthy": True},
                "file_statistics": {"markdown_files": 0},
            }
        )

        response = client.get("/status")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "markdown-generator"
        assert data["status"] == "running"

    @patch("main.markdown_generator")
    def test_generate_markdown_success(self, mock_gen):
        """Test successful markdown generation."""
        mock_gen.generate_markdown_from_ranked_content = AsyncMock(
            return_value={
                "status": "success",
                "files_generated": 5,
                "timestamp": "20240101_120000",
                "markdown_files": [],
            }
        )

        request_data = {
            "content_items": [
                {
                    "title": "Test Article",
                    "source_url": "https://example.com",
                    "ai_summary": "Test summary",
                    "final_score": 0.8,
                }
            ]
        }

        response = client.post("/generate", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["files_generated"] == 5

    def test_generate_markdown_no_content(self):
        """Test markdown generation with no content items."""
        request_data = {"content_items": []}

        response = client.post("/generate", json=request_data)
        assert response.status_code == 400

        # Check the error message
        data = response.json()
        assert "No content items provided" in data["detail"]

    @patch("main.content_watcher")
    def test_trigger_check_with_new_content(self, mock_watcher):
        """Test manual trigger when new content is found."""
        mock_watcher.check_for_new_ranked_content = AsyncMock(
            return_value={"status": "success", "files_generated": 3}
        )

        response = client.post("/trigger")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert "result" in data

    @patch("main.content_watcher")
    def test_trigger_check_no_new_content(self, mock_watcher):
        """Test manual trigger when no new content is found."""
        mock_watcher.check_for_new_ranked_content = AsyncMock(return_value=None)

        response = client.post("/trigger")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "no_new_content"

    @patch("main.content_watcher")
    def test_watcher_status_endpoint(self, mock_watcher):
        """Test watcher status endpoint."""
        mock_watcher.get_watcher_status.return_value = {
            "watching": True,
            "processed_blobs": 5,
            "last_check": datetime.now(timezone.utc).isoformat(),
        }

        response = client.get("/watcher/status")
        assert response.status_code == 200

        data = response.json()
        assert data["watching"] is True
        assert "processed_blobs" in data


class TestMarkdownRequestValidation:
    """Test request model validation."""

    def test_valid_markdown_request(self):
        """Test valid markdown generation request."""
        request_data = {
            "content_items": [
                {
                    "title": "Test Article",
                    "source_url": "https://example.com",
                    "ai_summary": "Test summary",
                    "final_score": 0.8,
                }
            ],
            "auto_notify": True,
            "template_style": "jekyll",
        }

        with patch("main.markdown_generator") as mock_gen:
            mock_gen.generate_markdown_from_ranked_content = AsyncMock(
                return_value={
                    "status": "success",
                    "files_generated": 1,
                    "timestamp": "20240101_120000",
                    "markdown_files": [],
                }
            )

            response = client.post("/generate", json=request_data)
            assert response.status_code == 200

    def test_missing_required_fields(self):
        """Test request with missing required fields."""
        # Missing content_items
        response = client.post("/generate", json={})
        assert response.status_code == 422  # Validation error

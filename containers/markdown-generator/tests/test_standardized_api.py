"""Tests for standardized API endpoints in markdown generator service."""

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


class TestStandardizedAPIEndpoints:
    """Test the new standardized API endpoints."""

    def test_api_health_endpoint_format(self):
        """Test standardized health endpoint returns proper StandardResponse format."""
        # Mock health checker response
        mock_health_result = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "markdown-generator",
            "blob_storage_healthy": True,
        }

        # Patch the global health_checker directly
        with patch("main.health_checker", mock_health_checker):
            mock_health_checker.check_health = AsyncMock(
                return_value=mock_health_result
            )

            response = client.get("/api/markdown-generator/health")

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse structure
        assert "status" in data
        assert "data" in data
        assert "message" in data
        assert "metadata" in data

        assert data["status"] == "success"
        assert data["data"] == mock_health_result
        assert "Health check completed successfully" in data["message"]
        assert data["metadata"]["function"] == "markdown-generator"

    def test_api_status_endpoint_format(self):
        """Test standardized status endpoint returns proper StandardResponse format."""
        # Mock service status response
        mock_status = MagicMock()
        mock_status.model_dump.return_value = {
            "service": "markdown-generator",
            "status": "healthy",
            "version": "1.0.0",
            "content_watcher": {"status": "running"},
            "blob_storage": {"healthy": True},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Patch the global health_checker directly
        with patch("main.health_checker", mock_health_checker), patch(
            "main.content_watcher", mock_watcher
        ):
            mock_health_checker.get_service_status = AsyncMock(return_value=mock_status)

            response = client.get("/api/markdown-generator/status")

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse structure
        assert "status" in data
        assert "data" in data
        assert "message" in data
        assert "metadata" in data

        assert data["status"] == "success"
        assert "Service status retrieved successfully" in data["message"]
        assert data["metadata"]["function"] == "markdown-generator"

    def test_api_process_endpoint_success(self):
        """Test standardized process endpoint with successful processing."""
        # Mock generation result
        mock_result = {
            "status": "success",
            "files_generated": 3,
            "manifest_file": "manifest.json",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "markdown_files": [],
        }

        # Patch the global markdown_generator directly
        with patch("main.markdown_generator", mock_generator):
            mock_generator.generate_markdown_from_ranked_content = AsyncMock(
                return_value=mock_result
            )

            request_data = {
                "content_items": [
                    {
                        "title": "Test Article",
                        "source_url": "https://example.com/test",
                        "ai_summary": "Test summary",
                        "final_score": 0.8,
                    }
                ],
                "template_style": "jekyll",
            }

            response = client.post("/api/markdown-generator/process", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse structure
        assert "status" in data
        assert "data" in data
        assert "message" in data
        assert "metadata" in data

        assert data["status"] == "success"
        assert data["data"] == mock_result
        assert "Generated 3 files" in data["message"]
        assert data["metadata"]["function"] == "markdown-generator"

    def test_api_process_endpoint_validation_error(self):
        """Test standardized process endpoint with validation error."""
        request_data = {
            "content_items": [],  # Empty list should cause validation error
            "template_style": "jekyll",
        }

        response = client.post("/api/markdown-generator/process", json=request_data)

        assert (
            response.status_code == 200
        )  # StandardResponse returns 200 with error flag
        data = response.json()

        # Verify StandardResponse error structure
        assert "status" in data
        assert "errors" in data
        assert "message" in data
        assert "metadata" in data

        assert data["status"] == "error"
        assert "No content items provided" in data["errors"]
        assert "Request validation failed" in data["message"]

    def test_api_process_endpoint_error_handling(self):
        """Test standardized process endpoint error handling."""
        # Mock generator to raise exception
        with patch("main.markdown_generator", mock_generator):
            mock_generator.generate_markdown_from_ranked_content = AsyncMock(
                side_effect=Exception("Generation failed")
            )

            request_data = {
                "content_items": [
                    {
                        "title": "Test Article",
                        "source_url": "https://example.com/test",
                        "ai_summary": "Test summary",
                        "final_score": 0.8,
                    }
                ]
            }

            response = client.post("/api/markdown-generator/process", json=request_data)

        assert (
            response.status_code == 200
        )  # StandardResponse returns 200 with error flag
        data = response.json()

        # Verify StandardResponse error structure
        assert data["status"] == "error"
        assert "Generation failed" in data["errors"]
        assert "Markdown generation failed" in data["message"]

    def test_api_docs_endpoint(self):
        """Test standardized docs endpoint returns comprehensive API documentation."""
        response = client.get("/api/markdown-generator/docs")

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse structure
        assert "status" in data
        assert "data" in data
        assert "message" in data
        assert "metadata" in data

        assert data["status"] == "success"

        # Verify documentation content
        docs_data = data["data"]
        assert docs_data["service"] == "markdown-generator"
        assert "endpoints" in docs_data
        assert "standardized" in docs_data["endpoints"]
        assert "legacy" in docs_data["endpoints"]
        assert "features" in docs_data
        assert "schemas" in docs_data


class TestBackwardCompatibility:
    """Test that legacy endpoints remain unchanged."""

    def test_legacy_health_endpoint_unchanged(self):
        """Test that legacy health endpoint still works as before."""
        mock_health_result = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "markdown-generator",
            "blob_storage_healthy": True,
        }

        with patch("main.health_checker", mock_health_checker):
            mock_health_checker.check_health = AsyncMock(
                return_value=mock_health_result
            )

            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Should be direct response, not StandardResponse wrapper
        assert data == mock_health_result
        assert (
            "status" not in data or data.get("status") != "success"
        )  # Not StandardResponse format

    def test_legacy_root_endpoint_unchanged(self):
        """Test that root endpoint still works as before."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Should have original structure
        assert "service" in data
        assert "version" in data
        assert "status" in data
        assert "endpoints" in data
        assert (
            "status" not in data or data.get("status") != "success"
        )  # Not StandardResponse format

    def test_legacy_status_endpoint_unchanged(self):
        """Test that legacy status endpoint still works as before."""
        # Import ServiceStatus model to create proper mock
        from models import ServiceStatus

        # Create a proper ServiceStatus object
        mock_status = ServiceStatus(
            service="markdown-generator",
            status="healthy",
            version="1.0.0",
            content_watcher={"status": "running"},
            blob_storage={"healthy": True},
            file_statistics={"files": 0},
            timestamp=datetime.now(timezone.utc).isoformat(),
            configuration={"config": "loaded"},
        )

        with patch("main.health_checker", mock_health_checker), patch(
            "main.content_watcher", mock_watcher
        ):
            mock_health_checker.get_service_status = AsyncMock(return_value=mock_status)

            response = client.get("/status")

        assert response.status_code == 200
        data = response.json()

        # Should be direct ServiceStatus response
        assert "service" in data
        assert (
            "status" not in data or data.get("status") != "success"
        )  # Not StandardResponse format

    def test_legacy_generate_endpoint_unchanged(self):
        """Test that legacy generate endpoint still works as before."""
        mock_result = {
            "status": "success",
            "files_generated": 2,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        with patch("main.markdown_generator", mock_generator):
            mock_generator.generate_markdown_from_ranked_content = AsyncMock(
                return_value=mock_result
            )

            request_data = {
                "content_items": [
                    {
                        "title": "Test Article",
                        "source_url": "https://example.com/test",
                        "ai_summary": "Test summary",
                        "final_score": 0.8,
                    }
                ]
            }

            response = client.post("/generate", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Should be GenerationResult format - status is part of the model but means something different
        assert "status" in data
        assert "files_generated" in data
        # This status is from GenerationResult.status, not StandardResponse.status
        assert (
            data["status"] == "success"
        )  # This is the generation status, not response status


class TestStandardizedErrorHandling:
    """Test standardized error handling patterns."""

    def test_404_error_format(self):
        """Test that 404 errors follow standardized format."""
        response = client.get("/api/markdown-generator/nonexistent")

        assert response.status_code == 404
        data = response.json()

        # FastAPI default 404 format
        assert "detail" in data

    def test_method_not_allowed_error_format(self):
        """Test that method not allowed errors are handled properly."""
        response = client.post("/api/markdown-generator/health")

        assert response.status_code == 405
        data = response.json()

        # FastAPI default 405 format
        assert "detail" in data

    def test_validation_error_format(self):
        """Test that request validation errors are handled properly."""
        # Send invalid JSON to process endpoint
        response = client.post(
            "/api/markdown-generator/process", json={"invalid": "data"}
        )

        assert response.status_code == 422  # FastAPI validation error
        data = response.json()

        # FastAPI validation error format
        assert "detail" in data


class TestResponseMetadata:
    """Test metadata injection in standardized responses."""

    def test_metadata_in_success_response(self):
        """Test that metadata is properly injected in success responses."""
        mock_health_result = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "markdown-generator",
            "blob_storage_healthy": True,
        }

        with patch("main.health_checker", mock_health_checker):
            mock_health_checker.check_health = AsyncMock(
                return_value=mock_health_result
            )

            response = client.get("/api/markdown-generator/health")

        assert response.status_code == 200
        data = response.json()

        # Verify metadata presence and content
        assert "metadata" in data
        metadata = data["metadata"]
        assert metadata["function"] == "markdown-generator"
        assert "timestamp" in metadata

    def test_metadata_in_error_response(self):
        """Test that metadata is properly injected in error responses."""
        # Mock health checker to raise exception
        with patch("main.health_checker", mock_health_checker):
            mock_health_checker.check_health = AsyncMock(
                side_effect=Exception("Health check failed")
            )

            response = client.get("/api/markdown-generator/health")

        assert (
            response.status_code == 200
        )  # StandardResponse returns 200 with error flag
        data = response.json()

        # Verify metadata presence in error response
        assert "metadata" in data
        metadata = data["metadata"]
        assert metadata["function"] == "markdown-generator"
        assert "timestamp" in metadata

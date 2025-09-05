#!/usr/bin/env python3
"""
Standardized API Tests for Content Generator

Tests for the standardized API endpoints following the FastAPI-native patterns.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from main import app


class TestStandardizedAPIEndpoints:
    """Test standardized API endpoints format."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_api_health_endpoint_format(self, client):
        """Test standardized health endpoint returns proper format."""
        response = client.get("/api/content-generator/health")
        assert response.status_code == 200

        data = response.json()

        # Check StandardResponse structure
        assert "status" in data
        assert "message" in data
        assert "data" in data
        assert "errors" in data
        assert "metadata" in data

        # Check successful response
        assert data["status"] == "success"
        assert "healthy" in data["message"].lower()
        assert data["errors"] is None

        # Check service metadata
        metadata = data["metadata"]
        assert metadata["function"] == "content-generator"
        assert "timestamp" in metadata

    def test_api_status_endpoint_format(self, client):
        """Test standardized status endpoint returns proper format."""
        response = client.get("/api/content-generator/status")
        assert response.status_code == 200

        data = response.json()

        # Check StandardResponse structure
        assert "status" in data
        assert "message" in data
        assert "data" in data
        assert "errors" in data
        assert "metadata" in data

        # Check successful response
        assert data["status"] == "success"
        assert "status retrieved successfully" in data["message"].lower()
        assert data["errors"] is None

        # Check status data structure
        status_data = data["data"]
        assert status_data["service"] == "Content Generator"
        assert "uptime_seconds" in status_data
        assert "total_generated" in status_data
        assert "generation_capabilities" in status_data

    def test_api_process_endpoint_success(self, client):
        """Test standardized process endpoint with valid request."""
        # Mock the generation method
        with patch("main.get_content_generator") as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service

            # Create mock generated content
            mock_result = MagicMock()
            mock_result.model_dump.return_value = {
                "topic": "Test Topic",
                "content_type": "blog",
                "title": "Test Article",
                "content": "This is test content",
                "word_count": 100,
                "tags": ["test"],
                "sources": [],
                "writer_personality": "professional",
            }

            # Set up async mock
            mock_service.generate_content = AsyncMock(return_value=mock_result)

            request_data = {
                "topics": [
                    {
                        "topic": "Test Topic",
                        "sources": [
                            {
                                "name": "Test Source",
                                "url": "https://example.com",
                                "title": "Test Article",
                                "summary": "Test summary",
                            }
                        ],
                        "rank": 1,
                        "ai_score": 0.8,
                        "sentiment": "positive",
                        "tags": ["test"],
                    }
                ],
                "content_type": "blog",
                "writer_personality": "professional",
            }

            response = client.post("/api/content-generator/process", json=request_data)
            assert response.status_code == 200

            data = response.json()

            # Check StandardResponse structure
            assert "status" in data
            assert "message" in data
            assert "data" in data
            assert "errors" in data
            assert "metadata" in data

            # Check successful response
            assert data["status"] == "success"
            assert "Successfully generated" in data["message"]
            assert data["errors"] is None

            # Check generation data
            generation_data = data["data"]
            assert "topic" in generation_data
            assert "content" in generation_data

    def test_api_process_endpoint_error_handling(self, client):
        """Test standardized process endpoint error handling."""
        # Test with empty topics
        invalid_request = {"topics": [], "content_type": "blog"}

        response = client.post("/api/content-generator/process", json=invalid_request)
        assert (
            response.status_code == 200
        )  # FastAPI-native returns 200 with error status

        data = response.json()
        assert data["status"] == "error"
        assert "No topics provided" in data["message"]

        # Test with malformed request
        malformed_request = {
            "content_type": "blog"
            # Missing topics field
        }

        response = client.post("/api/content-generator/process", json=malformed_request)
        assert response.status_code == 422  # Validation error

    def test_api_process_endpoint_generation_failure(self, client):
        """Test standardized process endpoint when generation fails."""
        with patch("main.get_content_generator") as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service

            # Set up async mock to raise exception
            mock_service.generate_content = AsyncMock(
                side_effect=Exception("Generation failed")
            )

            request_data = {
                "topics": [
                    {
                        "topic": "Test Topic",
                        "sources": [],
                        "rank": 1,
                        "ai_score": 0.8,
                        "sentiment": "positive",
                        "tags": ["test"],
                    }
                ],
                "content_type": "blog",
            }

            response = client.post("/api/content-generator/process", json=request_data)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "error"
            assert "generation failed" in data["message"].lower()

    def test_api_docs_endpoint(self, client):
        """Test standardized docs endpoint."""
        response = client.get("/api/content-generator/docs")
        assert response.status_code == 200

        data = response.json()

        # Check StandardResponse structure
        assert "status" in data
        assert "message" in data
        assert "data" in data
        assert "errors" in data
        assert "metadata" in data

        # Check successful response
        assert data["status"] == "success"
        assert "documentation retrieved successfully" in data["message"].lower()
        assert data["errors"] is None

        # Check docs data structure
        docs_data = data["data"]
        assert docs_data["service"] == "content-generator"
        assert "endpoints" in docs_data
        assert "legacy_endpoints" in docs_data

        # Verify standardized endpoints are documented
        endpoints = docs_data["endpoints"]
        assert "health" in endpoints
        assert "status" in endpoints
        assert "process" in endpoints
        assert "docs" in endpoints


class TestBackwardCompatibility:
    """Test that legacy endpoints remain unchanged."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_legacy_health_endpoint_unchanged(self, client):
        """Test that legacy health endpoint still works."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        # Legacy format should still work
        assert "status" in data
        assert "service" in data

    def test_legacy_root_endpoint_unchanged(self, client):
        """Test that legacy root endpoint still works."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "service" in data
        assert data["service"] == "Content Generator"
        assert "endpoints" in data

    def test_legacy_status_endpoint_unchanged(self, client):
        """Test that legacy status endpoint still works."""
        response = client.get("/status")
        assert response.status_code == 200

        data = response.json()
        # Legacy format should work
        assert "service" in data
        assert "status" in data
        assert "active_generations" in data
        assert "ai_services" in data

    def test_legacy_generation_endpoints_unchanged(self, client):
        """Test that legacy generation endpoints still work."""
        # Mock the actual service method to return proper data
        with patch("main.get_content_generator") as mock_get_service:
            # Create actual GeneratedContent object
            from datetime import datetime

            from models import GeneratedContent, SourceData

            mock_service = MagicMock()
            mock_get_service.return_value = mock_service

            # Create proper GeneratedContent object
            generated_content = GeneratedContent(
                topic="Test Topic",
                content_type="tldr",
                title="Test Article",
                content="This is test content",
                word_count=100,
                tags=["test"],
                sources=[],
                writer_personality="professional",
                verification_status="pending",
                metadata={},
                generation_time=datetime.now(),
                ai_model="gpt-3.5-turbo",
            )

            # Set up async mock to return the proper object
            mock_service.generate_content = AsyncMock(return_value=generated_content)

            topic_data = {
                "topic": "Test Topic",
                "sources": [],
                "rank": 1,
                "ai_score": 0.8,
                "sentiment": "positive",
                "tags": ["test"],
            }

            response = client.post("/generate/tldr", json=topic_data)
            assert response.status_code == 200

            data = response.json()
            # Legacy format should work
            assert "topic" in data
            assert "content" in data


class TestStandardizedErrorHandling:
    """Test standardized error response formats."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_404_error_format(self, client):
        """Test 404 errors return proper format."""
        response = client.get("/api/content-generator/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed_error_format(self, client):
        """Test method not allowed errors."""
        response = client.post("/api/content-generator/health")
        assert response.status_code == 405

    def test_validation_error_format(self, client):
        """Test validation errors return proper format."""
        # Send invalid JSON structure
        response = client.post(
            "/api/content-generator/process", json={"invalid": "structure"}
        )
        assert response.status_code == 422


class TestResponseMetadata:
    """Test that response metadata is included."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_metadata_in_success_response(self, client):
        """Test metadata is included in successful responses."""
        response = client.get("/api/content-generator/health")
        assert response.status_code == 200

        data = response.json()
        metadata = data["metadata"]
        assert "timestamp" in metadata
        assert "function" in metadata
        assert metadata["function"] == "content-generator"

    def test_metadata_in_error_response(self, client):
        """Test metadata is included in error responses."""
        invalid_request = {"topics": [], "content_type": "blog"}

        response = client.post("/api/content-generator/process", json=invalid_request)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "error"
        metadata = data["metadata"]
        assert "timestamp" in metadata
        assert "function" in metadata

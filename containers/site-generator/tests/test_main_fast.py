#!/usr/bin/env python3
"""
Fast API tests for site-generator FastAPI endpoints.

Tests the HTTP REST API with contract-based mocking for fast execution.
"""

import json
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from main import app
from models import GenerationRequest, GenerationStatus, SiteTheme

from tests.contracts.blob_storage_contract import RankedContentContract


class TestSiteGeneratorAPI:
    """Fast API tests for site-generator endpoints."""

    @pytest.fixture
    def client(self):
        """Test client for FastAPI app."""
        return TestClient(app)

    @pytest.fixture
    def mock_processor_for_api(self, mock_blob_client, mock_template_manager):
        """Mock processor for API tests with dependency injection."""
        with patch("main.processor") as mock_proc:
            # Configure the mock processor
            mock_proc.blob_client = mock_blob_client
            mock_proc.template_manager = mock_template_manager
            mock_proc.generation_status = {}

            # Mock async methods
            async def mock_generate_site(site_id, request):
                mock_proc.generation_status[site_id] = {
                    "status": GenerationStatus.COMPLETED,
                    "started_at": "2025-08-24T10:00:00Z",
                    "completed_at": "2025-08-24T10:01:00Z",
                    "progress": "Site generation completed successfully",
                }
                return {"site_id": site_id, "status": "completed"}

            async def mock_get_generation_status(site_id):
                from models import GenerationStatusResponse

                if site_id in mock_proc.generation_status:
                    status_data = mock_proc.generation_status[site_id]
                    return GenerationStatusResponse(
                        site_id=site_id,
                        status=status_data["status"],
                        started_at=status_data["started_at"],
                        progress=status_data["progress"],
                    )
                return GenerationStatusResponse(
                    site_id=site_id, status=GenerationStatus.NOT_FOUND
                )

            mock_proc.generate_site = mock_generate_site
            mock_proc.get_generation_status = mock_get_generation_status

            yield mock_proc

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_generate_site_endpoint_success(self, client, mock_processor_for_api):
        """Test successful site generation via API."""
        request_data = {
            "content_source": "ranked",
            "theme": "modern",
            "max_articles": 5,
            "site_title": "Test AI Content Farm",
            "site_description": "Test site for AI content curation",
        }

        response = client.post("/api/sites/generate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "site_id" in data
        assert data["message"] == "Site generation started"

    def test_generate_site_endpoint_validation_error(self, client):
        """Test site generation with invalid request data."""
        # Missing required fields
        invalid_request = {
            "theme": "modern",
            # Missing content_source, site_title, site_description
        }

        response = client.post("/api/sites/generate", json=invalid_request)

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    def test_get_generation_status_endpoint(self, client, mock_processor_for_api):
        """Test getting site generation status via API."""
        site_id = "test-site-123"

        # First, start a generation to create status
        request_data = {
            "content_source": "ranked",
            "theme": "modern",
            "max_articles": 5,
            "site_title": "Test Site",
            "site_description": "Test Description",
        }

        generate_response = client.post("/api/sites/generate", json=request_data)
        assert generate_response.status_code == 200

        # Get the site_id from response
        site_id = generate_response.json()["site_id"]

        # Now check status
        status_response = client.get(f"/api/sites/{site_id}/status")

        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["site_id"] == site_id
        assert status_data["status"] == "completed"
        assert "started_at" in status_data

    def test_get_nonexistent_site_status(self, client, mock_processor_for_api):
        """Test getting status for non-existent site."""
        nonexistent_site_id = "nonexistent-site-456"

        response = client.get(f"/api/sites/{nonexistent_site_id}/status")

        assert response.status_code == 200  # Should return 200 with NOT_FOUND status
        data = response.json()
        assert data["site_id"] == nonexistent_site_id
        assert data["status"] == "not_found"

    def test_list_sites_endpoint(self, client, mock_processor_for_api):
        """Test listing generated sites."""
        # Mock some sites in the processor
        mock_processor_for_api.generation_status = {
            "site-1": {"status": "completed", "started_at": "2025-08-24T10:00:00Z"},
            "site-2": {"status": "in_progress", "started_at": "2025-08-24T10:05:00Z"},
        }

        response = client.get("/api/sites")

        assert response.status_code == 200
        data = response.json()
        assert "sites" in data
        assert len(data["sites"]) == 2

    def test_api_content_type_validation(self, client):
        """Test API validates Content-Type header."""
        # Test with invalid content type
        response = client.post(
            "/api/sites/generate",
            data="invalid-data",
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 422

    def test_api_response_format_consistency(self, client, mock_processor_for_api):
        """Test all API responses follow consistent format."""
        # Test generation endpoint response format
        request_data = {
            "content_source": "ranked",
            "theme": "modern",
            "max_articles": 5,
            "site_title": "Test Site",
            "site_description": "Test Description",
        }

        response = client.post("/api/sites/generate", json=request_data)
        data = response.json()

        # Should have standard response format
        assert "status" in data
        assert data["status"] in ["success", "error"]
        if data["status"] == "success":
            assert "site_id" in data
            assert "message" in data

    def test_error_handling_in_api(self, client):
        """Test API error handling with proper HTTP status codes."""
        # Test various error scenarios
        test_cases = [
            {
                "data": {},  # Empty request
                "expected_status": 422,
                "description": "Empty request body",
            },
            {
                "data": {"invalid": "data"},  # Invalid fields
                "expected_status": 422,
                "description": "Invalid request fields",
            },
        ]

        for case in test_cases:
            response = client.post("/api/sites/generate", json=case["data"])
            assert (
                response.status_code == case["expected_status"]
            ), f"Failed for: {case['description']}"

    def test_api_performance_expectations(self, client, mock_processor_for_api):
        """Test API responds within performance expectations."""
        import time

        request_data = {
            "content_source": "ranked",
            "theme": "modern",
            "max_articles": 5,
            "site_title": "Performance Test Site",
            "site_description": "Testing API performance",
        }

        start_time = time.time()
        response = client.post("/api/sites/generate", json=request_data)
        end_time = time.time()

        # API should respond quickly (under 1 second for mocked operations)
        response_time = end_time - start_time
        assert response_time < 1.0, f"API response too slow: {response_time:.2f}s"
        assert response.status_code == 200

    def test_theme_validation(self, client):
        """Test theme parameter validation."""
        valid_themes = ["modern", "classic", "minimal"]

        for theme in valid_themes:
            request_data = {
                "content_source": "ranked",
                "theme": theme,
                "max_articles": 5,
                "site_title": "Theme Test Site",
                "site_description": "Testing theme validation",
            }

            response = client.post("/api/sites/generate", json=request_data)
            # Should accept valid themes
            assert response.status_code in [200, 202]

        # Test invalid theme
        invalid_request = {
            "content_source": "ranked",
            "theme": "invalid_theme",
            "max_articles": 5,
            "site_title": "Theme Test Site",
            "site_description": "Testing theme validation",
        }

        response = client.post("/api/sites/generate", json=invalid_request)
        assert response.status_code == 422  # Should reject invalid theme

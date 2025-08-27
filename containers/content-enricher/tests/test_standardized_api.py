#!/usr/bin/env python3
"""
Standardized API Tests for Content Enricher

Tests for the standardized API endpoints following the FastAPI-native patterns.
"""

from unittest.mock import MagicMock, patch

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
        response = client.get("/api/content-enricher/health")
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
        assert metadata["function"] == "content-enricher"
        assert "timestamp" in metadata

    def test_api_status_endpoint_format(self, client):
        """Test standardized status endpoint returns proper format."""
        response = client.get("/api/content-enricher/status")
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
        assert status_data["service"] == "content-enricher"
        assert "stats" in status_data
        assert "pipeline" in status_data

    def test_api_process_endpoint_success(self, client):
        """Test standardized process endpoint with valid request."""
        # Mock the enrichment function
        with patch("main.enrich_content_batch") as mock_enrich:
            mock_enrich.return_value = {
                "enriched_items": [
                    {
                        "id": "test-item-1",
                        "title": "Test Article",
                        "content": "Test content",
                        "enrichment": {
                            "sentiment": "positive",
                            "keywords": ["test", "article"],
                            "summary": "Test summary",
                        },
                    }
                ],
                "metadata": {
                    "enrichment_id": "enrich-123",
                    "processed_at": "2024-01-01T00:00:00Z",
                },
            }

            request_data = {
                "items": [
                    {
                        "id": "test-item-1",
                        "title": "Test Article",
                        "clean_title": "Test Article",
                        "normalized_score": 0.8,
                        "engagement_score": 0.7,
                        "source_url": "https://example.com/article1",
                        "content_type": "text",
                    }
                ]
            }

            response = client.post("/api/content-enricher/process", json=request_data)
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
            assert "Successfully enriched" in data["message"]
            assert data["errors"] is None

            # Check enrichment data
            enrichment_data = data["data"]
            assert "enriched_items" in enrichment_data
            assert len(enrichment_data["enriched_items"]) == 1

    def test_api_process_endpoint_error_handling(self, client):
        """Test standardized process endpoint error handling."""
        # Test with malformed request
        invalid_request = {
            "items": [
                {
                    "id": "test-item-1",
                    # Missing required fields
                }
            ]
        }

        response = client.post("/api/content-enricher/process", json=invalid_request)
        assert response.status_code == 422  # Validation error

        # Test with enrichment failure
        with patch("main.enrich_content_batch") as mock_enrich:
            mock_enrich.side_effect = Exception("Enrichment failed")

            valid_request = {
                "items": [
                    {
                        "id": "test-item-1",
                        "title": "Test Article",
                        "clean_title": "Test Article",
                        "normalized_score": 0.8,
                        "engagement_score": 0.7,
                        "source_url": "https://example.com/article1",
                        "content_type": "text",
                    }
                ]
            }

            response = client.post("/api/content-enricher/process", json=valid_request)
            assert (
                response.status_code == 200
            )  # FastAPI-native returns 200 with error status

            data = response.json()
            assert data["status"] == "error"
            assert "enrichment failed" in data["message"].lower()

    def test_api_docs_endpoint(self, client):
        """Test standardized docs endpoint."""
        response = client.get("/api/content-enricher/docs")
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
        assert docs_data["service"] == "content-enricher"
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
        assert data["status"] == "healthy"

    def test_legacy_enrich_endpoint_unchanged(self, client):
        """Test that legacy enrich endpoint still works."""
        with patch("main.enrich_content_batch") as mock_enrich:
            mock_enrich.return_value = {
                "enriched_items": [
                    {
                        "id": "test-item-1",
                        "title": "Test Article",
                        "content": "Test content",
                        "enrichment": {
                            "sentiment": "positive",
                            "keywords": ["test", "article"],
                        },
                    }
                ],
                "metadata": {
                    "enrichment_id": "enrich-123",
                    "processed_at": "2024-01-01T00:00:00Z",
                },
            }

            request_data = {
                "items": [
                    {
                        "id": "test-item-1",
                        "title": "Test Article",
                        "clean_title": "Test Article",
                        "normalized_score": 0.8,
                        "engagement_score": 0.7,
                        "source_url": "https://example.com/article1",
                        "content_type": "text",
                    }
                ]
            }

            response = client.post("/enrich", json=request_data)
            assert response.status_code == 200

            data = response.json()
            # Legacy format should work
            assert "enriched_items" in data
            assert "metadata" in data


class TestStandardizedErrorHandling:
    """Test standardized error response formats."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_404_error_format(self, client):
        """Test 404 errors return proper format."""
        response = client.get("/api/content-enricher/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed_error_format(self, client):
        """Test method not allowed errors."""
        response = client.post("/api/content-enricher/health")
        assert response.status_code == 405

    def test_validation_error_format(self, client):
        """Test validation errors return proper format."""
        # Send invalid JSON
        response = client.post("/api/content-enricher/process", json={})
        assert response.status_code == 422


class TestResponseTimingMetadata:
    """Test that response timing metadata is included."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_execution_time_in_success_response(self, client):
        """Test execution time is included in successful responses."""
        response = client.get("/api/content-enricher/health")
        assert response.status_code == 200

        data = response.json()
        metadata = data["metadata"]
        assert "timestamp" in metadata
        assert "function" in metadata
        assert metadata["function"] == "content-enricher"

    def test_execution_time_in_error_response(self, client):
        """Test execution time is included in error responses."""
        with patch("main.enrich_content_batch") as mock_enrich:
            mock_enrich.side_effect = Exception("Test error")

            request_data = {
                "items": [
                    {
                        "id": "test-item-1",
                        "title": "Test Article",
                        "clean_title": "Test Article",
                        "normalized_score": 0.8,
                        "engagement_score": 0.7,
                        "source_url": "https://example.com/article1",
                        "content_type": "text",
                    }
                ]
            }

            response = client.post("/api/content-enricher/process", json=request_data)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "error"
            metadata = data["metadata"]
            assert "timestamp" in metadata
            assert "function" in metadata

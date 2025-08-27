"""
Test suite for Content Ranker standardized API endpoints.

Tests the new standardized API format (/api/content-ranker/*) alongside
backward compatibility with legacy endpoints. Ensures consistent
StandardResponse format across all endpoints.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestStandardizedAPIEndpoints:
    """Test the new standardized API endpoints."""

    def test_api_health_endpoint_format(self):
        """Test /api/content-ranker/health returns StandardResponse format."""
        with patch("main.health_check") as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "azure_connectivity": "connected",
            }

            response = client.get("/api/content-ranker/health")

            assert response.status_code == 200
            data = response.json()

            # Verify StandardResponse format
            assert data["status"] == "success"
            assert data["message"] == "Content ranker service is healthy"
            assert "data" in data
            assert "metadata" in data

            # Verify health data structure
            health_data = data["data"]
            assert health_data["service"] == "content-ranker"
            assert health_data["status"] == "healthy"
            assert health_data["version"] == "1.0.0"
            assert "dependencies" in health_data

            # Verify metadata
            metadata = data["metadata"]
            assert "execution_time_ms" in metadata
            assert metadata["function"] == "content-ranker"
            assert metadata["version"] == "1.0.0"

    @patch("main.ranker_service")
    def test_api_status_endpoint_format(self, mock_service):
        """Test /api/content-ranker/status returns StandardResponse format."""
        # Mock service status
        mock_service.get_ranking_status = AsyncMock(
            return_value={
                "total_ranked": 150,
                "last_ranking": "2025-08-27T10:00:00Z",
                "average_score": 0.75,
            }
        )

        response = client.get("/api/content-ranker/status")

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse format
        assert data["status"] == "success"
        assert data["message"] == "Content ranker status retrieved successfully"
        assert "data" in data
        assert "metadata" in data

        # Verify status data structure
        status_data = data["data"]
        assert status_data["service"] == "content-ranker"
        assert status_data["status"] == "running"
        assert "stats" in status_data
        assert status_data["stats"]["total_ranked"] == 150

        # Verify metadata
        metadata = data["metadata"]
        assert "execution_time_ms" in metadata
        assert metadata["function"] == "content-ranker"

    @patch("main.ranker_service")
    def test_api_process_endpoint_success(self, mock_service):
        """Test /api/content-ranker/process with successful ranking."""
        # Mock ranking service
        mock_service.rank_specific_content = AsyncMock(
            return_value=[
                {"id": "item_001", "title": "Test Content", "score": 0.85, "rank": 1},
                {"id": "item_002", "title": "Another Test", "score": 0.72, "rank": 2},
            ]
        )

        request_data = {
            "content_items": [
                {
                    "id": "item_001",
                    "title": "Test Content",
                    "content": "Test content body",
                }
            ],
            "weights": {"engagement": 0.5, "recency": 0.3, "topic_relevance": 0.2},
        }

        response = client.post("/api/content-ranker/process", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse format
        assert data["status"] == "success"
        assert "Successfully ranked" in data["message"]
        assert "data" in data
        assert "metadata" in data

        # Verify ranking result data
        result_data = data["data"]
        assert "ranked_items" in result_data
        assert "metadata" in result_data
        assert len(result_data["ranked_items"]) == 2

        # Verify ranking metadata
        ranking_metadata = result_data["metadata"]
        assert ranking_metadata["total_items_processed"] == 1
        assert ranking_metadata["items_returned"] == 2
        assert ranking_metadata["ranking_algorithm"] == "multi_factor_composite"

    @patch("main.ranker_service")
    def test_api_process_endpoint_error_handling(self, mock_service):
        """Test /api/content-ranker/process error handling."""
        # Mock service error
        mock_service.rank_specific_content = AsyncMock(
            side_effect=RuntimeError("Ranking failed")
        )

        request_data = {
            "content_items": [{"id": "test", "title": "Test"}],
            "weights": {"engagement": 1.0},
        }

        response = client.post("/api/content-ranker/process", json=request_data)

        assert response.status_code == 500
        data = response.json()

        # Verify standardized error format
        assert data["status"] == "error"
        assert (
            data["message"] == "Ranking failed"
        )  # Backward compatibility: exact error message
        assert "Failed to rank content items" in str(data["errors"])  # Details field
        assert "metadata" in data
        assert data["metadata"]["function"] == "content-ranker"

    def test_api_docs_endpoint(self):
        """Test /api/content-ranker/docs returns API documentation."""
        response = client.get("/api/content-ranker/docs")

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse format
        assert data["status"] == "success"
        assert data["message"] == "Content ranker API documentation"
        assert "data" in data

        # Verify documentation structure
        docs = data["data"]
        assert docs["service"] == "content-ranker"
        assert docs["version"] == "1.0.0"
        assert "endpoints" in docs
        assert "ranking_factors" in docs
        assert "sample_request" in docs

        # Verify endpoint documentation
        endpoints = docs["endpoints"]
        assert "/api/content-ranker/health" in endpoints
        assert "/api/content-ranker/status" in endpoints
        assert "/api/content-ranker/process" in endpoints


class TestBackwardCompatibility:
    """Test that legacy endpoints still work unchanged."""

    def test_legacy_health_endpoint_unchanged(self):
        """Test legacy /health endpoint maintains original format."""
        with patch("main.health_check") as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "azure_connectivity": "connected",
            }

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()

            # Should maintain legacy format
            assert "status" in data
            assert "service" in data
            assert data["service"] == "content-ranker"

    def test_legacy_root_endpoint_standardized(self):
        """Test root endpoint now uses standardized format."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Root endpoint should be updated to StandardResponse
        assert data["status"] == "success"
        assert data["message"] == "Content Ranker API running"
        assert "data" in data

        service_data = data["data"]
        assert service_data["service"] == "content-ranker"
        assert "endpoints" in service_data

    @patch("main.ranker_service")
    def test_legacy_rank_endpoint_unchanged(self, mock_service):
        """Test legacy /rank endpoint maintains original format."""
        mock_service.rank_specific_content = AsyncMock(
            return_value=[{"id": "test", "score": 0.8}]
        )

        request_data = {
            "content_items": [{"id": "test", "title": "Test"}],
            "weights": {"engagement": 1.0},
        }

        response = client.post("/rank", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Should maintain legacy RankingResponse format
        assert "ranked_items" in data
        assert "metadata" in data


class TestStandardizedErrorHandling:
    """Test that all error conditions return StandardResponse format."""

    def test_404_error_format(self):
        """Test 404 errors use standardized format."""
        response = client.get("/api/content-ranker/nonexistent")

        assert response.status_code == 404
        data = response.json()
        print("404 response:", data)  # Debug output

        # Should use standardized error format
        assert data["status"] == "error"
        assert data["message"] == "endpoint not found"
        assert "metadata" in data
        assert data["metadata"]["function"] == "content-ranker"

    def test_method_not_allowed_error_format(self):
        """Test 405 errors use standardized format."""
        response = client.post("/api/content-ranker/health")  # GET endpoint

        assert response.status_code == 405
        data = response.json()

        # Should use standardized error format
        assert data["status"] == "error"
        assert "Method not allowed" in data["message"]
        assert data["metadata"]["function"] == "content-ranker"

    def test_validation_error_format(self):
        """Test validation errors use standardized format."""
        # Send invalid request to process endpoint
        response = client.post("/api/content-ranker/process", json={})

        assert response.status_code == 422
        data = response.json()

        # Should use standardized validation error format
        assert data["status"] == "error"
        assert "validation" in data["message"].lower()
        assert "errors" in data
        assert data["metadata"]["function"] == "content-ranker"


class TestResponseTimingMetadata:
    """Test that all responses include execution time metadata."""

    def test_execution_time_in_success_response(self):
        """Test successful responses include execution time."""
        with patch("main.health_check") as mock_health:
            mock_health.return_value = {"status": "healthy"}

            response = client.get("/api/content-ranker/health")

            assert response.status_code == 200
            data = response.json()

            metadata = data["metadata"]
            assert "execution_time_ms" in metadata
            assert isinstance(metadata["execution_time_ms"], int)
            assert metadata["execution_time_ms"] >= 1

    @patch("main.ranker_service")
    def test_execution_time_in_error_response(self, mock_service):
        """Test error responses include execution time."""
        mock_service.rank_specific_content = AsyncMock(
            side_effect=RuntimeError("Test error")
        )

        request_data = {
            "content_items": [{"id": "test", "title": "Test"}],
            "weights": {"engagement": 1.0},
        }

        response = client.post("/api/content-ranker/process", json=request_data)

        assert response.status_code == 500
        data = response.json()

        metadata = data["metadata"]
        assert "execution_time_ms" in metadata
        assert isinstance(metadata["execution_time_ms"], int)
        assert metadata["execution_time_ms"] >= 1

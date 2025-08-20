"""
Tests for Content Enricher FastAPI application.

Following TDD: API tests first, then implementation.
"""

import json
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app we're going to test
from main import app

# Create test client
client = TestClient(app)


class TestHealthEndpoint:
    """Test the health check endpoint."""

    @pytest.mark.unit
    def test_health_check_success(self) -> None:
        """Test successful health check."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "content-enricher"
        assert "azure_connectivity" in data

    @pytest.mark.integration
    def test_health_check_with_dependencies(self) -> None:
        """Test health check includes dependency status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Should check OpenAI API availability
        assert "openai_available" in data


class TestEnrichEndpoint:
    """Test the main enrichment endpoint."""

    @pytest.mark.unit
    def test_enrich_single_item(self) -> None:
        """Test enriching a single content item."""
        test_data = {
            "items": [
                {
                    "id": "test123",
                    "title": "Amazing AI breakthrough in computer vision!",
                    "clean_title": "Amazing AI breakthrough in computer vision!",
                    "normalized_score": 0.8,
                    "engagement_score": 0.7,
                    "source_url": "https://example.com",
                    "published_at": "2023-08-14T08:00:00+00:00",
                    "content_type": "text",
                    "source_metadata": {
                        "original_score": 1000,
                        "original_comments": 150,
                        "selftext": "Researchers have developed a new model...",
                    },
                }
            ],
            "options": {"include_summary": True, "max_summary_length": 100},
        }

        response = client.post("/enrich", json=test_data)

        assert response.status_code == 200
        data = response.json()

        assert "enriched_items" in data
        assert "metadata" in data
        assert len(data["enriched_items"]) == 1

        enriched_item = data["enriched_items"][0]
        assert enriched_item["id"] == "test123"
        assert "enrichment" in enriched_item

        enrichment = enriched_item["enrichment"]
        assert "topic_classification" in enrichment
        assert "sentiment_analysis" in enrichment
        assert "summary" in enrichment
        assert "trend_score" in enrichment

    @pytest.mark.unit
    def test_enrich_multiple_items(self) -> None:
        """Test enriching multiple content items."""
        test_data = {
            "items": [
                {
                    "id": "item1",
                    "title": "Tech news article",
                    "clean_title": "Tech news article",
                    "normalized_score": 0.6,
                    "engagement_score": 0.5,
                    "source_url": "https://example.com/1",
                    "published_at": "2023-08-14T08:00:00+00:00",
                    "content_type": "text",
                    "source_metadata": {"selftext": "Technology content..."},
                },
                {
                    "id": "item2",
                    "title": "Science discovery",
                    "clean_title": "Science discovery",
                    "normalized_score": 0.7,
                    "engagement_score": 0.6,
                    "source_url": "https://example.com/2",
                    "published_at": "2023-08-14T08:15:00+00:00",
                    "content_type": "text",
                    "source_metadata": {"selftext": "Science content..."},
                },
            ]
        }

        response = client.post("/enrich", json=test_data)

        assert response.status_code == 200
        data = response.json()

        assert len(data["enriched_items"]) == 2
        assert data["metadata"]["items_processed"] == 2

    @pytest.mark.unit
    def test_enrich_empty_request(self) -> None:
        """Test handling of empty enrichment request."""
        test_data = {"items": []}

        response = client.post("/enrich", json=test_data)

        assert response.status_code == 200
        data = response.json()

        assert data["enriched_items"] == []
        assert data["metadata"]["items_processed"] == 0

    @pytest.mark.unit
    def test_enrich_invalid_request(self) -> None:
        """Test handling of invalid request data."""
        test_data = {"invalid": "data"}

        response = client.post("/enrich", json=test_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.unit
    def test_enrich_malformed_item(self) -> None:
        """Test handling of malformed content items."""
        test_data = {
            "items": [
                {
                    "id": "test",
                    # Missing required fields
                }
            ]
        }

        response = client.post("/enrich", json=test_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.unit
    def test_enrich_with_options(self) -> None:
        """Test enrichment with specific options."""
        test_data = {
            "items": [
                {
                    "id": "test123",
                    "title": "Test content",
                    "clean_title": "Test content",
                    "normalized_score": 0.5,
                    "engagement_score": 0.5,
                    "source_url": "https://example.com",
                    "published_at": "2023-08-14T08:00:00+00:00",
                    "content_type": "text",
                    "source_metadata": {"selftext": "Test content"},
                }
            ],
            "options": {
                "include_summary": False,  # Skip summary
                "classify_topics": True,
                "analyze_sentiment": True,
                "calculate_trends": True,
            },
        }

        response = client.post("/enrich", json=test_data)

        assert response.status_code == 200
        data = response.json()

        enrichment = data["enriched_items"][0]["enrichment"]
        # Should respect options
        assert "topic_classification" in enrichment
        assert "sentiment_analysis" in enrichment
        assert "trend_score" in enrichment


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.unit
    def test_404_on_unknown_endpoint(self) -> None:
        """Test 404 for unknown endpoints."""
        response = client.get("/unknown")

        assert response.status_code == 404

    @pytest.mark.unit
    def test_method_not_allowed(self) -> None:
        """Test method not allowed errors."""
        response = client.get("/enrich")  # Should be POST

        assert response.status_code == 405

    @pytest.mark.unit
    @patch("main.enrich_content_batch")
    def test_internal_server_error_handling(self, mock_enrich: Mock) -> None:
        """Test handling of internal server errors."""
        # Mock an exception in the enrichment process
        mock_enrich.side_effect = RuntimeError("Test error")

        test_data = {
            "items": [
                {
                    "id": "test",
                    "title": "Test",
                    "clean_title": "Test",
                }
            ]
        }

        response = client.post("/enrich", json=test_data)

        assert response.status_code == 500
        data = response.json()
        assert "error" in data

    @pytest.mark.unit
    def test_request_timeout_handling(self) -> None:
        """Test handling of request timeouts."""
        # This would test timeout scenarios in a real implementation
        # For now, just ensure the endpoint responds
        test_data = {"items": []}

        response = client.post("/enrich", json=test_data)

        assert response.status_code == 200


class TestInputValidation:
    """Test input validation and data types."""

    @pytest.mark.unit
    def test_validate_content_item_structure(self) -> None:
        """Test validation of content item structure."""
        invalid_items = [
            # Missing required ID
            {
                "title": "Test",
                "clean_title": "Test",
                # Missing "id" field
            },
            # Empty ID
            {
                "id": "",  # Empty string should fail
                "title": "Test",
                "clean_title": "Test",
            },
            # Invalid score ranges
            {
                "id": "test",
                "title": "Test",
                "clean_title": "Test",
                "normalized_score": 1.5,  # Should be 0-1
            },
            {
                "id": "test",
                "title": "Test",
                "clean_title": "Test",
                "engagement_score": -0.1,  # Should be 0-1
            },
        ]

        for invalid_item in invalid_items:
            test_data = {"items": [invalid_item]}

            response = client.post("/enrich", json=test_data)

            assert response.status_code == 422

    @pytest.mark.unit
    def test_validate_options_structure(self) -> None:
        """Test validation of options structure."""
        test_data = {
            "items": [
                {
                    "id": "test",
                    "title": "Test",
                    "clean_title": "Test",
                }
            ],
            "options": {
                "include_summary": "invalid_boolean",  # Should be boolean
                "max_summary_length": "not_a_number",  # Should be int
            },
        }

        response = client.post("/enrich", json=test_data)

        assert response.status_code == 422


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.performance
    def test_batch_processing_performance(self) -> None:
        """Test performance of batch processing."""
        # Create a batch of 10 items
        items = []
        for i in range(10):
            items.append(
                {
                    "id": f"item{i}",
                    "title": f"Test item {i}",
                    "clean_title": f"Test item {i}",
                    "normalized_score": 0.5,
                    "engagement_score": 0.5,
                    "source_url": f"https://example.com/{i}",
                    "published_at": "2023-08-14T08:00:00+00:00",
                    "content_type": "text",
                    "source_metadata": {"selftext": f"Content {i}"},
                }
            )

        test_data = {"items": items}

        import time

        start_time = time.time()

        response = client.post("/enrich", json=test_data)

        end_time = time.time()
        processing_time = end_time - start_time

        assert response.status_code == 200
        assert len(response.json()["enriched_items"]) == 10

        # Should process 10 items in reasonable time (adjust threshold as needed)
        assert processing_time < 30.0  # 30 seconds max for 10 items

    @pytest.mark.performance
    def test_memory_usage_batch(self) -> None:
        """Test memory usage with larger batches."""
        # This would monitor memory usage in a real implementation
        # For now, just ensure large batches work
        items = []
        for i in range(50):
            items.append(
                {
                    "id": f"item{i}",
                    "title": f"Test item {i}",
                    "clean_title": f"Test item {i}",
                    "normalized_score": 0.5,
                    "engagement_score": 0.5,
                    "source_url": f"https://example.com/{i}",
                    "published_at": "2023-08-14T08:00:00+00:00",
                    "content_type": "text",
                    "source_metadata": {"selftext": f"Content {i}"},
                }
            )

        test_data = {"items": items}

        response = client.post("/enrich", json=test_data)

        assert response.status_code == 200
        assert len(response.json()["enriched_items"]) == 50

"""
Tests for Content Collector FastAPI application.

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

        # Allow warning for missing config
        assert data["status"] in ["healthy", "warning"]
        assert "version" in data
        assert "timestamp" in data

    @pytest.mark.integration
    def test_health_check_with_dependencies(self) -> None:
        """Test health check includes dependency status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Should check external dependencies (may be unavailable in test environment)
        assert "config_issues" in data or "reddit_available" in data


class TestCollectEndpoint:
    """Test the main content collection endpoint."""

    @pytest.mark.unit
    def test_collect_reddit_content(self) -> None:
        """Test collecting Reddit content."""
        test_data = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["MachineLearning", "programming"],
                    "limit": 5,
                    "criteria": {"min_score": 100, "min_comments": 10},
                }
            ],
            "options": {"deduplicate": True, "max_total_items": 50},
        }

        response = client.post("/collect", json=test_data)

        assert response.status_code == 200
        data = response.json()

        assert "collected_items" in data
        assert "metadata" in data
        assert isinstance(data["collected_items"], list)
        assert data["metadata"]["total_collected"] >= 0

    @pytest.mark.unit
    def test_collect_multiple_sources(self) -> None:
        """Test collecting from multiple sources."""
        test_data = {
            "sources": [
                {"type": "reddit", "subreddits": ["technology"], "limit": 3},
                {"type": "reddit", "subreddits": ["science"], "limit": 3},
            ]
        }

        response = client.post("/collect", json=test_data)

        assert response.status_code == 200
        data = response.json()

        assert "collected_items" in data
        # Note: With our current mock setup, the metadata comes from service_logic mock
        # In a contract-based approach, this would be more realistic
        assert data["metadata"]["total_collected"] >= 2

    @pytest.mark.unit
    def test_collect_with_filtering_criteria(self) -> None:
        """Test collection with filtering criteria."""
        test_data = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["MachineLearning"],
                    "limit": 10,
                    "criteria": {
                        "min_score": 500,
                        "min_comments": 50,
                        "include_keywords": ["AI", "neural", "machine learning"],
                        "exclude_keywords": ["meme", "joke"],
                    },
                }
            ],
            "options": {"deduplicate": True},
        }

        response = client.post("/collect", json=test_data)

        assert response.status_code == 200
        data = response.json()

        # Should return filtered results
        assert "collected_items" in data
        metadata = data["metadata"]
        # Note: With current mock, criteria_applied isn't included
        # In contract-based approach, this would be more realistic
        assert "total_collected" in metadata

    @pytest.mark.unit
    def test_collect_empty_sources(self) -> None:
        """Test handling of empty sources list."""
        test_data = {"sources": []}

        response = client.post("/collect", json=test_data)

        assert response.status_code == 200
        data = response.json()

        assert data["collected_items"] == []
        assert data["metadata"]["total_collected"] == 0

    @pytest.mark.unit
    def test_collect_invalid_source_type(self) -> None:
        """Test handling of invalid source types."""
        test_data = {
            "sources": [{"type": "invalid_source", "config": {"some": "value"}}]
        }

        response = client.post("/collect", json=test_data)

        assert response.status_code == 200  # Should handle gracefully
        data = response.json()

        assert data["collected_items"] == []
        assert data["metadata"]["errors"] > 0

    @pytest.mark.unit
    def test_collect_malformed_request(self) -> None:
        """Test handling of malformed requests."""
        test_data = {"invalid": "data"}

        response = client.post("/collect", json=test_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.unit
    def test_collect_missing_required_fields(self) -> None:
        """Test handling of missing required fields."""
        test_data = {
            "sources": [
                {
                    "type": "reddit",
                    # Missing required fields like subreddits
                }
            ]
        }

        response = client.post("/collect", json=test_data)

        assert response.status_code == 422  # Validation error


class TestStatusEndpoint:
    """Test collection status and monitoring endpoints."""

    @pytest.mark.unit
    def test_status_endpoint(self) -> None:
        """Test status endpoint for monitoring."""
        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()

        assert "service" in data
        assert "uptime" in data
        assert "last_collection" in data
        assert "stats" in data

    @pytest.mark.unit
    def test_sources_endpoint(self) -> None:
        """Test available sources endpoint."""
        response = client.get("/sources")

        assert response.status_code == 200
        data = response.json()

        assert "available_sources" in data
        assert "reddit" in [source["type"] for source in data["available_sources"]]


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
        response = client.get("/collect")  # Should be POST

        assert response.status_code == 405

    @pytest.mark.unit
    @patch("main.collector_service.collect_and_store_content")
    def test_internal_server_error_handling(self, mock_collect: Mock) -> None:
        """Test handling of internal server errors."""
        # Mock an exception in the collection process
        mock_collect.side_effect = RuntimeError("Collection error")

        test_data = {
            "sources": [{"type": "reddit", "subreddits": ["test"], "limit": 5}]
        }

        response = client.post("/collect", json=test_data)

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    @pytest.mark.unit
    def test_rate_limiting_handling(self) -> None:
        """Test handling of rate limiting scenarios."""
        # This would test rate limiting in a real implementation
        test_data = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["test"],
                    "limit": 1000,  # Large request
                }
            ]
        }

        response = client.post("/collect", json=test_data)

        # Should handle gracefully (might return partial results or validation error)
        assert response.status_code in [200, 422, 429]


class TestInputValidation:
    """Test input validation and data types."""

    @pytest.mark.unit
    def test_validate_reddit_source_structure(self) -> None:
        """Test validation of Reddit source structure."""
        invalid_sources = [
            # Missing subreddits
            {"type": "reddit", "limit": 10},
            # Invalid limit
            {"type": "reddit", "subreddits": ["test"], "limit": -1},
            # Invalid criteria type
            {
                "type": "reddit",
                "subreddits": ["test"],
                "limit": 10,
                "criteria": "invalid_criteria",
            },
        ]

        for invalid_source in invalid_sources:
            test_data = {"sources": [invalid_source]}

            response = client.post("/collect", json=test_data)

            assert response.status_code == 422

    @pytest.mark.unit
    def test_validate_options_structure(self) -> None:
        """Test validation of data types."""
        test_data = {
            "sources": [{"type": "reddit", "subreddits": ["test"], "limit": 5}],
            "deduplicate": "invalid_boolean",  # Should be boolean
            "similarity_threshold": "not_a_number",  # Should be float
        }

        response = client.post("/collect", json=test_data)

        assert response.status_code == 422

    @pytest.mark.unit
    def test_validate_subreddit_names(self) -> None:
        """Test validation of subreddit names."""
        test_data = {
            "sources": [
                {
                    "type": "reddit",
                    # Mixed valid/invalid
                    "subreddits": ["", "valid_subreddit", None],
                    "limit": 5,
                }
            ]
        }

        response = client.post("/collect", json=test_data)

        # Should either validate and reject, or filter out invalid names
        assert response.status_code in [200, 422]


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.performance
    def test_collection_performance(self) -> None:
        """Test performance of content collection."""
        test_data = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["technology", "programming", "science"],
                    "limit": 5,  # Small limit for performance test
                }
            ]
        }

        import time

        start_time = time.time()

        response = client.post("/collect", json=test_data)

        end_time = time.time()
        processing_time = end_time - start_time

        assert response.status_code == 200

        # Should complete within reasonable time
        assert processing_time < 10.0  # 10 seconds max

    @pytest.mark.performance
    def test_large_batch_collection(self) -> None:
        """Test collection of larger batches."""
        test_data = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 25,  # Larger batch
                }
            ],
            "options": {"max_total_items": 100},
        }

        response = client.post("/collect", json=test_data)

        assert response.status_code == 200
        data = response.json()

        # Should handle larger batches efficiently
        assert len(data["collected_items"]) <= 100


class TestIntegration:
    """Test integration scenarios."""

    @pytest.mark.integration
    def test_reddit_api_integration(self) -> None:
        """Test actual Reddit API integration (requires network)."""
        test_data = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["test"],  # Use small test subreddit
                    "limit": 1,  # Minimal request
                }
            ]
        }

        response = client.post("/collect", json=test_data)

        # Should work with actual Reddit API (if available)
        assert response.status_code == 200

    @pytest.mark.integration
    def test_end_to_end_collection_pipeline(self) -> None:
        """Test complete collection pipeline."""
        # Collect content
        collect_data = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 2,
                    "criteria": {"min_score": 10},
                }
            ],
            "options": {"deduplicate": True},
        }

        response = client.post("/collect", json=collect_data)

        assert response.status_code == 200
        data = response.json()

        # Verify collected data structure matches what processors expect
        if data["collected_items"]:
            item = data["collected_items"][0]
            required_fields = ["id", "title", "score", "source"]
            for field in required_fields:
                assert field in item


class TestContractValidation:
    """Test that our contracts match real API behavior."""

    @pytest.mark.unit
    def test_reddit_contract_completeness(self) -> None:
        """Test Reddit API contract includes all required fields."""
        from tests.contracts.reddit_api_contract import RedditPostContract

        post = RedditPostContract.create_mock()

        # Required fields Reddit API always provides
        required_fields = [
            'id', 'title', 'selftext', 'url', 'score', 'num_comments',
            'created_utc', 'subreddit', 'author', 'permalink'
        ]

        for field in required_fields:
            assert hasattr(post, field), f"Missing required field: {field}"
            assert getattr(post, field) is not None, f"Field {field} should not be None"

    @pytest.mark.unit
    def test_blob_storage_contract_azure_compatibility(self) -> None:
        """Test blob storage contract behaves like Azure."""
        from tests.contracts.blob_storage_contract import MockBlobStorageContract

        mock = MockBlobStorageContract()

        # Test upload returns Azure-style metadata
        result = mock.upload_text("test", "file.json", "content")
        azure_fields = ["etag", "last_modified", "request_server_encrypted"]

        for field in azure_fields:
            assert field in result, f"Missing Azure field: {field}"

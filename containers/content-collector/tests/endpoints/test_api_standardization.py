"""
Tests for API Response Standardization (Issue #523)

Tests that verify the fixes for:
1. Inconsistent null/empty value representation
2. Reddit authentication status inconsistency
3. Missing Mastodon source discovery
4. Source registration extensibility
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Add paths for proper imports when running from project root
current_dir = os.path.dirname(os.path.abspath(__file__))
content_collector_dir = os.path.join(current_dir, "../../")
sys.path.insert(0, content_collector_dir)
sys.path.insert(0, os.path.join(content_collector_dir, "../../../"))

from containers.content_collector.main import app

client = TestClient(app)


class TestAPIStandardization:
    """Test suite for API response standardization fixes."""

    def test_health_endpoint_consistent_empty_values(self):
        """Test that health endpoint uses consistent empty value format."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()

        # Verify response structure
        assert "status" in data
        assert "message" in data
        assert "data" in data
        assert "errors" in data
        assert "metadata" in data

        # Verify errors is always an empty list, not null
        assert data["errors"] == []
        assert data["errors"] is not None

        # Verify data structure contains expected health fields
        health_data = data["data"]
        assert "dependencies" in health_data
        assert "issues" in health_data

        # Issues should be empty list, not null
        assert isinstance(health_data["issues"], list)

    def test_sources_endpoint_includes_mastodon(self):
        """Test that sources endpoint dynamically includes Mastodon."""
        response = client.get("/sources")
        assert response.status_code == 200

        data = response.json()
        sources = data["data"]["sources"]

        # Verify all expected sources are present
        expected_sources = ["reddit", "mastodon", "rss", "web"]
        for source_type in expected_sources:
            assert source_type in sources, f"Missing source type: {source_type}"

        # Verify Mastodon configuration
        mastodon = sources["mastodon"]
        assert mastodon["type"] == "mastodon"
        assert "Mastodon social network" in mastodon["description"]
        assert "parameters" in mastodon
        assert "server_url" in mastodon["parameters"]
        assert "hashtags" in mastodon["parameters"]

    @patch(
        "containers.content-collector.source_collectors.SourceCollectorFactory.get_reddit_collector_info"
    )
    def test_reddit_authentication_status_consistency(self, mock_reddit_info):
        """Test that Reddit shows consistent authentication status."""
        # Mock Reddit collector info with valid credentials
        mock_reddit_info.return_value = {
            "recommended_collector": "RedditPRAWCollector",
            "reason": "Valid credentials found",
            "credentials_source": "keyvault",
            "credential_status": {"appears_valid": True},
            "authentication_status": "authenticated",
            "status": "available",
        }

        response = client.get("/sources")
        assert response.status_code == 200

        data = response.json()
        reddit = data["data"]["sources"]["reddit"]

        # Verify authentication status is properly reflected
        assert reddit["authentication"] == "authenticated"
        assert reddit["status"] == "available"

        # Test with invalid credentials
        mock_reddit_info.return_value = {
            "recommended_collector": "RedditPublicCollector",
            "reason": "No credentials found",
            "credentials_source": "none",
            "credential_status": {"appears_valid": False},
            "authentication_status": "unauthenticated",
            "status": "limited",
        }

        response = client.get("/sources")
        assert response.status_code == 200

        data = response.json()
        reddit = data["data"]["sources"]["reddit"]

        assert reddit["authentication"] == "unauthenticated"
        assert reddit["status"] == "limited"

    def test_sources_endpoint_response_consistency(self):
        """Test that sources endpoint follows consistent response format."""
        response = client.get("/sources")
        assert response.status_code == 200

        data = response.json()

        # Verify standard response format
        assert data["status"] == "success"
        assert isinstance(data["message"], str)
        assert data["errors"] == []  # Should be empty list, not null
        assert "metadata" in data

        # Verify data structure
        assert "sources" in data["data"]
        assert "total_sources" in data["data"]

        sources = data["data"]["sources"]

        # Verify each source has consistent structure
        for source_type, source_info in sources.items():
            assert "type" in source_info
            assert "description" in source_info
            assert "parameters" in source_info
            assert "authentication" in source_info
            assert "status" in source_info

            # Verify parameters is not null/empty
            assert isinstance(source_info["parameters"], dict)
            assert len(source_info["parameters"]) > 0

    def test_error_response_consistency(self):
        """Test that error responses use consistent format."""
        # Test a non-existent endpoint to trigger error
        response = client.get("/nonexistent")
        assert response.status_code == 404

        # Note: FastAPI's built-in 404 may not use our format,
        # but custom endpoint errors should

        # Test source type that doesn't exist
        response = client.get("/sources/nonexistent")

        if response.status_code != 200:
            # If it's an error response, verify format
            data = response.json()
            if isinstance(data, dict) and "errors" in data:
                # Our custom error response should use empty list
                assert isinstance(data["errors"], list)

    @patch(
        "containers.content-collector.collectors.factory.CollectorFactory.COLLECTORS"
    )
    def test_source_discovery_extensibility(self, mock_collectors):
        """Test that new collectors are automatically discovered."""
        # Mock an extended set of collectors
        mock_collectors.keys.return_value = [
            "reddit",
            "mastodon",
            "rss",
            "web",
            "twitter",
            "linkedin",
        ]

        response = client.get("/sources")

        # Should handle the extended set gracefully
        # (May not have full config for unknown types, but shouldn't crash)
        assert response.status_code == 200

        data = response.json()
        sources = data["data"]["sources"]

        # Should at least have the known sources
        known_sources = ["reddit", "mastodon", "rss", "web"]
        for source_type in known_sources:
            assert source_type in sources


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

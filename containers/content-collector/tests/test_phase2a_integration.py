"""
Phase 2A Integration Tests: Content Collector Standardizati        # List blobs to verify our collection was saved
        blobs = blob_client.list_blobs(container_name)
        collection_blob_found = any(
            collection_id in blob["name"] 
            for blob in blobs
        )sts that validate the content collector follows standardized patterns:
- Uses shared blob storage library
- Saves to COLLECTED_CONTENT container
- Provides standard API endpoints
- Integrates with pipeline workflow
"""

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from main import app

from libs.blob_storage import BlobContainers, BlobStorageClient


class TestPhase2AIntegration:
    """Integration tests for Phase 2A Content Collector Standardization."""

    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    def blob_client(self):
        """Blob storage client."""
        return BlobStorageClient()

    @pytest.mark.asyncio
    async def test_content_collector_blob_storage_integration(
        self, client, blob_client
    ):
        """Test that content collector properly saves to blob storage."""
        # Collect some content
        test_request = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["test"],
                    "limit": 2,
                    "criteria": {"min_score": 1, "min_comments": 0},
                }
            ],
            "deduplicate": True,
            "similarity_threshold": 0.8,
        }

        response = client.post("/collect", json=test_request)
        assert response.status_code == 200

        result = response.json()
        assert "collection_id" in result
        assert "storage_location" in result
        assert result["storage_location"] is not None

        # Verify the content was saved to the correct container
        collection_id = result["collection_id"]
        container_name = BlobContainers.COLLECTED_CONTENT

        # List blobs to verify our collection was saved
        blobs = blob_client.list_blobs(container_name)
        collection_blob_found = any(collection_id in blob["name"] for blob in blobs)
        assert (
            collection_blob_found
        ), f"Collection {collection_id} not found in {container_name}"

    @pytest.mark.asyncio
    async def test_standardized_api_endpoints(self, client):
        """Test that content collector provides all required standard endpoints."""
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "content-collector"
        assert "version" in data
        assert "endpoints" in data

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        health_data = response.json()
        assert "status" in health_data
        assert health_data["status"] in ["healthy", "warning", "error"]

        # Test status endpoint
        response = client.get("/status")
        assert response.status_code == 200
        status_data = response.json()
        assert "service" in status_data
        assert "uptime" in status_data
        assert "stats" in status_data

        # Test sources endpoint
        response = client.get("/sources")
        assert response.status_code == 200
        sources_data = response.json()
        assert "available_sources" in sources_data

    @pytest.mark.asyncio
    async def test_blob_storage_container_standardization(self, client):
        """Test that content collector uses standardized blob containers."""
        # This test validates that the service uses BlobContainers.COLLECTED_CONTENT
        # instead of hardcoded strings like "raw-content"

        test_request = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 1,
                    "criteria": {"min_score": 1, "min_comments": 0},
                }
            ]
        }

        response = client.post("/collect", json=test_request)
        assert response.status_code == 200

        result = response.json()
        print(f"DEBUG: Response = {result}")
        storage_location = result.get("storage_location", "")
        print(f"DEBUG: storage_location = {storage_location}")

        # Verify it uses the standard container name
        assert (
            storage_location is not None
        ), f"storage_location should not be None: {result}"
        assert BlobContainers.COLLECTED_CONTENT in storage_location
        # Old container name should not be used
        assert "raw-content" not in storage_location

    @pytest.mark.asyncio
    async def test_content_format_standardization(self, client, blob_client):
        """Test that collected content follows standardized format."""
        test_request = {
            "sources": [{"type": "reddit", "subreddits": ["test"], "limit": 1}]
        }

        response = client.post("/collect", json=test_request)
        assert response.status_code == 200

        result = response.json()
        collection_id = result["collection_id"]

        # Find and download the blob
        container_name = BlobContainers.COLLECTED_CONTENT
        blobs = blob_client.list_blobs(container_name)

        target_blob = None
        for blob in blobs:
            if collection_id in blob["name"]:
                target_blob = blob
                break

        assert (
            target_blob is not None
        ), f"Could not find blob for collection {collection_id}"

        # Download and verify content format
        blob_content = blob_client.download_text(container_name, target_blob["name"])
        content_data = json.loads(blob_content)

        # Verify standard format
        assert "collection_id" in content_data
        assert "metadata" in content_data
        assert "items" in content_data
        assert "format_version" in content_data

        # Verify metadata includes required fields
        metadata = content_data["metadata"]
        assert "total_collected" in metadata
        assert "collected_at" in metadata
        assert "collection_version" in metadata

    @pytest.mark.asyncio
    async def test_pipeline_readiness(self, client):
        """Test that content collector is ready for pipeline integration."""
        # Test collection with realistic parameters
        test_request = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 5,
                    "criteria": {"min_score": 10, "min_comments": 2},
                }
            ],
            "deduplicate": True,
        }

        response = client.post("/collect", json=test_request)
        assert response.status_code == 200

        result = response.json()

        # Verify collection succeeded and has pipeline-ready data
        assert "collection_id" in result
        assert "collected_items" in result
        assert "metadata" in result
        assert "storage_location" in result

        # Verify timing information for pipeline monitoring
        metadata = result["metadata"]
        assert "processing_time_seconds" in metadata
        assert "timestamp" in metadata

        # Verify the collection has a meaningful amount of data
        if result["collected_items"]:  # Only check if items were collected
            assert len(result["collected_items"]) > 0
            # Check first item has required fields for downstream processing
            first_item = result["collected_items"][0]
            assert "id" in first_item
            assert "title" in first_item
            assert "source" in first_item
            assert "collected_at" in first_item

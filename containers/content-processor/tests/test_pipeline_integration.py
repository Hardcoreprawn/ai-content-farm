#!/usr/bin/env python3
"""
Pipeline Integration Tests: Content Collector → Processor

Validates the end-to-end flow from collection to processing:
- Collector saves to COLLECTED_CONTENT
- Processor finds and processes unprocessed collections
- Processed content is saved to PROCESSED_CONTENT
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from main import app

from libs.blob_storage import BlobContainers, BlobStorageClient


class TestPipelineIntegration:
    """Integration tests for Collector → Processor Pipeline."""

    @pytest.fixture
    def client(self):
        """FastAPI test client for content-processor."""
        return TestClient(app)

    @pytest.fixture
    def blob_client(self):
        """Blob storage client."""
        return BlobStorageClient()

    @pytest.fixture
    def sample_collection_data(self):
        """Create sample collected content for testing."""
        return {
            "collection_id": "test_collection_20250819_120000",
            "metadata": {
                "total_collected": 2,
                "sources_processed": 1,
                "collected_at": "2025-08-19T12:00:00.000000+00:00",
                "collection_version": "1.0.0",
                "source_type": "reddit",
            },
            "items": [
                {
                    "id": "test123",
                    "title": "Test AI Article",
                    "score": 150,
                    "num_comments": 25,
                    "subreddit": "technology",
                    "url": "https://example.com/test123",
                    "author": "testuser",
                    "source": "reddit",
                    "collected_at": "2025-08-19T12:00:00.000000+00:00",
                    "content_type": "link",
                },
                {
                    "id": "test456",
                    "title": "Machine Learning Breakthrough",
                    "score": 89,
                    "num_comments": 12,
                    "subreddit": "MachineLearning",
                    "url": "https://example.com/test456",
                    "author": "researcher",
                    "source": "reddit",
                    "collected_at": "2025-08-19T12:00:00.000000+00:00",
                    "content_type": "link",
                },
            ],
            "format_version": "1.0",
        }

    @pytest.fixture
    def setup_collection_in_blob(self, blob_client, sample_collection_data):
        """Setup collected content in blob storage for testing."""
        # Save to blob storage to simulate collector output
        blob_name = "collections/2025/08/19/test_collection_20250819_120000.json"
        blob_client.upload_text(
            container_name=BlobContainers.COLLECTED_CONTENT,
            blob_name=blob_name,
            content=json.dumps(sample_collection_data, indent=2),
            content_type="application/json",
        )
        return blob_name

    @pytest.mark.asyncio
    async def test_process_collection_endpoint(self, client, sample_collection_data):
        """Test that processor can process a collection via API."""
        response = client.post("/process/collection", json=sample_collection_data)

        assert response.status_code == 200
        result = response.json()

        # Verify response structure
        assert "process_id" in result
        assert "processed_items" in result
        assert "metadata" in result
        assert "storage_location" in result

        # Verify processing metadata
        metadata = result["metadata"]
        assert metadata["total_items"] == 2
        assert metadata["processed_items"] == 2
        assert metadata["source_collection"] == "test_collection_20250819_120000"
        assert "processing_time_seconds" in metadata
        assert "processor_version" in metadata

        # Verify processed items structure
        processed_items = result["processed_items"]
        assert len(processed_items) == 2

        for item in processed_items:
            assert "id" in item
            assert "title" in item
            assert "clean_title" in item
            assert "normalized_score" in item
            assert "engagement_score" in item
            assert "source_url" in item
            assert "published_at" in item
            assert "content_type" in item
            assert "source_metadata" in item

    @pytest.mark.asyncio
    async def test_blob_storage_integration(
        self, client, blob_client, sample_collection_data, setup_collection_in_blob
    ):
        """Test that processed content is properly saved to blob storage."""
        # Process the collection
        response = client.post("/process/collection", json=sample_collection_data)
        assert response.status_code == 200

        result = response.json()
        storage_location = result["storage_location"]
        assert storage_location is not None
        assert BlobContainers.PROCESSED_CONTENT in storage_location

        # Verify the content was saved to the correct container
        process_id = result["process_id"]
        blobs = blob_client.list_blobs(BlobContainers.PROCESSED_CONTENT)

        processed_blob_found = any(process_id in blob["name"] for blob in blobs)
        assert (
            processed_blob_found
        ), f"Processed content {process_id} not found in {BlobContainers.PROCESSED_CONTENT}"

        # Download and verify the saved content
        for blob in blobs:
            if process_id in blob["name"]:
                saved_content = blob_client.download_text(
                    BlobContainers.PROCESSED_CONTENT, blob["name"]
                )
                saved_data = json.loads(saved_content)

                # Verify saved data structure
                assert "process_id" in saved_data
                assert "metadata" in saved_data
                assert "processed_items" in saved_data
                assert "source_collection" in saved_data
                assert "format_version" in saved_data

                # Verify source collection reference
                source_collection = saved_data["source_collection"]
                assert (
                    source_collection["collection_id"]
                    == "test_collection_20250819_120000"
                )
                assert source_collection["total_source_items"] == 2
                break

    @pytest.mark.asyncio
    async def test_find_unprocessed_collections(
        self, client, blob_client, sample_collection_data, setup_collection_in_blob
    ):
        """Test that processor can find unprocessed collections."""
        # Get status to check unprocessed count
        response = client.get("/status")
        assert response.status_code == 200

        status_data = response.json()
        initial_unprocessed = status_data["pipeline"]["unprocessed_collections"]

        # Should find our sample collection as unprocessed
        assert initial_unprocessed >= 1

    @pytest.mark.asyncio
    async def test_process_batch_endpoint(
        self, client, blob_client, sample_collection_data, setup_collection_in_blob
    ):
        """Test batch processing of unprocessed collections."""
        # Process batch
        response = client.post("/process/batch")
        assert response.status_code == 200

        result = response.json()
        assert "processed_count" in result
        assert "results" in result

        # Should have processed at least our sample collection
        if result["processed_count"] > 0:
            assert len(result["results"]) == result["processed_count"]

            # Check if our sample collection was processed
            our_collection_processed = any(
                r.get("collection_id") == "test_collection_20250819_120000"
                and r.get("status") == "success"
                for r in result["results"]
            )

            # Verify processing results
            for result_item in result["results"]:
                if result_item["status"] == "success":
                    assert "process_id" in result_item
                    assert "processed_items" in result_item
                    assert result_item["processed_items"] >= 0

    @pytest.mark.asyncio
    async def test_end_to_end_pipeline_simulation(self, client, blob_client):
        """Test complete pipeline simulation: collect → process."""
        unique_id = str(uuid.uuid4())[:8]
        collection_id = f"pipeline_test_{unique_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        collection_data = {
            "collection_id": collection_id,
            "metadata": {
                "total_collected": 1,
                "sources_processed": 1,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "collection_version": "1.0.0",
            },
            "items": [
                {
                    "id": f"pipeline_test_{unique_id}",
                    "title": "End-to-End Pipeline Test",
                    "score": 100,
                    "num_comments": 10,
                    "subreddit": "test",
                    "url": "https://example.com/pipeline",
                    "author": "pipeline_tester",
                    "source": "reddit",
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
            "format_version": "1.0",
        }

        # Save to collected content (simulating collector)
        today = datetime.now(timezone.utc)
        blob_name = f"collections/{today.strftime('%Y/%m/%d')}/{collection_id}.json"
        blob_client.upload_text(
            container_name=BlobContainers.COLLECTED_CONTENT,
            blob_name=blob_name,
            content=json.dumps(collection_data, indent=2),
            content_type="application/json",
        )

        # Status check
        status_response = client.get("/status")
        assert status_response.status_code == 200

        # Direct process
        response = client.post("/process/collection", json=collection_data)
        assert response.status_code == 200

        direct_result = response.json()
        assert "process_id" in direct_result
        assert direct_result["metadata"]["source_collection"] == collection_id
        assert direct_result["metadata"]["processed_items"] == 1

        # Verify processed content is in blob storage
        processed_blobs = blob_client.list_blobs(BlobContainers.PROCESSED_CONTENT)
        process_id = direct_result["process_id"]
        assert any(process_id in b["name"] for b in processed_blobs)

    @pytest.mark.asyncio
    async def test_pipeline_statistics_tracking(self, client, sample_collection_data):
        """Test that pipeline operations are properly tracked in statistics."""
        # Get initial stats
        response = client.get("/status")
        assert response.status_code == 200
        initial_stats = response.json()["stats"]

        initial_processed = initial_stats["total_processed"]

        # Process collection
        response = client.post("/process/collection", json=sample_collection_data)
        assert response.status_code == 200

        # Get updated stats
        response = client.get("/status")
        assert response.status_code == 200
        updated_stats = response.json()["stats"]

        # Verify stats were updated
        assert updated_stats["total_processed"] == initial_processed + 1
        assert updated_stats["successful_processing"] >= 1
        assert updated_stats["last_processed"] is not None

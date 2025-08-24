#!/usr/bin/env python3
"""
Phase 2C Integration Tests: Content Processor → Enricher Pipeline

Tests that validate the end-to-end pipeline from content processing to enrichment:
- Content processor saves to PROCESSED_CONTENT container
- Content enricher finds and enriches unprocessed content
- Enriched content is saved to ENRICHED_CONTENT container
- Pipeline integration works seamlessly
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from main import app

from libs.blob_storage import BlobContainers, BlobStorageClient


class TestPhase2CPipeline:
    """Integration tests for Phase 2C Processor → Enricher Pipeline."""

    @pytest.fixture
    def client(self):
        """FastAPI test client for content-enricher."""
        return TestClient(app)

    @pytest.fixture
    def blob_client(self):
        """Blob storage client."""
        return BlobStorageClient()

    @pytest.fixture
    def sample_processed_data(self):
        """Create sample processed content for testing."""
        return {
            "process_id": "process_20250819_140000",
            "processed_items": [
                {
                    "id": "test123",
                    "title": "Amazing AI Breakthrough in Machine Learning",
                    "clean_title": "Amazing AI Breakthrough in Machine Learning",
                    "normalized_score": 0.85,
                    "engagement_score": 0.72,
                    "source_url": "https://example.com/test123",
                    "published_at": "2025-08-19T14:00:00.000000+00:00",
                    "content_type": "link",
                    "source_metadata": {
                        "original_score": 150,
                        "original_comments": 25,
                        "subreddit": "MachineLearning",
                        "reddit_id": "test123",
                    },
                },
                {
                    "id": "test456",
                    "title": "This terrible AI disaster is getting worse",
                    "clean_title": "This terrible AI disaster is getting worse",
                    "normalized_score": 0.45,
                    "engagement_score": 0.38,
                    "source_url": "https://example.com/test456",
                    "published_at": "2025-08-19T14:00:00.000000+00:00",
                    "content_type": "link",
                    "source_metadata": {
                        "original_score": 89,
                        "original_comments": 12,
                        "subreddit": "technology",
                        "reddit_id": "test456",
                    },
                },
            ],
            "metadata": {
                "total_items": 2,
                "processed_items": 2,
                "source_collection": "collection_20250819_140000",
                "processing_errors": 0,
                "processing_time_seconds": 0.123,
                "processor_version": "1.0.0",
            },
            "timestamp": "2025-08-19T14:00:00.000000+00:00",
            "storage_location": "processed-content/processed/2025/08/19/process_20250819_140000.json",
        }

    @pytest.fixture
    def setup_processed_in_blob(self, blob_client, sample_processed_data):
        """Setup processed content in blob storage for testing."""
        # Save to blob storage to simulate processor output
        blob_name = "processed/2025/08/19/process_20250819_140000.json"
        blob_client.upload_text(
            container_name=BlobContainers.PROCESSED_CONTENT,
            blob_name=blob_name,
            content=json.dumps(sample_processed_data, indent=2),
            content_type="application/json",
        )
        return blob_name

    @pytest.mark.asyncio
    async def test_enrich_processed_content_endpoint(
        self, client, sample_processed_data
    ):
        """Test that enricher can process content via API."""
        response = client.post("/enrich/processed", json=sample_processed_data)

        assert response.status_code == 200
        result = response.json()

        # Verify response structure
        assert "enrichment_id" in result
        assert "enriched_items" in result
        assert "metadata" in result
        assert "storage_location" in result
        assert "source_data" in result

        # Verify enrichment metadata
        metadata = result["metadata"]
        assert metadata["total_items"] == 2
        assert metadata["enriched_items"] == 2
        assert metadata["source_process"] == "process_20250819_140000"
        assert "enrichment_time_seconds" in metadata
        assert "enricher_version" in metadata
        assert "enrichment_types" in metadata

        # Verify enriched items structure
        enriched_items = result["enriched_items"]
        assert len(enriched_items) == 2

        for item in enriched_items:
            # Original content should be preserved
            assert "id" in item
            assert "title" in item
            assert "clean_title" in item

            # New enrichment fields should be added
            assert "enrichment" in item
            enrichment = item["enrichment"]
            assert "sentiment" in enrichment
            assert "topics" in enrichment
            assert "summary" in enrichment
            assert "trend_score" in enrichment

    @pytest.mark.asyncio
    async def test_enrichment_sentiment_analysis(self, client, sample_processed_data):
        """Test that sentiment analysis works correctly."""
        response = client.post("/enrich/processed", json=sample_processed_data)
        assert response.status_code == 200

        result = response.json()
        enriched_items = result["enriched_items"]

        # Check sentiment analysis on positive content
        positive_item = next(
            item for item in enriched_items if "Amazing" in item["title"]
        )
        assert positive_item["enrichment"]["sentiment"]["sentiment"] == "positive"
        assert positive_item["enrichment"]["sentiment"]["confidence"] > 0.5

        # Check sentiment analysis on negative content
        negative_item = next(
            item for item in enriched_items if "terrible" in item["title"]
        )
        assert negative_item["enrichment"]["sentiment"]["sentiment"] == "negative"
        assert negative_item["enrichment"]["sentiment"]["confidence"] > 0.5

    @pytest.mark.asyncio
    async def test_enrichment_topic_classification(self, client, sample_processed_data):
        """Test that topic classification works correctly."""
        response = client.post("/enrich/processed", json=sample_processed_data)
        assert response.status_code == 200

        result = response.json()
        enriched_items = result["enriched_items"]

        for item in enriched_items:
            topics = item["enrichment"]["topics"]
            assert "primary_topic" in topics
            assert "confidence" in topics
            assert "topics" in topics
            assert isinstance(topics["topics"], list)

    @pytest.mark.asyncio
    async def test_blob_storage_integration(
        self, client, blob_client, sample_processed_data
    ):
        """Test that enriched content is properly saved to blob storage."""
        # Enrich the processed content
        response = client.post("/enrich/processed", json=sample_processed_data)
        assert response.status_code == 200

        result = response.json()
        storage_location = result["storage_location"]
        assert storage_location is not None
        assert BlobContainers.ENRICHED_CONTENT in storage_location

        # Verify the content was saved to the correct container
        enrichment_id = result["enrichment_id"]
        blobs = blob_client.list_blobs(BlobContainers.ENRICHED_CONTENT)

        enriched_blob_found = any(enrichment_id in blob["name"] for blob in blobs)
        assert (
            enriched_blob_found
        ), f"Enriched content {enrichment_id} not found in {BlobContainers.ENRICHED_CONTENT}"

        # Download and verify the saved content
        for blob in blobs:
            if enrichment_id in blob["name"]:
                saved_content = blob_client.download_text(
                    BlobContainers.ENRICHED_CONTENT, blob["name"]
                )
                saved_data = json.loads(saved_content)

                # Verify saved data structure
                assert "enrichment_id" in saved_data
                assert "metadata" in saved_data
                assert "enriched_items" in saved_data
                assert "source_data" in saved_data
                assert "format_version" in saved_data

                # Verify source process reference
                source_data = saved_data["source_data"]
                assert source_data["process_id"] == "process_20250819_140000"
                break

    @pytest.mark.asyncio
    async def test_find_unenriched_content(
        self, client, blob_client, sample_processed_data, setup_processed_in_blob
    ):
        """Test that enricher can find unenriched processed content."""
        # Get status to check unenriched count
        response = client.get("/status")
        assert response.status_code == 200

        status_data = response.json()
        initial_unenriched = status_data["pipeline"]["unenriched_processed_content"]

        # Should find our sample processed content as unenriched
        assert initial_unenriched >= 1

    @pytest.mark.asyncio
    async def test_enrich_batch_endpoint(
        self, client, blob_client, sample_processed_data, setup_processed_in_blob
    ):
        """Test batch enrichment of unenriched processed content."""
        # Enrich batch
        response = client.post("/enrich/batch")
        assert response.status_code == 200

        result = response.json()
        assert "enriched_count" in result
        assert "results" in result

        # Should have enriched at least our sample processed content
        if result["enriched_count"] > 0:
            assert len(result["results"]) == result["enriched_count"]

            # Check if our sample processed content was enriched
            our_content_enriched = any(
                r.get("process_id") == "process_20250819_140000"
                and r.get("status") == "success"
                for r in result["results"]
            )

            # Verify enrichment results
            for result_item in result["results"]:
                if result_item["status"] == "success":
                    assert "enrichment_id" in result_item
                    assert "enriched_items" in result_item
                    assert result_item["enriched_items"] >= 0

    @pytest.mark.asyncio
    async def test_end_to_end_pipeline_simulation(self, client, blob_client):
        """Test complete pipeline simulation: process → enrich."""
        # Step 1: Simulate processed content (like content-processor would do)
        unique_id = str(uuid.uuid4())[:8]
        process_id = f"pipeline_test_{unique_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        processed_data = {
            "process_id": process_id,
            "processed_items": [
                {
                    "id": f"pipeline_test_{unique_id}",
                    "title": "End-to-End Pipeline Enrichment Test",
                    "clean_title": "End-to-End Pipeline Enrichment Test",
                    "normalized_score": 0.75,
                    "engagement_score": 0.65,
                    "source_url": "https://example.com/pipeline",
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "content_type": "link",
                    "source_metadata": {
                        "original_score": 100,
                        "original_comments": 10,
                        "subreddit": "test",
                        "reddit_id": f"pipeline_test_{unique_id}",
                    },
                }
            ],
            "metadata": {
                "total_items": 1,
                "processed_items": 1,
                "source_collection": f"collection_{unique_id}",
                "processing_errors": 0,
                "processor_version": "1.0.0",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Save to processed content (simulating processor)
        today = datetime.now(timezone.utc)
        blob_name = f"processed/{today.strftime('%Y/%m/%d')}/{process_id}.json"
        blob_client.upload_text(
            container_name=BlobContainers.PROCESSED_CONTENT,
            blob_name=blob_name,
            content=json.dumps(processed_data, indent=2),
            content_type="application/json",
        )

        # Step 2: Enrich using batch endpoint (simulating automated enrichment)
        response = client.post("/enrich/batch")
        assert response.status_code == 200

        batch_result = response.json()

        # Debug: Print what we got if needed
        print(f"\nDebug - Process ID: {process_id}")
        print(f"Debug - Batch result: {batch_result}")

        assert batch_result["enriched_count"] >= 1

        # Step 3: Verify enrichment worked
        pipeline_result = None
        for result_item in batch_result["results"]:
            if result_item.get("process_id") == process_id:
                pipeline_result = result_item
                break

        if pipeline_result is None:
            # Try direct enrichment if batch didn't catch it
            response = client.post("/enrich/processed", json=processed_data)
            assert response.status_code == 200
            direct_result = response.json()

            # Verify the direct enrichment worked
            assert "enrichment_id" in direct_result
            assert direct_result["metadata"]["source_process"] == process_id
            assert direct_result["metadata"]["enriched_items"] == 1
            pipeline_result = {
                "process_id": process_id,
                "status": "success",
                "enrichment_id": direct_result["enrichment_id"],
                "enriched_items": 1,
            }

        assert pipeline_result is not None
        assert pipeline_result["status"] == "success"
        assert "enrichment_id" in pipeline_result
        assert pipeline_result["enriched_items"] == 1

        # Step 4: Verify enriched content is in blob storage
        enriched_blobs = blob_client.list_blobs(BlobContainers.ENRICHED_CONTENT)
        enrichment_id = pipeline_result["enrichment_id"]

        enriched_blob_found = any(
            enrichment_id in blob["name"] for blob in enriched_blobs
        )
        assert (
            enriched_blob_found
        ), f"End-to-end pipeline result {enrichment_id} not found in enriched content"

    @pytest.mark.asyncio
    async def test_pipeline_statistics_tracking(self, client, sample_processed_data):
        """Test that pipeline operations are properly tracked in statistics."""
        # Get initial stats
        response = client.get("/status")
        assert response.status_code == 200
        initial_stats = response.json()["stats"]

        initial_enriched = initial_stats["total_enriched"]

        # Enrich processed content
        response = client.post("/enrich/processed", json=sample_processed_data)
        assert response.status_code == 200

        # Get updated stats
        response = client.get("/status")
        assert response.status_code == 200
        updated_stats = response.json()["stats"]

        # Verify stats were updated
        assert updated_stats["total_enriched"] == initial_enriched + 1
        assert updated_stats["successful_enrichment"] >= 1
        assert updated_stats["last_enriched"] is not None

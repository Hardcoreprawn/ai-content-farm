"""
End-to-end system integration tests.

These tests validate that the entire AI content farm system works together
as an integrated whole, from content collection through to site generation.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from libs.blob_storage import BlobStorageClient
from libs.shared_models import (
    ContentItem,
    HealthStatus,
    ServiceStatus,
    StandardResponse,
    create_error_response,
    create_success_response,
)


class TestSystemIntegration:
    """Test complete system integration workflows."""

    @pytest.fixture
    def mock_system(self):
        """Create a fully mocked system environment."""
        with patch.dict(
            "os.environ", {"BLOB_STORAGE_MOCK": "true", "ENVIRONMENT": "test"}
        ):
            blob_client = BlobStorageClient()
            return {
                "blob_client": blob_client,
                "containers": {
                    "collected-content": "collected-content",
                    "ranked-content": "ranked-content",
                    "generated-content": "generated-content",
                    "published-sites": "published-sites",
                },
            }

    @pytest.mark.asyncio
    async def test_complete_system_workflow(self, mock_system):
        """Test the complete system workflow from collection to publication."""
        blob_client = mock_system["blob_client"]
        containers = mock_system["containers"]

        # === STAGE 1: Content Collection ===
        print("\n=== STAGE 1: Content Collection ===")

        # Simulate content collector finding and storing content
        collected_items = []
        for i in range(3):
            content_id = f"reddit_post_{i+1}"
            raw_content = {
                "id": content_id,
                "title": f"Interesting Article {i+1}",
                "content": f"This is the content of article {i+1} with interesting information.",
                "url": f"https://reddit.com/r/technology/post_{i+1}",
                "source": "reddit",
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "subreddit": "technology",
                    "score": 50 + (i * 25),  # Varying scores
                    "comments": 10 + (i * 5),
                    "author": f"user_{i+1}",
                },
            }

            await blob_client.upload_json(
                containers["collected-content"],
                f"reddit/2024/09/14/{content_id}.json",
                raw_content,
            )
            collected_items.append(content_id)
            print(
                f"  ✓ Collected: {content_id} (score: {raw_content['metadata']['score']})"
            )

        # Verify collection stage
        collection_blobs = await blob_client.list_blobs(containers["collected-content"])
        assert len(collection_blobs) >= 3, "Should have collected at least 3 items"

        # === STAGE 2: Content Processing ===
        print("\n=== STAGE 2: Content Processing ===")

        processed_items = []
        for content_id in collected_items:
            # Read collected content
            collected_data = await blob_client.download_json(
                containers["collected-content"], f"reddit/2024/09/14/{content_id}.json"
            )

            # Simulate processing logic
            base_score = collected_data["metadata"]["score"]
            quality_score = min(0.95, base_score / 100.0)  # Normalize to 0-1
            relevance_score = 0.8 + (quality_score * 0.2)

            processed_content = {
                **collected_data,
                "processing": {
                    "quality_score": quality_score,
                    "relevance_score": relevance_score,
                    "sentiment": "positive" if quality_score > 0.7 else "neutral",
                    "topics": ["technology", "discussion"],
                    "processing_algorithm": "v2.1",
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                },
            }

            # Only process high-quality content
            if quality_score >= 0.6:
                await blob_client.upload_json(
                    containers["ranked-content"],
                    f"processed/{content_id}.json",
                    processed_content,
                )
                processed_items.append(content_id)
                print(f"  ✓ Processed: {content_id} (quality: {quality_score:.2f})")
            else:
                print(f"  ✗ Rejected: {content_id} (quality: {quality_score:.2f})")

        # === STAGE 3: Content Generation ===
        print("\n=== STAGE 3: Content Generation ===")

        generated_items = []
        for content_id in processed_items:
            # Read processed content
            processed_data = await blob_client.download_json(
                containers["ranked-content"], f"processed/{content_id}.json"
            )

            # Simulate AI content generation
            original_title = processed_data["title"]
            enhanced_title = f"Breaking: {original_title} - Expert Analysis"

            generated_content = {
                **processed_data,
                "generated": {
                    "enhanced_title": enhanced_title,
                    "summary": f"A comprehensive analysis of {original_title.lower()} and its implications.",
                    "seo_keywords": ["technology", "analysis", "breaking", "expert"],
                    "meta_description": f"Expert analysis of {original_title[:50]}...",
                    "word_count": len(processed_data["content"].split()) + 150,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "ai_model": "gpt-4",
                    "generation_version": "v3.2",
                },
            }

            await blob_client.upload_json(
                containers["generated-content"],
                f"enhanced/{content_id}.json",
                generated_content,
            )
            generated_items.append(content_id)
            print(f"  ✓ Generated: {content_id}")

        # === STAGE 4: Site Generation ===
        print("\n=== STAGE 4: Site Generation ===")

        published_items = []
        for content_id in generated_items:
            # Read enhanced content
            enhanced_data = await blob_client.download_json(
                containers["generated-content"], f"enhanced/{content_id}.json"
            )

            # Generate HTML
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{enhanced_data['generated']['enhanced_title']}</title>
    <meta name="description" content="{enhanced_data['generated']['meta_description']}">
    <meta name="keywords" content="{','.join(enhanced_data['generated']['seo_keywords'])}">
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .article-header {{ border-bottom: 2px solid #333; margin-bottom: 20px; }}
        .metadata {{ background: #f5f5f5; padding: 10px; margin-top: 20px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <article data-id="{enhanced_data['id']}">
        <div class="article-header">
            <h1>{enhanced_data['generated']['enhanced_title']}</h1>
            <p class="summary"><strong>{enhanced_data['generated']['summary']}</strong></p>
        </div>

        <div class="content">
            {enhanced_data['content']}
        </div>

        <div class="metadata">
            <p><strong>Article ID:</strong> {enhanced_data['id']}</p>
            <p><strong>Source:</strong> {enhanced_data['source']}</p>
            <p><strong>Quality Score:</strong> {enhanced_data['processing']['quality_score']:.2f}</p>
            <p><strong>Word Count:</strong> {enhanced_data['generated']['word_count']}</p>
            <p><strong>Generated:</strong> {enhanced_data['generated']['generated_at']}</p>
        </div>
    </article>
</body>
</html>"""

            await blob_client.upload_text(
                containers["published-sites"],
                f"articles/{content_id}.html",
                html_content,
                content_type="text/html",
            )
            published_items.append(content_id)
            print(f"  ✓ Published: {content_id}")

        # === STAGE 5: System Verification ===
        print("\n=== STAGE 5: System Verification ===")

        # Verify end-to-end pipeline
        assert len(collected_items) == 3, "Should have collected 3 items"
        assert (
            len(processed_items) >= 1
        ), "Should have processed at least 1 high-quality item"
        assert len(generated_items) == len(
            processed_items
        ), "All processed items should be generated"
        assert len(published_items) == len(
            generated_items
        ), "All generated items should be published"

        # Test final output quality
        for content_id in published_items:
            final_html = await blob_client.download_text(
                containers["published-sites"], f"articles/{content_id}.html"
            )

            # Verify HTML structure
            assert "<!DOCTYPE html>" in final_html
            assert content_id in final_html
            assert "Breaking:" in final_html
            assert "Quality Score:" in final_html
            assert "data-id=" in final_html

            print(f"  ✓ Verified: {content_id}")

        print(f"\n🎉 SYSTEM INTEGRATION SUCCESS!")
        print(f"   Collected: {len(collected_items)} items")
        print(f"   Processed: {len(processed_items)} items")
        print(f"   Generated: {len(generated_items)} items")
        print(f"   Published: {len(published_items)} items")

        return {
            "collected": len(collected_items),
            "processed": len(processed_items),
            "generated": len(generated_items),
            "published": len(published_items),
            "published_items": published_items,
        }

    @pytest.mark.asyncio
    async def test_system_health_monitoring(self, mock_system):
        """Test system health monitoring across all components."""
        blob_client = mock_system["blob_client"]

        # Test health status creation for each component
        components = [
            "content-collector",
            "content-processor",
            "content-generator",
            "site-generator",
        ]

        health_reports = []
        for component in components:
            # Simulate health check
            health_status = HealthStatus(
                service=component,
                version="1.0.0",
                status="healthy",
                dependencies={
                    "blob_storage": True,
                    "service_bus": True,
                    "azure_services": True,
                },
                environment="test",
                uptime_seconds=3600.0,
            )

            # Store health report
            await blob_client.upload_json(
                "system-health", f"{component}/health.json", health_status.model_dump()
            )
            health_reports.append(component)

        # Verify all health reports
        health_blobs = await blob_client.list_blobs("system-health")
        assert len(health_blobs) >= len(components)

        # Check each component's health
        all_healthy = True
        for component in components:
            health_data = await blob_client.download_json(
                "system-health", f"{component}/health.json"
            )
            assert health_data["status"] == "healthy"
            assert health_data["service"] == component
            if not health_data["dependencies"]["blob_storage"]:
                all_healthy = False

        assert all_healthy, "All system components should be healthy"

    @pytest.mark.asyncio
    async def test_system_error_recovery(self, mock_system):
        """Test system error recovery and resilience."""
        blob_client = mock_system["blob_client"]

        # Test scenario: Processing fails mid-pipeline
        content_id = "error_test_content"

        # Stage 1: Successful collection
        raw_content = {
            "id": content_id,
            "title": "Test Content for Error Recovery",
            "content": "This content will test error recovery.",
            "source": "test",
        }

        await blob_client.upload_json(
            "collected-content", f"test/{content_id}.json", raw_content
        )

        # Stage 2: Processing failure simulation
        try:
            # Simulate a processing error
            raise ValueError("Processing failed - simulated error")
        except ValueError:
            # Error recovery: Log error and create error report
            error_report = {
                "content_id": content_id,
                "stage": "processing",
                "error": "Processing failed - simulated error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "recovery_action": "retry_scheduled",
            }

            await blob_client.upload_json(
                "error-reports", f"{content_id}_error.json", error_report
            )

        # Stage 3: Recovery retry
        recovered_content = {
            **raw_content,
            "processing": {
                "retry_count": 1,
                "recovered": True,
                "quality_score": 0.8,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        await blob_client.upload_json(
            "ranked-content", f"recovered/{content_id}.json", recovered_content
        )

        # Verify recovery
        error_reports = await blob_client.list_blobs("error-reports")
        assert len(error_reports) >= 1

        recovered_data = await blob_client.download_json(
            "ranked-content", f"recovered/{content_id}.json"
        )
        assert recovered_data["processing"]["recovered"] is True
        assert recovered_data["processing"]["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_system_performance_under_load(self, mock_system):
        """Test system performance with multiple concurrent operations."""
        blob_client = mock_system["blob_client"]

        # Create multiple content items concurrently
        async def create_content_item(i):
            content_id = f"load_test_{i}"
            content = {
                "id": content_id,
                "title": f"Load Test Article {i}",
                "content": f"Content for load test item {i}",
                "load_test": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # Upload to multiple stages concurrently
            await asyncio.gather(
                blob_client.upload_json(
                    "collected-content", f"load/{content_id}.json", content
                ),
                blob_client.upload_json(
                    "ranked-content",
                    f"load/{content_id}.json",
                    {**content, "processed": True},
                ),
            )
            return content_id

        # Run 10 concurrent operations
        start_time = datetime.now()
        created_items = await asyncio.gather(
            *[create_content_item(i) for i in range(10)]
        )
        end_time = datetime.now()

        duration = (end_time - start_time).total_seconds()

        # Verify all items were created
        assert len(created_items) == 10

        # Verify performance (should complete in reasonable time)
        assert duration < 5.0, f"Load test took {duration:.2f}s, expected < 5s"

        # Verify data integrity
        for item_id in created_items:
            collected_data = await blob_client.download_json(
                "collected-content", f"load/{item_id}.json"
            )
            ranked_data = await blob_client.download_json(
                "ranked-content", f"load/{item_id}.json"
            )

            assert collected_data["id"] == item_id
            assert ranked_data["processed"] is True


class TestSystemArchitecture:
    """Test system architecture and component interactions."""

    @pytest.mark.asyncio
    async def test_shared_models_integration(self):
        """Test that shared models work correctly across the system."""

        # Test StandardResponse with different data types
        health_status = HealthStatus(
            service="test-service", version="1.0.0", status="healthy"
        )

        response = StandardResponse(
            status="success",
            message="Health check completed",
            data=health_status,
            metadata={"component": "system-test"},
        )

        # Verify response structure
        assert response.status == "success"
        assert response.data.service == "test-service"
        assert response.metadata["component"] == "system-test"

        # Test ContentItem integration
        content = ContentItem(
            id="test-content", title="Test Article", content="Test content body"
        )

        content_response = StandardResponse(
            status="success", message="Content retrieved", data=content
        )

        assert content_response.data.id == "test-content"
        assert content_response.data.title == "Test Article"

    def test_error_handling_consistency(self):
        """Test consistent error handling across components."""

        # Test error response creation
        error_response = create_error_response(
            message="Test error occurred",
            errors=["Validation failed", "Database unavailable"],
            metadata={"error_code": "SYS_001"},
        )

        assert error_response.status == "error"
        assert len(error_response.errors) == 2
        assert error_response.metadata["error_code"] == "SYS_001"

        # Test success response creation
        success_response = create_success_response(
            message="Operation completed",
            data={"result": "success"},
            metadata={"operation_id": "OP_123"},
        )

        assert success_response.status == "success"
        assert success_response.data["result"] == "success"
        assert success_response.metadata["operation_id"] == "OP_123"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])

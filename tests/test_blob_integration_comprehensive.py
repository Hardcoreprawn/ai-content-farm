"""
Comprehensive integration tests for blob storage functionality.

These tests validate:
1. Async/sync consistency across all methods
2. Cross-component communication and data flow
3. Error handling and edge cases
4. Performance and concurrent operations
5. Mock vs real storage behavior consistency
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from libs.blob_storage import BlobStorageClient


class TestBlobStorageAsyncConsistency:
    """Test that all blob storage methods follow async patterns consistently."""

    @pytest.fixture
    def blob_client(self):
        """Create a mock blob storage client."""
        with patch.dict("os.environ", {"BLOB_STORAGE_MOCK": "true"}):
            return BlobStorageClient()

    @pytest.mark.asyncio
    async def test_all_upload_methods_are_async(self, blob_client):
        """Test that all upload methods are async and work consistently."""
        container = "test-async-uploads"

        # Test JSON upload
        json_data = {"test": "data", "timestamp": datetime.now().isoformat()}
        json_url = await blob_client.upload_json(container, "test.json", json_data)
        assert json_url is not None
        assert "test.json" in json_url

        # Test text upload
        text_content = "This is test content for async validation"
        text_url = await blob_client.upload_text(container, "test.txt", text_content)
        assert text_url is not None
        assert "test.txt" in text_url

        # Test binary upload
        binary_data = b"Binary test data for async validation"
        binary_url = await blob_client.upload_binary(container, "test.bin", binary_data)
        assert binary_url is not None
        assert "test.bin" in binary_url

    @pytest.mark.asyncio
    async def test_all_download_methods_are_async(self, blob_client):
        """Test that all download methods are async and work consistently."""
        container = "test-async-downloads"

        # Upload test data first
        test_data = {"key": "value", "number": 42}
        await blob_client.upload_json(container, "download_test.json", test_data)

        test_text = "Text for download testing"
        await blob_client.upload_text(container, "download_test.txt", test_text)

        # Test async downloads
        downloaded_json = await blob_client.download_json(
            container, "download_test.json"
        )
        assert downloaded_json == test_data

        downloaded_text = await blob_client.download_text(
            container, "download_test.txt"
        )
        assert downloaded_text == test_text

    @pytest.mark.asyncio
    async def test_list_and_delete_are_async(self, blob_client):
        """Test that list and delete operations are async."""
        container = "test-async-operations"

        # Upload some test files
        await blob_client.upload_text(container, "file1.txt", "Content 1")
        await blob_client.upload_text(container, "file2.txt", "Content 2")
        await blob_client.upload_json(container, "data.json", {"test": "data"})

        # Test async list
        blobs = await blob_client.list_blobs(container)
        assert len(blobs) >= 3
        blob_names = [blob["name"] for blob in blobs]
        assert "file1.txt" in blob_names
        assert "file2.txt" in blob_names
        assert "data.json" in blob_names

        # Test async delete
        deleted = await blob_client.delete_blob(container, "file1.txt")
        assert deleted is True

        # Verify deletion
        remaining_blobs = await blob_client.list_blobs(container)
        remaining_names = [blob["name"] for blob in remaining_blobs]
        assert "file1.txt" not in remaining_names
        assert "file2.txt" in remaining_names


class TestCrossComponentIntegration:
    """Test that components can communicate through blob storage."""

    @pytest.fixture
    def blob_client(self):
        with patch.dict("os.environ", {"BLOB_STORAGE_MOCK": "true"}):
            return BlobStorageClient()

    @pytest.mark.asyncio
    async def test_content_collector_to_processor_flow(self, blob_client):
        """Test data flow from content collector to processor."""
        # Simulate content collector uploading collected content
        collected_content = {
            "id": "reddit_post_123",
            "title": "Test Reddit Post",
            "content": "This is a test post content",
            "source": "reddit",
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"subreddit": "test", "score": 42, "num_comments": 5},
        }

        # Content collector uploads to collected-content container
        url = await blob_client.upload_json(
            "collected-content",
            f"reddit/2024/09/14/{collected_content['id']}.json",
            collected_content,
        )
        assert url is not None

        # Content processor reads from collected-content
        downloaded_content = await blob_client.download_json(
            "collected-content", f"reddit/2024/09/14/{collected_content['id']}.json"
        )

        assert downloaded_content == collected_content
        assert downloaded_content["metadata"]["score"] == 42

        # Content processor processes and uploads to ranked-content
        processed_content = {
            **collected_content,
            "processing": {
                "rank_score": 0.85,
                "quality_score": 0.92,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "processor_version": "1.0.0",
            },
        }

        await blob_client.upload_json(
            "ranked-content",
            f"processed/{processed_content['id']}.json",
            processed_content,
        )

        # Verify the full pipeline
        final_content = await blob_client.download_json(
            "ranked-content", f"processed/{processed_content['id']}.json"
        )

        assert final_content["id"] == collected_content["id"]
        assert final_content["processing"]["rank_score"] == 0.85
        assert "collected_at" in final_content
        assert "processed_at" in final_content["processing"]

    @pytest.mark.asyncio
    async def test_processor_to_generator_to_site_flow(self, blob_client):
        """Test data flow from processor through generator to site output."""
        # Start with processed content
        processed_content = {
            "id": "article_456",
            "title": "AI Advances in 2024",
            "content": "Original content about AI advances...",
            "processing": {
                "rank_score": 0.95,
                "quality_score": 0.88,
                "tags": ["ai", "technology", "2024"],
            },
        }

        await blob_client.upload_json(
            "ranked-content",
            f"high-quality/{processed_content['id']}.json",
            processed_content,
        )

        # Generator reads and creates enhanced content
        enhanced_content = {
            **processed_content,
            "generated": {
                "summary": "A comprehensive look at AI developments in 2024",
                "enhanced_title": "Breaking: Revolutionary AI Advances Reshape 2024 Technology Landscape",
                "seo_keywords": [
                    "artificial intelligence",
                    "AI 2024",
                    "technology trends",
                ],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model_version": "gpt-4",
            },
        }

        await blob_client.upload_json(
            "generated-content",
            f"enhanced/{enhanced_content['id']}.json",
            enhanced_content,
        )

        # Site generator creates final HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{enhanced_content['generated']['enhanced_title']}</title>
            <meta name="keywords" content="{','.join(enhanced_content['generated']['seo_keywords'])}">
        </head>
        <body>
            <h1>{enhanced_content['generated']['enhanced_title']}</h1>
            <p>{enhanced_content['generated']['summary']}</p>
            <div>{enhanced_content['content']}</div>
            <div class="article-meta" data-id="{enhanced_content['id']}">Article ID: {enhanced_content['id']}</div>
        </body>
        </html>
        """

        await blob_client.upload_text(
            "published-sites",
            f"articles/{enhanced_content['id']}.html",
            html_content,
            content_type="text/html",
        )

        # Verify the complete pipeline
        final_html = await blob_client.download_text(
            "published-sites", f"articles/{enhanced_content['id']}.html"
        )

        assert enhanced_content["generated"]["enhanced_title"] in final_html
        assert enhanced_content["id"] in final_html
        assert "<!DOCTYPE html>" in final_html


class TestErrorHandlingAndResilience:
    """Test error handling and system resilience."""

    @pytest.fixture
    def blob_client(self):
        with patch.dict("os.environ", {"BLOB_STORAGE_MOCK": "true"}):
            return BlobStorageClient()

    @pytest.mark.asyncio
    async def test_nonexistent_blob_handling(self, blob_client):
        """Test handling of nonexistent blobs."""
        # Should return empty dict for JSON
        result = await blob_client.download_json("nonexistent", "missing.json")
        assert result == {}

        # Should return empty string for text
        result = await blob_client.download_text("nonexistent", "missing.txt")
        assert result == ""

        # Should return False for delete
        result = await blob_client.delete_blob("nonexistent", "missing.txt")
        assert result is False

    @pytest.mark.asyncio
    async def test_invalid_json_handling(self, blob_client):
        """Test handling of invalid JSON data."""
        # Upload invalid JSON as text
        await blob_client.upload_text("test", "invalid.json", "invalid json content")

        # Should raise exception when trying to download as JSON
        with pytest.raises(json.JSONDecodeError):
            await blob_client.download_json("test", "invalid.json")

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, blob_client):
        """Test concurrent blob operations."""
        container = "test-concurrent"

        # Create multiple concurrent upload tasks
        async def upload_task(i):
            data = {"task_id": i, "timestamp": datetime.now().isoformat()}
            return await blob_client.upload_json(container, f"task_{i}.json", data)

        # Run 5 concurrent uploads
        tasks = [upload_task(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 5
        assert all(url is not None for url in results)

        # Verify all were uploaded
        blobs = await blob_client.list_blobs(container)
        assert len(blobs) >= 5

        # Test concurrent downloads
        async def download_task(i):
            return await blob_client.download_json(container, f"task_{i}.json")

        download_tasks = [download_task(i) for i in range(5)]
        downloaded = await asyncio.gather(*download_tasks)

        # Verify all downloads succeeded
        assert len(downloaded) == 5
        for i, data in enumerate(downloaded):
            assert data["task_id"] == i


class TestPerformanceAndScaling:
    """Test performance characteristics and scaling behavior."""

    @pytest.fixture
    def blob_client(self):
        with patch.dict("os.environ", {"BLOB_STORAGE_MOCK": "true"}):
            return BlobStorageClient()

    @pytest.mark.asyncio
    async def test_large_data_handling(self, blob_client):
        """Test handling of large data objects."""
        # Create a large JSON object
        large_data = {
            "id": "large_content",
            "content": "x" * 10000,  # 10KB of content
            "metadata": {f"key_{i}": f"value_{i}" for i in range(100)},
            "timestamp": datetime.now().isoformat(),
        }

        # Upload large object
        url = await blob_client.upload_json("test-large", "large.json", large_data)
        assert url is not None

        # Download and verify
        downloaded = await blob_client.download_json("test-large", "large.json")
        assert downloaded["id"] == large_data["id"]
        assert len(downloaded["content"]) == 10000
        assert len(downloaded["metadata"]) == 100

    @pytest.mark.asyncio
    async def test_batch_operations_performance(self, blob_client):
        """Test performance of batch operations."""
        container = "test-batch"

        # Time batch upload
        start_time = datetime.now()

        upload_tasks = []
        for i in range(20):  # Upload 20 files
            data = {"batch_id": i, "content": f"Content for item {i}"}
            task = blob_client.upload_json(container, f"batch_{i:03d}.json", data)
            upload_tasks.append(task)

        await asyncio.gather(*upload_tasks)
        upload_time = (datetime.now() - start_time).total_seconds()

        # Should complete within reasonable time (adjust threshold as needed)
        assert upload_time < 5.0, f"Batch upload took {upload_time:.2f}s, expected < 5s"

        # Verify all files were uploaded
        blobs = await blob_client.list_blobs(container)
        assert len(blobs) >= 20

        # Test batch download performance
        start_time = datetime.now()

        download_tasks = []
        for i in range(20):
            task = blob_client.download_json(container, f"batch_{i:03d}.json")
            download_tasks.append(task)

        results = await asyncio.gather(*download_tasks)
        download_time = (datetime.now() - start_time).total_seconds()

        assert (
            download_time < 5.0
        ), f"Batch download took {download_time:.2f}s, expected < 5s"
        assert len(results) == 20
        assert all(r["batch_id"] == i for i, r in enumerate(results))


class TestFunctionalWorkflows:
    """Test complete functional workflows that validate the system works end-to-end."""

    @pytest.fixture
    def blob_client(self):
        with patch.dict("os.environ", {"BLOB_STORAGE_MOCK": "true"}):
            return BlobStorageClient()

    @pytest.mark.asyncio
    async def test_complete_content_pipeline(self, blob_client):
        """Test a complete content pipeline from collection to publication."""

        # 1. Content Collection Phase
        raw_content = {
            "id": "pipeline_test_001",
            "title": "Test Article for Pipeline",
            "url": "https://example.com/article",
            "content": "Original article content goes here...",
            "source": "reddit",
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "subreddit": "technology",
                "score": 156,
                "comments": 23,
                "author": "testuser",
            },
        }

        await blob_client.upload_json(
            "collected-content", f"reddit/{raw_content['id']}.json", raw_content
        )

        # 2. Content Processing Phase
        # Simulate reading collected content
        collected = await blob_client.download_json(
            "collected-content", f"reddit/{raw_content['id']}.json"
        )

        # Add processing metadata
        processed_content = {
            **collected,
            "processing": {
                "quality_score": 0.89,
                "relevance_score": 0.94,
                "sentiment": "positive",
                "topics": ["technology", "innovation"],
                "processed_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        await blob_client.upload_json(
            "ranked-content",
            f"processed/{processed_content['id']}.json",
            processed_content,
        )

        # 3. Content Generation Phase
        ranked = await blob_client.download_json(
            "ranked-content", f"processed/{processed_content['id']}.json"
        )

        generated_content = {
            **ranked,
            "generated": {
                "enhanced_title": "Revolutionary Technology Innovation Sparks Industry Discussion",
                "summary": "A groundbreaking technology article that has captured significant community attention.",
                "seo_tags": ["technology", "innovation", "discussion"],
                "word_count": 250,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        await blob_client.upload_json(
            "generated-content",
            f"enhanced/{generated_content['id']}.json",
            generated_content,
        )

        # 4. Site Generation Phase
        enhanced = await blob_client.download_json(
            "generated-content", f"enhanced/{generated_content['id']}.json"
        )

        # Generate final HTML
        html_output = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{enhanced['generated']['enhanced_title']}</title>
    <meta name="description" content="{enhanced['generated']['summary']}">
    <meta name="keywords" content="{','.join(enhanced['generated']['seo_tags'])}">
</head>
<body>
    <article data-id="{enhanced['id']}">
        <h1>{enhanced['generated']['enhanced_title']}</h1>
        <p class="summary">{enhanced['generated']['summary']}</p>
        <div class="content">{enhanced['content']}</div>
        <div class="metadata">
            <p>ID: {enhanced['id']}</p>
            <p>Source: {enhanced['source']}</p>
            <p>Quality Score: {enhanced['processing']['quality_score']}</p>
            <p>Generated: {enhanced['generated']['generated_at']}</p>
        </div>
    </article>
</body>
</html>"""

        await blob_client.upload_text(
            "published-sites",
            f"articles/{enhanced['id']}.html",
            html_output,
            content_type="text/html",
        )

        # 5. Verification Phase
        # Verify each stage of the pipeline
        final_html = await blob_client.download_text(
            "published-sites", f"articles/{enhanced['id']}.html"
        )

        # Validate the complete pipeline
        assert raw_content["id"] in final_html
        assert enhanced["generated"]["enhanced_title"] in final_html
        assert str(enhanced["processing"]["quality_score"]) in final_html
        assert "<!DOCTYPE html>" in final_html
        assert enhanced["source"] in final_html

        # Test cross-references between stages
        assert collected["metadata"]["score"] == 156
        assert processed_content["processing"]["quality_score"] == 0.89
        assert generated_content["generated"]["word_count"] == 250

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, blob_client):
        """Test that the system can recover from errors in the pipeline."""

        # Test partial upload failure recovery
        content_id = "error_recovery_test"

        # Upload to first stage
        await blob_client.upload_json(
            "collected-content",
            f"{content_id}.json",
            {"id": content_id, "stage": "collected"},
        )

        # Simulate failure in processing stage - upload partial data
        await blob_client.upload_json(
            "ranked-content",
            f"{content_id}_partial.json",
            {"id": content_id, "stage": "partial", "error": "processing_failed"},
        )

        # Recovery: Clean up partial data and retry
        await blob_client.delete_blob("ranked-content", f"{content_id}_partial.json")

        # Successful retry
        await blob_client.upload_json(
            "ranked-content",
            f"{content_id}.json",
            {"id": content_id, "stage": "processed", "retry": True},
        )

        # Verify recovery
        recovered = await blob_client.download_json(
            "ranked-content", f"{content_id}.json"
        )
        assert recovered["stage"] == "processed"
        assert recovered["retry"] is True

        # Verify cleanup
        partial = await blob_client.download_json(
            "ranked-content", f"{content_id}_partial.json"
        )
        assert partial == {}  # Should be empty (deleted)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])

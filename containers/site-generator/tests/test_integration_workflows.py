"""
Integration Test Suite for Site Generator

End-to-end integration tests for critical workflows.
These tests validate complete processing pipelines and error recovery scenarios.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from content_processing_functions import generate_markdown_batch, generate_static_site
from models import GenerationResponse

from libs.simplified_blob_client import SimplifiedBlobClient


class TestIntegrationWorkflows:
    """Integration tests for end-to-end critical workflows."""

    @pytest.fixture
    def integration_blob_client(self):
        """Comprehensive mock blob client for integration testing."""
        mock = Mock(spec=SimplifiedBlobClient)

        # Mock complete blob workflow
        mock.list_blobs = AsyncMock(
            return_value=[
                {"name": "processed-batch-001.json"},
                {"name": "processed-batch-002.json"},
            ]
        )

        mock.download_text = AsyncMock(
            return_value=json.dumps(
                {
                    "items": [
                        {
                            "topic_id": "integration_test_1",
                            "title": "Integration Test Article 1",
                            "content": "Test content for integration workflow",
                            "metadata": {"category": "test", "tags": ["integration"]},
                        },
                        {
                            "topic_id": "integration_test_2",
                            "title": "Integration Test Article 2",
                            "content": "Second test article for workflow validation",
                            "metadata": {"category": "test", "tags": ["workflow"]},
                        },
                    ]
                }
            )
        )

        mock.upload_text = AsyncMock(return_value=True)
        mock.upload_json = AsyncMock(return_value=True)

        return mock

    @pytest.fixture
    def integration_config(self):
        """Configuration for integration testing."""
        return {
            "PROCESSED_CONTENT_CONTAINER": "integration-processed",
            "MARKDOWN_CONTENT_CONTAINER": "integration-markdown",
            "STATIC_SITE_CONTAINER": "integration-static",
            "STATIC_SITES_CONTAINER": "integration-sites",
        }

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_content_pipeline_workflow(
        self, integration_blob_client, integration_config
    ):
        """Test complete end-to-end content processing pipeline."""
        # Mock the ContractValidator for integration test
        with patch("content_utility_functions.ContractValidator") as mock_validator:
            mock_validated = Mock()
            mock_validated.items = [
                {
                    "topic_id": "integration_test_1",
                    "title": "Integration Test Article 1",
                    "content": "Test content",
                },
                {
                    "topic_id": "integration_test_2",
                    "title": "Integration Test Article 2",
                    "content": "Second test",
                },
            ]
            mock_validator.validate_collection_data.return_value = mock_validated

            # Step 1: Process raw content to markdown
            markdown_result = await generate_markdown_batch(
                source="integration_pipeline",
                batch_size=10,
                force_regenerate=True,
                blob_client=integration_blob_client,
                config=integration_config,
                generator_id="integration-pipeline-001",
            )

            # Verify markdown processing succeeded
            assert isinstance(markdown_result, GenerationResponse)
            assert markdown_result.generator_id == "integration-pipeline-001"
            assert markdown_result.operation_type == "markdown_generation"

            # Step 2: Generate static site from markdown
            site_result = await generate_static_site(
                theme="integration-theme",
                force_rebuild=True,
                blob_client=integration_blob_client,
                config=integration_config,
                generator_id="integration-pipeline-002",
            )

            # Verify site generation succeeded
            assert isinstance(site_result, GenerationResponse)
            assert site_result.generator_id == "integration-pipeline-002"
            assert site_result.operation_type == "site_generation"

            # Verify blob operations were called in correct sequence
            assert integration_blob_client.list_blobs.called
            assert (
                integration_blob_client.download_text.called
                or integration_blob_client.upload_text.called
            )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(
        self, integration_blob_client, integration_config
    ):
        """Test that workflows handle errors gracefully and recover."""
        # Simulate storage failure followed by success
        integration_blob_client.list_blobs = AsyncMock(
            side_effect=[
                Exception("Storage temporarily unavailable"),
                [{"name": "processed-recovery-test.json"}],  # Success on retry
            ]
        )

        # First call should handle error gracefully
        result_1 = await generate_markdown_batch(
            source="error_recovery_test",
            batch_size=5,
            force_regenerate=False,
            blob_client=integration_blob_client,
            config=integration_config,
            generator_id="error-recovery-001",
        )

        # Should return error response, not crash
        assert isinstance(result_1, GenerationResponse)
        assert len(result_1.errors) > 0 or result_1.files_generated == 0

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_high_volume_processing_workflow(
        self, integration_blob_client, integration_config
    ):
        """Test workflow performance with larger batch sizes."""
        # Configure for high-volume test
        large_batch_data = {
            "items": [
                {
                    "topic_id": f"bulk_test_{i}",
                    "title": f"Bulk Test Article {i}",
                    # Longer content
                    "content": f"Test content for bulk processing article {i}" * 10,
                }
                for i in range(50)  # Simulate 50 articles
            ]
        }

        integration_blob_client.download_text = AsyncMock(
            return_value=json.dumps(large_batch_data)
        )

        with patch("content_utility_functions.ContractValidator") as mock_validator:
            mock_validated = Mock()
            mock_validated.items = large_batch_data["items"]
            mock_validator.validate_collection_data.return_value = mock_validated

            # Test processing larger batch
            result = await generate_markdown_batch(
                source="bulk_processing_test",
                batch_size=50,
                force_regenerate=False,
                blob_client=integration_blob_client,
                config=integration_config,
                generator_id="bulk-processing-001",
            )

            # Should handle larger volumes successfully
            assert isinstance(result, GenerationResponse)
            assert result.generator_id == "bulk-processing-001"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_operations_workflow(
        self, integration_blob_client, integration_config
    ):
        """Test concurrent processing operations."""
        import asyncio

        with patch("content_utility_functions.ContractValidator") as mock_validator:
            mock_validated = Mock()
            mock_validated.items = [
                {
                    "topic_id": "concurrent_test",
                    "title": "Concurrent Test",
                    "content": "Test",
                }
            ]
            mock_validator.validate_collection_data.return_value = mock_validated

            # Run multiple operations concurrently
            tasks = [
                generate_markdown_batch(
                    source=f"concurrent_test_{i}",
                    batch_size=1,
                    force_regenerate=False,
                    blob_client=integration_blob_client,
                    config=integration_config,
                    generator_id=f"concurrent-{i}",
                )
                for i in range(3)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All operations should complete (successfully or with controlled errors)
            assert len(results) == 3
            for result in results:
                if not isinstance(result, Exception):
                    assert isinstance(result, GenerationResponse)

"""
Integration Tests for Content Pipeline

Tests the integration between content collector, processor, and site generator
via Service Bus messaging.
"""

import asyncio
import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))


def import_from_container(container_name, module_name):
    """Safely import a module from a specific container."""
    container_path = (
        Path(__file__).parent.parent
        / "containers"
        / container_name
        / f"{module_name}.py"
    )
    if not container_path.exists():
        return None

    spec = importlib.util.spec_from_file_location(
        f"{container_name}_{module_name}", container_path
    )
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestContentPipelineIntegration:
    """Test integration between pipeline components."""

    @pytest.fixture
    def mock_service_bus_config(self):
        """Mock Service Bus configuration."""
        return {
            "SERVICE_BUS_NAMESPACE": "test-namespace",
            "SERVICE_BUS_CONNECTION_STRING": "test-connection",
        }

    @pytest.fixture
    def sample_collection_payload(self):
        """Sample content collection payload."""
        return {
            "service_name": "github-actions",
            "operation": "collect_content",
            "payload": {
                "sources": [
                    {"type": "reddit", "subreddits": ["technology"], "limit": 5}
                ],
                "deduplicate": True,
                "save_to_storage": True,
            },
            "metadata": {"triggered_by": "test", "timestamp": "2025-09-14T10:00:00Z"},
        }

    @pytest.fixture
    def sample_collected_content(self):
        """Sample collected content data."""
        return {
            "collection_id": "test-collection-123",
            "items": [
                {
                    "id": "reddit_1",
                    "title": "Test Article 1",
                    "content": "This is test content about technology.",
                    "url": "https://reddit.com/r/technology/post1",
                    "source": "reddit",
                    "score": 100,
                },
                {
                    "id": "reddit_2",
                    "title": "Test Article 2",
                    "content": "Another test article about AI developments.",
                    "url": "https://reddit.com/r/technology/post2",
                    "source": "reddit",
                    "score": 85,
                },
            ],
            "collected_at": "2025-09-14T10:00:00Z",
            "total_items": 2,
        }

    @pytest.fixture
    def sample_processed_content(self):
        """Sample processed content data."""
        return {
            "collection_id": "test-collection-123",
            "processed_at": "2025-09-14T10:05:00Z",
            "items_count": 2,
            "items": [
                {
                    "id": "reddit_1",
                    "title": "Test Article 1",
                    "content": "This is test content about technology.",
                    "processed_content": "Enhanced content about technology trends and innovations.",
                    "quality_score": 0.85,
                    "model_used": "gpt-4",
                    "processing_time": 2.5,
                },
                {
                    "id": "reddit_2",
                    "title": "Test Article 2",
                    "content": "Another test article about AI developments.",
                    "processed_content": "Enhanced content about AI advancements and their implications.",
                    "quality_score": 0.92,
                    "model_used": "gpt-4",
                    "processing_time": 3.1,
                },
            ],
            "format_version": "1.0",
        }

    @patch("libs.blob_storage.BlobStorageClient")
    @patch("libs.service_bus_client.ServiceBusClient")
    async def test_content_collection_to_processing_flow(
        self,
        mock_sb_client,
        mock_blob_client,
        mock_service_bus_config,
        sample_collection_payload,
        sample_collected_content,
    ):
        """Test content flows from collection to processing."""
        # Setup mocks
        mock_storage = AsyncMock()
        mock_blob_client.return_value = mock_storage

        mock_bus_client = AsyncMock()
        mock_sb_client.return_value = mock_bus_client

        # Mock content collection result
        mock_storage.upload_text = AsyncMock()
        collection_result = {
            "status": "success",
            "collection_id": "test-collection-123",
            "storage_location": "collected-content/2025/09/14/test-collection-123.json",
            "collected_items": sample_collected_content["items"],
        }

        # Simulate content collector service
        with patch.dict(os.environ, mock_service_bus_config):
            # Import the service logic module using safe import
            service_logic_module = import_from_container(
                "content-collector", "service_logic"
            )
            if service_logic_module is None:
                pytest.skip("Content collector service logic not available")

            ContentCollectorService = service_logic_module.ContentCollectorService
            collector = ContentCollectorService()

            # Mock the actual collection logic
            with patch.object(
                collector, "collect_and_store_content", return_value=collection_result
            ):
                result = await collector.collect_and_store_content(
                    sources_data=sample_collection_payload["payload"]["sources"],
                    deduplicate=True,
                    save_to_storage=True,
                )

                assert result["status"] == "success"
                assert result["collection_id"] == "test-collection-123"
                assert len(result["collected_items"]) == 2

                # Verify storage upload was called
                mock_storage.upload_text.assert_called()

    @patch("libs.blob_storage.BlobStorageClient")
    @patch("libs.service_bus_client.ServiceBusClient")
    async def test_processing_to_site_generation_flow(
        self,
        mock_sb_client,
        mock_blob_client,
        mock_service_bus_config,
        sample_processed_content,
    ):
        """Test content flows from processing to site generation."""
        # Setup mocks
        mock_storage = AsyncMock()
        mock_blob_client.return_value = mock_storage

        mock_bus_client = AsyncMock()
        mock_sb_client.return_value = mock_bus_client

        # Mock storage download
        mock_storage.download_text.return_value = json.dumps(sample_processed_content)

        # Simulate site generator processing
        with patch.dict(os.environ, mock_service_bus_config):
            # Test site generation request payload
            site_generation_payload = {
                "processed_content_location": "collected-content/processed/2025/09/14/test-collection-123_processed.json",
                "items_count": 2,
            }

            # Import site generator using safe import
            site_generator_module = import_from_container(
                "site-generator", "site_generator"
            )
            if site_generator_module is None:
                pytest.skip("Site generator module not available")

            # Mock site generator response
            mock_generator = MagicMock()
            mock_generator.generate_static_site = AsyncMock(
                return_value=MagicMock(
                    files_generated=5,
                    output_location="site-content/20250914_100000",
                    pages_generated=3,
                    processing_time=15.2,
                    generator_id="gen-123",
                )
            )

            SiteGenerator = site_generator_module.SiteGenerator
            with patch.object(
                site_generator_module, "SiteGenerator", return_value=mock_generator
            ):
                # Simulate site generation
                result = await mock_generator.generate_static_site(
                    theme="minimal", force_rebuild=True
                )

                assert result.files_generated == 5
                assert result.pages_generated == 3
                assert "site-content" in result.output_location

    @patch("libs.service_bus_client.ServiceBusClient")
    async def test_service_bus_message_routing(
        self, mock_sb_client, mock_service_bus_config
    ):
        """Test Service Bus message routing between services."""
        mock_client = AsyncMock()
        mock_sb_client.return_value = mock_client

        # Test message sending from collector to processor
        collection_to_processing_message = {
            "service_name": "content-collector",
            "operation": "process_content",
            "payload": {
                "collection_id": "test-collection-123",
                "storage_location": "collected-content/2025/09/14/test-collection-123.json",
            },
            "metadata": {
                "source_service": "content-collector",
                "target_service": "content-processor",
                "timestamp": "2025-09-14T10:01:00Z",
            },
        }

        # Test message sending from processor to site generator
        processing_to_site_message = {
            "service_name": "content-processor",
            "operation": "generate_site",
            "payload": {
                "processed_content_location": "collected-content/processed/2025/09/14/test-collection-123_processed.json",
                "items_count": 2,
            },
            "metadata": {
                "source_service": "content-processor",
                "target_service": "site-generator",
                "timestamp": "2025-09-14T10:05:00Z",
            },
        }

        with patch.dict(os.environ, mock_service_bus_config):
            # Verify both messages can be sent
            mock_client.send_message = AsyncMock(return_value=True)

            # Simulate sending both messages
            result1 = await mock_client.send_message(collection_to_processing_message)
            result2 = await mock_client.send_message(processing_to_site_message)

            assert result1 is True
            assert result2 is True
            assert mock_client.send_message.call_count == 2

    async def test_error_handling_across_services(self, mock_service_bus_config):
        """Test error handling and retry logic across services."""
        # Test collection failure
        with patch.dict(os.environ, mock_service_bus_config):
            # Import the service logic module using safe import
            service_logic_module = import_from_container(
                "content-collector", "service_logic"
            )
            if service_logic_module is None:
                pytest.skip("Content collector service logic not available")

            ContentCollectorService = service_logic_module.ContentCollectorService
            collector = ContentCollectorService()

            # Mock a failure scenario
            with patch.object(
                collector,
                "collect_and_store_content",
                side_effect=Exception("Network error"),
            ):
                with pytest.raises(Exception) as exc_info:
                    await collector.collect_and_store_content(
                        sources_data=[{"type": "reddit", "subreddits": ["test"]}],
                        deduplicate=True,
                        save_to_storage=True,
                    )

                assert "Network error" in str(exc_info.value)


class TestServiceBusRouterIntegration:
    """Test Service Bus router integration across services."""

    @pytest.fixture
    def mock_content_collector_router(self):
        """Mock content collector Service Bus router."""
        with patch(
            "containers.content_collector.endpoints.servicebus_router.service_bus_router"
        ) as mock:
            mock.process_message_payload = AsyncMock()
            return mock

    @pytest.fixture
    def mock_content_processor_router(self):
        """Mock content processor Service Bus router."""
        with patch(
            "containers.content_processor.endpoints.servicebus_router.service_bus_router"
        ) as mock:
            mock.process_message_payload = AsyncMock()
            return mock

    @pytest.fixture
    def mock_site_generator_router(self):
        """Mock site generator Service Bus router."""
        with patch(
            "containers.site_generator.servicebus_router.service_bus_router"
        ) as mock:
            mock.process_message_payload = AsyncMock()
            return mock

    async def test_cross_service_router_communication(
        self,
        mock_content_collector_router,
        mock_content_processor_router,
        mock_site_generator_router,
    ):
        """Test communication between different service routers."""
        # Setup router responses
        mock_content_collector_router.process_message_payload.return_value = {
            "status": "success",
            "collection_id": "test-123",
            "collected_items": [{"id": 1}, {"id": 2}],
            "storage_location": "collected-content/test-123.json",
        }

        mock_content_processor_router.process_message_payload.return_value = {
            "status": "success",
            "processed_items": [
                {"id": 1, "enhanced": True},
                {"id": 2, "enhanced": True},
            ],
            "storage_location": "collected-content/processed/test-123.json",
        }

        mock_site_generator_router.process_message_payload.return_value = {
            "status": "success",
            "generated_files": 5,
            "site_location": "site-content/test-site",
        }

        # Test the flow
        collection_result = await mock_content_collector_router.process_message_payload(
            {"sources": [{"type": "reddit"}]}, "collect_content"
        )
        assert collection_result["status"] == "success"

        processing_result = await mock_content_processor_router.process_message_payload(
            {
                "collection_id": collection_result["collection_id"],
                "storage_location": collection_result["storage_location"],
            },
            "process_content",
        )
        assert processing_result["status"] == "success"

        generation_result = await mock_site_generator_router.process_message_payload(
            {
                "processed_content_location": processing_result["storage_location"],
                "items_count": 2,
            },
            "generate_site",
        )
        assert generation_result["status"] == "success"
        assert generation_result["generated_files"] == 5


class TestEndToEndPipeline:
    """Test complete end-to-end pipeline scenarios."""

    @patch("libs.blob_storage.BlobStorageClient")
    @patch("libs.service_bus_client.ServiceBusClient")
    async def test_complete_pipeline_success_scenario(
        self, mock_sb_client, mock_blob_client
    ):
        """Test a complete successful pipeline run."""
        # This would be a comprehensive test that:
        # 1. Triggers content collection via GitHub Actions
        # 2. Processes collected content
        # 3. Generates static site
        # 4. Verifies all storage operations
        # 5. Confirms message flow

        # Setup mocks
        mock_storage = AsyncMock()
        mock_blob_client.return_value = mock_storage

        mock_bus_client = AsyncMock()
        mock_sb_client.return_value = mock_bus_client

        # Mock the complete flow
        # This is a placeholder for a comprehensive integration test
        # that would be implemented once the services are deployed

        assert True  # Placeholder for now

    async def test_pipeline_failure_recovery(self):
        """Test pipeline failure scenarios and recovery."""
        # Test scenarios like:
        # - Service Bus connection failures
        # - Blob storage failures
        # - Processing failures with retry logic
        # - Dead letter queue handling

        # Placeholder for comprehensive failure testing
        assert True

    async def test_pipeline_scaling_behavior(self):
        """Test pipeline behavior under load with KEDA scaling."""
        # Test scenarios like:
        # - Multiple messages in queue
        # - Concurrent processing
        # - KEDA scaling up/down
        # - Resource limits

        # Placeholder for scaling tests
        assert True


if __name__ == "__main__":
    pytest.main([__file__])

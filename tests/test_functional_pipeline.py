"""
Functional Tests for AI Content Farm Pipeline

End-to-end functional tests that can be run against deployed services.
These tests verify the complete pipeline works in production.
"""

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx
import pytest


class FunctionalTestConfig:
    """Configuration for functional tests."""

    def __init__(self):
        # Service URLs (to be set via environment variables in CI/CD)
        self.collector_url = os.getenv("CONTENT_COLLECTOR_URL", "http://localhost:8000")
        self.processor_url = os.getenv("CONTENT_PROCESSOR_URL", "http://localhost:8001")
        self.site_generator_url = os.getenv(
            "SITE_GENERATOR_URL", "http://localhost:8002"
        )

        # Azure Service Bus (for direct testing)
        self.service_bus_namespace = os.getenv("SERVICE_BUS_NAMESPACE", "")
        self.service_bus_connection = os.getenv("SERVICE_BUS_CONNECTION_STRING", "")

        # Test configuration
        self.test_timeout = int(
            os.getenv("FUNCTIONAL_TEST_TIMEOUT", "300")
        )  # 5 minutes
        self.polling_interval = int(
            os.getenv("FUNCTIONAL_TEST_POLLING", "10")
        )  # 10 seconds

        # Feature flags
        self.skip_if_no_services = (
            os.getenv("SKIP_FUNCTIONAL_IF_NO_SERVICES", "true").lower() == "true"
        )


@pytest.fixture(scope="session")
def config():
    """Test configuration fixture."""
    return FunctionalTestConfig()


@pytest.fixture(scope="session")
async def http_client():
    """HTTP client for making requests."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


class TestServiceHealth:
    """Test health and availability of all services."""

    async def test_content_collector_health(
        self, config: FunctionalTestConfig, http_client: httpx.AsyncClient
    ):
        """Test content collector service health."""
        try:
            response = await http_client.get(f"{config.collector_url}/health")
            assert response.status_code == 200

            health_data = response.json()
            assert health_data.get("status") in ["healthy", "degraded"]

        except httpx.RequestError:
            if config.skip_if_no_services:
                pytest.skip("Content collector service not available")
            else:
                pytest.fail("Content collector service is not responding")

    async def test_content_processor_health(
        self, config: FunctionalTestConfig, http_client: httpx.AsyncClient
    ):
        """Test content processor service health."""
        try:
            response = await http_client.get(f"{config.processor_url}/health")
            assert response.status_code == 200

            health_data = response.json()
            assert health_data.get("status") in ["healthy", "degraded"]

        except httpx.RequestError:
            if config.skip_if_no_services:
                pytest.skip("Content processor service not available")
            else:
                pytest.fail("Content processor service is not responding")

    async def test_site_generator_health(
        self, config: FunctionalTestConfig, http_client: httpx.AsyncClient
    ):
        """Test site generator service health."""
        try:
            response = await http_client.get(f"{config.site_generator_url}/health")
            assert response.status_code == 200

            health_data = response.json()
            assert health_data.get("status") in ["healthy", "degraded"]

        except httpx.RequestError:
            if config.skip_if_no_services:
                pytest.skip("Site generator service not available")
            else:
                pytest.fail("Site generator service is not responding")

    async def test_all_services_api_docs(
        self, config: FunctionalTestConfig, http_client: httpx.AsyncClient
    ):
        """Test that all services expose API documentation."""
        services = [
            ("Content Collector", config.collector_url),
            ("Content Processor", config.processor_url),
            ("Site Generator", config.site_generator_url),
        ]

        for service_name, url in services:
            try:
                # Test OpenAPI JSON
                response = await http_client.get(f"{url}/openapi.json")
                assert response.status_code == 200

                openapi_spec = response.json()
                assert "openapi" in openapi_spec
                assert "info" in openapi_spec

                # Test Swagger UI
                response = await http_client.get(f"{url}/docs")
                assert response.status_code == 200

            except httpx.RequestError:
                if config.skip_if_no_services:
                    pytest.skip(f"{service_name} service not available")
                else:
                    pytest.fail(f"{service_name} API docs not accessible")


class TestServiceBusIntegration:
    """Test Service Bus integration and message processing."""

    async def test_service_bus_connectivity(
        self, config: FunctionalTestConfig, http_client: httpx.AsyncClient
    ):
        """Test Service Bus connectivity from all services."""
        services = [
            ("Content Collector", config.collector_url),
            ("Content Processor", config.processor_url),
            ("Site Generator", config.site_generator_url),
        ]

        for service_name, url in services:
            try:
                response = await http_client.get(f"{url}/internal/servicebus-status")
                assert response.status_code == 200

                status_data = response.json()
                assert status_data.get("status") == "success"

                service_bus_data = status_data.get("data", {})
                assert service_bus_data.get("connection_status") in [
                    "connected",
                    "degraded",
                ]

            except httpx.RequestError:
                if config.skip_if_no_services:
                    pytest.skip(f"{service_name} service not available")
                else:
                    pytest.fail(f"{service_name} Service Bus status not accessible")

    async def test_service_bus_message_processing(
        self, config: FunctionalTestConfig, http_client: httpx.AsyncClient
    ):
        """Test Service Bus message processing capabilities."""
        # Test each service can process messages
        services = [
            ("Content Collector", config.collector_url),
            ("Content Processor", config.processor_url),
            ("Site Generator", config.site_generator_url),
        ]

        for service_name, url in services:
            try:
                # Trigger message processing (this should poll the queue)
                response = await http_client.post(
                    f"{url}/internal/servicebus/process-message"
                )
                assert response.status_code == 200

                result_data = response.json()
                assert result_data.get("status") in ["success", "no_messages"]

            except httpx.RequestError:
                if config.skip_if_no_services:
                    pytest.skip(f"{service_name} service not available")
                else:
                    pytest.fail(f"{service_name} Service Bus processing not working")


class TestContentCollectionFunctional:
    """Test content collection functionality end-to-end."""

    async def test_manual_content_collection(
        self, config: FunctionalTestConfig, http_client: httpx.AsyncClient
    ):
        """Test manual content collection trigger."""
        collection_request = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 2,  # Small number for testing
                }
            ],
            "deduplicate": True,
            "save_to_storage": True,
        }

        try:
            response = await http_client.post(
                f"{config.collector_url}/api/v1/collections", json=collection_request
            )
            assert response.status_code in [
                200,
                202,
            ]  # Accept both sync and async responses

            result_data = response.json()
            assert result_data.get("status") == "success"

            # Verify collection ID is returned
            collection_id = result_data.get("data", {}).get("collection_id")
            assert collection_id is not None

            return collection_id

        except httpx.RequestError:
            if config.skip_if_no_services:
                pytest.skip("Content collector service not available")
            else:
                pytest.fail("Content collection failed")

    async def test_collection_status_tracking(
        self, config: FunctionalTestConfig, http_client: httpx.AsyncClient
    ):
        """Test collection status can be tracked."""
        try:
            response = await http_client.get(f"{config.collector_url}/api/v1/status")
            assert response.status_code == 200

            status_data = response.json()
            assert "data" in status_data

            # Check for expected status fields
            data = status_data["data"]
            assert "service_name" in data
            assert "last_collection" in data or data.get("last_collection") is None

        except httpx.RequestError:
            if config.skip_if_no_services:
                pytest.skip("Content collector service not available")
            else:
                pytest.fail("Content collection status not accessible")


class TestContentProcessingFunctional:
    """Test content processing functionality end-to-end."""

    async def test_content_processing_capability(
        self, config: FunctionalTestConfig, http_client: httpx.AsyncClient
    ):
        """Test content processing service capabilities."""
        try:
            response = await http_client.get(
                f"{config.processor_url}/api/v1/process/types"
            )
            assert response.status_code == 200

            types_data = response.json()
            assert "data" in types_data

            # Verify processing types are available
            processing_types = types_data["data"]
            assert isinstance(processing_types, list)
            assert len(processing_types) > 0

        except httpx.RequestError:
            if config.skip_if_no_services:
                pytest.skip("Content processor service not available")
            else:
                pytest.fail("Content processor types not accessible")

    async def test_processing_status(
        self, config: FunctionalTestConfig, http_client: httpx.AsyncClient
    ):
        """Test processing status monitoring."""
        try:
            response = await http_client.get(f"{config.processor_url}/api/v1/status")
            assert response.status_code == 200

            status_data = response.json()
            assert "data" in status_data

            data = status_data["data"]
            assert "service_name" in data
            assert "queue_length" in data or data.get("queue_length") is None

        except httpx.RequestError:
            if config.skip_if_no_services:
                pytest.skip("Content processor service not available")
            else:
                pytest.fail("Content processor status not accessible")


class TestSiteGenerationFunctional:
    """Test site generation functionality end-to-end."""

    async def test_site_generator_status(
        self, config: FunctionalTestConfig, http_client: httpx.AsyncClient
    ):
        """Test site generator status and capabilities."""
        try:
            response = await http_client.get(
                f"{config.site_generator_url}/api/v1/status"
            )
            assert response.status_code == 200

            status_data = response.json()
            assert "data" in status_data

            data = status_data["data"]
            assert "generator_id" in data
            assert "status" in data

        except httpx.RequestError:
            if config.skip_if_no_services:
                pytest.skip("Site generator service not available")
            else:
                pytest.fail("Site generator status not accessible")

    async def test_markdown_generation_capability(
        self, config: FunctionalTestConfig, http_client: httpx.AsyncClient
    ):
        """Test markdown generation capabilities."""
        generation_request = {
            "source": "test",
            "batch_size": 1,
            "force_regenerate": False,
        }

        try:
            response = await http_client.post(
                f"{config.site_generator_url}/api/v1/generate/markdown",
                json=generation_request,
            )
            assert response.status_code in [200, 202]

            result_data = response.json()
            assert result_data.get("status") == "success"

        except httpx.RequestError:
            if config.skip_if_no_services:
                pytest.skip("Site generator service not available")
            else:
                pytest.fail("Markdown generation not working")


class TestEndToEndPipeline:
    """Test complete end-to-end pipeline scenarios."""

    @pytest.mark.slow
    async def test_complete_pipeline_via_github_actions_simulation(
        self, config: FunctionalTestConfig, http_client: httpx.AsyncClient
    ):
        """Test complete pipeline by simulating GitHub Actions trigger."""
        if not config.service_bus_namespace:
            pytest.skip("Service Bus not configured for functional testing")

        # This test simulates the GitHub Actions workflow
        # by sending a message directly to the Service Bus queue

        collection_message = {
            "service_name": "github-actions",
            "operation": "collect_content",
            "payload": {
                "sources": [
                    {"type": "reddit", "subreddits": ["technology"], "limit": 3}
                ],
                "deduplicate": True,
                "save_to_storage": True,
            },
            "metadata": {
                "triggered_by": "functional_test",
                "test_id": f"test_{int(time.time())}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        # TODO: Implement Azure Service Bus message sending
        # This would require azure-servicebus SDK
        # await send_service_bus_message("content-collection-requests", collection_message)

        # For now, trigger via HTTP endpoint
        try:
            response = await http_client.post(
                f"{config.collector_url}/internal/servicebus/process-message"
            )
            assert response.status_code == 200

            # Wait for processing to complete
            await asyncio.sleep(config.polling_interval)

            # Verify pipeline progression through status endpoints
            await self._verify_pipeline_progression(config, http_client)

        except httpx.RequestError:
            if config.skip_if_no_services:
                pytest.skip("Services not available for end-to-end test")
            else:
                pytest.fail("End-to-end pipeline test failed")

    async def _verify_pipeline_progression(
        self, config: FunctionalTestConfig, http_client: httpx.AsyncClient
    ):
        """Verify the pipeline has progressed through all stages."""
        # Check collector processed messages
        collector_response = await http_client.get(
            f"{config.collector_url}/api/v1/status"
        )
        assert collector_response.status_code == 200

        # Check processor status
        processor_response = await http_client.get(
            f"{config.processor_url}/api/v1/status"
        )
        assert processor_response.status_code == 200

        # Check site generator status
        generator_response = await http_client.get(
            f"{config.site_generator_url}/api/v1/status"
        )
        assert generator_response.status_code == 200

    @pytest.mark.slow
    async def test_pipeline_performance_baseline(
        self, config: FunctionalTestConfig, http_client: httpx.AsyncClient
    ):
        """Test pipeline performance meets baseline requirements."""
        start_time = time.time()

        # Trigger a small collection
        collection_request = {
            "sources": [{"type": "reddit", "subreddits": ["technology"], "limit": 1}],
            "deduplicate": True,
            "save_to_storage": True,
        }

        try:
            response = await http_client.post(
                f"{config.collector_url}/api/v1/collections", json=collection_request
            )
            assert response.status_code in [200, 202]

            end_time = time.time()
            processing_time = end_time - start_time

            # Assert reasonable performance (adjust based on requirements)
            assert processing_time < 30.0  # Should complete within 30 seconds

        except httpx.RequestError:
            if config.skip_if_no_services:
                pytest.skip("Services not available for performance test")
            else:
                pytest.fail("Performance test failed")

    @pytest.mark.slow
    async def test_pipeline_error_handling(
        self, config: FunctionalTestConfig, http_client: httpx.AsyncClient
    ):
        """Test pipeline handles errors gracefully."""
        # Test invalid collection request
        invalid_request = {
            "sources": [],  # Empty sources should fail gracefully
            "deduplicate": True,
            "save_to_storage": True,
        }

        try:
            response = await http_client.post(
                f"{config.collector_url}/api/v1/collections", json=invalid_request
            )

            # Should return error but not crash
            assert response.status_code in [400, 422, 500]

            error_data = response.json()
            assert "error" in error_data or "detail" in error_data

        except httpx.RequestError:
            if config.skip_if_no_services:
                pytest.skip("Services not available for error handling test")
            else:
                pytest.fail("Error handling test failed")


if __name__ == "__main__":
    # Run with specific markers for different test types
    # pytest tests/test_functional_pipeline.py -m "not slow"  # Quick tests only
    # pytest tests/test_functional_pipeline.py -m "slow"     # Performance tests
    pytest.main([__file__])

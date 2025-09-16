"""
Integration test for queue properties and metrics collection system.
This test validates the complete end-to-end functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libs.scaling_metrics import ScalingMetricsCollector
from libs.service_bus_client import ServiceBusClient, ServiceBusConfig
from libs.service_bus_router import ServiceBusRouterBase


class TestMetricsQueuePropertiesIntegration:
    """Integration tests for queue properties and metrics collection."""

    @pytest.mark.asyncio
    async def test_end_to_end_queue_monitoring(self):
        """Test complete queue monitoring with properties and metrics."""

        # Setup
        config = ServiceBusConfig(
            namespace="test-namespace", queue_name="integration-test-queue"
        )

        service_bus_client = ServiceBusClient(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            metrics_collector = ScalingMetricsCollector("integration-test", temp_dir)

            # Mock Azure Service Bus components
            with patch(
                "azure.servicebus.management.ServiceBusAdministrationClient"
            ) as mock_mgmt:
                mock_mgmt_instance = MagicMock()
                mock_mgmt.return_value = mock_mgmt_instance

                # Mock queue properties response
                from azure.servicebus.management import QueueRuntimeProperties

                mock_properties = MagicMock(spec=QueueRuntimeProperties)
                mock_properties.active_message_count = 25
                mock_properties.dead_letter_message_count = 2
                mock_properties.scheduled_message_count = 0
                mock_properties.transfer_message_count = 0
                mock_properties.transfer_dead_letter_message_count = 0
                mock_properties.size_in_bytes = 2048
                mock_properties.created_at = None
                mock_properties.updated_at = None
                mock_properties.accessed_at = None

                mock_mgmt_instance.get_queue_runtime_properties.return_value = (
                    mock_properties
                )

                # Test queue properties retrieval
                queue_props = await service_bus_client.get_queue_properties()

                assert queue_props["status"] == "healthy"
                assert queue_props["active_message_count"] == 25
                assert queue_props["dead_letter_message_count"] == 2
                assert queue_props["total_message_count"] == 27

                # Test metrics collection with queue depth information
                metrics_collector.record_batch_processing(
                    batch_id="integration_batch_1",
                    queue_name="integration-test-queue",
                    batch_size=5,
                    total_processing_time_ms=1500,
                    messages_processed=5,
                    messages_failed=0,
                    queue_depth_before=queue_props["active_message_count"],
                    queue_depth_after=queue_props["active_message_count"] - 5,
                )

                # Test performance summary includes queue depth
                summary = metrics_collector.get_performance_summary()

                assert summary["service"] == "integration-test"
                assert summary["batches_processed"] == 1
                assert summary["avg_queue_depth_before"] == 25.0
                assert summary["avg_queue_depth_after"] == 20.0
                assert summary["avg_messages_per_batch"] == 5.0

                # Test metrics persistence
                metrics_collector.flush_metrics()

                # Verify files were created
                storage_path = Path(temp_dir)
                batch_files = list(storage_path.glob("batches_*.json"))
                assert len(batch_files) == 1

                # Verify content includes queue depth
                import json

                with open(batch_files[0]) as f:
                    batch_data = json.load(f)
                    assert len(batch_data) == 1
                    assert batch_data[0]["queue_depth_before"] == 25
                    assert batch_data[0]["queue_depth_after"] == 20

    @pytest.mark.asyncio
    async def test_service_bus_router_metrics_integration(self):
        """Test metrics collection integration without router complexity."""

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create metrics collector
            metrics_collector = ScalingMetricsCollector("router-test", temp_dir)

            # Simulate queue monitoring before processing
            queue_depth_before = 15

            # Simulate processing some messages
            batch_id = "integration_batch"
            processing_time = 1200
            messages_processed = 3

            # Simulate queue monitoring after processing
            queue_depth_after = 12

            # Record batch processing with queue depth
            metrics_collector.record_batch_processing(
                batch_id=batch_id,
                queue_name="router-test-queue",
                batch_size=messages_processed,
                total_processing_time_ms=processing_time,
                messages_processed=messages_processed,
                messages_failed=0,
                queue_depth_before=queue_depth_before,
                queue_depth_after=queue_depth_after,
            )

            # Verify metrics include queue depth
            summary = metrics_collector.get_performance_summary()
            assert summary["service"] == "router-test"
            assert summary["avg_queue_depth_before"] == 15.0
            assert summary["avg_queue_depth_after"] == 12.0
            assert summary["batches_processed"] == 1

            # Test persistence
            metrics_collector.flush_metrics()

            # Verify files contain queue depth data
            storage_path = Path(temp_dir)
            batch_files = list(storage_path.glob("batches_*.json"))
            assert len(batch_files) == 1

            import json

            with open(batch_files[0]) as f:
                batch_data = json.load(f)
                assert batch_data[0]["queue_depth_before"] == 15
                assert batch_data[0]["queue_depth_after"] == 12

    def test_metrics_analyzer_with_queue_depth(self):
        """Test that scaling analyzer can process queue depth metrics."""

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test metrics data with queue depth
            import json
            from datetime import datetime, timezone

            from libs.scaling_analyzer import ScalingAnalyzer

            # Create sample batch metrics with queue depth
            batch_metrics = [
                {
                    "batch_id": "test_batch_1",
                    "service_name": "test-service",
                    "queue_name": "test-queue",
                    "batch_size": 3,
                    "total_processing_time_ms": 1200,
                    "messages_processed": 3,
                    "messages_failed": 0,
                    "container_id": "test-container",
                    "container_startup_time_ms": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "queue_depth_before": 20,
                    "queue_depth_after": 17,
                },
                {
                    "batch_id": "test_batch_2",
                    "service_name": "test-service",
                    "queue_name": "test-queue",
                    "batch_size": 5,
                    "total_processing_time_ms": 1800,
                    "messages_processed": 5,
                    "messages_failed": 0,
                    "container_id": "test-container",
                    "container_startup_time_ms": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "queue_depth_before": 17,
                    "queue_depth_after": 12,
                },
            ]

            # Write test data to temp directory
            test_file = Path(temp_dir) / "batches_test-service_20240101_120000.json"
            with open(test_file, "w") as f:
                json.dump(batch_metrics, f)

            # Test analyzer
            analyzer = ScalingAnalyzer(temp_dir)
            # Load the metrics we just created
            analyzer.load_metrics(hours_back=1)
            analysis = analyzer.analyze_service_performance("test-service")

            # Verify analysis includes queue depth insights
            assert analysis["status"] == "healthy"
            assert "queue_depth_analysis" in analysis
            # (20 + 17) / 2
            assert analysis["queue_depth_analysis"]["avg_queue_depth_before"] == 18.5
            # (17 + 12) / 2
            assert analysis["queue_depth_analysis"]["avg_queue_depth_after"] == 14.5
            # (3 + 5) / 2
            assert analysis["queue_depth_analysis"]["avg_queue_reduction"] == 4.0

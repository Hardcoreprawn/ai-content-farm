"""
Test scaling metrics collection and analysis functionality.
"""

import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from libs.scaling_analyzer import ScalingAnalyzer
from libs.scaling_metrics import ScalingMetricsCollector, get_metrics_collector


class TestScalingMetrics:
    """Test scaling metrics collection."""

    def test_metrics_collector_initialization(self):
        """Test metrics collector initializes correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = ScalingMetricsCollector("test-service", temp_dir)

            assert collector.service_name == "test-service"
            assert collector.storage_path == Path(temp_dir)
            assert len(collector._message_metrics) == 0
            assert len(collector._batch_metrics) == 0

    def test_record_message_processing(self):
        """Test recording individual message metrics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = ScalingMetricsCollector("test-service", temp_dir)

            collector.record_message_processing(
                message_id="msg_123",
                queue_name="test-queue",
                processing_time_ms=150,
                batch_size=3,
                batch_position=1,
                success=True,
            )

            assert len(collector._message_metrics) == 1
            metric = collector._message_metrics[0]

            assert metric.message_id == "msg_123"
            assert metric.queue_name == "test-queue"
            assert metric.processing_time_ms == 150
            assert metric.batch_size == 3
            assert metric.batch_position == 1
            assert metric.success is True
            assert metric.error_type is None

    def test_record_batch_processing(self):
        """Test recording batch processing metrics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = ScalingMetricsCollector("test-service", temp_dir)

            collector.record_batch_processing(
                batch_id="batch_456",
                queue_name="test-queue",
                batch_size=5,
                total_processing_time_ms=2500,
                messages_processed=4,
                messages_failed=1,
                queue_depth_before=10,
                queue_depth_after=6,
            )

            assert len(collector._batch_metrics) == 1
            metric = collector._batch_metrics[0]

            assert metric.batch_id == "batch_456"
            assert metric.batch_size == 5
            assert metric.total_processing_time_ms == 2500
            assert metric.messages_processed == 4
            assert metric.messages_failed == 1
            assert metric.queue_depth_before == 10
            assert metric.queue_depth_after == 6

    def test_performance_summary(self):
        """Test performance summary generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = ScalingMetricsCollector("test-service", temp_dir)

            # Record several batches
            for i in range(3):
                collector.record_batch_processing(
                    batch_id=f"batch_{i}",
                    queue_name="test-queue",
                    batch_size=3,
                    total_processing_time_ms=1000 + i * 100,  # 1000, 1100, 1200
                    messages_processed=3,
                    messages_failed=0,
                )

            summary = collector.get_performance_summary()

            assert summary["service"] == "test-service"
            assert summary["batches_processed"] == 3
            # Average of 1000, 1100, 1200
            assert summary["avg_batch_time_ms"] == 1100.0
            assert summary["avg_messages_per_batch"] == 3.0
            assert summary["avg_time_per_message_ms"] == 366.7  # 1100 / 3
            assert summary["total_messages_processed"] == 9
            assert summary["total_messages_failed"] == 0

    def test_flush_metrics_to_storage(self):
        """Test flushing metrics to JSON files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = ScalingMetricsCollector("test-service", temp_dir)

            # Add some metrics
            collector.record_message_processing(
                message_id="msg_1",
                queue_name="test-queue",
                processing_time_ms=100,
                batch_size=1,
                batch_position=0,
                success=True,
            )

            collector.record_batch_processing(
                batch_id="batch_1",
                queue_name="test-queue",
                batch_size=1,
                total_processing_time_ms=150,
                messages_processed=1,
                messages_failed=0,
                queue_depth_before=10,
                queue_depth_after=9,
            )

            # Flush to storage
            collector.flush_metrics()

            # Check files were created
            storage_path = Path(temp_dir)
            message_files = list(storage_path.glob("messages_*.json"))
            batch_files = list(storage_path.glob("batches_*.json"))

            assert len(message_files) == 1
            assert len(batch_files) == 1

            # Verify content
            with open(message_files[0]) as f:
                message_data = json.load(f)
                assert len(message_data) == 1
                assert message_data[0]["message_id"] == "msg_1"

            with open(batch_files[0]) as f:
                batch_data = json.load(f)
                assert len(batch_data) == 1
                assert batch_data[0]["batch_id"] == "batch_1"

    def test_queue_depth_metrics(self):
        """Test queue depth tracking in batch processing metrics."""
        collector = ScalingMetricsCollector("test-service")

        # Record batch with queue depth information
        collector.record_batch_processing(
            batch_id="batch_with_depth",
            queue_name="test-queue",
            batch_size=5,
            total_processing_time_ms=2000,
            messages_processed=5,
            messages_failed=0,
            queue_depth_before=15,
            queue_depth_after=10,
        )

        # Check metrics were recorded with queue depth
        assert len(collector._batch_metrics) == 1
        batch_metric = collector._batch_metrics[0]

        assert batch_metric.queue_depth_before == 15
        assert batch_metric.queue_depth_after == 10

        # Generate summary
        summary = collector.get_performance_summary()
        assert "avg_queue_depth_before" in summary
        assert "avg_queue_depth_after" in summary
        assert summary["avg_queue_depth_before"] == 15.0
        assert summary["avg_queue_depth_after"] == 10.0

    def test_queue_depth_optional(self):
        """Test that queue depth parameters are optional."""
        collector = ScalingMetricsCollector("test-service")

        # Record batch without queue depth information
        collector.record_batch_processing(
            batch_id="batch_no_depth",
            queue_name="test-queue",
            batch_size=3,
            total_processing_time_ms=1000,
            messages_processed=3,
            messages_failed=0,
        )

        # Check metrics were recorded without queue depth
        assert len(collector._batch_metrics) == 1
        batch_metric = collector._batch_metrics[0]

        assert batch_metric.queue_depth_before is None
        assert batch_metric.queue_depth_after is None

        # Generate summary should handle missing queue depth gracefully
        summary = collector.get_performance_summary()
        assert summary.get("avg_queue_depth_before") is None
        assert summary.get("avg_queue_depth_after") is None

    def test_mixed_queue_depth_batches(self):
        """Test averaging queue depth when some batches have depth and others don't."""
        collector = ScalingMetricsCollector("test-service")

        # Batch with depth
        collector.record_batch_processing(
            batch_id="batch_1",
            queue_name="test-queue",
            batch_size=2,
            total_processing_time_ms=500,
            messages_processed=2,
            messages_failed=0,
            queue_depth_before=20,
            queue_depth_after=18,
        )

        # Batch without depth
        collector.record_batch_processing(
            batch_id="batch_2",
            queue_name="test-queue",
            batch_size=3,
            total_processing_time_ms=750,
            messages_processed=3,
            messages_failed=0,
        )

        # Batch with depth again
        collector.record_batch_processing(
            batch_id="batch_3",
            queue_name="test-queue",
            batch_size=1,
            total_processing_time_ms=250,
            messages_processed=1,
            messages_failed=0,
            queue_depth_before=10,
            queue_depth_after=9,
        )

        summary = collector.get_performance_summary()

        # Should average only the batches that have depth information
        # (20 + 10) / 2 = 15.0
        assert summary["avg_queue_depth_before"] == 15.0
        # (18 + 9) / 2 = 13.5
        assert summary["avg_queue_depth_after"] == 13.5

    def test_flush_metrics_clears_buffers(self):
        """Test that flushing metrics clears the in-memory buffers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = ScalingMetricsCollector("test-service", temp_dir)

            # Add some test data
            collector.record_message_processing(
                message_id="test_msg",
                queue_name="test-queue",
                processing_time_ms=100,
                batch_size=1,
                batch_position=0,
                success=True,
            )

            collector.record_batch_processing(
                batch_id="test_batch",
                queue_name="test-queue",
                batch_size=1,
                total_processing_time_ms=150,
                messages_processed=1,
                messages_failed=0,
            )

            # Verify data is in buffers
            assert len(collector._message_metrics) == 1
            assert len(collector._batch_metrics) == 1

            # Flush and verify buffers are cleared
            collector.flush_metrics()
            assert len(collector._message_metrics) == 0
            assert len(collector._batch_metrics) == 0


class TestScalingAnalyzer:
    """Test scaling analysis functionality."""

    def test_analyzer_initialization(self):
        """Test analyzer initializes correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = ScalingAnalyzer(temp_dir)

            assert analyzer.metrics_path == Path(temp_dir)
            assert len(analyzer.batch_metrics) == 0
            assert len(analyzer.message_metrics) == 0

    def test_analyze_service_performance_no_data(self):
        """Test analysis when no data is available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = ScalingAnalyzer(temp_dir)

            result = analyzer.analyze_service_performance("unknown-service")

            assert "error" in result
            assert "No batch metrics found" in result["error"]

    def test_analyze_service_performance_with_data(self):
        """Test analysis with sample data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample metrics data
            batch_metrics = [
                {
                    "service_name": "test-service",
                    "total_processing_time_ms": 1000,
                    "batch_size": 3,
                    "messages_processed": 3,
                    "messages_failed": 0,
                    "container_startup_time_ms": 2000,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "service_name": "test-service",
                    "total_processing_time_ms": 1200,
                    "batch_size": 2,
                    "messages_processed": 2,
                    "messages_failed": 0,
                    "container_startup_time_ms": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            ]

            # Write test data
            metrics_file = Path(temp_dir) / "batches_test-service_test.json"
            with open(metrics_file, "w") as f:
                json.dump(batch_metrics, f)

            analyzer = ScalingAnalyzer(temp_dir)
            analyzer.load_metrics(hours_back=1)

            result = analyzer.analyze_service_performance("test-service")

            assert result["service_name"] == "test-service"
            assert result["batches_analyzed"] == 2
            assert result["total_messages_processed"] == 5
            assert result["processing_performance"]["avg_batch_time_ms"] == 1100.0
            assert result["scaling_performance"]["avg_container_startup_ms"] == 2000.0


# Integration test
@pytest.mark.integration
class TestMetricsIntegration:
    """Test integration between metrics collection and analysis."""

    def test_end_to_end_metrics_flow(self):
        """Test complete metrics collection and analysis flow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Collect metrics
            collector = ScalingMetricsCollector("content-processor", temp_dir)

            # Simulate processing several batches
            for batch_num in range(3):
                # Record messages in this batch
                for msg_num in range(2):
                    collector.record_message_processing(
                        message_id=f"msg_{batch_num}_{msg_num}",
                        queue_name="content-processing-requests",
                        processing_time_ms=500 + msg_num * 100,
                        batch_size=2,
                        batch_position=msg_num,
                        success=True,
                    )

                # Record the batch
                collector.record_batch_processing(
                    batch_id=f"batch_{batch_num}",
                    queue_name="content-processing-requests",
                    batch_size=2,
                    total_processing_time_ms=1200 + batch_num * 200,
                    messages_processed=2,
                    messages_failed=0,
                )

            # Flush to storage
            collector.flush_metrics()

            # Step 2: Analyze metrics
            analyzer = ScalingAnalyzer(temp_dir)
            analyzer.load_metrics(hours_back=1)

            analysis = analyzer.analyze_service_performance("content-processor")

            # Verify analysis results
            assert analysis["service_name"] == "content-processor"
            assert analysis["batches_analyzed"] == 3
            assert analysis["total_messages_processed"] == 6

            # Step 3: Generate recommendations
            recommendations = analyzer.generate_scaling_recommendations(
                "content-processor"
            )

            # Should have some recommendations
            assert len(recommendations) >= 1

            # Step 4: Generate report
            report = analyzer.generate_report(["content-processor"])

            assert "CONTENT-PROCESSOR" in report  # Check exact case
            assert "Performance Metrics" in report
            # Scaling Recommendations section should exist
            assert (
                "Scaling Recommendations" in report
                or "No optimization recommendations" in report
            )


if __name__ == "__main__":
    # Run basic test
    test = TestScalingMetrics()
    test.test_metrics_collector_initialization()
    test.test_record_message_processing()
    test.test_performance_summary()
    print("✅ Basic scaling metrics tests passed!")

    # Run integration test
    integration = TestMetricsIntegration()
    integration.test_end_to_end_metrics_flow()
    print("✅ Integration test passed!")

    print("\n🎯 Scaling metrics system is ready for data collection!")

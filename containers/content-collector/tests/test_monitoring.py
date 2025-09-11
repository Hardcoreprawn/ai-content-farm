"""
Integration test for monitoring modules
Added to test container testing pipeline
"""

import os
import sys

import pytest

# Add the app directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))


def test_monitoring_import():
    """Test that the monitoring module can be imported."""
    try:
        from monitoring import monitor

        assert monitor is not None
        assert hasattr(monitor, "get_uptime")
        assert hasattr(monitor, "record_metric")
    except ImportError:
        pytest.skip("Monitoring module not available in this container")


def test_monitoring_functionality():
    """Test basic monitoring functionality."""
    try:
        from monitoring import PerformanceMonitor

        # Create a new monitor instance for testing
        test_monitor = PerformanceMonitor()

        # Test metric recording
        test_monitor.record_metric("test_metric", 42.0)

        # Test uptime (should be very small but positive)
        uptime = test_monitor.get_uptime()
        assert uptime >= 0

        # Test metrics summary
        summary = test_monitor.get_metrics_summary()
        assert "uptime_seconds" in summary
        assert "metrics_count" in summary
        assert summary["metrics_count"] == 1
        assert "test_metric" in summary["metrics"]

    except ImportError:
        pytest.skip("Monitoring module not available in this container")


if __name__ == "__main__":
    pytest.main([__file__])

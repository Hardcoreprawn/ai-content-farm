# Performance Monitoring Module
# Added to test container rebuild pipeline

import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Simple performance monitoring for pipeline testing."""

    def __init__(self):
        self.start_time = time.time()
        self.metrics = {}

    def record_metric(self, name: str, value: float) -> None:
        """Record a performance metric with timestamp."""
        self.metrics[name] = {
            "value": value,
            "timestamp": time.time(),
            "uptime_at_record": self.get_uptime(),
        }
        logger.info(f"Performance metric recorded: {name} = {value}")

    def get_metric_count(self) -> int:
        """Get the total number of recorded metrics."""
        return len(self.metrics)

    def get_uptime(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self.start_time

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        return {
            "uptime_seconds": self.get_uptime(),
            "metrics_count": len(self.metrics),
            "last_updated": time.time(),
            "metrics": self.metrics,
        }


# Global monitor instance
monitor = PerformanceMonitor()

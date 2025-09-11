# Performance Monitoring Module
# Added to test container rebuild pipeline

import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ProcessingMetrics:
    """Processing performance metrics for pipeline testing."""

    def __init__(self):
        self.start_time = time.time()
        self.processed_items = 0
        self.errors = 0

    def increment_processed(self) -> None:
        """Increment processed items counter."""
        self.processed_items += 1

    def increment_errors(self) -> None:
        """Increment error counter."""
        self.errors += 1
        logger.warning(f"Processing error count: {self.errors}")

    def get_processing_rate(self) -> float:
        """Get items processed per second."""
        uptime = time.time() - self.start_time
        return self.processed_items / uptime if uptime > 0 else 0

    def get_metrics(self) -> Dict[str, Any]:
        """Get processing metrics summary."""
        return {
            "processed_items": self.processed_items,
            "errors": self.errors,
            "processing_rate_per_sec": self.get_processing_rate(),
            "uptime_seconds": time.time() - self.start_time,
        }


# Global metrics instance
metrics = ProcessingMetrics()

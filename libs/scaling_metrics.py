"""
Scaling Metrics Collection for KEDA Optimization

Collects performance data to optimize KEDA scaling rules and resource allocation.
Provides insights into:
- Message processing performance
- Container scaling behavior
- Resource utilization patterns
- Cost optimization opportunities
"""

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MessageProcessingMetric:
    """Single message processing performance metric."""

    message_id: str
    service_name: str
    queue_name: str
    processing_time_ms: int
    batch_size: int
    batch_position: int  # Position in batch (0-based)
    container_id: str
    timestamp: str
    success: bool
    error_type: Optional[str] = None
    resource_usage: Optional[Dict[str, Any]] = None


@dataclass
class BatchProcessingMetric:
    """Batch processing performance metric."""

    batch_id: str
    service_name: str
    queue_name: str
    batch_size: int
    total_processing_time_ms: int
    messages_processed: int
    messages_failed: int
    container_id: str
    container_startup_time_ms: Optional[int]
    timestamp: str
    queue_depth_before: Optional[int] = None
    queue_depth_after: Optional[int] = None


@dataclass
class ScalingEvent:
    """KEDA scaling event metric."""

    service_name: str
    queue_name: str
    event_type: str  # scale_up, scale_down, steady_state
    containers_before: int
    containers_after: int
    queue_depth: int
    trigger_reason: str
    timestamp: str


class ScalingMetricsCollector:
    """Collects and stores scaling performance metrics."""

    def __init__(self, service_name: str, storage_path: str = "/tmp/scaling_metrics"):
        self.service_name = service_name
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)

        # In-memory buffers for batching writes
        self._message_metrics: List[MessageProcessingMetric] = []
        self._batch_metrics: List[BatchProcessingMetric] = []
        self._scaling_events: List[ScalingEvent] = []

        self._container_start_time = time.time() * 1000  # Container startup tracking

    def record_message_processing(
        self,
        message_id: str,
        queue_name: str,
        processing_time_ms: int,
        batch_size: int,
        batch_position: int,
        success: bool,
        error_type: Optional[str] = None,
        container_id: Optional[str] = None,
    ):
        """Record individual message processing metrics."""
        metric = MessageProcessingMetric(
            message_id=message_id,
            service_name=self.service_name,
            queue_name=queue_name,
            processing_time_ms=processing_time_ms,
            batch_size=batch_size,
            batch_position=batch_position,
            container_id=container_id or self._get_container_id(),
            timestamp=self._get_timestamp(),
            success=success,
            error_type=error_type,
        )

        self._message_metrics.append(metric)

        # Auto-flush if buffer gets large
        if len(self._message_metrics) >= 50:
            self.flush_metrics()

    def record_batch_processing(
        self,
        batch_id: str,
        queue_name: str,
        batch_size: int,
        total_processing_time_ms: int,
        messages_processed: int,
        messages_failed: int,
        queue_depth_before: Optional[int] = None,
        queue_depth_after: Optional[int] = None,
        container_id: Optional[str] = None,
    ):
        """Record batch processing metrics."""
        # Calculate container startup time (only for first batch)
        container_startup_time = None
        if not self._batch_metrics:
            container_startup_time = int(
                time.time() * 1000 - self._container_start_time
            )

        metric = BatchProcessingMetric(
            batch_id=batch_id,
            service_name=self.service_name,
            queue_name=queue_name,
            batch_size=batch_size,
            total_processing_time_ms=total_processing_time_ms,
            messages_processed=messages_processed,
            messages_failed=messages_failed,
            container_id=container_id or self._get_container_id(),
            container_startup_time_ms=container_startup_time,
            timestamp=self._get_timestamp(),
            queue_depth_before=queue_depth_before,
            queue_depth_after=queue_depth_after,
        )

        self._batch_metrics.append(metric)

        # Log key performance indicators
        avg_time_per_message = total_processing_time_ms / max(messages_processed, 1)
        logger.info(
            f"Batch processed: {messages_processed} messages in {total_processing_time_ms}ms "
            f"({avg_time_per_message:.1f}ms/message, batch_size={batch_size})"
        )

        if container_startup_time:
            logger.info(f"Container startup time: {container_startup_time}ms")

    def record_scaling_event(
        self,
        queue_name: str,
        event_type: str,
        containers_before: int,
        containers_after: int,
        queue_depth: int,
        trigger_reason: str,
    ):
        """Record KEDA scaling events."""
        event = ScalingEvent(
            service_name=self.service_name,
            queue_name=queue_name,
            event_type=event_type,
            containers_before=containers_before,
            containers_after=containers_after,
            queue_depth=queue_depth,
            trigger_reason=trigger_reason,
            timestamp=self._get_timestamp(),
        )

        self._scaling_events.append(event)

        logger.info(
            f"Scaling event: {event_type} - {containers_before} -> {containers_after} containers "
            f"(queue_depth={queue_depth}, reason={trigger_reason})"
        )

    def flush_metrics(self):
        """Write buffered metrics to storage."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        # Write message metrics
        if self._message_metrics:
            message_file = (
                self.storage_path / f"messages_{self.service_name}_{timestamp}.json"
            )
            with open(message_file, "w") as f:
                json.dump([asdict(m) for m in self._message_metrics], f, indent=2)
            logger.debug(
                f"Wrote {len(self._message_metrics)} message metrics to {message_file}"
            )
            self._message_metrics.clear()

        # Write batch metrics
        if self._batch_metrics:
            batch_file = (
                self.storage_path / f"batches_{self.service_name}_{timestamp}.json"
            )
            with open(batch_file, "w") as f:
                json.dump([asdict(m) for m in self._batch_metrics], f, indent=2)
            logger.debug(
                f"Wrote {len(self._batch_metrics)} batch metrics to {batch_file}"
            )
            self._batch_metrics.clear()

        # Write scaling events
        if self._scaling_events:
            scaling_file = (
                self.storage_path / f"scaling_{self.service_name}_{timestamp}.json"
            )
            with open(scaling_file, "w") as f:
                json.dump([asdict(e) for e in self._scaling_events], f, indent=2)
            logger.debug(
                f"Wrote {len(self._scaling_events)} scaling events to {scaling_file}"
            )
            self._scaling_events.clear()

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary for monitoring."""
        if not self._batch_metrics:
            return {"status": "no_data", "batches_processed": 0}

        # Calculate averages from recent batches
        recent_batches = self._batch_metrics[-10:]  # Last 10 batches

        avg_batch_time = sum(b.total_processing_time_ms for b in recent_batches) / len(
            recent_batches
        )
        avg_messages_per_batch = sum(
            b.messages_processed for b in recent_batches
        ) / len(recent_batches)
        avg_time_per_message = avg_batch_time / max(avg_messages_per_batch, 1)

        # Calculate queue depth averages (only for batches that have depth info)
        batches_with_depth_before = [
            b for b in recent_batches if b.queue_depth_before is not None
        ]
        batches_with_depth_after = [
            b for b in recent_batches if b.queue_depth_after is not None
        ]

        avg_queue_depth_before = None
        avg_queue_depth_after = None

        if batches_with_depth_before:
            avg_queue_depth_before = sum(
                b.queue_depth_before
                for b in batches_with_depth_before
                if b.queue_depth_before is not None
            ) / len(batches_with_depth_before)

        if batches_with_depth_after:
            avg_queue_depth_after = sum(
                b.queue_depth_after
                for b in batches_with_depth_after
                if b.queue_depth_after is not None
            ) / len(batches_with_depth_after)

        summary = {
            "service": self.service_name,
            "batches_processed": len(self._batch_metrics),
            "avg_batch_time_ms": round(avg_batch_time, 1),
            "avg_messages_per_batch": round(avg_messages_per_batch, 1),
            "avg_time_per_message_ms": round(avg_time_per_message, 1),
            "container_startup_time_ms": (
                self._batch_metrics[0].container_startup_time_ms
                if self._batch_metrics
                else None
            ),
            "total_messages_processed": sum(
                b.messages_processed for b in self._batch_metrics
            ),
            "total_messages_failed": sum(
                b.messages_failed for b in self._batch_metrics
            ),
        }

        # Add queue depth averages if available
        if avg_queue_depth_before is not None:
            summary["avg_queue_depth_before"] = round(avg_queue_depth_before, 1)
        if avg_queue_depth_after is not None:
            summary["avg_queue_depth_after"] = round(avg_queue_depth_after, 1)

        return summary

    def _get_container_id(self) -> str:
        """Get container ID from environment or generate one."""
        import os

        return os.getenv("HOSTNAME", f"container_{int(time.time())}")[-8:]

    def _get_timestamp(self) -> str:
        """Get current ISO timestamp."""
        return datetime.now(timezone.utc).isoformat()


# Global instance - initialize once per container
_metrics_collector: Optional[ScalingMetricsCollector] = None


def get_metrics_collector(service_name: str) -> ScalingMetricsCollector:
    """Get or create the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = ScalingMetricsCollector(service_name)
    return _metrics_collector

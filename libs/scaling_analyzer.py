"""
Scaling Performance Analysis Tool

Analyzes collected metrics to provide insights for KEDA scaling optimization.
Generates recommendations for:
- Optimal batch sizes per service
- KEDA queue_length thresholds
- Cost vs performance tradeoffs
- Container scaling patterns
"""

import json
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Removed matplotlib dependency for now - can add visualization later
# import matplotlib.pyplot as plt
# import pandas as pd


@dataclass
class ScalingRecommendation:
    """Scaling optimization recommendation."""

    service_name: str
    current_config: Dict[str, Any]
    recommended_config: Dict[str, Any]
    expected_improvement: str
    confidence: float  # 0.0 to 1.0
    reasoning: str


class ScalingAnalyzer:
    """Analyzes scaling metrics and provides optimization recommendations."""

    def __init__(self, metrics_path: str = "/tmp/scaling_metrics"):
        self.metrics_path = Path(metrics_path)
        self.batch_metrics: List[Dict] = []
        self.message_metrics: List[Dict] = []
        self.scaling_events: List[Dict] = []

    def load_metrics(self, hours_back: int = 24):
        """Load metrics from the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)

        for metrics_file in self.metrics_path.glob("*.json"):
            try:
                with open(metrics_file, "r") as f:
                    data = json.load(f)

                if "batches_" in metrics_file.name:
                    self.batch_metrics.extend(
                        [
                            m
                            for m in data
                            if self._is_recent(m["timestamp"], cutoff_time)
                        ]
                    )
                elif "messages_" in metrics_file.name:
                    self.message_metrics.extend(
                        [
                            m
                            for m in data
                            if self._is_recent(m["timestamp"], cutoff_time)
                        ]
                    )
                elif "scaling_" in metrics_file.name:
                    self.scaling_events.extend(
                        [
                            e
                            for e in data
                            if self._is_recent(e["timestamp"], cutoff_time)
                        ]
                    )

            except Exception as e:
                print(f"Failed to load {metrics_file}: {e}")

    def analyze_service_performance(self, service_name: str) -> Dict[str, Any]:
        """Analyze performance metrics for a specific service."""
        service_batches = [
            b for b in self.batch_metrics if b["service_name"] == service_name
        ]
        service_messages = [
            m for m in self.message_metrics if m["service_name"] == service_name
        ]

        if not service_batches:
            return {"error": f"No batch metrics found for {service_name}"}

        # Processing time analysis
        processing_times = [b["total_processing_time_ms"] for b in service_batches]
        batch_sizes = [b["batch_size"] for b in service_batches]
        messages_per_batch = [b["messages_processed"] for b in service_batches]

        # Calculate averages and percentiles
        avg_processing_time = statistics.mean(processing_times)
        p95_processing_time = (
            statistics.quantiles(processing_times, n=20)[18]
            if len(processing_times) > 20
            else max(processing_times)
        )

        avg_batch_size = statistics.mean(batch_sizes)
        avg_messages_per_batch = statistics.mean(messages_per_batch)

        # Message-level analysis
        if service_messages:
            message_times = [m["processing_time_ms"] for m in service_messages]
            avg_message_time = statistics.mean(message_times)
            p95_message_time = (
                statistics.quantiles(message_times, n=20)[18]
                if len(message_times) > 20
                else max(message_times)
            )
        else:
            avg_message_time = avg_processing_time / max(avg_messages_per_batch, 1)
            p95_message_time = p95_processing_time

        # Container startup analysis
        startup_times = [
            b["container_startup_time_ms"]
            for b in service_batches
            if b.get("container_startup_time_ms")
        ]
        avg_startup_time = statistics.mean(startup_times) if startup_times else 0

        # Throughput analysis
        total_messages = sum(messages_per_batch)
        total_time_hours = len(service_batches) * (
            avg_processing_time / 1000 / 3600
        )  # Rough estimate
        messages_per_hour = total_messages / max(total_time_hours, 0.001)

        # Queue depth analysis
        queue_depth_analysis = self._analyze_queue_depth(service_batches)

        analysis_result = {
            "service_name": service_name,
            "status": "healthy",
            "batches_analyzed": len(service_batches),
            "total_messages_processed": total_messages,
            "processing_performance": {
                "avg_batch_time_ms": round(avg_processing_time, 1),
                "p95_batch_time_ms": round(p95_processing_time, 1),
                "avg_message_time_ms": round(avg_message_time, 1),
                "p95_message_time_ms": round(p95_message_time, 1),
                "avg_batch_size": round(avg_batch_size, 1),
                "avg_messages_per_batch": round(avg_messages_per_batch, 1),
            },
            "scaling_performance": {
                "avg_container_startup_ms": round(avg_startup_time, 1),
                "estimated_messages_per_hour": round(messages_per_hour, 0),
                "processing_efficiency": (
                    round((avg_messages_per_batch / avg_batch_size) * 100, 1)
                    if avg_batch_size > 0
                    else 0
                ),
            },
            "cost_analysis": {
                "startup_overhead_ratio": (
                    round(
                        (avg_startup_time / (avg_startup_time + avg_processing_time))
                        * 100,
                        1,
                    )
                    if avg_startup_time > 0
                    else 0
                ),
                "processing_to_startup_ratio": round(
                    avg_processing_time / max(avg_startup_time, 1), 2
                ),
            },
        }

        # Add queue depth analysis if available
        if queue_depth_analysis:
            analysis_result["queue_depth_analysis"] = queue_depth_analysis

        return analysis_result

    def generate_scaling_recommendations(
        self, service_name: str
    ) -> List[ScalingRecommendation]:
        """Generate KEDA scaling recommendations based on performance data."""
        analysis = self.analyze_service_performance(service_name)

        if "error" in analysis:
            return []

        recommendations = []

        # Get current performance metrics
        avg_batch_time = analysis["processing_performance"]["avg_batch_time_ms"]
        avg_startup_time = analysis["scaling_performance"]["avg_container_startup_ms"]
        avg_batch_size = analysis["processing_performance"]["avg_batch_size"]
        startup_overhead = analysis["cost_analysis"]["startup_overhead_ratio"]

        # Recommendation 1: Optimize queue_length based on batch processing capacity
        current_max_messages = self._get_current_max_messages(service_name)
        if avg_batch_time > 0 and current_max_messages:
            # Calculate optimal queue_length
            if startup_overhead > 30:  # High startup overhead
                recommended_queue_length = (
                    current_max_messages * 2
                )  # Wait for more messages
                reasoning = f"High startup overhead ({startup_overhead:.1f}%) suggests waiting for larger batches"
                confidence = 0.8
            elif startup_overhead < 10:  # Low startup overhead
                recommended_queue_length = max(
                    1, current_max_messages // 2
                )  # More responsive scaling
                reasoning = f"Low startup overhead ({startup_overhead:.1f}%) allows responsive scaling"
                confidence = 0.7
            else:
                recommended_queue_length = current_max_messages  # Keep current
                reasoning = "Current scaling appears balanced"
                confidence = 0.6

            recommendations.append(
                ScalingRecommendation(
                    service_name=service_name,
                    current_config={
                        "queue_length": 1,
                        "max_messages": current_max_messages,
                    },
                    recommended_config={
                        "queue_length": recommended_queue_length,
                        "max_messages": current_max_messages,
                    },
                    expected_improvement=f"Reduce scaling overhead by ~{min(startup_overhead * 0.3, 20):.0f}%",
                    confidence=confidence,
                    reasoning=reasoning,
                )
            )

        # Recommendation 2: Batch size optimization
        processing_efficiency = analysis["scaling_performance"]["processing_efficiency"]
        if processing_efficiency < 80:  # Low efficiency suggests batch size issues
            if avg_batch_size < (current_max_messages or 10) * 0.5:
                # Batches are often not full - suggests queue_length too low
                recommendations.append(
                    ScalingRecommendation(
                        service_name=service_name,
                        current_config={
                            "batch_efficiency": f"{processing_efficiency:.1f}%"
                        },
                        recommended_config={
                            "increase_queue_length": "to allow fuller batches"
                        },
                        expected_improvement=f"Improve batch efficiency from {processing_efficiency:.1f}% to ~85%",
                        confidence=0.7,
                        reasoning="Small batch sizes suggest premature scaling - increase queue_length",
                    )
                )

        # Recommendation 3: Message age-based scaling for SLA
        avg_message_time = analysis["processing_performance"]["avg_message_time_ms"]
        if avg_message_time > 30000:  # Messages taking >30s to process
            recommendations.append(
                ScalingRecommendation(
                    service_name=service_name,
                    current_config={"sla_protection": "none"},
                    recommended_config={"add_message_age_trigger": "300s"},  # 5 minutes
                    expected_improvement="Prevent SLA violations for long-running processing",
                    confidence=0.8,
                    reasoning=f"Average message time {avg_message_time/1000:.1f}s requires SLA protection",
                )
            )

        return recommendations

    def generate_report(self, services: Optional[List[str]] = None) -> str:
        """Generate a comprehensive scaling analysis report."""
        if services is None:
            services = list(set(b["service_name"] for b in self.batch_metrics))

        report = ["# KEDA Scaling Performance Analysis Report"]
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Data period: Last 24 hours")
        report.append("")

        for service in services:
            analysis = self.analyze_service_performance(service)
            if "error" in analysis:
                continue

            report.append(f"## {service.upper()}")
            report.append("")

            # Performance summary
            perf = analysis["processing_performance"]
            scale = analysis["scaling_performance"]
            cost = analysis["cost_analysis"]

            report.append("### Performance Metrics")
            report.append(f"- **Batches processed**: {analysis['batches_analyzed']}")
            report.append(
                f"- **Total messages**: {analysis['total_messages_processed']}"
            )
            report.append(f"- **Avg batch time**: {perf['avg_batch_time_ms']:.1f}ms")
            report.append(
                f"- **Avg message time**: {perf['avg_message_time_ms']:.1f}ms"
            )
            report.append(
                f"- **Processing efficiency**: {scale['processing_efficiency']:.1f}%"
            )
            report.append(
                f"- **Startup overhead**: {cost['startup_overhead_ratio']:.1f}%"
            )
            report.append("")

            # Recommendations
            recommendations = self.generate_scaling_recommendations(service)
            if recommendations:
                report.append("### Scaling Recommendations")
                for i, rec in enumerate(recommendations, 1):
                    report.append(
                        f"{i}. **{rec.expected_improvement}** (confidence: {rec.confidence:.0%})"
                    )
                    report.append(f"   - Current: {rec.current_config}")
                    report.append(f"   - Recommended: {rec.recommended_config}")
                    report.append(f"   - Reasoning: {rec.reasoning}")
                    report.append("")
            else:
                report.append("### Scaling Recommendations")
                report.append("No optimization recommendations at this time.")
                report.append("")

        return "\n".join(report)

    def _analyze_queue_depth(
        self, service_batches: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Analyze queue depth patterns from batch metrics."""
        batches_with_depth = [
            b
            for b in service_batches
            if b.get("queue_depth_before") is not None
            and b.get("queue_depth_after") is not None
        ]

        if not batches_with_depth:
            return None

        depths_before = [b["queue_depth_before"] for b in batches_with_depth]
        depths_after = [b["queue_depth_after"] for b in batches_with_depth]
        queue_reductions = [
            b["queue_depth_before"] - b["queue_depth_after"] for b in batches_with_depth
        ]

        return {
            "samples_with_depth": len(batches_with_depth),
            "avg_queue_depth_before": round(statistics.mean(depths_before), 1),
            "avg_queue_depth_after": round(statistics.mean(depths_after), 1),
            "avg_queue_reduction": round(statistics.mean(queue_reductions), 1),
            "max_queue_depth_observed": max(depths_before),
            "min_queue_depth_observed": min(depths_after),
            "queue_processing_efficiency": (
                round(
                    (statistics.mean(queue_reductions) / statistics.mean(depths_before))
                    * 100,
                    1,
                )
                if statistics.mean(depths_before) > 0
                else 0
            ),
        }

    def _is_recent(self, timestamp_str: str, cutoff: datetime) -> bool:
        """Check if timestamp is after cutoff."""
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return timestamp.replace(tzinfo=None) > cutoff
        except:
            return False

    def _get_current_max_messages(self, service_name: str) -> Optional[int]:
        """Get current max_messages setting for service."""
        # This would normally read from config, for now return known values
        defaults = {
            "content-collector": 15,
            "content-processor": 3,
            "site-generator": 2,
        }
        return defaults.get(service_name)


# CLI interface for running analysis
if __name__ == "__main__":
    import sys

    analyzer = ScalingAnalyzer()
    analyzer.load_metrics(hours_back=24)

    if len(sys.argv) > 1:
        service_name = sys.argv[1]
        analysis = analyzer.analyze_service_performance(service_name)
        print(json.dumps(analysis, indent=2))

        recommendations = analyzer.generate_scaling_recommendations(service_name)
        if recommendations:
            print(f"\nRecommendations for {service_name}:")
            for rec in recommendations:
                print(f"- {rec.expected_improvement}")
                print(f"  Reasoning: {rec.reasoning}")
    else:
        # Generate full report
        report = analyzer.generate_report()
        print(report)

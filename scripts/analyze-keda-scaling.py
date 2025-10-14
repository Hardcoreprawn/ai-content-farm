#!/usr/bin/env python3
"""
KEDA Scaling Analysis Tool
Analyzes queue depths, processing times, and container scaling behavior
to provide recommendations for optimal KEDA scaling parameters.

Usage:
    python analyze-keda-scaling.py --csv metrics.csv
    python analyze-keda-scaling.py --live --duration 30
"""

import argparse
import csv
import json
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class ScalingMetrics:
    """Container scaling metrics over time"""

    timestamp: datetime
    queue_depth: int
    replica_count: int
    target_replica_count: int
    scaling_latency: float  # Time to scale up/down


@dataclass
class PipelineStage:
    """Configuration and metrics for a pipeline stage"""

    name: str
    queue_name: str
    container_name: str
    current_min_replicas: int
    current_max_replicas: int
    current_queue_length: int
    current_activation_length: int
    metrics: List[ScalingMetrics]

    @property
    def avg_queue_depth(self) -> float:
        if not self.metrics:
            return 0.0
        return np.mean([m.queue_depth for m in self.metrics])

    @property
    def max_queue_depth(self) -> int:
        if not self.metrics:
            return 0
        return max(m.queue_depth for m in self.metrics)

    @property
    def avg_replicas(self) -> float:
        if not self.metrics:
            return 0.0
        return np.mean([m.replica_count for m in self.metrics])

    @property
    def scale_up_events(self) -> int:
        """Count how many times replicas increased"""
        count = 0
        for i in range(1, len(self.metrics)):
            if self.metrics[i].replica_count > self.metrics[i - 1].replica_count:
                count += 1
        return count

    @property
    def scale_down_events(self) -> int:
        """Count how many times replicas decreased"""
        count = 0
        for i in range(1, len(self.metrics)):
            if self.metrics[i].replica_count < self.metrics[i - 1].replica_count:
                count += 1
        return count

    @property
    def avg_scale_up_latency(self) -> float:
        """Average time from queue increase to replica scale up"""
        latencies = []
        for i in range(1, len(self.metrics)):
            prev = self.metrics[i - 1]
            curr = self.metrics[i]
            if curr.replica_count > prev.replica_count:
                time_diff = (curr.timestamp - prev.timestamp).total_seconds()
                latencies.append(time_diff)
        return np.mean(latencies) if latencies else 0.0


class KEDAAnalyzer:
    """Analyze KEDA scaling behavior and provide recommendations"""

    # Pipeline stage configuration
    STAGES = {
        "collector": {
            "queue": "content-collection-requests",
            "container": "collector",
            "current_config": {
                "min_replicas": 0,
                "max_replicas": 1,
                "queue_length": None,  # Manual trigger
                "activation_length": None,
            },
        },
        "processor": {
            "queue": "content-processing-requests",
            "container": "processor",
            "current_config": {
                "min_replicas": 0,
                "max_replicas": 6,
                "queue_length": 8,
                "activation_length": 1,
            },
        },
        "markdown": {
            "queue": "markdown-generation-requests",
            "container": "markdown",
            "current_config": {
                "min_replicas": 0,
                "max_replicas": 1,
                "queue_length": 1,
                "activation_length": 1,
            },
        },
        "publisher": {
            "queue": "site-publishing-requests",
            "container": "publisher",
            "current_config": {
                "min_replicas": 0,
                "max_replicas": 1,
                "queue_length": 1,
                "activation_length": 1,
            },
        },
    }

    def __init__(self, resource_group: str = "ai-content-prod-rg"):
        self.resource_group = resource_group
        self.stages: Dict[str, PipelineStage] = {}

    def load_from_csv(self, csv_file: Path) -> None:
        """Load metrics from CSV export"""
        print(f"📊 Loading metrics from {csv_file}")

        with open(csv_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")

                # Process each stage
                for stage_key in ["collector", "processor", "markdown", "publisher"]:
                    queue_col = f"{stage_key.replace('collector', 'collection')}_queue"
                    replica_col = f"{stage_key}_replicas"

                    if stage_key not in self.stages:
                        config = self.STAGES[stage_key]["current_config"]
                        self.stages[stage_key] = PipelineStage(
                            name=stage_key.capitalize(),
                            queue_name=self.STAGES[stage_key]["queue"],
                            container_name=self.STAGES[stage_key]["container"],
                            current_min_replicas=config["min_replicas"],
                            current_max_replicas=config["max_replicas"],
                            current_queue_length=config.get("queue_length", 0),
                            current_activation_length=config.get(
                                "activation_length", 0
                            ),
                            metrics=[],
                        )

                    metric = ScalingMetrics(
                        timestamp=timestamp,
                        queue_depth=int(row.get(queue_col, 0)),
                        replica_count=int(row.get(replica_col, 0)),
                        target_replica_count=0,  # Calculate from queue depth
                        scaling_latency=0.0,
                    )
                    self.stages[stage_key].metrics.append(metric)

        print(f"✅ Loaded {len(next(iter(self.stages.values())).metrics)} data points")

    def analyze_stage(self, stage: PipelineStage) -> Dict:
        """Analyze a single pipeline stage and generate recommendations"""
        print(f"\n{'='*70}")
        print(f"📈 Analyzing {stage.name}")
        print(f"{'='*70}")

        # Current configuration
        print(f"\n🔧 Current Configuration:")
        print(f"   Min Replicas: {stage.current_min_replicas}")
        print(f"   Max Replicas: {stage.current_max_replicas}")
        print(f"   Queue Length Trigger: {stage.current_queue_length or 'N/A'}")
        print(f"   Activation Length: {stage.current_activation_length or 'N/A'}")

        # Observed behavior
        print(f"\n📊 Observed Behavior:")
        print(f"   Avg Queue Depth: {stage.avg_queue_depth:.1f} messages")
        print(f"   Max Queue Depth: {stage.max_queue_depth} messages")
        print(f"   Avg Replicas: {stage.avg_replicas:.2f}")
        print(f"   Scale-up Events: {stage.scale_up_events}")
        print(f"   Scale-down Events: {stage.scale_down_events}")
        print(f"   Avg Scale-up Latency: {stage.avg_scale_up_latency:.1f}s")

        # Calculate recommendations
        recommendations = self._calculate_recommendations(stage)

        print(f"\n💡 Recommendations:")
        for rec in recommendations["suggestions"]:
            print(f"   • {rec}")

        if recommendations["warnings"]:
            print(f"\n⚠️  Warnings:")
            for warn in recommendations["warnings"]:
                print(f"   • {warn}")

        return recommendations

    def _calculate_recommendations(self, stage: PipelineStage) -> Dict:
        """Calculate optimal KEDA parameters based on observed behavior"""
        suggestions = []
        warnings = []
        optimal_config = {
            "min_replicas": stage.current_min_replicas,
            "max_replicas": stage.current_max_replicas,
            "queue_length": stage.current_queue_length,
            "activation_length": stage.current_activation_length,
        }

        # Analyze queue buildup patterns
        if (
            stage.max_queue_depth > 100
            and stage.avg_replicas < stage.current_max_replicas * 0.5
        ):
            suggestions.append(
                f"Queue depth reached {stage.max_queue_depth} but avg replicas only "
                f"{stage.avg_replicas:.1f}. Consider decreasing queueLength trigger "
                f"from {stage.current_queue_length} to {max(1, stage.current_queue_length // 2)}"
            )
            optimal_config["queue_length"] = max(1, stage.current_queue_length // 2)

        # Analyze under-utilization
        if (
            stage.avg_queue_depth < stage.current_queue_length / 2
            and stage.scale_up_events > 5
        ):
            suggestions.append(
                f"Frequent scaling ({stage.scale_up_events} events) with low avg queue "
                f"({stage.avg_queue_depth:.1f}). Consider increasing queueLength from "
                f"{stage.current_queue_length} to {stage.current_queue_length * 2}"
            )
            optimal_config["queue_length"] = stage.current_queue_length * 2

        # Analyze max replica utilization
        if stage.avg_replicas > stage.current_max_replicas * 0.9:
            warnings.append(
                f"Replica count near maximum ({stage.avg_replicas:.1f} / "
                f"{stage.current_max_replicas}). Consider increasing max_replicas."
            )
            optimal_config["max_replicas"] = stage.current_max_replicas + 2

        # Analyze scale-up latency
        if stage.avg_scale_up_latency > 60:
            warnings.append(
                f"Slow scale-up latency ({stage.avg_scale_up_latency:.0f}s). "
                f"Consider pre-warming with min_replicas=1 during peak hours."
            )

        # Check for thrashing (frequent up/down)
        if stage.scale_up_events > 10 and stage.scale_down_events > 10:
            warnings.append(
                f"Frequent scaling thrashing detected ({stage.scale_up_events} up, "
                f"{stage.scale_down_events} down). Consider adjusting cooldown periods."
            )

        return {
            "suggestions": suggestions,
            "warnings": warnings,
            "optimal_config": optimal_config,
        }

    def generate_terraform_config(self, stage_name: str, config: Dict) -> str:
        """Generate Terraform configuration snippet"""
        queue_name = self.STAGES[stage_name]["queue"]

        return f"""
# Recommended KEDA scaling configuration for {stage_name}
custom_scale_rule {{
  name             = "{queue_name}-scaler"
  custom_rule_type = "azure-queue"
  metadata = {{
    queueName             = "{queue_name}"
    accountName           = azurerm_storage_account.main.name
    queueLength           = "{config['queue_length']}"
    activationQueueLength = "{config['activation_length']}"
    cloud                 = "AzurePublicCloud"
  }}
}}

template {{
  min_replicas = {config['min_replicas']}
  max_replicas = {config['max_replicas']}
}}
"""

    def generate_report(self, output_file: Optional[Path] = None) -> None:
        """Generate comprehensive analysis report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "resource_group": self.resource_group,
            "stages": {},
        }

        print("\n" + "=" * 70)
        print("🎯 KEDA SCALING ANALYSIS REPORT")
        print("=" * 70)

        for stage_name, stage in self.stages.items():
            recommendations = self.analyze_stage(stage)

            report["stages"][stage_name] = {
                "current_config": {
                    "min_replicas": stage.current_min_replicas,
                    "max_replicas": stage.current_max_replicas,
                    "queue_length": stage.current_queue_length,
                    "activation_length": stage.current_activation_length,
                },
                "metrics": {
                    "avg_queue_depth": stage.avg_queue_depth,
                    "max_queue_depth": stage.max_queue_depth,
                    "avg_replicas": stage.avg_replicas,
                    "scale_up_events": stage.scale_up_events,
                    "scale_down_events": stage.scale_down_events,
                    "avg_scale_up_latency": stage.avg_scale_up_latency,
                },
                "recommendations": recommendations,
            }

            # Show Terraform config if recommendations exist
            if recommendations["suggestions"] or recommendations["warnings"]:
                print(f"\n📝 Terraform Configuration for {stage.name}:")
                print(
                    self.generate_terraform_config(
                        stage_name, recommendations["optimal_config"]
                    )
                )

        # Save report if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2, default=str)
            print(f"\n✅ Full report saved to: {output_file}")

        # Summary
        print("\n" + "=" * 70)
        print("📊 SUMMARY")
        print("=" * 70)
        total_suggestions = sum(
            len(s["recommendations"]["suggestions"]) for s in report["stages"].values()
        )
        total_warnings = sum(
            len(s["recommendations"]["warnings"]) for s in report["stages"].values()
        )

        print(f"   Total Suggestions: {total_suggestions}")
        print(f"   Total Warnings: {total_warnings}")
        print(f"\n💡 Next Steps:")
        print(f"   1. Review recommendations above")
        print(f"   2. Update Terraform configurations as needed")
        print(f"   3. Test changes in non-production first")
        print(f"   4. Monitor for 24-48 hours after deployment")
        print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze KEDA scaling behavior and provide recommendations"
    )
    parser.add_argument(
        "--csv", type=Path, help="Path to CSV file from monitor-pipeline-performance.sh"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for JSON report (default: keda-analysis-{timestamp}.json)",
    )
    parser.add_argument(
        "--resource-group",
        default="ai-content-prod-rg",
        help="Azure resource group name",
    )

    args = parser.parse_args()

    if not args.csv:
        print("❌ Error: --csv argument required")
        print("\nUsage:")
        print(
            "  1. Run: ./monitor-pipeline-performance.sh --export metrics.csv --duration 30"
        )
        print("  2. Run: python analyze-keda-scaling.py --csv metrics.csv")
        sys.exit(1)

    if not args.csv.exists():
        print(f"❌ Error: CSV file not found: {args.csv}")
        sys.exit(1)

    # Generate default output filename
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = Path(f"keda-analysis-{timestamp}.json")

    # Run analysis
    analyzer = KEDAAnalyzer(resource_group=args.resource_group)
    analyzer.load_from_csv(args.csv)
    analyzer.generate_report(output_file=args.output)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Pipeline Flow-Through Analysis
Measures end-to-end processing times and identifies bottlenecks by tracking
individual content items through the entire pipeline.

Usage:
    python analyze-pipeline-flow.py --duration 60 --sample-size 20
"""

import argparse
import json
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np


@dataclass
class ContentItem:
    """Track a single content item through the pipeline"""

    item_id: str
    collection_start: Optional[datetime] = None
    collection_end: Optional[datetime] = None
    processing_start: Optional[datetime] = None
    processing_end: Optional[datetime] = None
    markdown_start: Optional[datetime] = None
    markdown_end: Optional[datetime] = None
    publish_start: Optional[datetime] = None
    publish_end: Optional[datetime] = None

    @property
    def collection_duration(self) -> Optional[float]:
        if self.collection_start and self.collection_end:
            return (self.collection_end - self.collection_start).total_seconds()
        return None

    @property
    def processing_duration(self) -> Optional[float]:
        if self.processing_start and self.processing_end:
            return (self.processing_end - self.processing_start).total_seconds()
        return None

    @property
    def markdown_duration(self) -> Optional[float]:
        if self.markdown_start and self.markdown_end:
            return (self.markdown_end - self.markdown_start).total_seconds()
        return None

    @property
    def publish_duration(self) -> Optional[float]:
        if self.publish_start and self.publish_end:
            return (self.publish_end - self.publish_start).total_seconds()
        return None

    @property
    def total_duration(self) -> Optional[float]:
        if self.collection_start and self.publish_end:
            return (self.publish_end - self.collection_start).total_seconds()
        return None

    @property
    def is_complete(self) -> bool:
        return all(
            [
                self.collection_end,
                self.processing_end,
                self.markdown_end,
                self.publish_end,
            ]
        )


@dataclass
class PipelineStats:
    """Overall pipeline statistics"""

    total_items: int = 0
    completed_items: int = 0
    items_in_flight: int = 0

    avg_collection_time: float = 0.0
    avg_processing_time: float = 0.0
    avg_markdown_time: float = 0.0
    avg_publish_time: float = 0.0
    avg_total_time: float = 0.0

    p50_total_time: float = 0.0
    p95_total_time: float = 0.0
    p99_total_time: float = 0.0

    throughput_items_per_hour: float = 0.0
    bottleneck_stage: str = ""

    stage_durations: Dict[str, List[float]] = field(
        default_factory=lambda: {
            "collection": [],
            "processing": [],
            "markdown": [],
            "publish": [],
        }
    )


class PipelineFlowAnalyzer:
    """Analyze pipeline flow-through and identify bottlenecks"""

    def __init__(self, resource_group: str = "ai-content-prod-rg"):
        self.resource_group = resource_group
        self.storage_account = self._get_storage_account()
        self.items: Dict[str, ContentItem] = {}
        self.stats = PipelineStats()

    def _get_storage_account(self) -> str:
        """Get storage account name from Azure"""
        try:
            result = subprocess.run(
                [
                    "az",
                    "storage",
                    "account",
                    "list",
                    "--resource-group",
                    self.resource_group,
                    "--query",
                    "[0].name",
                    "-o",
                    "tsv",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"❌ Error getting storage account: {e}")
            sys.exit(1)

    def _query_log_analytics(self, query: str, timespan: str = "PT1H") -> List[Dict]:
        """Query Azure Log Analytics for container logs"""
        try:
            # Get workspace ID
            workspace_result = subprocess.run(
                [
                    "az",
                    "monitor",
                    "log-analytics",
                    "workspace",
                    "list",
                    "--resource-group",
                    self.resource_group,
                    "--query",
                    "[0].customerId",
                    "-o",
                    "tsv",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            workspace_id = workspace_result.stdout.strip()

            # Run query
            result = subprocess.run(
                [
                    "az",
                    "monitor",
                    "log-analytics",
                    "query",
                    "-w",
                    workspace_id,
                    "--analytics-query",
                    query,
                    "--timespan",
                    timespan,
                    "-o",
                    "json",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            data = json.loads(result.stdout)
            return data.get("tables", [{}])[0].get("rows", [])

        except subprocess.CalledProcessError as e:
            print(f"⚠️  Warning: Could not query logs: {e}")
            return []

    def _track_blob_operations(self, duration_minutes: int = 60) -> None:
        """Track blob operations to infer pipeline flow"""
        print(f"📊 Tracking blob operations for {duration_minutes} minutes...")

        # Query for blob operations from storage logs
        query = f"""
        StorageBlobLogs
        | where TimeGenerated > ago({duration_minutes}m)
        | where OperationName in ('PutBlob', 'GetBlob')
        | where Uri contains 'collected-content' or Uri contains 'processed-content'
               or Uri contains 'markdown-content' or Uri contains 'published-content'
        | project TimeGenerated, OperationName, Uri, StatusCode
        | order by TimeGenerated asc
        """

        rows = self._query_log_analytics(query, f"PT{duration_minutes}M")

        print(f"   Found {len(rows)} blob operations")

        # Parse blob operations to track content flow
        for row in rows:
            self._parse_blob_operation(row)

    def _parse_blob_operation(self, row: List) -> None:
        """Parse a blob operation log entry"""
        # Log Analytics returns rows as arrays
        if len(row) < 4:
            return

        timestamp = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
        operation = row[1]
        uri = row[2]
        status = row[3]

        # Skip failed operations
        if status not in ["200", "201"]:
            return

        # Extract item ID from URI
        # Example: .../collected-content/reddit-tech-20250814-123456.json
        parts = uri.split("/")
        if len(parts) < 2:
            return

        filename = parts[-1]
        item_id = filename.replace(".json", "")

        # Determine stage from container name
        if "collected-content" in uri:
            if item_id not in self.items:
                self.items[item_id] = ContentItem(item_id=item_id)
            if operation == "PutBlob":
                self.items[item_id].collection_end = timestamp
        elif "processed-content" in uri:
            if item_id not in self.items:
                self.items[item_id] = ContentItem(item_id=item_id)
            if operation == "GetBlob":
                self.items[item_id].processing_start = timestamp
            elif operation == "PutBlob":
                self.items[item_id].processing_end = timestamp
        elif "markdown-content" in uri:
            if item_id not in self.items:
                self.items[item_id] = ContentItem(item_id=item_id)
            if operation == "GetBlob":
                self.items[item_id].markdown_start = timestamp
            elif operation == "PutBlob":
                self.items[item_id].markdown_end = timestamp
        elif "published-content" in uri:
            if item_id not in self.items:
                self.items[item_id] = ContentItem(item_id=item_id)
            if operation == "PutBlob":
                self.items[item_id].publish_end = timestamp

    def _calculate_stats(self) -> None:
        """Calculate pipeline statistics"""
        completed = [item for item in self.items.values() if item.is_complete]

        self.stats.total_items = len(self.items)
        self.stats.completed_items = len(completed)
        self.stats.items_in_flight = self.stats.total_items - self.stats.completed_items

        if not completed:
            print("⚠️  No completed items found in monitoring period")
            return

        # Collect durations
        for item in completed:
            if item.collection_duration:
                self.stats.stage_durations["collection"].append(
                    item.collection_duration
                )
            if item.processing_duration:
                self.stats.stage_durations["processing"].append(
                    item.processing_duration
                )
            if item.markdown_duration:
                self.stats.stage_durations["markdown"].append(item.markdown_duration)
            if item.publish_duration:
                self.stats.stage_durations["publish"].append(item.publish_duration)

        # Calculate averages
        self.stats.avg_collection_time = (
            np.mean(self.stats.stage_durations["collection"])
            if self.stats.stage_durations["collection"]
            else 0.0
        )
        self.stats.avg_processing_time = (
            np.mean(self.stats.stage_durations["processing"])
            if self.stats.stage_durations["processing"]
            else 0.0
        )
        self.stats.avg_markdown_time = (
            np.mean(self.stats.stage_durations["markdown"])
            if self.stats.stage_durations["markdown"]
            else 0.0
        )
        self.stats.avg_publish_time = (
            np.mean(self.stats.stage_durations["publish"])
            if self.stats.stage_durations["publish"]
            else 0.0
        )

        # Calculate total times
        total_times = [item.total_duration for item in completed if item.total_duration]
        if total_times:
            self.stats.avg_total_time = np.mean(total_times)
            self.stats.p50_total_time = np.percentile(total_times, 50)
            self.stats.p95_total_time = np.percentile(total_times, 95)
            self.stats.p99_total_time = np.percentile(total_times, 99)

        # Calculate throughput (items per hour)
        if total_times:
            min_start = min(
                item.collection_start for item in completed if item.collection_start
            )
            max_end = max(item.publish_end for item in completed if item.publish_end)
            duration_hours = (max_end - min_start).total_seconds() / 3600
            self.stats.throughput_items_per_hour = len(completed) / duration_hours

        # Identify bottleneck
        stage_times = {
            "collection": self.stats.avg_collection_time,
            "processing": self.stats.avg_processing_time,
            "markdown": self.stats.avg_markdown_time,
            "publish": self.stats.avg_publish_time,
        }
        self.stats.bottleneck_stage = max(stage_times, key=stage_times.get)

    def _print_report(self) -> None:
        """Print analysis report"""
        print("\n" + "=" * 70)
        print("🔄 PIPELINE FLOW-THROUGH ANALYSIS")
        print("=" * 70)

        print(f"\n📊 Overall Metrics:")
        print(f"   Total Items Tracked: {self.stats.total_items}")
        print(f"   Completed Items: {self.stats.completed_items}")
        print(f"   Items In-Flight: {self.stats.items_in_flight}")
        print(f"   Throughput: {self.stats.throughput_items_per_hour:.1f} items/hour")

        print(f"\n⏱️  Stage Durations (Average):")
        print(f"   Collection:  {self.stats.avg_collection_time:6.1f}s")
        print(
            f"   Processing:  {self.stats.avg_processing_time:6.1f}s  {'🔴 BOTTLENECK' if self.stats.bottleneck_stage == 'processing' else ''}"
        )
        print(
            f"   Markdown:    {self.stats.avg_markdown_time:6.1f}s  {'🔴 BOTTLENECK' if self.stats.bottleneck_stage == 'markdown' else ''}"
        )
        print(
            f"   Publishing:  {self.stats.avg_publish_time:6.1f}s  {'🔴 BOTTLENECK' if self.stats.bottleneck_stage == 'publish' else ''}"
        )

        print(f"\n📈 End-to-End Times:")
        print(
            f"   Average: {self.stats.avg_total_time:.1f}s ({self.stats.avg_total_time/60:.1f} min)"
        )
        print(
            f"   P50:     {self.stats.p50_total_time:.1f}s ({self.stats.p50_total_time/60:.1f} min)"
        )
        print(
            f"   P95:     {self.stats.p95_total_time:.1f}s ({self.stats.p95_total_time/60:.1f} min)"
        )
        print(
            f"   P99:     {self.stats.p99_total_time:.1f}s ({self.stats.p99_total_time/60:.1f} min)"
        )

        print(f"\n💡 Recommendations:")

        # Bottleneck recommendations
        if self.stats.bottleneck_stage == "processing":
            print(
                f"   • Processing is the bottleneck ({self.stats.avg_processing_time:.1f}s avg)"
            )
            print(f"   • Consider increasing max_replicas for content-processor")
            print(f"   • Current config allows up to 6 replicas - may need more")
            print(f"   • Check if hitting OpenAI rate limits")
        elif self.stats.bottleneck_stage == "markdown":
            print(
                f"   • Markdown generation is the bottleneck ({self.stats.avg_markdown_time:.1f}s avg)"
            )
            print(f"   • Currently limited to 1 replica (by design)")
            print(f"   • Optimize markdown template complexity if possible")
        elif self.stats.bottleneck_stage == "publish":
            print(
                f"   • Publishing is the bottleneck ({self.stats.avg_publish_time:.1f}s avg)"
            )
            print(f"   • Currently limited to 1 replica (Hugo requirement)")
            print(f"   • Consider incremental builds instead of full rebuilds")

        # Throughput recommendations
        if self.stats.throughput_items_per_hour < 10:
            print(
                f"   • Low throughput ({self.stats.throughput_items_per_hour:.1f} items/hour)"
            )
            print(f"   • Review KEDA queueLength settings to scale faster")
        elif self.stats.throughput_items_per_hour > 100:
            print(
                f"   • High throughput ({self.stats.throughput_items_per_hour:.1f} items/hour)"
            )
            print(f"   • Consider increasing queueLength to reduce scaling frequency")

        print("=" * 70 + "\n")

    def analyze(self, duration_minutes: int = 60) -> None:
        """Run full pipeline flow analysis"""
        print(f"🚀 Starting pipeline flow analysis...")
        print(f"   Resource Group: {self.resource_group}")
        print(f"   Storage Account: {self.storage_account}")
        print(f"   Duration: {duration_minutes} minutes\n")

        # Track operations
        self._track_blob_operations(duration_minutes)

        # Calculate statistics
        self._calculate_stats()

        # Print report
        self._print_report()


def main():
    parser = argparse.ArgumentParser(
        description="Analyze pipeline flow-through and identify bottlenecks"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Analysis duration in minutes (default: 60)",
    )
    parser.add_argument(
        "--resource-group",
        default="ai-content-prod-rg",
        help="Azure resource group name",
    )

    args = parser.parse_args()

    # Check for required dependencies
    try:
        import numpy
    except ImportError:
        print("❌ Error: numpy not installed")
        print("   Run: pip install numpy")
        sys.exit(1)

    # Run analysis
    analyzer = PipelineFlowAnalyzer(resource_group=args.resource_group)
    analyzer.analyze(duration_minutes=args.duration)


if __name__ == "__main__":
    main()

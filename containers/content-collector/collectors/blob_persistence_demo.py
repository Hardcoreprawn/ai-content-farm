"""
Blob Storage Persistence Example - LEGACY

DEPRECATED: Demo script for adaptive strategy persistence
Status: PENDING REMOVAL - Not needed with simplified architecture

Demonstrated how complex adaptive strategies persisted metrics to blob storage.
Simplified collectors don't need this complexity.

Demonstrates how the adaptive collection system uses Azure Blob Storage
for persistent metrics and strategy data across container restarts.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from .blob_metrics_storage import BlobMetricsStorage, get_metrics_storage
from .source_strategies import RedditCollectionStrategy

logger = logging.getLogger(__name__)


async def demo_blob_persistence():
    """Demonstrate blob storage persistence for collection metrics."""

    print("🔵 Azure Blob Storage Persistence Demo")
    print("=" * 50)

    # Initialize blob storage
    storage = get_metrics_storage()

    # Check storage health
    health = storage.health_check()
    print(f"📊 Storage Health: {health['status']}")
    if health["status"] != "healthy":
        print(f"❌ Storage not healthy: {health}")
        return

    # Create a test strategy
    reddit_strategy = RedditCollectionStrategy("demo_reddit_source")

    print(f"\n📈 Testing Strategy: {reddit_strategy.strategy_key}")

    # Simulate some collection activity
    print("\n🔄 Simulating collection activity...")

    # Simulate successful requests
    for i in range(5):
        await reddit_strategy.before_request()
        await reddit_strategy.after_request(
            success=True,
            response_time=1.5 + (i * 0.3),
            status_code=200,
            headers={"x-ratelimit-limit": "60", "x-ratelimit-remaining": str(55 - i)},
        )
        print(
            f"  ✅ Request {i+1}: Success (delay: {reddit_strategy.current_delay:.1f}s)"
        )

    # Simulate a rate limit hit
    await reddit_strategy.after_request(
        success=False, response_time=2.0, status_code=429, headers={"retry-after": "60"}
    )
    print(
        f"  ⚠️  Rate limit hit (delay increased to: {reddit_strategy.current_delay:.1f}s)"
    )

    # Get current metrics
    current_metrics = reddit_strategy.get_metrics_summary()
    print(f"\n📊 Current Metrics:")
    print(f"  Success Rate: {current_metrics['success_rate']:.1%}")
    print(f"  Adaptive Delay: {current_metrics['adaptive_delay']:.1f}s")
    print(f"  Health: {current_metrics['health']}")
    print(f"  Requests Made: {current_metrics['requests_made']}")

    # Save metrics to blob storage
    print(f"\n💾 Saving metrics to blob storage...")

    # Show what gets saved
    print(f"\n📝 What gets saved to blob storage:")
    print(f"  Container: collection-metrics")
    print(f"  Strategy Key: {reddit_strategy.strategy_key}")
    print(f"  Blob Path: strategies/{reddit_strategy.strategy_key}/latest.json")
    print(
        f"  Historical Path: strategies/{reddit_strategy.strategy_key}/metrics/YYYY/MM/DD/HHMMSS.json"
    )

    # Create a new strategy instance to test loading
    print(f"\n🔄 Creating new strategy instance (simulating container restart)...")
    new_strategy = RedditCollectionStrategy("demo_reddit_source")

    # Load historical metrics
    await new_strategy._load_historical_metrics()

    new_metrics = new_strategy.get_metrics_summary()
    print(f"📈 Restored Metrics:")
    print(f"  Adaptive Delay: {new_metrics['adaptive_delay']:.1f}s")
    print(
        f"  (Should match previous delay of {current_metrics['adaptive_delay']:.1f}s)"
    )

    # Show storage usage
    print(f"\n💿 Storage Usage:")
    usage = await storage.get_storage_usage()
    print(f"  Total Blobs: {usage['total_blobs']}")
    print(f"  Total Size: {usage['total_size_mb']} MB")
    print(f"  Strategy Blobs: {usage['strategy_blobs']}")
    print(f"  Global Blobs: {usage['global_blobs']}")
    print(f"  Report Blobs: {usage['report_blobs']}")

    # Save a performance report
    print(f"\n📋 Saving performance report...")
    report_data = {
        "demo_timestamp": datetime.now().isoformat(),
        "strategies_tested": 1,
        "total_requests": current_metrics["requests_made"],
        "demonstration": "blob_persistence",
    }

    blob_name = await storage.save_performance_report(report_data, "demo")
    print(f"  Report saved to: {blob_name}")

    # Show historical data capability
    print(f"\n📚 Historical Data Capability:")
    history = await storage.get_strategy_history(reddit_strategy.strategy_key, days=1)
    print(f"  Historical entries found: {len(history)}")
    if history:
        latest = history[0]
        print(f"  Latest entry timestamp: {latest.get('timestamp', 'unknown')}")

    print(f"\n✅ Demo Complete!")
    print(f"\nKey Benefits:")
    print(f"  🔄 Metrics survive container restarts")
    print(f"  📈 Strategies learn and improve over time")
    print(f"  🗄️  Centralized storage in Azure Blob Storage")
    print(f"  📊 Historical analysis and reporting")
    print(f"  🧹 Automatic cleanup of old data")


async def demo_multi_source_persistence():
    """Demonstrate persistence across multiple source types."""

    print("\n🌐 Multi-Source Persistence Demo")
    print("=" * 40)

    from .source_strategies import RSSCollectionStrategy, WebCollectionStrategy

    storage = get_metrics_storage()

    # Create different strategy types
    strategies = [
        RedditCollectionStrategy("reddit_tech"),
        RSSCollectionStrategy("rss_feeds"),
        WebCollectionStrategy("web_scraper"),
    ]

    print(f"📋 Testing {len(strategies)} different strategy types:")

    for strategy in strategies:
        print(f"\n  🔧 {strategy.__class__.__name__} ({strategy.strategy_key})")

        # Simulate activity
        await strategy.before_request()
        await strategy.after_request(
            success=True, response_time=strategy.current_delay, status_code=200
        )

        # Save metrics
        await strategy._save_metrics()

        # Show adaptive parameters
        params = await strategy.get_collection_parameters()
        print(f"    Delay: {params.get('request_delay', 'N/A'):.1f}s")
        print(f"    Timeout: {params.get('timeout', 'N/A')}s")
        print(f"    Health: {strategy.get_health_status().value}")

    # Show storage organization
    print(f"\n🗂️  Storage Organization:")
    usage = await storage.get_storage_usage()
    print(f"  Each strategy type maintains separate metrics")
    print(f"  Total strategies stored: {usage['strategy_blobs']}")
    print(f"  Independent adaptation and learning")

    print(f"\n✅ Multi-source demo complete!")


if __name__ == "__main__":
    # Run demos
    async def run_demos():
        await demo_blob_persistence()
        await demo_multi_source_persistence()

    asyncio.run(run_demos())

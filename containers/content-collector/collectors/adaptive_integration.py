"""
Adaptive Collection System Integration

Example integration showing how to use the adaptive collection strategies
with existing collectors to create a respectful, self-adjusting system.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import SourceCollector
from .collection_monitor import get_monitor, monitor_collection
from .reddit import RedditCollector

logger = logging.getLogger(__name__)


class AdaptiveCollectorWrapper:
    """Wrapper that adds adaptive strategy support to existing collectors."""

    def __init__(self, storage_client):
        self.storage_client = storage_client
        self.monitor = get_monitor()

        # Original collectors
        self.reddit_collector = RedditCollector(storage_client)

        # Track collection sessions
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    async def collect_from_template(self, template_path: str) -> Dict[str, Any]:
        """Collect content using an adaptive template."""
        # Load template
        with open(template_path, "r") as f:
            template = json.load(f)

        if not template.get("metadata", {}).get("strategy_enabled", False):
            logger.warning(
                f"Template {template_path} does not have adaptive strategies enabled"
            )
            return await self._collect_legacy_template(template)

        logger.info(
            f"Starting adaptive collection from template: {template['metadata']['name']}"
        )

        results = {
            "template": template["metadata"]["name"],
            "started_at": datetime.now().isoformat(),
            "sources": {},
            "summary": {},
            "strategy_reports": {},
        }

        # Process each source with its adaptive strategy
        for source_config in template["sources"]:
            source_type = source_config["type"]
            source_name = f"{source_type}_{hash(str(source_config)) % 1000}"

            try:
                source_result = await self._collect_adaptive_source(
                    source_config, source_name
                )
                results["sources"][source_name] = source_result

                # Get strategy report
                strategy_summary = self.monitor.get_strategy_summary(
                    f"{source_type}:{source_name}"
                )
                if strategy_summary:
                    results["strategy_reports"][source_name] = strategy_summary

            except Exception as e:
                logger.error(f"Failed to collect from {source_name}: {e}")
                results["sources"][source_name] = {
                    "success": False,
                    "error": str(e),
                    "items": [],
                }

        # Generate summary
        results["summary"] = await self._generate_collection_summary(results)
        results["completed_at"] = datetime.now().isoformat()

        # Save performance report if requested
        if template.get("monitoring", {}).get("track_performance", False):
            blob_name = await self.monitor.save_performance_report(
                "template_collection"
            )
            results["performance_report"] = blob_name

        return results

    async def _collect_adaptive_source(
        self, source_config: Dict[str, Any], source_name: str
    ) -> Dict[str, Any]:
        """Collect from a single source using adaptive strategy."""
        source_type = source_config["type"]
        strategy_config = source_config.get("strategy", {})

        # Register source with monitor
        await self.monitor.register_source(source_type, source_name, strategy_config)

        if source_type == "reddit":
            return await self._collect_reddit_adaptive(source_config, source_name)
        elif source_type == "rss":
            return await self._collect_rss_adaptive(source_config, source_name)
        elif source_type == "web":
            return await self._collect_web_adaptive(source_config, source_name)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

    async def _collect_reddit_adaptive(
        self, source_config: Dict[str, Any], source_name: str
    ) -> Dict[str, Any]:
        """Collect Reddit content with adaptive strategy."""

        async def reddit_collection_func(
            collection_params: Dict[str, Any],
        ) -> Dict[str, Any]:
            """Wrapper function for Reddit collection."""
            # Merge template config with adaptive parameters
            collection_request = {
                "name": source_name,
                "source": "reddit",
                "config": {
                    **source_config,
                    "request_delay": collection_params.get("request_delay", 2.0),
                    "timeout": collection_params.get("timeout", 30),
                    "retry_attempts": collection_params.get("retry_attempts", 2),
                },
            }

            # Use existing Reddit collector with adaptive parameters
            result = await self.reddit_collector.collect(collection_request)

            return {
                "items": result if isinstance(result, list) else [],
                "status_code": 200,
                "success": True,
            }

        # Monitor the collection
        result, response_metrics = await monitor_collection(
            "reddit", source_name, reddit_collection_func
        )

        return {
            "success": response_metrics["success"],
            "items": result.get("items", []) if result else [],
            "response_time": response_metrics["response_time"],
            "strategy_applied": True,
            "metrics": response_metrics,
        }

    async def _collect_rss_adaptive(
        self, source_config: Dict[str, Any], source_name: str
    ) -> Dict[str, Any]:
        """Collect RSS content with adaptive strategy."""

        async def rss_collection_func(
            collection_params: Dict[str, Any],
        ) -> Dict[str, Any]:
            """Wrapper function for RSS collection."""
            # This would integrate with an RSS collector
            # For now, return mock data
            await asyncio.sleep(collection_params.get("request_delay", 0.5))

            return {
                "items": [
                    {"title": f"RSS Item {i}", "url": f"http://example.com/{i}"}
                    for i in range(source_config.get("limit", 5))
                ],
                "status_code": 200,
                "success": True,
            }

        result, response_metrics = await monitor_collection(
            "rss", source_name, rss_collection_func
        )

        return {
            "success": response_metrics["success"],
            "items": result.get("items", []) if result else [],
            "response_time": response_metrics["response_time"],
            "strategy_applied": True,
            "metrics": response_metrics,
        }

    async def _collect_web_adaptive(
        self, source_config: Dict[str, Any], source_name: str
    ) -> Dict[str, Any]:
        """Collect web content with adaptive strategy."""

        async def web_collection_func(
            collection_params: Dict[str, Any],
        ) -> Dict[str, Any]:
            """Wrapper function for web collection."""
            # This would integrate with a web scraper
            # For now, return mock data
            await asyncio.sleep(collection_params.get("request_delay", 3.0))

            return {
                "items": [
                    {
                        "title": f"Web Article {i}",
                        "url": f"http://example.com/article/{i}",
                    }
                    for i in range(source_config.get("limit", 3))
                ],
                "status_code": 200,
                "success": True,
            }

        result, response_metrics = await monitor_collection(
            "web", source_name, web_collection_func
        )

        return {
            "success": response_metrics["success"],
            "items": result.get("items", []) if result else [],
            "response_time": response_metrics["response_time"],
            "strategy_applied": True,
            "metrics": response_metrics,
        }

    async def _collect_legacy_template(
        self, template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback for templates without adaptive strategies."""
        logger.info("Using legacy collection method")

        # Convert to legacy format and use existing collectors
        results = {
            "template": template.get("metadata", {}).get("name", "legacy"),
            "started_at": datetime.now().isoformat(),
            "sources": {},
            "strategy_applied": False,
        }

        for i, source_config in enumerate(template["sources"]):
            if source_config["type"] == "reddit":
                collection_request = {
                    "name": f"legacy_reddit_{i}",
                    "source": "reddit",
                    "config": source_config,
                }

                try:
                    result = await self.reddit_collector.collect(collection_request)
                    results["sources"][f"reddit_{i}"] = {
                        "success": True,
                        "items": result if isinstance(result, list) else [],
                        "strategy_applied": False,
                    }
                except Exception as e:
                    results["sources"][f"reddit_{i}"] = {
                        "success": False,
                        "error": str(e),
                        "items": [],
                    }

        results["completed_at"] = datetime.now().isoformat()
        return results

    async def _generate_collection_summary(
        self, results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate summary of collection results."""
        total_items = 0
        successful_sources = 0
        total_sources = len(results["sources"])
        total_response_time = 0.0

        for source_name, source_result in results["sources"].items():
            if source_result.get("success", False):
                successful_sources += 1
                total_items += len(source_result.get("items", []))

            if "response_time" in source_result:
                total_response_time += source_result["response_time"]

        # Get global monitor summary
        global_summary = self.monitor.get_global_summary()

        return {
            "total_items_collected": total_items,
            "successful_sources": successful_sources,
            "total_sources": total_sources,
            "success_rate": (
                successful_sources / total_sources if total_sources > 0 else 0
            ),
            "avg_response_time": (
                total_response_time / total_sources if total_sources > 0 else 0
            ),
            "global_health_percentage": global_summary.get("health_percentage", 0),
            "adaptive_strategies_used": any(
                result.get("strategy_applied", False)
                for result in results["sources"].values()
            ),
        }

    async def get_system_health_report(self) -> Dict[str, Any]:
        """Get comprehensive system health report."""
        global_summary = self.monitor.get_global_summary()

        # Get recommendations for all active strategies
        recommendations = {}
        for strategy_key in self.monitor.active_strategies.keys():
            recommendations[strategy_key] = (
                await self.monitor.get_source_recommendations(strategy_key)
            )

        return {
            "timestamp": datetime.now().isoformat(),
            "global_metrics": global_summary,
            "active_strategies": len(self.monitor.active_strategies),
            "recommendations": recommendations,
            "system_status": (
                "healthy"
                if global_summary.get("health_percentage", 0) > 80
                else "degraded"
            ),
        }


# Example usage function
async def example_adaptive_collection():
    """Example of how to use the adaptive collection system."""

    # For this example, we'll mock the storage client since the path may vary
    class MockStorageClient:
        pass

    # Initialize storage and collector
    storage_client = MockStorageClient()
    adaptive_collector = AdaptiveCollectorWrapper(storage_client)

    # Run adaptive collection from template
    template_path = (
        "/workspaces/ai-content-farm/collection-templates/sustainable-reddit.json"
    )

    try:
        results = await adaptive_collector.collect_from_template(template_path)

        print("Collection Results:")
        print(f"Template: {results['template']}")
        print(f"Total items: {results['summary']['total_items_collected']}")
        print(f"Success rate: {results['summary']['success_rate']:.1%}")
        print(
            f"Adaptive strategies used: {results['summary']['adaptive_strategies_used']}"
        )

        # Print strategy reports
        print("\nStrategy Performance:")
        for source_name, strategy_report in results.get("strategy_reports", {}).items():
            print(
                f"  {source_name}: {strategy_report['health']} "
                f"({strategy_report['success_rate']:.1%} success, "
                f"{strategy_report['adaptive_delay']:.1f}s delay)"
            )

        # Get system health
        health_report = await adaptive_collector.get_system_health_report()
        print(f"\nSystem Health: {health_report['system_status']}")
        print(
            f"Overall Health: {health_report['global_metrics']['health_percentage']:.1f}%"
        )

        return results

    except Exception as e:
        logger.error(f"Adaptive collection failed: {e}")
        raise


if __name__ == "__main__":
    # Run example
    asyncio.run(example_adaptive_collection())

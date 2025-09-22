"""
Simplified Collector Factory - ACTIVE

CURRENT ARCHITECTURE: Simple factory for creating and managing content collectors
Status: ACTIVE - Core component of the simplified collector system

Provides easy creation and management of simplified content collectors.
Replaces complex source collector patterns with a clean factory interface.

Features:
- Registry-based collector creation
- Support for Reddit and Mastodon collectors
- Configuration-driven collector setup
- Multi-source collection utilities
- Easy extensibility for new collector types

Easy creation and management of content collectors.
"""

import logging
from typing import Any, Dict, List, Optional, Type

from collectors.simple_base import SimpleCollector
from collectors.simple_mastodon import SimpleMastodonCollector
from collectors.simple_reddit import SimpleRedditCollector

logger = logging.getLogger(__name__)


class CollectorFactory:
    """Factory for creating and managing content collectors."""

    # Registry of available collector classes
    COLLECTORS: Dict[str, Type[SimpleCollector]] = {
        "reddit": SimpleRedditCollector,
        "mastodon": SimpleMastodonCollector,
    }

    @classmethod
    def create_collector(
        self, source_type: str, config: Optional[Dict[str, Any]] = None
    ) -> SimpleCollector:
        """Create a collector for the specified source type."""

        if source_type not in self.COLLECTORS:
            available = ", ".join(self.COLLECTORS.keys())
            raise ValueError(
                f"Unknown collector type '{source_type}'. Available: {available}"
            )

        collector_class = self.COLLECTORS[source_type]
        return collector_class(config)

    @classmethod
    def create_collectors_from_config(
        self, config: Dict[str, Any]
    ) -> List[SimpleCollector]:
        """Create multiple collectors from configuration."""

        collectors = []

        for source_config in config.get("sources", []):
            source_type = source_config.get("type")
            if not source_type:
                logger.warning("Source configuration missing 'type' field, skipping")
                continue

            try:
                collector = self.create_collector(source_type, source_config)
                collectors.append(collector)
                logger.info(f"Created {source_type} collector")
            except Exception as e:
                logger.error(f"Failed to create {source_type} collector: {e}")
                continue

        return collectors

    @classmethod
    def get_available_sources(self) -> List[str]:
        """Get list of available collector source types."""
        return list(self.COLLECTORS.keys())

    @classmethod
    def register_collector(
        self, source_type: str, collector_class: Type[SimpleCollector]
    ):
        """Register a new collector type."""
        self.COLLECTORS[source_type] = collector_class
        logger.info(f"Registered collector for '{source_type}'")


# Convenience function for simple usage
def create_collector(
    source_type: str, config: Optional[Dict[str, Any]] = None
) -> SimpleCollector:
    """Create a collector - convenience function."""
    return CollectorFactory.create_collector(source_type, config)


# Function to collect from multiple sources
async def collect_from_sources(
    sources: List[str], config: Optional[Dict[str, Any]] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Collect content from multiple sources.

    Args:
        sources: List of source types to collect from
        config: Configuration dict with source-specific settings

    Returns:
        Dict mapping source names to lists of collected items
    """
    results = {}
    config = config or {}

    for source_type in sources:
        try:
            # Get source-specific config
            source_config = config.get(source_type, {})

            # Create and use collector
            collector = create_collector(source_type, source_config)

            async with collector:  # Use context manager for HTTP collectors
                items = await collector.collect_with_retry()
                results[source_type] = items
                logger.info(f"Collected {len(items)} items from {source_type}")

        except Exception as e:
            logger.error(f"Failed to collect from {source_type}: {e}")
            results[source_type] = []

    return results

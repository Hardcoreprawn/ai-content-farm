"""
Source Collector Factory

Factory for creating appropriate source collectors.
"""

from typing import Any, Dict, List, Optional

from collectors.base import SourceCollector
from collectors.reddit import RedditPRAWCollector, RedditPublicCollector
from collectors.web import WebContentCollector


class SourceCollectorFactory:
    """Factory for creating appropriate source collectors."""

    @staticmethod
    def create_collector(
        source_type: str, config: Optional[Dict[str, Any]] = None
    ) -> SourceCollector:
        """Create a collector for the specified source type."""

        if source_type == "reddit":
            # Determine which Reddit collector to use based on configuration
            if config and config.get("client_id") and config.get("client_secret"):
                return RedditPRAWCollector(config)
            else:
                return RedditPublicCollector(config)
        elif source_type == "web":
            return WebContentCollector(config)
        else:
            raise ValueError(f"Unknown source type: {source_type}")

    @staticmethod
    def get_available_sources() -> List[str]:
        """Get list of available source types."""
        return ["reddit", "web"]

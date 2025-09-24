"""
Simplified Web Collector - ACTIVE (Refactored)

CURRENT ARCHITECTURE: Simple, reliable web content collection
Status: ACTIVE - Provides web scraping for specific sites

Handles structured content extraction from specific websites like Hacker News,
Lobsters, and Slashdot using their public APIs or RSS feeds where available.
Designed for reliability and easy testing without complex adaptive strategies.

Features:
- Site-specific extraction logic for popular tech sites
- Public API usage where available (Hacker News)
- RSS fallback for sites that provide feeds
- Simple retry logic with exponential backoff
- Standardized format across all sites
- Proper error handling and rate limiting

Refactored into modular components for better maintainability:
- web_strategies.py: Collection strategies for API and RSS
- web_standardizers.py: Site-specific content standardizers
- web_utilities.py: Utility functions for content processing
"""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from collectors.simple_base import CollectorError, HTTPCollector
from collectors.web_strategies import APICollectionStrategy, RSSCollectionStrategy
from collectors.web_utilities import deduplicate_items, meets_content_criteria

logger = logging.getLogger(__name__)


class SimpleWebCollector(HTTPCollector):
    """Simplified web collector for specific tech sites."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}

        # Web-specific defaults
        config.setdefault("base_delay", 1.5)  # Be respectful to websites
        config.setdefault("max_delay", 300.0)  # 5 minutes max
        config.setdefault("backoff_multiplier", 2.0)
        config.setdefault("max_items", 20)

        super().__init__(config)

        # Web configuration
        self.max_items = config.get("max_items", 20)
        self.min_points = config.get("min_points", 10)
        self.websites = config.get("websites", ["news.ycombinator.com"])

        # Initialize collection strategies
        self.api_strategy = APICollectionStrategy(self)
        self.rss_strategy = RSSCollectionStrategy(self)

        # Site-specific configuration
        self.site_config = {
            "news.ycombinator.com": {
                "name": "Hacker News",
                "method": "api",
                "min_score": self.min_points,
            },
            "lobste.rs": {
                "name": "Lobsters",
                "method": "rss",
                "rss_url": "https://lobste.rs/rss",
                "min_score": self.min_points,
            },
            "slashdot.org": {
                "name": "Slashdot",
                "method": "rss",
                "rss_url": "http://rss.slashdot.org/Slashdot/slashdot",
                "min_score": 0,  # Slashdot doesn't have points system
            },
        }

        logger.info(f"Configured web collector for {len(self.websites)} websites")

    def get_source_name(self) -> str:
        return "web"

    async def collect_batch(self, **kwargs) -> List[Dict[str, Any]]:
        """Collect a batch of articles from configured websites."""
        # Override config with any provided parameters
        websites = kwargs.get("websites", self.websites)
        max_items = kwargs.get("max_items", self.max_items)
        min_points = kwargs.get("min_points", self.min_points)

        all_items = []
        items_per_site = max(1, max_items // len(websites)) if websites else max_items

        for website_url in websites:
            try:
                logger.info(f"Collecting from website: {website_url}")

                # Determine collection method and collect items
                if "news.ycombinator.com" in website_url:
                    items = await self.api_strategy.collect_hackernews(
                        max_items=items_per_site
                    )
                else:
                    # Use RSS strategy for other sites
                    rss_urls = self._get_rss_urls_for_website(website_url)
                    items = await self.rss_strategy.collect_from_rss(
                        rss_urls, max_items_per_feed=items_per_site
                    )

                # Filter items based on criteria
                filtered_items = [
                    item
                    for item in items
                    if meets_content_criteria(item, min_score=min_points)
                ]

                all_items.extend(filtered_items)
                logger.info(
                    f"Collected {len(filtered_items)}/{len(items)} items from {website_url}"
                )

            except CollectorError as e:
                logger.error(f"Collection error for {website_url}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error for {website_url}: {e}")
                continue

        # Deduplicate and limit results
        deduplicated = deduplicate_items(all_items)
        final_items = deduplicated[:max_items]

        logger.info(f"Final collection: {len(final_items)} unique items")
        return final_items

    def _get_rss_urls_for_website(self, website_url: str) -> List[str]:
        """Get RSS URLs for a given website."""
        domain = urlparse(website_url).netloc
        site_config = self.site_config.get(domain, {})

        if "rss_url" in site_config:
            return [site_config["rss_url"]]

        # Default RSS URLs for common sites
        default_rss = {
            "lobste.rs": ["https://lobste.rs/rss"],
            "slashdot.org": ["http://rss.slashdot.org/Slashdot/slashdot"],
        }

        return default_rss.get(domain, [])

    async def health_check(self) -> tuple[bool, str]:
        """Check if the web collector can access configured websites."""
        try:
            # Test a simple HackerNews API call
            test_url = "https://hacker-news.firebaseio.com/v0/maxitem.json"
            response = await self._make_request(test_url)

            if response and "data" in response:
                return True, "Web collector healthy - API accessible"
            else:
                return False, "Web collector unhealthy - API not accessible"

        except Exception as e:
            return False, f"Web collector health check failed: {str(e)}"

"""
Web Content Collector

Collector for web content using RSS feeds and web scraping.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import feedparser
import httpx
from collectors.base import InternetConnectivityMixin, SourceCollector

logger = logging.getLogger(__name__)


class WebCollectionStrategy:
    """Web-specific adaptive collection strategy."""

    def __init__(self, source_name: str = "web", **kwargs):
        from .adaptive_strategy import AdaptiveCollectionStrategy, StrategyParameters

        # Web-specific parameters
        web_params = StrategyParameters(
            base_delay=1.0,  # More aggressive for web content
            min_delay=0.5,
            max_delay=300.0,
            backoff_multiplier=1.8,
            success_reduction_factor=0.8,
            rate_limit_buffer=0.1,  # Lower buffer for RSS feeds
            max_requests_per_window=60,  # Higher limit for web content
            window_duration=60,
            health_check_interval=600,  # Less frequent checks
            adaptation_sensitivity=0.1,
        )

        class WebAdaptiveStrategy(AdaptiveCollectionStrategy):
            def get_collection_parameters(self):
                return {
                    "max_items": 100,
                    "max_pages": 5,
                    "include_content": True,
                    "follow_redirects": True,
                }

        self._strategy = WebAdaptiveStrategy(source_name, web_params, **kwargs)

    def __getattr__(self, name):
        """Delegate all other attributes to the underlying strategy."""
        return getattr(self._strategy, name)


class WebContentCollector(SourceCollector, InternetConnectivityMixin):
    """Base collector for web content using RSS feeds and web scraping."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.site_configs = {
            "arstechnica": {
                "name": "Ars Technica",
                "rss_url": "http://feeds.arstechnica.com/arstechnica/index",
                "base_url": "https://arstechnica.com",
                "selector": "div.post-content p",
            },
            "slashdot": {
                "name": "Slashdot",
                "rss_url": "http://rss.slashdot.org/Slashdot/slashdot",
                "base_url": "https://slashdot.org",
                "selector": "div.body p",
            },
            "theregister": {
                "name": "The Register",
                "rss_url": "https://www.theregister.com/headlines.atom",
                "base_url": "https://www.theregister.com",
                "selector": "div#body p",
            },
            "thenewstack": {
                "name": "The New Stack",
                "rss_url": "https://thenewstack.io/feed/",
                "base_url": "https://thenewstack.io",
                "selector": "div.post-content p",
            },
        }

    def get_source_name(self) -> str:
        return "web_content"

    def _create_adaptive_strategy(self):
        """Create Web-specific adaptive strategy."""
        return WebCollectionStrategy(self.get_source_name())

    def _get_strategy_parameters(self):
        """Get web-specific adaptive strategy parameters."""
        from .adaptive_strategy import StrategyParameters

        return StrategyParameters(
            base_delay=1.0,  # More aggressive for web content
            min_delay=0.5,
            max_delay=300.0,
            backoff_multiplier=1.8,
            success_reduction_factor=0.8,
            rate_limit_buffer=0.1,  # Lower buffer for RSS feeds
            max_requests_per_window=60,  # Higher limit for web content
            window_duration=60,
            health_check_interval=600,  # Less frequent checks
            adaptation_sensitivity=0.1,
        )

    async def check_connectivity(self) -> Tuple[bool, str]:
        """Check connectivity to web sources."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Test a few key sites
                test_sites = ["https://arstechnica.com", "https://slashdot.org"]
                for site in test_sites:
                    try:
                        response = await client.get(site)
                        if response.status_code == 200:
                            return True, f"Web connectivity confirmed via {site}"
                    except Exception:
                        continue
                return False, "No web connectivity detected"
        except Exception as e:
            return False, f"Connectivity check failed: {str(e)}"

    async def check_authentication(self) -> Tuple[bool, str]:
        """Web sources don't require authentication."""
        return True, "No authentication required for web sources"

    async def collect_content(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Collect content from web sources.

        Args:
            params: Should contain 'sites' list and optional 'limit'
        """
        sites = params.get("sites", ["arstechnica", "theregister"])
        limit = params.get("limit", 10)

        all_items = []

        for site in sites:
            if site not in self.site_configs:
                logger.warning(f"Unknown site: {site}")
                continue

            try:
                site_config = self.site_configs[site]
                items = await self._collect_from_site(site, site_config, limit)
                all_items.extend(items)
            except Exception as e:
                logger.error(f"Failed to collect from {site}: {e}")
                continue

        # Sort by date and limit total results
        all_items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return all_items[:limit]

    async def _collect_from_site(
        self, site_key: str, site_config: Dict[str, Any], limit: int
    ) -> List[Dict[str, Any]]:
        """Collect content from a specific site."""
        items = []

        try:
            # First try RSS feed
            rss_url = site_config["rss_url"]
            logger.info(f"Fetching RSS from {site_config['name']}: {rss_url}")

            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(rss_url)
                response.raise_for_status()

                # Parse RSS feed
                feed = feedparser.parse(response.text)

                for entry in feed.entries[:limit]:
                    try:
                        # Extract basic info from RSS
                        title = entry.get("title", "No title")
                        link = entry.get("link", "")
                        summary = entry.get("summary", entry.get("description", ""))

                        # Clean up summary HTML
                        summary = re.sub(r"<[^>]+>", "", summary)
                        summary = re.sub(r"\s+", " ", summary).strip()

                        # Parse date
                        published = entry.get("published_parsed") or entry.get(
                            "updated_parsed"
                        )
                        if published:
                            created_at = datetime(
                                *published[:6], tzinfo=timezone.utc
                            ).isoformat()
                        else:
                            created_at = datetime.now(timezone.utc).isoformat()

                        # Create standardized item
                        item = {
                            "id": f"{site_key}_{hash(link) % 100000}",
                            "source": "web",
                            "site": site_key,
                            "site_name": site_config["name"],
                            "title": title,
                            "content": summary[:500],  # Limit content length
                            "url": link,
                            "author": entry.get("author", site_config["name"]),
                            "score": 0,  # No score for web content
                            "num_comments": 0,  # No comments for web content
                            "content_type": "article",
                            "created_at": created_at,
                            "collected_at": datetime.now(timezone.utc).isoformat(),
                            "raw_data": {
                                "rss_entry": {
                                    "title": entry.get("title"),
                                    "link": entry.get("link"),
                                    "published": entry.get("published"),
                                    "summary": entry.get("summary"),
                                    "tags": [
                                        tag.get("term", "")
                                        for tag in entry.get("tags", [])
                                    ],
                                },
                                "source": "web",
                                "source_type": "rss_feed",
                                "site": site_key,
                                "collected_at": datetime.now(timezone.utc).isoformat(),
                            },
                        }
                        items.append(item)

                    except Exception as e:
                        logger.error(f"Error processing RSS entry from {site_key}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error fetching RSS from {site_key}: {e}")

        return items


class ArsTechnicaCollector(WebContentCollector):
    """Ars Technica RSS collector."""

    def get_source_name(self) -> str:
        return "arstechnica"

    def _create_adaptive_strategy(self):
        """Create Ars Technica-specific adaptive strategy."""
        return WebCollectionStrategy(self.get_source_name())

    async def collect_content(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect from Ars Technica."""
        params["sites"] = ["arstechnica"]
        return await super().collect_content(params)


class SlashdotCollector(WebContentCollector):
    """Slashdot RSS collector."""

    def get_source_name(self) -> str:
        return "slashdot"

    def _create_adaptive_strategy(self):
        """Create Slashdot-specific adaptive strategy."""
        return WebCollectionStrategy(self.get_source_name())

    async def collect_content(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect from Slashdot."""
        params["sites"] = ["slashdot"]
        return await super().collect_content(params)


class TheRegisterCollector(WebContentCollector):
    """The Register RSS collector."""

    def get_source_name(self) -> str:
        return "theregister"

    def _create_adaptive_strategy(self):
        """Create The Register-specific adaptive strategy."""
        return WebCollectionStrategy(self.get_source_name())

    async def collect_content(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect from The Register."""
        params["sites"] = ["theregister"]
        return await super().collect_content(params)


class TheNewStackCollector(WebContentCollector):
    """The New Stack RSS collector."""

    def get_source_name(self) -> str:
        return "thenewstack"

    def _create_adaptive_strategy(self):
        """Create The New Stack-specific adaptive strategy."""
        return WebCollectionStrategy(self.get_source_name())

    async def collect_content(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect from The New Stack."""
        params["sites"] = ["thenewstack"]
        return await super().collect_content(params)

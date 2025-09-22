"""
Mastodon Content Collector - LEGACY

DEPRECATED: Complex Mastodon collector with adaptive strategies
Status: PENDING REMOVAL - Replaced by simple_mastodon.py which is more reliable

Uses complex adaptive collection patterns that were causing CI/CD failures.
Use simple_mastodon.py instead for public Mastodon API collection.

Collector for Mastodon content using the public API.
Supports collecting from public timelines, hashtags, and trends.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import httpx
from collectors.adaptive_strategy import AdaptiveCollectionStrategy, StrategyParameters
from collectors.base import InternetConnectivityMixin, SourceCollector

from libs.secure_error_handler import ErrorSeverity, SecureErrorHandler

logger = logging.getLogger(__name__)


class MastodonCollectionStrategy(AdaptiveCollectionStrategy):
    """Adaptive strategy specifically tuned for Mastodon's API patterns."""

    def __init__(self, source_name: str = "mastodon", **kwargs):
        # Mastodon-specific parameters
        mastodon_params = StrategyParameters(
            base_delay=1.5,  # Mastodon is generally more lenient than Reddit
            min_delay=1.0,
            max_delay=300.0,
            backoff_multiplier=2.0,
            success_reduction_factor=0.9,
            rate_limit_buffer=0.2,  # Moderate buffer
            max_requests_per_window=100,  # More generous than Reddit
            window_duration=300,  # 5-minute windows
            health_check_interval=300,
            adaptation_sensitivity=0.1,
        )

        super().__init__(source_name, mastodon_params, **kwargs)

    async def get_collection_parameters(self):
        """Return Mastodon-specific collection parameters."""
        return {
            "max_items": 40,  # Mastodon API limit
            "types": ["public_timeline", "hashtags", "trends"],
            "hashtags": ["technology", "programming", "opensource"],
            "include_media": True,
            "min_content_length": 10,
        }


class MastodonError(Exception):
    """Custom exception for Mastodon-related errors."""

    def __init__(
        self, message: str, error_type: str = "UNKNOWN", details: Optional[Dict] = None
    ):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}


class MastodonCollector(SourceCollector, InternetConnectivityMixin):
    """Collector for Mastodon using public API (no authentication required for public timelines)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Default to mastodon.social but allow configuration
        self.instance_url = self.config.get("instance_url", "https://mastodon.social")
        if not self.instance_url.startswith(("http://", "https://")):
            self.instance_url = f"https://{self.instance_url}"

        # Ensure URL ends with proper format
        if self.instance_url.endswith("/"):
            self.instance_url = self.instance_url[:-1]

        # Import config for consistent user agent
        from config import config as app_config

        # Configure HTTP client
        self.headers = {
            "User-Agent": app_config.reddit_user_agent,
            "Accept": "application/json",
        }

        logger.info(f"Initialized Mastodon collector for instance: {self.instance_url}")

    def get_source_name(self) -> str:
        return "mastodon"

    def _create_adaptive_strategy(self):
        """Create Mastodon-specific adaptive strategy."""
        return MastodonCollectionStrategy(source_name=self.get_source_name())

    def _get_strategy_parameters(self):
        """Get Mastodon-specific adaptive strategy parameters."""
        from .adaptive_strategy import StrategyParameters

        return StrategyParameters(
            base_delay=1.5,  # Mastodon is generally more lenient than Reddit
            min_delay=1.0,
            max_delay=300.0,
            backoff_multiplier=2.0,
            success_reduction_factor=0.9,
            rate_limit_buffer=0.2,  # Moderate buffer
            max_requests_per_window=100,  # More generous than Reddit
            window_duration=300,  # 5-minute windows
            health_check_interval=300,
            adaptation_sensitivity=0.1,
        )

    async def check_connectivity(self) -> Tuple[bool, str]:
        """Check Mastodon instance accessibility."""
        try:
            async with httpx.AsyncClient() as client:
                # Test the instance info endpoint
                response = await client.get(
                    f"{self.instance_url}/api/v1/instance",
                    headers=self.headers,
                    timeout=10,
                )
                if response.status_code == 200:
                    data = response.json()
                    instance_name = data.get("title", "Unknown")
                    return True, f"Mastodon instance '{instance_name}' accessible"
                else:
                    return False, f"Mastodon API returned status {response.status_code}"
        except Exception as e:
            return False, f"Mastodon instance not accessible: {str(e)}"

    async def check_authentication(self) -> Tuple[bool, str]:
        """Public API doesn't require authentication for public timelines."""
        return True, "No authentication required for public API endpoints"

    async def collect_content(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Collect content from Mastodon.

        Supported collection types:
        - public_timeline: Public timeline posts
        - hashtags: Posts with specific hashtags
        - trends: Trending hashtags/topics
        """
        collection_type = params.get("type", "public_timeline")
        limit = params.get("limit", 20)

        try:
            if collection_type == "public_timeline":
                return await self._fetch_public_timeline(limit)
            elif collection_type == "hashtags":
                hashtags = params.get("hashtags", ["technology", "programming"])
                return await self._fetch_hashtag_posts(hashtags, limit)
            elif collection_type == "trends":
                return await self._fetch_trends()
            else:
                logger.warning(f"Unknown collection type: {collection_type}")
                return []

        except Exception as e:
            logger.error(f"Failed to collect Mastodon content: {e}")
            return []

    async def _fetch_public_timeline(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch posts from public timeline."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.instance_url}/api/v1/timelines/public",
                    headers=self.headers,
                    params={
                        "limit": min(limit, 40),  # Mastodon max is 40
                        "local": False,  # Include federated posts
                    },
                    timeout=15,
                )
                response.raise_for_status()

                posts = response.json()
                processed_posts = []

                for post in posts:
                    processed_post = self._process_post(post)
                    if processed_post:
                        processed_posts.append(processed_post)

                logger.info(
                    f"Successfully fetched {len(processed_posts)} posts from public timeline"
                )
                return processed_posts

        except Exception as e:
            logger.error(f"Failed to fetch public timeline: {e}")
            raise MastodonError(f"Failed to fetch public timeline: {e}", "API_ERROR")

    async def _fetch_hashtag_posts(
        self, hashtags: List[str], limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Fetch posts for specific hashtags."""
        all_posts = []
        posts_per_hashtag = max(1, limit // len(hashtags))

        for hashtag in hashtags:
            try:
                # Remove # if present
                clean_hashtag = hashtag.lstrip("#")

                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.instance_url}/api/v1/timelines/tag/{clean_hashtag}",
                        headers=self.headers,
                        params={
                            "limit": min(posts_per_hashtag, 40),
                        },
                        timeout=15,
                    )
                    response.raise_for_status()

                    posts = response.json()
                    for post in posts:
                        processed_post = self._process_post(post)
                        if processed_post:
                            processed_post["source_hashtag"] = hashtag
                            all_posts.append(processed_post)

                logger.info(f"Fetched {len(posts)} posts for hashtag #{clean_hashtag}")

            except Exception as e:
                logger.error(f"Failed to fetch posts for hashtag #{hashtag}: {e}")

        return all_posts[:limit]  # Respect the total limit

    async def _fetch_trends(self) -> List[Dict[str, Any]]:
        """Fetch trending hashtags/topics."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.instance_url}/api/v1/trends",
                    headers=self.headers,
                    timeout=10,
                )
                response.raise_for_status()

                trends = response.json()
                processed_trends = []

                for trend in trends:
                    processed_trend = {
                        "type": "trend",
                        "name": trend.get("name", ""),
                        "url": trend.get("url", ""),
                        "history": trend.get("history", []),
                        "source": "mastodon",
                        "source_instance": self.instance_url,
                        "collected_at": datetime.now(timezone.utc).isoformat(),
                    }
                    processed_trends.append(processed_trend)

                logger.info(
                    f"Successfully fetched {len(processed_trends)} trending topics"
                )
                return processed_trends

        except Exception as e:
            logger.error(f"Failed to fetch trends: {e}")
            raise MastodonError(f"Failed to fetch trends: {e}", "API_ERROR")

    def _process_post(self, post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a raw Mastodon post into our standard format."""
        try:
            # Extract account information
            account = post.get("account", {})

            # Extract content (prefer plain text, fall back to HTML)
            content = post.get("content", "")

            # Get media attachments
            media_attachments = []
            for media in post.get("media_attachments", []):
                media_attachments.append(
                    {
                        "type": media.get("type"),
                        "url": media.get("url"),
                        "preview_url": media.get("preview_url"),
                        "description": media.get("description"),
                    }
                )

            # Extract hashtags
            tags = [tag.get("name", "") for tag in post.get("tags", [])]

            processed_post = {
                "id": post.get("id"),
                "content": content,
                "author": {
                    "username": account.get("username", ""),
                    "display_name": account.get("display_name", ""),
                    "url": account.get("url", ""),
                    "followers_count": account.get("followers_count", 0),
                    "following_count": account.get("following_count", 0),
                },
                "url": post.get("url", ""),
                "created_at": post.get("created_at", ""),
                "language": post.get("language"),
                "replies_count": post.get("replies_count", 0),
                "reblogs_count": post.get("reblogs_count", 0),
                "favourites_count": post.get("favourites_count", 0),
                "tags": tags,
                "media_attachments": media_attachments,
                "visibility": post.get("visibility", "public"),
                "source": "mastodon",
                "source_instance": self.instance_url,
                "collected_at": datetime.now(timezone.utc).isoformat(),
            }

            # Filter out very short or empty posts
            if len(content.strip()) < 10:
                return None

            return processed_post

        except Exception as e:
            logger.error(f"Failed to process post: {e}")
            return None

    async def get_health_status(self) -> str:
        """Get current health status."""
        return self.adaptive_strategy.session_metrics.health_status.value

    async def get_current_delay(self) -> float:
        """Get current adaptive delay."""
        return self.adaptive_strategy.current_delay

    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get collection metrics summary."""
        return self.adaptive_strategy.get_metrics_summary()

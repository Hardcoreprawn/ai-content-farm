"""
Source-Specific Collection Strategies - LEGACY

DEPRECATED: Complex source-specific adaptive strategies
Status: PENDING REMOVAL - Replaced by simple retry logic in simple_* collectors

Implemented complex adaptive strategies for different sources with learning algorithms.
Simplified collectors use basic configuration instead.

Implements adaptive strategies tailored to different content sources
with their unique rate limiting and behavioral patterns.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .adaptive_strategy import (
    AdaptiveCollectionStrategy,
    SourceHealth,
    StrategyParameters,
)

logger = logging.getLogger(__name__)


class RedditCollectionStrategy(AdaptiveCollectionStrategy):
    """Adaptive strategy specifically tuned for Reddit's API patterns."""

    def __init__(self, source_name: str = "reddit", **kwargs):
        # Reddit-specific parameters
        reddit_params = StrategyParameters(
            base_delay=2.0,  # Reddit prefers slower requests
            min_delay=1.0,  # Never go below 1 second
            max_delay=600.0,  # Up to 10 minutes for severe rate limiting
            backoff_multiplier=2.5,  # Aggressive backoff for Reddit
            success_reduction_factor=0.9,  # Conservative reduction
            rate_limit_buffer=0.2,  # 20% buffer for Reddit
            max_requests_per_window=30,  # Conservative limit
            window_duration=60,
            health_check_interval=300,
        )

        super().__init__(source_name, reddit_params, **kwargs)

        # Reddit-specific state
        self.oauth_token = None
        self.token_expires_at = None
        self.last_auth_attempt = None
        self.auth_failures = 0
        self.subreddit_cooldowns: Dict[str, datetime] = {}

    async def get_collection_parameters(self) -> Dict[str, Any]:
        """Get Reddit collection parameters based on current strategy."""
        base_params = {
            "limit": self._get_adaptive_limit(),
            "sort": "hot",  # Less likely to hit rate limits than 'new'
            "time_filter": self._get_adaptive_time_filter(),
            "request_delay": self.current_delay,
            "retry_attempts": self._get_retry_attempts(),
            "timeout": self._get_adaptive_timeout(),
        }

        # Add health-based adjustments
        if self.session_metrics.health_status == SourceHealth.RATE_LIMITED:
            base_params.update(
                {
                    "limit": max(1, base_params["limit"] // 2),
                    "sort": "hot",  # Stick to hot posts when rate limited
                    "time_filter": "day",  # Broader time filter
                }
            )
        elif self.session_metrics.health_status == SourceHealth.ERROR:
            base_params.update(
                {
                    "limit": max(1, base_params["limit"] // 3),
                    "retry_attempts": 1,  # Reduce retries when errors are high
                    "timeout": min(30, base_params["timeout"] * 2),
                }
            )

        return base_params

    def _get_adaptive_limit(self) -> int:
        """Get adaptive limit based on current performance."""
        base_limit = 25

        if self.session_metrics.success_rate > 0.9 and self.consecutive_successes > 5:
            return min(50, int(base_limit * 1.5))
        elif self.session_metrics.success_rate < 0.7:
            return max(5, int(base_limit * 0.5))
        else:
            return base_limit

    def _get_adaptive_time_filter(self) -> str:
        """Get adaptive time filter based on performance."""
        if self.session_metrics.health_status == SourceHealth.HEALTHY:
            if self.session_metrics.avg_response_time < 2.0:
                return "hour"  # More recent content when performing well
            else:
                return "day"
        else:
            return "day"  # Broader filter when having issues

    def _get_retry_attempts(self) -> int:
        """Get adaptive retry attempts."""
        if self.session_metrics.health_status in [
            SourceHealth.RATE_LIMITED,
            SourceHealth.ERROR,
        ]:
            return 1
        elif self.session_metrics.success_rate > 0.9:
            return 3
        else:
            return 2

    def _get_adaptive_timeout(self) -> int:
        """Get adaptive timeout based on response times."""
        base_timeout = 30
        if self.session_metrics.avg_response_time > 5.0:
            return min(60, int(base_timeout * 1.5))
        else:
            return base_timeout

    async def handle_subreddit_cooldown(
        self, subreddit: str, cooldown_seconds: int = 300
    ):
        """Handle cooldown for specific subreddit."""
        cooldown_until = datetime.now() + timedelta(seconds=cooldown_seconds)
        self.subreddit_cooldowns[subreddit] = cooldown_until
        logger.warning(f"Subreddit {subreddit} on cooldown until {cooldown_until}")

    def is_subreddit_available(self, subreddit: str) -> bool:
        """Check if subreddit is available (not on cooldown)."""
        if subreddit in self.subreddit_cooldowns:
            if datetime.now() < self.subreddit_cooldowns[subreddit]:
                return False
            else:
                del self.subreddit_cooldowns[subreddit]
        return True

    async def after_request(
        self,
        success: bool,
        response_time: float,
        status_code: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        error: Optional[Exception] = None,
    ) -> None:
        """Reddit-specific post-request handling."""
        await super().after_request(success, response_time, status_code, headers, error)

        # Handle Reddit-specific errors
        if not success and error:
            error_str = str(error).lower()
            if "forbidden" in error_str or "private" in error_str:
                logger.warning(
                    f"[Reddit] Access forbidden - may need to adjust subreddit list"
                )
            elif "not found" in error_str:
                logger.warning(
                    f"[Reddit] Subreddit not found - should remove from collection"
                )
            elif "suspended" in error_str or "banned" in error_str:
                logger.error(f"[Reddit] Account suspended/banned - stopping collection")
                self.current_delay = self.params.max_delay


class RSSCollectionStrategy(AdaptiveCollectionStrategy):
    """Adaptive strategy for RSS feeds with respect for publisher resources."""

    def __init__(self, source_name: str = "rss", **kwargs):
        # RSS-specific parameters (generally more lenient)
        rss_params = StrategyParameters(
            base_delay=0.5,  # RSS feeds can handle faster requests
            min_delay=0.2,
            max_delay=300.0,
            backoff_multiplier=1.8,  # Less aggressive backoff
            success_reduction_factor=0.8,
            rate_limit_buffer=0.1,
            max_requests_per_window=60,  # RSS can handle more requests
            window_duration=60,
            health_check_interval=600,  # Check less frequently
        )

        super().__init__(source_name, rss_params, **kwargs)

        # RSS-specific state
        self.feed_etags: Dict[str, str] = {}
        self.feed_last_modified: Dict[str, str] = {}
        self.feed_health: Dict[str, SourceHealth] = {}

    async def get_collection_parameters(self) -> Dict[str, Any]:
        """Get RSS collection parameters."""
        return {
            "request_delay": self.current_delay,
            "timeout": self._get_adaptive_timeout(),
            "retry_attempts": self._get_retry_attempts(),
            "use_etag": True,
            "use_last_modified": True,
            "follow_redirects": True,
            "max_content_length": self._get_max_content_length(),
        }

    def _get_adaptive_timeout(self) -> int:
        """RSS feeds might be slower than APIs."""
        base_timeout = 15
        if self.session_metrics.avg_response_time > 10.0:
            return min(45, int(base_timeout * 2))
        return base_timeout

    def _get_retry_attempts(self) -> int:
        """RSS feeds might have temporary issues."""
        if self.session_metrics.health_status == SourceHealth.ERROR:
            return 1
        return 2

    def _get_max_content_length(self) -> int:
        """Adaptive content length based on performance."""
        base_length = 1024 * 1024  # 1MB
        if self.session_metrics.avg_response_time > 5.0:
            return base_length // 2  # Reduce if slow
        return base_length

    async def handle_feed_response(
        self, feed_url: str, response_headers: Dict[str, str]
    ):
        """Handle RSS feed-specific response data."""
        # Store ETag and Last-Modified for efficient polling
        if "etag" in response_headers:
            self.feed_etags[feed_url] = response_headers["etag"]
        if "last-modified" in response_headers:
            self.feed_last_modified[feed_url] = response_headers["last-modified"]

    def get_feed_headers(self, feed_url: str) -> Dict[str, str]:
        """Get headers for RSS feed request with caching support."""
        headers = {"User-Agent": "AI Content Farm/1.0 (Respectful RSS Reader)"}

        if feed_url in self.feed_etags:
            headers["If-None-Match"] = self.feed_etags[feed_url]
        if feed_url in self.feed_last_modified:
            headers["If-Modified-Since"] = self.feed_last_modified[feed_url]

        return headers


class WebCollectionStrategy(AdaptiveCollectionStrategy):
    """Adaptive strategy for web scraping with respect for robots.txt and server load."""

    def __init__(self, source_name: str = "web", **kwargs):
        # Web scraping parameters (most conservative)
        web_params = StrategyParameters(
            base_delay=3.0,  # Be respectful to web servers
            min_delay=1.0,
            max_delay=900.0,  # Up to 15 minutes for aggressive rate limiting
            backoff_multiplier=3.0,  # Very aggressive backoff
            success_reduction_factor=0.95,  # Very conservative reduction
            rate_limit_buffer=0.3,  # 30% buffer
            max_requests_per_window=20,  # Very conservative
            window_duration=60,
            health_check_interval=300,
        )

        super().__init__(source_name, web_params, **kwargs)

        # Web-specific state
        self.robots_cache: Dict[str, Dict[str, Any]] = {}
        self.domain_cooldowns: Dict[str, datetime] = {}
        self.crawl_delays: Dict[str, float] = {}

    async def get_collection_parameters(self) -> Dict[str, Any]:
        """Get web collection parameters."""
        return {
            "request_delay": self.current_delay,
            "timeout": self._get_adaptive_timeout(),
            "retry_attempts": 1,  # Be conservative with retries
            "respect_robots_txt": True,
            "user_agent": "AI Content Farm/1.0 (Educational Research)",
            "max_content_length": self._get_max_content_length(),
            "follow_redirects": True,
            "max_redirects": 3,
        }

    def _get_adaptive_timeout(self) -> int:
        """Web pages can be slow to load."""
        base_timeout = 30
        if self.session_metrics.avg_response_time > 15.0:
            return min(90, int(base_timeout * 2))
        return base_timeout

    def _get_max_content_length(self) -> int:
        """Adaptive content length for web pages."""
        base_length = 5 * 1024 * 1024  # 5MB
        if self.session_metrics.avg_response_time > 10.0:
            return base_length // 2
        return base_length

    async def check_robots_txt(self, domain: str) -> bool:
        """Check if collection is allowed by robots.txt."""
        # Implementation would check robots.txt
        # For now, return True but log the check
        logger.debug(f"Checking robots.txt for {domain}")
        return True

    async def handle_domain_cooldown(self, domain: str, cooldown_seconds: int = 600):
        """Handle cooldown for specific domain."""
        cooldown_until = datetime.now() + timedelta(seconds=cooldown_seconds)
        self.domain_cooldowns[domain] = cooldown_until
        logger.warning(f"Domain {domain} on cooldown until {cooldown_until}")

    def is_domain_available(self, domain: str) -> bool:
        """Check if domain is available (not on cooldown)."""
        if domain in self.domain_cooldowns:
            if datetime.now() < self.domain_cooldowns[domain]:
                return False
            else:
                del self.domain_cooldowns[domain]
        return True


class MastodonCollectionStrategy(AdaptiveCollectionStrategy):
    """Adaptive strategy specifically tuned for Mastodon's API patterns."""

    def __init__(self, source_name: str = "mastodon", **kwargs):
        # Mastodon-specific parameters
        mastodon_params = StrategyParameters(
            base_delay=1.5,  # Mastodon is generally more lenient than Reddit
            min_delay=1.0,  # Reasonable minimum
            max_delay=300.0,  # Up to 5 minutes for rate limiting
            backoff_multiplier=2.0,  # Standard backoff
            success_reduction_factor=0.9,  # Conservative reduction
            rate_limit_buffer=0.2,  # 20% buffer
            max_requests_per_window=100,  # More generous than Reddit
            window_duration=300,  # 5-minute windows
            health_check_interval=300,
        )

        super().__init__(source_name, mastodon_params, **kwargs)

        # Mastodon-specific state
        self.instance_url = None
        self.instance_info = None
        self.last_instance_check = None
        self.hashtag_cooldowns: Dict[str, datetime] = {}
        self.instance_health = "unknown"

    async def get_collection_parameters(self) -> Dict[str, Any]:
        """Get Mastodon collection parameters based on current strategy."""
        base_params = {
            "delay": self.current_delay,
            "retry_count": (
                3 if self.session_metrics.health_status == SourceHealth.HEALTHY else 1
            ),
            "timeout": 15,  # Mastodon can be slower than Reddit
        }

        # Add collection strategy based on health
        if self.session_metrics.health_status == SourceHealth.HEALTHY:
            base_params.update(
                {
                    "limit": 40,  # Mastodon max
                    "include_local": False,  # Include federated content
                    "include_replies": False,  # Skip replies for performance
                }
            )
        elif self.session_metrics.health_status == SourceHealth.DEGRADED:
            base_params.update(
                {
                    "limit": 20,
                    "include_local": True,  # Local only for better performance
                    "include_replies": False,
                }
            )
        else:  # UNHEALTHY
            base_params.update(
                {
                    "limit": 10,
                    "include_local": True,
                    "include_replies": False,
                    "minimal_processing": True,
                }
            )

        return base_params

    async def handle_rate_limit(
        self, response_headers: Optional[Dict[str, str]] = None
    ):
        """Handle Mastodon rate limiting."""
        await super().handle_rate_limit(response_headers)

        # Mastodon uses X-RateLimit headers
        if response_headers:
            remaining = response_headers.get("X-RateLimit-Remaining")
            reset_time = response_headers.get("X-RateLimit-Reset")

            if remaining and int(remaining) < 5:
                # Low on rate limit quota
                self.current_delay = min(
                    self.current_delay * 1.5, self.strategy_params.max_delay
                )
                logger.warning(
                    f"Mastodon rate limit low: {remaining} requests remaining"
                )

            if reset_time:
                try:
                    reset_timestamp = int(reset_time)
                    reset_datetime = datetime.fromtimestamp(reset_timestamp)
                    wait_seconds = (reset_datetime - datetime.now()).total_seconds()
                    if wait_seconds > 0:
                        self.current_delay = max(self.current_delay, wait_seconds)
                        logger.info(
                            f"Mastodon rate limit reset in {wait_seconds:.1f} seconds"
                        )
                except (ValueError, TypeError):
                    logger.warning("Invalid Mastodon rate limit reset time")

    async def handle_success(self, collected_count: int):
        """Handle successful collection from Mastodon."""
        await super().handle_success(collected_count)

        # Update instance health status
        self.instance_health = "healthy"
        self.last_instance_check = datetime.now()

        # Clear old hashtag cooldowns
        current_time = datetime.now()
        expired_hashtags = [
            hashtag
            for hashtag, cooldown_time in self.hashtag_cooldowns.items()
            if current_time > cooldown_time
        ]
        for hashtag in expired_hashtags:
            del self.hashtag_cooldowns[hashtag]

    async def handle_error(
        self, error: Exception, error_context: Optional[Dict[str, Any]] = None
    ):
        """Handle Mastodon collection errors."""
        await super().handle_error(error, error_context)

        error_str = str(error).lower()

        # Instance-specific error handling
        if "instance" in error_str or "server" in error_str:
            self.instance_health = "degraded"
            logger.warning(f"Mastodon instance issues detected: {error}")

        # Hashtag-specific cooldowns
        if error_context and "hashtag" in error_context:
            hashtag = error_context["hashtag"]
            cooldown_minutes = 30  # Default cooldown

            if "rate limit" in error_str:
                cooldown_minutes = 60  # Longer cooldown for rate limits
            elif "not found" in error_str:
                cooldown_minutes = 120  # Even longer for missing hashtags

            cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)
            self.hashtag_cooldowns[hashtag] = cooldown_until
            logger.warning(f"Hashtag #{hashtag} on cooldown until {cooldown_until}")

    def is_hashtag_available(self, hashtag: str) -> bool:
        """Check if hashtag is available (not on cooldown)."""
        if hashtag in self.hashtag_cooldowns:
            if datetime.now() < self.hashtag_cooldowns[hashtag]:
                return False
            else:
                del self.hashtag_cooldowns[hashtag]
        return True

    def get_instance_health(self) -> str:
        """Get current instance health status."""
        return self.instance_health


class StrategyFactory:
    """Factory for creating appropriate collection strategies."""

    STRATEGY_MAP = {
        "reddit": RedditCollectionStrategy,
        "rss": RSSCollectionStrategy,
        "web": WebCollectionStrategy,
        "mastodon": MastodonCollectionStrategy,
    }

    @classmethod
    def create_strategy(
        self,
        source_type: str,
        source_name: Optional[str] = None,
        custom_params: Optional[StrategyParameters] = None,
        **kwargs,
    ) -> AdaptiveCollectionStrategy:
        """Create appropriate strategy for source type."""
        source_name = source_name or source_type

        strategy_class = self.STRATEGY_MAP.get(source_type)
        if not strategy_class:
            raise ValueError(f"Unknown source type: {source_type}")

        if custom_params:
            kwargs["strategy_params"] = custom_params

        return strategy_class(source_name=source_name, **kwargs)

    @classmethod
    def get_supported_sources(cls) -> List[str]:
        """Get list of supported source types."""
        return list(cls.STRATEGY_MAP.keys())

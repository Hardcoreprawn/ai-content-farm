"""
Reddit Content Collectors - LEGACY

DEPRECATED: Complex Reddit collector with adaptive strategies
Status: PENDING REMOVAL - Replaced by simple_reddit.py which is more reliable

Contains PRAW-based collectors that were causing authentication and testing issues.
Use simple_reddit.py instead for public Reddit API collection.

Collectors for Reddit content using public API and PRAW with enhanced error handling.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from collectors.base import InternetConnectivityMixin, SourceCollector
from keyvault_client import get_reddit_credentials_with_fallback

from libs.secure_error_handler import ErrorSeverity, SecureErrorHandler

logger = logging.getLogger(__name__)


class RedditError(Exception):
    """Custom exception for Reddit-related errors."""

    def __init__(
        self, message: str, error_type: str = "UNKNOWN", details: Optional[Dict] = None
    ):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}


class RedditCollectionStrategy:
    """Reddit-specific adaptive collection strategy."""

    def __init__(self, source_name: str = "reddit", **kwargs):
        from .adaptive_strategy import AdaptiveCollectionStrategy, StrategyParameters

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
            adaptation_sensitivity=0.1,
        )

        class RedditAdaptiveStrategy(AdaptiveCollectionStrategy):
            async def get_collection_parameters(self):
                """Get Reddit-specific collection parameters with adaptive delay."""
                return {
                    "max_items": 50,
                    "time_filter": "day",
                    "sort": "hot",
                    "respect_rate_limits": True,
                    "request_delay": self.current_delay,
                }

        self._strategy = RedditAdaptiveStrategy(source_name, reddit_params, **kwargs)

    def __getattr__(self, name):
        """Delegate all other attributes to the underlying strategy."""
        return getattr(self._strategy, name)


class RedditPublicCollector(SourceCollector, InternetConnectivityMixin):
    """Collector for Reddit using public JSON API (no authentication required)."""

    def get_source_name(self) -> str:
        return "reddit_public"

    def _create_adaptive_strategy(self):
        """Create Reddit-specific adaptive strategy."""
        return RedditCollectionStrategy(self.get_source_name())

    def _get_strategy_parameters(self):
        """Get Reddit-specific adaptive strategy parameters."""
        from .adaptive_strategy import StrategyParameters

        """Get Reddit-specific adaptive strategy parameters."""
        from .adaptive_strategy import StrategyParameters

        return StrategyParameters(
            base_delay=3.0,  # Conservative for Reddit
            min_delay=2.0,
            max_delay=600.0,
            backoff_multiplier=2.5,
            success_reduction_factor=0.9,
            rate_limit_buffer=0.3,  # Higher buffer for Reddit's strict limits
            max_requests_per_window=25,  # Conservative Reddit limit
            window_duration=60,
            health_check_interval=300,
            adaptation_sensitivity=0.1,
        )

    async def check_connectivity(self) -> Tuple[bool, str]:
        """Check Reddit public API accessibility."""
        try:
            # Test Reddit's public API using httpx for async
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.reddit.com/r/technology/hot.json?limit=1",
                    headers={"User-Agent": "ai-content-farm-collector/1.0"},
                    timeout=5,
                )
                if response.status_code == 200:
                    return True, "Reddit public API accessible"
                else:
                    return False, f"Reddit API returned status {response.status_code}"
        except Exception as e:
            return False, f"Reddit API not accessible: {str(e)}"

    async def check_authentication(self) -> Tuple[bool, str]:
        """Public API doesn't require authentication."""
        return True, "No authentication required for public API"

    async def collect_content(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect content from Reddit subreddits using public API."""
        subreddits = params.get("subreddits", ["technology"])
        limit = params.get("limit", 10)

        all_posts = []

        for subreddit in subreddits:
            try:
                posts = await self._fetch_from_subreddit(subreddit, limit)
                all_posts.extend(posts)
            except Exception as e:
                logger.error(f"Failed to fetch from r/{subreddit}: {e}")

        return all_posts

    async def _fetch_from_subreddit(
        self, subreddit: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Fetch posts from a specific subreddit using public API."""
        if not subreddit or subreddit is None:
            return []

        url = f"https://www.reddit.com/r/{subreddit}/hot.json"
        headers = {"User-Agent": "ai-content-farm-collector/1.0"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, headers=headers, params={"limit": limit}, timeout=10
                )
                response.raise_for_status()

                data = response.json()
                posts = []

                for child in data.get("data", {}).get("children", []):
                    post_data = child.get("data", {})
                    if post_data:
                        # Add metadata
                        post_data["source"] = "reddit"
                        post_data["source_type"] = "subreddit"
                        post_data["collected_at"] = datetime.now(
                            timezone.utc
                        ).isoformat()
                        posts.append(post_data)

                return posts

        except Exception as e:
            logger.error(f"Error fetching from r/{subreddit}: {e}")
            return []


class RedditPRAWCollector(SourceCollector, InternetConnectivityMixin):
    """Collector for Reddit using PRAW (requires API credentials) with enhanced error handling."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Get credentials from Key Vault with environment variable fallback
        credentials = get_reddit_credentials_with_fallback()

        self.client_id = self.config.get("client_id") or credentials.get("client_id")
        self.client_secret = self.config.get("client_secret") or credentials.get(
            "client_secret"
        )
        self.user_agent = (
            self.config.get("user_agent")
            or credentials.get("user_agent")
            or "ai-content-farm-collector/1.0"
        )

        # Enhanced credential validation
        self.credential_status = self._validate_credentials()

    def get_source_name(self) -> str:
        return "reddit_praw"

    def _create_adaptive_strategy(self):
        """Create Reddit-specific adaptive strategy."""
        return RedditCollectionStrategy(self.get_source_name())

    def _get_strategy_parameters(self):
        """Get Reddit PRAW-specific adaptive strategy parameters."""
        from .adaptive_strategy import StrategyParameters

        return StrategyParameters(
            base_delay=2.0,  # Slightly more aggressive for authenticated API
            min_delay=1.0,
            max_delay=600.0,
            backoff_multiplier=2.5,
            success_reduction_factor=0.9,
            rate_limit_buffer=0.2,
            max_requests_per_window=30,  # Higher limit for authenticated
            window_duration=60,
            health_check_interval=300,
            adaptation_sensitivity=0.1,
        )

        logger.info(
            f"RedditPRAWCollector initialized - Status: {self.credential_status['status']}, "
            f"Has client_id: {bool(self.client_id)}, Has client_secret: {bool(self.client_secret)}, "
            f"User agent: {self.user_agent}"
        )

    def _validate_credentials(self) -> Dict[str, Any]:
        """Validate and diagnose credential configuration."""
        status = {
            "status": "unknown",
            "message": "",
            "details": {},
            "recommendations": [],
        }

        # Check credential presence
        if not self.client_id:
            status["status"] = "missing_credentials"
            status["message"] = "Reddit client_id is missing"
            status["details"]["missing_client_id"] = True
            status["recommendations"].append(
                "Set REDDIT_CLIENT_ID environment variable or add to Key Vault as 'reddit-client-id'"
            )

        if not self.client_secret:
            status["status"] = "missing_credentials"
            status["message"] = "Reddit client_secret is missing"
            status["details"]["missing_client_secret"] = True
            status["recommendations"].append(
                "Set REDDIT_CLIENT_SECRET environment variable or add to Key Vault as 'reddit-client-secret'"
            )

        if not self.client_id or not self.client_secret:
            return status

        # Check credential format
        if len(self.client_id) < 10:
            status["status"] = "invalid_credentials"
            status["message"] = (
                "Reddit client_id appears to be too short (possible placeholder)"
            )
            status["details"]["client_id_length"] = len(self.client_id)
            status["recommendations"].append(
                "Verify reddit-client-id in Key Vault contains real Reddit app credentials"
            )

        if len(self.client_secret) < 20:
            status["status"] = "invalid_credentials"
            status["message"] = (
                "Reddit client_secret appears to be too short (possible placeholder)"
            )
            status["details"]["client_secret_length"] = len(self.client_secret)
            status["recommendations"].append(
                "Verify reddit-client-secret in Key Vault contains real Reddit app credentials"
            )

        if (
            "placeholder" in str(self.client_id).lower()
            or "placeholder" in str(self.client_secret).lower()
        ):
            status["status"] = "placeholder_credentials"
            status["message"] = "Reddit credentials contain placeholder values"
            status["recommendations"].append(
                "Replace placeholder credentials in Key Vault with real Reddit app credentials"
            )
            return status

        status["status"] = "valid"
        status["message"] = "Reddit credentials appear valid"
        return status

    def get_source_name(self) -> str:
        return "reddit_praw"

    async def check_connectivity(self) -> Tuple[bool, str]:
        """Check Reddit API accessibility with improved error detection."""
        # Test Reddit API directly (skip unreliable internet connectivity check)
        try:
            async with httpx.AsyncClient() as client:
                # Test basic connectivity to Reddit's homepage instead of OAuth endpoint
                response = await client.get(
                    "https://www.reddit.com/",
                    timeout=10,
                    headers={"User-Agent": "ai-content-farm-connectivity-check/1.0"},
                )
                # Any response from Reddit indicates connectivity
                if response.status_code in [200, 301, 302, 403, 429]:
                    return True, "Reddit API endpoint accessible"
                elif response.status_code == 429:
                    return (
                        False,
                        f"Reddit API rate limited (429) - Azure IP may be throttled. Status: {response.status_code}",
                    )
                elif response.status_code == 403:
                    return (
                        False,
                        f"Reddit API access forbidden (403) - Azure IP may be blocked. Status: {response.status_code}",
                    )
                else:
                    return (
                        False,
                        f"Reddit API returned status {response.status_code} - may indicate IP restrictions",
                    )
        except Exception as e:
            # Use secure error handler to prevent information disclosure
            error_handler = SecureErrorHandler("reddit-collector")
            error_response = error_handler.handle_error(
                error=e,
                error_type="connectivity",
                severity=ErrorSeverity.MEDIUM,
                user_message="Reddit API connection failed - check network connectivity and firewall settings",
            )
            return False, error_response["message"]

    async def check_authentication(self) -> Tuple[bool, str]:
        """Check if PRAW credentials are configured and valid with detailed diagnostics."""

        # First check credential validation
        if self.credential_status["status"] != "valid":
            error_msg = (
                f"Credential validation failed: {self.credential_status['message']}"
            )
            if self.credential_status["recommendations"]:
                error_msg += f" | Recommendations: {'; '.join(self.credential_status['recommendations'])}"
            return False, error_msg

        # Try manual OAuth2 authentication first (more reliable)
        try:
            logger.info("Testing Reddit API authentication via manual OAuth2...")
            return await self._test_manual_oauth2()
        except Exception as oauth_error:
            logger.warning(f"Manual OAuth2 test failed: {oauth_error}")

            # Fall back to asyncpraw test
            try:
                logger.info("Falling back to asyncpraw authentication test...")
                return await self._test_asyncpraw_auth()
            except Exception as praw_error:
                logger.error(
                    f"Both authentication methods failed. OAuth2: {oauth_error}, AsyncPRAW: {praw_error}"
                )
                return False, f"Authentication failed: {oauth_error}"

    async def _test_manual_oauth2(self) -> Tuple[bool, str]:
        """Test Reddit authentication using manual OAuth2 flow."""
        try:
            async with httpx.AsyncClient() as client:
                # Prepare OAuth2 request
                auth_data = {"grant_type": "client_credentials"}

                # Use basic auth with client credentials
                auth = (self.client_id, self.client_secret)
                headers = {
                    "User-Agent": self.user_agent,
                    "Content-Type": "application/x-www-form-urlencoded",
                }

                # Debug logging for production troubleshooting (safe - no actual credentials logged)
                logger.info(f"Attempting OAuth2 with User-Agent: {self.user_agent}")
                logger.info(
                    f"Client ID length: {len(self.client_id)}, Client Secret length: {len(self.client_secret)}"
                )
                logger.info(
                    f"Client ID starts with: {self.client_id[:4]}..., ends with: ...{self.client_id[-4:]}"
                )

                response = await client.post(
                    "https://www.reddit.com/api/v1/access_token",
                    data=auth_data,
                    auth=auth,
                    headers=headers,
                    timeout=10,
                )

                logger.info(f"OAuth2 response status: {response.status_code}")
                if response.status_code != 200:
                    response_text = (
                        response.text[:200] if response.text else "No response body"
                    )
                    logger.info(f"OAuth2 error response: {response_text}")

                if response.status_code == 200:
                    token_data = response.json()
                    if "access_token" in token_data:
                        logger.info("Manual OAuth2 authentication successful")
                        return (
                            True,
                            "Reddit API credentials valid - OAuth2 authentication successful",
                        )
                    else:
                        return (
                            False,
                            f"OAuth2 response missing access_token: {token_data}",
                        )
                elif response.status_code == 401:
                    return (
                        False,
                        "Reddit API authentication failed: Invalid credentials (401 Unauthorized)",
                    )
                elif response.status_code == 403:
                    return (
                        False,
                        "Reddit API authentication failed: Access forbidden (403)",
                    )
                elif response.status_code == 429:
                    return False, "Reddit API authentication failed: Rate limited (429)"
                else:
                    return (
                        False,
                        f"Reddit API authentication failed: HTTP {response.status_code}",
                    )

        except Exception as e:
            logger.error(f"Manual OAuth2 test error: {e}")
            raise

    async def _test_asyncpraw_auth(self) -> Tuple[bool, str]:
        """Test Reddit authentication using asyncpraw (fallback method)."""
        try:
            # Test authentication with Reddit API using asyncpraw
            try:
                import asyncpraw
            except ImportError as e:
                return (
                    False,
                    f"AsyncPRAW library not installed: {e}. Install with: pip install asyncpraw",
                )

            logger.info("Testing Reddit API authentication...")
            reddit = asyncpraw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
            )

            # Try to access a public subreddit to verify credentials
            try:
                test_subreddit = await reddit.subreddit("test")
                post_count = 0
                async for post in test_subreddit.hot(limit=1):
                    post_count += 1
                    break

                await reddit.close()

                logger.info(
                    f"Reddit API authentication successful (retrieved {post_count} test posts)"
                )
                return (
                    True,
                    f"Reddit API credentials valid - successfully retrieved test content",
                )

            except Exception as auth_error:
                await reddit.close()

                # Use secure error handler for detailed logging while protecting sensitive info
                error_handler = SecureErrorHandler("reddit-collector")
                error_str = str(auth_error).lower()

                # Determine appropriate user message based on error type
                if "401" in error_str or "unauthorized" in error_str:
                    user_message = "Reddit API authentication failed: Invalid credentials (401 Unauthorized). Check reddit-client-id and reddit-client-secret in Key Vault"
                elif "403" in error_str or "forbidden" in error_str:
                    user_message = "Reddit API authentication failed: Access forbidden (403). App may not be approved or Azure IP may be blocked"
                elif (
                    "429" in error_str or "rate" in error_str or "too many" in error_str
                ):
                    user_message = "Reddit API authentication failed: Rate limited (429). Azure IP may be throttled - try again later"
                elif "timeout" in error_str or "timed out" in error_str:
                    user_message = "Reddit API authentication failed: Connection timeout. Check network connectivity"
                elif "connection" in error_str or "network" in error_str:
                    user_message = "Reddit API authentication failed: Network/connection error. Check Azure network policies"
                else:
                    user_message = "Reddit API authentication failed: Unable to authenticate with provided credentials"

                error_response = error_handler.handle_error(
                    error=auth_error,
                    error_type="authentication",
                    severity=ErrorSeverity.HIGH,
                    user_message=user_message,
                    context={"operation": "reddit_auth_test"},
                )

                return False, error_response["message"]

        except Exception as e:
            logger.error(f"AsyncPRAW authentication test error: {e}")
            raise

    async def collect_content(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect content using AsyncPRAW with comprehensive error handling."""
        collection_errors = []

        try:
            try:
                import asyncpraw
            except ImportError as e:
                logger.warning(
                    f"AsyncPRAW not available: {e}, falling back to public API"
                )
                fallback_collector = RedditPublicCollector(self.config)
                return await fallback_collector.collect_content(params)

            # Validate credentials before attempting collection
            if self.credential_status["status"] != "valid":
                error_msg = (
                    f"Cannot collect content: {self.credential_status['message']}"
                )
                logger.error(error_msg)
                raise RedditError(
                    error_msg, "INVALID_CREDENTIALS", self.credential_status
                )

            reddit = asyncpraw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
            )

            items = []
            collection_errors = []  # Track errors per subreddit
            subreddits = params.get("subreddits", ["technology"])
            limit = params.get("limit", 10)
            sort_type = params.get("sort", "hot")  # hot, new, top, rising

            logger.info(
                f"Collecting Reddit content from {len(subreddits)} subreddits: {subreddits} (limit: {limit}, sort: {sort_type})"
            )

            for subreddit_name in subreddits:
                try:
                    logger.debug(f"Processing subreddit: r/{subreddit_name}")
                    subreddit = await reddit.subreddit(subreddit_name)

                    # Get posts based on sort type
                    if sort_type == "hot":
                        posts = subreddit.hot(limit=limit)
                    elif sort_type == "new":
                        posts = subreddit.new(limit=limit)
                    elif sort_type == "top":
                        posts = subreddit.top(limit=limit)
                    elif sort_type == "rising":
                        posts = subreddit.rising(limit=limit)
                    else:
                        posts = subreddit.hot(limit=limit)

                    subreddit_items = []
                    post_count = 0

                    # Check if posts is None (the source of our original error)
                    if posts is None:
                        error_msg = f"Reddit API returned None for r/{subreddit_name} {sort_type} posts - possible rate limiting or invalid subreddit"
                        logger.error(error_msg)
                        collection_errors.append(f"r/{subreddit_name}: {error_msg}")
                        continue

                    async for post in posts:
                        if post is None:
                            logger.warning(
                                f"Received None post in r/{subreddit_name}, skipping"
                            )
                            continue

                        try:
                            # Convert post to our standard format
                            item = {
                                "id": f"reddit_{post.id}",
                                "source": "reddit",
                                "subreddit": subreddit_name,
                                "title": post.title,
                                "content": post.selftext or "",
                                "url": post.url,
                                "author": (
                                    str(post.author) if post.author else "[deleted]"
                                ),
                                "score": post.score,
                                "num_comments": post.num_comments,
                                "content_type": "self" if post.is_self else "link",
                                "created_at": datetime.fromtimestamp(
                                    post.created_utc, tz=timezone.utc
                                ).isoformat(),
                                "collected_at": datetime.now(timezone.utc).isoformat(),
                                "raw_data": {
                                    "id": post.id,
                                    "permalink": post.permalink,
                                    "ups": post.ups,
                                    "downs": 0,  # Reddit doesn't provide downvotes
                                    "upvote_ratio": post.upvote_ratio,
                                    "gilded": getattr(post, "gilded", 0),
                                    "over_18": post.over_18,
                                    "spoiler": post.spoiler,
                                    "locked": post.locked,
                                    "stickied": post.stickied,
                                    "domain": post.domain,
                                    "source": "reddit",
                                    "source_type": "subreddit",
                                    "collected_at": datetime.now(
                                        timezone.utc
                                    ).isoformat(),
                                },
                            }
                            subreddit_items.append(item)
                            post_count += 1

                        except Exception as post_error:
                            logger.warning(
                                f"Error processing post in r/{subreddit_name}: {post_error}"
                            )
                            continue

                    logger.info(f"Collected {post_count} posts from r/{subreddit_name}")
                    items.extend(subreddit_items)

                except Exception as subreddit_error:
                    error_str = str(subreddit_error).lower()
                    if "404" in error_str or "not found" in error_str:
                        error_msg = f"Subreddit r/{subreddit_name} not found or private"
                    elif "403" in error_str or "forbidden" in error_str:
                        error_msg = f"Access forbidden to r/{subreddit_name} - may be private or banned"
                    elif "429" in error_str or "rate" in error_str:
                        error_msg = f"Rate limited while accessing r/{subreddit_name}"
                    else:
                        error_msg = (
                            f"Error accessing r/{subreddit_name}: {subreddit_error}"
                        )

                    logger.error(error_msg)
                    collection_errors.append(f"r/{subreddit_name}: {error_msg}")

            await reddit.close()

            if items:
                logger.info(
                    f"Successfully collected {len(items)} total items from Reddit"
                )
            else:
                error_summary = (
                    "; ".join(collection_errors)
                    if collection_errors
                    else "No items found"
                )
                logger.warning(
                    f"No items collected from Reddit. Errors: {error_summary}"
                )

            return items

        except RedditError:
            # Re-raise our custom errors
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error collecting Reddit content with AsyncPRAW: {str(e)}"
            )
            # Fallback to public API
            logger.info("Falling back to Reddit public API")
            fallback_collector = RedditPublicCollector(self.config)
            return await fallback_collector.collect_content(params)

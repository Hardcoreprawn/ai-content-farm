"""
Reddit Content Collectors

Collectors for Reddit content using public API and PRAW.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from collectors.base import InternetConnectivityMixin, SourceCollector
from keyvault_client import get_reddit_credentials_with_fallback

logger = logging.getLogger(__name__)


class RedditPublicCollector(SourceCollector, InternetConnectivityMixin):
    """Collector for Reddit using public JSON API (no authentication required)."""

    def get_source_name(self) -> str:
        return "reddit_public"

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
    """Collector for Reddit using PRAW (requires API credentials)."""

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

        logger.info(
            f"RedditPRAWCollector initialized with credentials: client_id={'***' if self.client_id else None}, client_secret={'***' if self.client_secret else None}, user_agent={self.user_agent}"
        )

    def get_source_name(self) -> str:
        return "reddit_praw"

    async def check_connectivity(self) -> Tuple[bool, str]:
        """Check Reddit API accessibility."""
        # First check basic internet connectivity
        has_internet, internet_msg = self.check_internet_connectivity(
            ["https://www.reddit.com"]
        )
        if not has_internet:
            return False, f"No internet connectivity: {internet_msg}"

        # Then check Reddit specifically
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.reddit.com/api/v1/access_token", timeout=5
                )
                # 401 is expected without auth
                if response.status_code in [200, 401]:
                    return True, "Reddit API endpoint accessible"
                else:
                    return (
                        False,
                        f"Reddit API returned unexpected status {response.status_code}",
                    )
        except Exception as e:
            return False, f"Reddit API not accessible: {str(e)}"

    async def check_authentication(self) -> Tuple[bool, str]:
        """Check if PRAW credentials are configured and valid."""
        if not self.client_id or not self.client_secret:
            missing_creds = []
            if not self.client_id:
                missing_creds.append("client_id")
            if not self.client_secret:
                missing_creds.append("client_secret")

            return (
                False,
                f"Reddit API credentials not configured: missing {', '.join(missing_creds)} (check Key Vault and environment variables)",
            )

        try:
            # Test authentication with Reddit API using asyncpraw
            import asyncpraw

            reddit = asyncpraw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
            )

            # Try to access a subreddit to verify credentials
            test_subreddit = await reddit.subreddit("test")
            # This will fail if credentials are invalid
            async for _ in test_subreddit.hot(limit=1):
                break

            await reddit.close()
            return (
                True,
                "Reddit API credentials valid (retrieved from Key Vault or environment)",
            )

        except ImportError:
            return False, "AsyncPRAW library not installed"
        except Exception as e:
            return (
                False,
                f"Reddit API authentication failed: {str(e)} (check Key Vault secrets: reddit-client-id, reddit-client-secret)",
            )

    async def collect_content(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect content using AsyncPRAW."""
        try:
            import asyncpraw

            reddit = asyncpraw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
            )

            items = []
            subreddits = params.get("subreddits", ["technology"])
            limit = params.get("limit", 10)
            sort_type = params.get("sort", "hot")  # hot, new, top, rising

            for subreddit_name in subreddits:
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

                async for post in posts:
                    # Convert post to our standard format
                    item = {
                        "id": f"reddit_{post.id}",
                        "source": "reddit",
                        "subreddit": subreddit_name,
                        "title": post.title,
                        "content": post.selftext or "",
                        "url": post.url,
                        "author": str(post.author) if post.author else "[deleted]",
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
                            "collected_at": datetime.now(timezone.utc).isoformat(),
                        },
                    }
                    items.append(item)

            await reddit.close()
            return items

        except ImportError:
            logger.warning("AsyncPRAW not available, falling back to public API")
            # Fallback to public API
            fallback_collector = RedditPublicCollector(self.config)
            return await fallback_collector.collect_content(params)
        except Exception as e:
            logger.error(f"Error collecting Reddit content with AsyncPRAW: {str(e)}")
            # Fallback to public API
            fallback_collector = RedditPublicCollector(self.config)
            return await fallback_collector.collect_content(params)

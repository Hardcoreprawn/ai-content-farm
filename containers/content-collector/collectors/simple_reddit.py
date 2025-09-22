"""
Simplified Reddit Collector - ACTIVE

CURRENT ARCHITECTURE: Simple, reliable Reddit content collection
Status: ACTIVE - Replaces complex reddit.py collector

Uses Reddit's public JSON API (no authentication required) with simple retry logic.
Designed for reliability and easy testing without complex adaptive strategies.

Features:
- Public Reddit JSON API access (no auth needed)
- Simple retry logic with exponential backoff
- Configurable subreddits, sort orders, and time filters
- Standardized item format
- Proper error handling and rate limiting

Simple, reliable Reddit content collection without complex adaptive strategies.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from collectors.simple_base import CollectorError, HTTPCollector

logger = logging.getLogger(__name__)


class SimpleRedditCollector(HTTPCollector):
    """Simplified Reddit collector using public JSON API."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}

        # Reddit-specific defaults
        config.setdefault("base_delay", 2.0)  # Reddit prefers slower requests
        config.setdefault("max_delay", 600.0)  # Up to 10 minutes
        config.setdefault("backoff_multiplier", 2.5)  # Aggressive backoff
        config.setdefault("max_items", 50)

        super().__init__(config)

        # Reddit configuration
        self.subreddits = config.get("subreddits", ["programming", "technology"])
        self.sort_order = config.get("sort", "hot")  # hot, new, top, rising
        # hour, day, week, month, year, all
        self.time_filter = config.get("time_filter", "day")

        logger.info(f"Configured Reddit collector for subreddits: {self.subreddits}")

    def get_source_name(self) -> str:
        return "reddit"

    async def collect_batch(self, **kwargs) -> List[Dict[str, Any]]:
        """Collect a batch of posts from configured subreddits."""

        # Override config with any provided parameters
        subreddits = kwargs.get("subreddits", self.subreddits)
        max_items = kwargs.get("max_items", self.max_items)
        sort_order = kwargs.get("sort", self.sort_order)
        time_filter = kwargs.get("time_filter", self.time_filter)

        all_items = []
        items_per_subreddit = max(1, max_items // len(subreddits))

        for subreddit in subreddits:
            try:
                logger.info(f"Collecting from r/{subreddit}")

                # Build Reddit JSON URL
                url = f"https://www.reddit.com/r/{subreddit}/{sort_order}.json"
                params = {
                    "limit": items_per_subreddit,
                    "t": time_filter,  # time filter for 'top' sort
                    "raw_json": 1,  # Get raw JSON without HTML encoding
                }

                # Add small delay to be respectful
                await asyncio.sleep(self.base_delay)

                # Fetch data
                data = await self.get_json(url, params=params)

                # Parse Reddit response
                posts = self._parse_reddit_response(data, subreddit)
                all_items.extend(posts)

                logger.info(f"Collected {len(posts)} posts from r/{subreddit}")

            except Exception as e:
                logger.warning(f"Failed to collect from r/{subreddit}: {e}")
                # Continue with other subreddits even if one fails
                continue

        # Limit total items
        return all_items[:max_items]

    def _parse_reddit_response(
        self, data: Dict[str, Any], subreddit: str
    ) -> List[Dict[str, Any]]:
        """Parse Reddit JSON response into standardized items."""
        items = []

        try:
            posts = data["data"]["children"]

            for post_wrapper in posts:
                post = post_wrapper["data"]

                # Skip pinned/stickied posts
                if post.get("stickied", False):
                    continue

                # Skip deleted/removed posts
                if post.get("removed_by_category") or post.get("author") == "[deleted]":
                    continue

                # Create standardized item
                item = self.standardize_reddit_post(post, subreddit)
                items.append(item)

        except KeyError as e:
            raise CollectorError(
                f"Unexpected Reddit API response format: missing {e}",
                source=self.get_source_name(),
                retryable=False,
            )

        return items

    def standardize_reddit_post(
        self, post: Dict[str, Any], subreddit: str
    ) -> Dict[str, Any]:
        """Convert Reddit post to standardized format."""

        # Extract content based on post type
        content = ""
        if post.get("selftext"):
            content = post["selftext"][:2000]  # Limit length
        elif post.get("url") and not post["url"].startswith("https://www.reddit.com/"):
            content = f"Link: {post['url']}"

        # Build permalink
        permalink = f"https://www.reddit.com{post['permalink']}"

        # Convert timestamp
        # Extract timestamp from created_utc and format for JSON serialization
        timestamp = datetime.fromtimestamp(
            post.get("created_utc", 0), tz=timezone.utc
        ).isoformat()

        return {
            "id": f"reddit_{post['id']}",
            "title": post.get("title", ""),
            "content": content,
            "url": permalink,
            "author": post.get("author", ""),
            "created_at": timestamp,
            "source": self.get_source_name(),
            "metadata": {
                "subreddit": subreddit,
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
                "upvote_ratio": post.get("upvote_ratio", 0.0),
                "post_type": "self" if post.get("selftext") else "link",
                "external_url": (
                    post.get("url")
                    if post.get("url")
                    and not post["url"].startswith("https://www.reddit.com/")
                    else None
                ),
                "flair": post.get("link_flair_text"),
                "nsfw": post.get("over_18", False),
                "spoiler": post.get("spoiler", False),
            },
        }

    async def health_check(self) -> tuple[bool, str]:
        """Check Reddit API accessibility."""
        try:
            # Try to fetch one post from r/programming (should always be available)
            url = "https://www.reddit.com/r/programming/hot.json"
            params = {"limit": 1, "raw_json": 1}

            data = await self.get_json(url, params=params)

            # Verify response structure
            if "data" not in data or "children" not in data["data"]:
                return False, "Reddit API returned unexpected format"

            return (
                True,
                f"Reddit API accessible - found {len(data['data']['children'])} posts",
            )

        except Exception as e:
            return False, f"Reddit API health check failed: {e}"


# For backward compatibility with existing code
class RedditPublicCollector(SimpleRedditCollector):
    """Alias for backward compatibility."""

    pass

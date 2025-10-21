"""
Pure async generator collection functions.

collect_reddit() and collect_mastodon() are async generators that yield
standardized items one at a time, with quality filtering and rate limiting.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)


class AsyncContextManagerHelper:
    """Helper to make async context manager from async generator."""

    def __init__(self, coro):
        self.coro = coro

    async def __aenter__(self):
        return await self.coro

    async def __aexit__(self, exc_type, exc, tb):
        pass


class _Response:
    """Wrapper to hold response status and json data."""

    def __init__(self, status: int, json_data: Any):
        self.status = status
        self._json_data = json_data

    async def json(self):
        """Return already-parsed JSON."""
        return self._json_data


async def _rate_limited_get_impl(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    delay: float = 2.0,
) -> Any:
    """Internal: Perform rate-limited GET and return response."""
    import aiohttp

    await asyncio.sleep(delay)

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            json_data = await resp.json()
            return _Response(resp.status, json_data)


def rate_limited_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    delay: float = 2.0,
) -> Any:
    """
    Rate-limited HTTP GET returning async context manager.

    Usage: async with rate_limited_get(...) as resp: data = await resp.json()

    Args:
        url: URL to fetch
        params: Query parameters
        headers: HTTP headers
        delay: Seconds to wait before request

    Returns:
        Async context manager yielding response with json() method
    """
    return AsyncContextManagerHelper(
        _rate_limited_get_impl(url, params, headers, delay)
    )


async def collect_reddit(
    subreddits: List[str],
    sort: str = "hot",
    time_filter: str = "day",
    min_score: int = 25,
    max_items: int = 25,
    delay: float = 2.0,
) -> AsyncIterator[Dict[str, Any]]:
    """
    Stream Reddit posts one at a time from subreddits.

    Uses public JSON API (no authentication required).
    Yields standardized items: id, title, content, source, url, collected_at, metadata.

    Args:
        subreddits: List of subreddit names (without r/)
        sort: Sort order (hot, new, top, rising)
        time_filter: Time filter for top sort (hour, day, week, month, year, all)
        min_score: Minimum upvote score to include
        max_items: Maximum total items to yield
        delay: Seconds between subreddit requests

    Yields:
        Standardized item dict
    """
    from collectors.standardize import standardize_reddit_item

    items_yielded = 0
    items_per_sub = max(1, max_items // len(subreddits))

    for subreddit in subreddits:
        if items_yielded >= max_items:
            break

        try:
            url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
            params = {
                "limit": items_per_sub,
                "t": time_filter,
                "raw_json": 1,
            }

            async with rate_limited_get(url, params=params, delay=delay) as resp:
                if resp.status != 200:
                    logger.warning(f"Reddit {subreddit}: HTTP {resp.status}")
                    continue

                data = await resp.json()

            # Parse posts from Reddit response
            posts = data.get("data", {}).get("children", [])

            for post in posts:
                if items_yielded >= max_items:
                    break

                raw = post.get("data", {})

                # Filter by score
                if raw.get("score", 0) < min_score:
                    continue

                # Skip over-18 content
                if raw.get("over_18"):
                    continue

                # Standardize and yield
                item = standardize_reddit_item(raw)
                items_yielded += 1
                yield item

        except Exception as e:
            logger.warning(f"Error collecting r/{subreddit}: {e}")
            continue


async def collect_mastodon(
    instance: str = "fosstodon.org",
    timeline: str = "public",
    min_boosts: int = 5,
    min_favourites: int = 10,
    max_items: int = 30,
    delay: float = 1.0,
) -> AsyncIterator[Dict[str, Any]]:
    """
    Stream Mastodon posts one at a time from instance.

    Uses public instance API (no authentication required).
    Yields standardized items: id, title, content, source, url, collected_at, metadata.

    Args:
        instance: Mastodon instance domain (fosstodon.org, hachyderm.io, etc)
        timeline: Timeline type (public, local)
        min_boosts: Minimum boost count to include
        min_favourites: Minimum favourite count to include
        max_items: Maximum total items to yield
        delay: Seconds between requests

    Yields:
        Standardized item dict
    """
    from collectors.standardize import standardize_mastodon_item

    items_yielded = 0

    try:
        url = f"https://{instance}/api/v1/timelines/{timeline}"
        params = {"limit": max_items * 2}  # Over-fetch to account for filtering

        async with rate_limited_get(url, params=params, delay=delay) as resp:
            if resp.status != 200:
                logger.warning(f"Mastodon {instance}: HTTP {resp.status}")
                return

            statuses = await resp.json()

        for status in statuses:
            if items_yielded >= max_items:
                break

            # Filter by engagement
            boosts = status.get("reblogs_count", 0)
            favourites = status.get("favourites_count", 0)

            if boosts < min_boosts or favourites < min_favourites:
                continue

            # Skip replies
            if status.get("in_reply_to_id"):
                continue

            # Standardize and yield
            item = standardize_mastodon_item(status, instance=instance)
            items_yielded += 1
            yield item

    except Exception as e:
        logger.warning(f"Error collecting from {instance}: {e}")

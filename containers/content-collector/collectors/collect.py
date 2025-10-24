"""
Pure async generator collection functions.

collect_reddit() and collect_mastodon() are async generators that yield
standardized items one at a time, with quality filtering and rate limiting.

NOTE: Reddit collection is currently DISABLED pending OAuth implementation.
Reddit's API policy requires OAuth authentication for all access as of 2023+.
The collect_reddit() function is preserved for future OAuth implementation.
Use collect_mastodon() for production content collection.
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

    ⚠️  CURRENTLY DISABLED - REQUIRES OAuth IMPLEMENTATION

    Reddit's API policy (2023+) requires OAuth authentication for all access.
    This function uses unauthenticated public JSON endpoints which will be
    blocked/throttled by Reddit. DO NOT USE in production until OAuth is added.

    Preserved for future implementation with proper OAuth token management.
    See: https://www.reddit.com/wiki/api (requires OAuth2)

    TODO: Add OAuth authentication before enabling Reddit collection
    - Implement OAuth token acquisition and refresh
    - Add proper User-Agent headers
    - Use https://oauth.reddit.com endpoints
    - Reference: Previous PRAW implementation in git history

    Uses public JSON API (no authentication - WILL BE BLOCKED).
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
    logger.warning(
        "⚠️  Reddit collection is DISABLED - requires OAuth implementation. "
        "This function will be blocked by Reddit API. "
        "Use collect_mastodon() instead for production content collection."
    )

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
    min_boosts: int = 0,
    min_favourites: int = 0,
    max_items: int = 30,
    delay: float = 1.0,
) -> AsyncIterator[Dict[str, Any]]:
    """
    Stream Mastodon posts one at a time from instance.

    Uses public instance API (no authentication required).
    Yields standardized items: id, title, content, source, url, collected_at, metadata.

    Args:
        instance: Mastodon instance domain (fosstodon.org, hachyderm.io, etc)
        timeline: Timeline type ('trending', 'public', 'local', etc)
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
        # Build URL based on timeline type
        if timeline == "trending":
            url = f"https://{instance}/api/v1/trends/statuses"
        else:
            url = f"https://{instance}/api/v1/timelines/{timeline}"
        params = {"limit": max_items * 2}  # Over-fetch to account for filtering

        logger.debug(f"Fetching from {instance}: {url} (params: {params})")

        async with rate_limited_get(url, params=params, delay=delay) as resp:
            if resp.status != 200:
                logger.warning(f"Mastodon {instance}: HTTP {resp.status}")
                return

            statuses = await resp.json()
            logger.debug(
                f"Mastodon {instance}: Got {len(statuses)} statuses, filtering with min_boosts={min_boosts}, min_favourites={min_favourites}"
            )

        filtered_out = 0
        for status in statuses:
            if items_yielded >= max_items:
                break

            # Filter by engagement
            boosts = status.get("reblogs_count", 0)
            favourites = status.get("favourites_count", 0)

            if boosts < min_boosts or favourites < min_favourites:
                filtered_out += 1
                logger.debug(
                    f"Mastodon {instance}: Filtered post (boosts={boosts}, favourites={favourites})"
                )
                continue

            # Skip replies
            if status.get("in_reply_to_id"):
                filtered_out += 1
                logger.debug(f"Mastodon {instance}: Skipped reply")
                continue

            # Standardize and yield
            item = standardize_mastodon_item(status, instance=instance)
            items_yielded += 1
            logger.debug(f"Mastodon {instance}: Yielded item {item.get('id')}")
            yield item

        logger.info(
            f"Mastodon {instance}: Complete - yielded {items_yielded}, filtered {filtered_out}"
        )

    except Exception as e:
        logger.error(
            f"Error collecting from {instance}: {e}",
            exc_info=True,
        )

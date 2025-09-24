"""
Web Collection Strategies

Collection methods for different web content sources including
API-based collection (HackerNews) and RSS-based collection.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import feedparser

from .web_standardizers import (
    GenericRSSStandardizer,
    HackerNewsStandardizer,
    LobstersStandardizer,
    SlashdotStandardizer,
)

logger = logging.getLogger(__name__)


class APICollectionStrategy:
    """Strategy for API-based content collection."""

    def __init__(self, http_collector):
        """Initialize with reference to HTTP collector."""
        self.http_collector = http_collector

    async def collect_hackernews(
        self, max_items: int = 20, story_type: str = "topstories"
    ) -> List[Dict[str, Any]]:
        """
        Collect content from HackerNews API.

        Args:
            max_items: Maximum number of items to collect
            story_type: Type of stories (topstories, newstories, beststories)

        Returns:
            List of standardized content items
        """
        items = []

        try:
            # Get list of story IDs
            stories_url = f"https://hacker-news.firebaseio.com/v0/{story_type}.json"
            story_ids_response = await self.http_collector._make_request(stories_url)

            if not story_ids_response:
                logger.warning("Failed to fetch HackerNews story IDs")
                return items

            story_ids = story_ids_response.get("data", [])[:max_items]

            # Fetch individual stories with concurrency control
            semaphore = asyncio.Semaphore(5)  # Limit concurrent requests

            async def fetch_story(story_id):
                async with semaphore:
                    story_url = (
                        f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                    )
                    return await self.http_collector._make_request(story_url)

            # Fetch all stories concurrently
            story_responses = await asyncio.gather(
                *[fetch_story(story_id) for story_id in story_ids],
                return_exceptions=True,
            )

            # Process responses
            for response in story_responses:
                if isinstance(response, Exception):
                    logger.warning(f"Failed to fetch story: {response}")
                    continue

                if not response or "data" not in response:
                    continue

                story_data = response["data"]
                if not story_data or story_data.get("type") != "story":
                    continue

                # Standardize the story
                standardized = HackerNewsStandardizer.standardize_story(story_data)
                if standardized and standardized.get("title"):
                    items.append(standardized)

        except Exception as e:
            logger.error(f"Error collecting HackerNews content: {e}")

        logger.info(f"Collected {len(items)} items from HackerNews API")
        return items


class RSSCollectionStrategy:
    """Strategy for RSS-based content collection."""

    def __init__(self, http_collector):
        """Initialize with reference to HTTP collector."""
        self.http_collector = http_collector

    async def collect_from_rss(
        self, urls: List[str], max_items_per_feed: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Collect content from RSS feeds.

        Args:
            urls: List of RSS feed URLs
            max_items_per_feed: Maximum items to collect per feed

        Returns:
            List of standardized content items
        """
        all_items = []

        for url in urls:
            try:
                items = await self._collect_single_rss_feed(url, max_items_per_feed)
                all_items.extend(items)

                # Add delay between feeds to be respectful
                if len(urls) > 1:
                    await asyncio.sleep(1.0)

            except Exception as e:
                logger.error(f"Error collecting from RSS feed {url}: {e}")
                continue

        logger.info(
            f"Collected {len(all_items)} total items from {len(urls)} RSS feeds"
        )
        return all_items

    async def _collect_single_rss_feed(
        self, url: str, max_items: int
    ) -> List[Dict[str, Any]]:
        """
        Collect content from a single RSS feed.

        Args:
            url: RSS feed URL
            max_items: Maximum items to collect

        Returns:
            List of standardized content items
        """
        items = []

        try:
            # Fetch RSS content
            response = await self.http_collector._make_request(url, expect_json=False)

            if not response or "content" not in response:
                logger.warning(f"Failed to fetch RSS feed: {url}")
                return items

            # Parse RSS content
            feed = feedparser.parse(response["content"])

            if not feed.entries:
                logger.warning(f"No entries found in RSS feed: {url}")
                return items

            # Process entries
            entries = feed.entries[:max_items]
            source_name = self._determine_source_name(url, feed)

            for entry in entries:
                try:
                    standardized = self._standardize_rss_entry(entry, source_name, url)
                    if standardized and standardized.get("title"):
                        items.append(standardized)
                except Exception as e:
                    logger.warning(f"Error processing RSS entry: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error collecting RSS feed {url}: {e}")

        logger.info(f"Collected {len(items)} items from RSS feed: {url}")
        return items

    def _determine_source_name(self, url: str, feed) -> str:
        """Determine the source name from URL or feed metadata."""
        # Check for known sites using secure URL parsing
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url.lower())

            # Check for legitimate domains only
            if parsed.netloc in [
                "news.ycombinator.com",
                "ycombinator.com",
            ] or parsed.netloc.endswith(".ycombinator.com"):
                return "hackernews"
            elif parsed.netloc == "lobste.rs":
                return "lobsters"
            elif parsed.netloc in ["slashdot.org"] or parsed.netloc.endswith(
                ".slashdot.org"
            ):
                return "slashdot"
        except Exception:
            pass

        # Try to extract from feed title or URL
        if hasattr(feed, "feed") and hasattr(feed.feed, "title"):
            title = feed.feed.title.lower()
            if "hacker" in title or "ycombinator" in title:
                return "hackernews"
            elif "lobsters" in title:
                return "lobsters"
            elif "slashdot" in title:
                return "slashdot"

        # Default to generic
        return "rss"

    def _standardize_rss_entry(
        self, entry: Any, source_name: str, url: str
    ) -> Dict[str, Any]:
        """
        Standardize RSS entry based on source type.

        Args:
            entry: RSS entry object
            source_name: Name of the source
            url: Original RSS URL

        Returns:
            Standardized content item
        """
        if source_name == "lobsters":
            return LobstersStandardizer.standardize_entry(entry)
        elif source_name == "slashdot":
            return SlashdotStandardizer.standardize_entry(entry)
        else:
            return GenericRSSStandardizer.standardize_entry(entry, source_name)

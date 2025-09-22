"""
Simplified RSS Collector - ACTIVE

CURRENT ARCHITECTURE: Simple, reliable RSS feed content collection
Status: ACTIVE - Provides RSS collection for content templates

Uses feedparser library for RSS/Atom feed parsing with simple retry logic.
Designed for reliability and easy testing without complex adaptive strategies.

Features:
- RSS/Atom feed parsing with feedparser
- Simple retry logic with exponential backoff
- Support for both feed_urls and websites config formats
- HTML content stripping and standardized format
- Proper error handling and rate limiting
- Flexible configuration matching collection templates

Simple, reliable RSS feed collection from multiple sources.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import feedparser
from collectors.simple_base import CollectorError, HTTPCollector

logger = logging.getLogger(__name__)


class SimpleRSSCollector(HTTPCollector):
    """Simplified RSS collector using feedparser library."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}

        # RSS-specific defaults
        # RSS feeds are usually more tolerant
        config.setdefault("base_delay", 1.0)
        config.setdefault("max_delay", 180.0)  # 3 minutes max
        config.setdefault("backoff_multiplier", 2.0)
        config.setdefault("max_items", 30)

        super().__init__(config)

        # RSS configuration - support both formats from collection templates
        self.feed_urls = config.get("feed_urls", [])
        self.websites = config.get("websites", [])

        # Combine both into a single list for processing
        self.all_feeds = list(self.feed_urls) + list(self.websites)

        if not self.all_feeds:
            # Default feeds if none provided
            self.all_feeds = [
                "https://feeds.feedburner.com/TechCrunch",
                "https://www.wired.com/feed/rss",
                "https://arstechnica.com/feed/",
            ]

        # Additional RSS settings
        self.published_within_hours = config.get("published_within_hours", 48)

        logger.info(f"Configured RSS collector for {len(self.all_feeds)} feeds")

    def get_source_name(self) -> str:
        return "rss"

    async def collect_batch(self, **kwargs) -> List[Dict[str, Any]]:
        """Collect a batch of articles from configured RSS feeds."""

        # Override config with any provided parameters
        feed_urls = kwargs.get("feed_urls", self.feed_urls)
        websites = kwargs.get("websites", self.websites)
        max_items = kwargs.get("max_items", self.max_items)
        published_within_hours = kwargs.get(
            "published_within_hours", self.published_within_hours
        )

        # Combine all feed sources
        all_feeds = list(feed_urls) + list(websites)
        if not all_feeds:
            all_feeds = self.all_feeds

        all_items = []
        items_per_feed = max(1, max_items // len(all_feeds)) if all_feeds else max_items

        for feed_url in all_feeds:
            try:
                logger.info(f"Collecting from RSS feed: {feed_url}")

                # Add small delay to be respectful
                await asyncio.sleep(self.base_delay)

                # Fetch RSS data
                articles = await self._collect_from_feed(
                    feed_url, items_per_feed, published_within_hours
                )
                all_items.extend(articles)

                logger.info(f"Collected {len(articles)} articles from {feed_url}")

            except Exception as e:
                logger.warning(f"Failed to collect from RSS feed {feed_url}: {e}")
                # Continue with other feeds even if one fails
                continue

        # Limit total items and remove duplicates
        return self._deduplicate_items(all_items)[:max_items]

    async def _collect_from_feed(
        self, feed_url: str, limit: int, published_within_hours: int
    ) -> List[Dict[str, Any]]:
        """Collect articles from a single RSS feed."""

        try:
            # Fetch the RSS feed
            response = await self.get_response(feed_url)

            # Parse RSS feed with feedparser
            feed = feedparser.parse(response.text)

            if feed.bozo and feed.bozo_exception:
                logger.warning(
                    f"RSS feed parse warning for {feed_url}: {feed.bozo_exception}"
                )

            articles = []
            cutoff_time = datetime.now(timezone.utc).timestamp() - (
                published_within_hours * 3600
            )

            # Get extra to account for filtering
            for entry in feed.entries[: limit * 2]:
                try:
                    # Check if article is recent enough
                    if not self._is_recent_enough(entry, cutoff_time):
                        continue

                    # Convert to standardized format
                    article = self._standardize_rss_entry(entry, feed, feed_url)
                    articles.append(article)

                    if len(articles) >= limit:
                        break

                except Exception as e:
                    logger.warning(f"Failed to process RSS entry from {feed_url}: {e}")
                    continue

            return articles

        except Exception as e:
            raise CollectorError(
                f"Failed to collect from RSS feed {feed_url}: {e}",
                source=self.get_source_name(),
                retryable=True,
            )

    def _is_recent_enough(self, entry: Any, cutoff_time: float) -> bool:
        """Check if RSS entry is recent enough based on configuration."""

        # Try different timestamp fields
        published = (
            entry.get("published_parsed")
            or entry.get("updated_parsed")
            or entry.get("created_parsed")
        )

        if not published:
            # If no timestamp, assume it's recent
            return True

        try:
            entry_time = datetime(*published[:6], tzinfo=timezone.utc).timestamp()
            return entry_time >= cutoff_time
        except (ValueError, TypeError):
            # If timestamp parsing fails, include the entry
            return True

    def _standardize_rss_entry(
        self, entry: Any, feed: Any, feed_url: str
    ) -> Dict[str, Any]:
        """Convert RSS entry to standardized format."""

        # Extract basic information
        title = entry.get("title", "No title").strip()
        link = entry.get("link", "").strip()

        # Extract and clean content
        content = ""
        if hasattr(entry, "summary"):
            content = entry.summary
        elif hasattr(entry, "description"):
            content = entry.description
        elif hasattr(entry, "content"):
            # Handle multiple content types
            if isinstance(entry.content, list) and entry.content:
                content = entry.content[0].value
            else:
                content = str(entry.content)

        # Clean HTML tags from content
        content = self._clean_html_content(content)

        # Extract author
        author = entry.get("author", "")
        if not author and hasattr(feed, "feed") and hasattr(feed.feed, "title"):
            author = feed.feed.title

        # Extract and format timestamp
        published = (
            entry.get("published_parsed")
            or entry.get("updated_parsed")
            or entry.get("created_parsed")
        )

        if published:
            try:
                created_at = datetime(*published[:6], tzinfo=timezone.utc).isoformat()
            except (ValueError, TypeError):
                created_at = datetime.now(timezone.utc).isoformat()
        else:
            created_at = datetime.now(timezone.utc).isoformat()

        # Generate unique ID
        item_id = self._generate_item_id(link, title, feed_url)

        # Extract tags/categories
        tags = []
        if hasattr(entry, "tags") and entry.tags:
            tags = [tag.get("term", "") for tag in entry.tags if tag.get("term")]

        # Get feed metadata
        feed_title = ""
        if hasattr(feed, "feed") and hasattr(feed.feed, "title"):
            feed_title = feed.feed.title

        return {
            "id": item_id,
            "title": title,
            "content": content[:2000],  # Limit content length
            "url": link,
            "author": author,
            "created_at": created_at,
            "source": self.get_source_name(),
            "metadata": {
                "feed_url": feed_url,
                "feed_title": feed_title,
                "tags": tags,
                "content_type": "article",
                "word_count": len(content.split()) if content else 0,
                "has_content": bool(content.strip()),
                "original_published": entry.get("published", ""),
                "entry_id": entry.get("id", ""),
            },
        }

    def _clean_html_content(self, content: str) -> str:
        """Clean HTML tags and normalize whitespace from content."""
        if not content:
            return ""

        # Remove HTML tags
        content = re.sub(r"<[^>]+>", "", content)

        # Normalize whitespace
        content = re.sub(r"\s+", " ", content)

        # Remove common HTML entities
        content = content.replace("&nbsp;", " ")
        content = content.replace("&amp;", "&")
        content = content.replace("&lt;", "<")
        content = content.replace("&gt;", ">")
        content = content.replace("&quot;", '"')
        content = content.replace("&#39;", "'")

        return content.strip()

    def _generate_item_id(self, link: str, title: str, feed_url: str) -> str:
        """Generate a unique ID for the RSS item."""

        if link:
            # Use URL as basis for ID
            url_hash = abs(hash(link)) % 1000000
            return f"rss_{url_hash}"
        elif title:
            # Use title as basis for ID
            title_hash = abs(hash(title)) % 1000000
            return f"rss_title_{title_hash}"
        else:
            # Use feed URL and timestamp
            feed_hash = abs(hash(feed_url)) % 1000000
            timestamp = int(datetime.now(timezone.utc).timestamp())
            return f"rss_feed_{feed_hash}_{timestamp}"

    def _deduplicate_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate items based on URL and title."""

        seen_urls = set()
        seen_titles = set()
        unique_items = []

        for item in items:
            url = item.get("url", "").strip()
            title = item.get("title", "").strip().lower()

            # Skip if we've seen this URL or title
            if url and url in seen_urls:
                continue
            if title and title in seen_titles:
                continue

            # Add to seen sets
            if url:
                seen_urls.add(url)
            if title:
                seen_titles.add(title)

            unique_items.append(item)

        return unique_items

    async def health_check(self) -> tuple[bool, str]:
        """Check RSS feed accessibility."""

        if not self.all_feeds:
            return False, "No RSS feeds configured"

        try:
            # Test the first feed
            test_feed = self.all_feeds[0]
            response = await self.get_response(test_feed)

            # Try to parse it
            feed = feedparser.parse(response.text)

            if feed.bozo and feed.bozo_exception:
                return False, f"RSS feed parse error: {feed.bozo_exception}"

            entry_count = len(feed.entries) if hasattr(feed, "entries") else 0

            return (
                True,
                f"RSS collector healthy - test feed has {entry_count} entries",
            )

        except Exception as e:
            return False, f"RSS collector health check failed: {e}"

"""
Simplified Web Collector - ACTIVE

CURRENT ARCHITECTURE: Simple, reliable web content collection
Status: ACTIVE - Provides web scraping for specific sites

Handles structured content extraction from specific websites like Hacker News,
Lobsters, and Slashdot using their public APIs or RSS feeds where available.
Designed for reliability and easy testing without complex adaptive strategies.

Features:
- Site-specific extraction logic for popular tech sites
- Public API usage where available (Hacker News)
- RSS fallback for sites that provide feeds
- Simple retry logic with exponential backoff
- Standardized format across all sites
- Proper error handling and rate limiting

Simple, reliable web content collection from curated tech sites.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import feedparser
from collectors.simple_base import CollectorError, HTTPCollector

logger = logging.getLogger(__name__)


class SimpleWebCollector(HTTPCollector):
    """Simplified web collector for specific tech sites."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}

        # Web-specific defaults
        config.setdefault("base_delay", 1.5)  # Be respectful to websites
        config.setdefault("max_delay", 300.0)  # 5 minutes max
        config.setdefault("backoff_multiplier", 2.0)
        config.setdefault("max_items", 20)

        super().__init__(config)

        # Web configuration
        self.websites = config.get(
            "websites",
            [
                "https://news.ycombinator.com",
                "https://lobste.rs",
                "https://slashdot.org",
            ],
        )

        # Criteria configuration
        self.min_points = config.get("min_points", 50)

        # Site-specific configurations
        self.site_configs = {
            "news.ycombinator.com": {
                "name": "Hacker News",
                "method": "api",
                "api_url": "https://hacker-news.firebaseio.com/v0",
                "story_types": ["topstories", "beststories"],
                "min_score": self.min_points,
            },
            "lobste.rs": {
                "name": "Lobsters",
                "method": "rss",
                "rss_url": "https://lobste.rs/rss",
                "min_score": self.min_points,
            },
            "slashdot.org": {
                "name": "Slashdot",
                "method": "rss",
                "rss_url": "http://rss.slashdot.org/Slashdot/slashdot",
                "min_score": 0,  # Slashdot doesn't have points system
            },
        }

        logger.info(f"Configured web collector for {len(self.websites)} websites")

    def get_source_name(self) -> str:
        return "web"

    async def collect_batch(self, **kwargs) -> List[Dict[str, Any]]:
        """Collect a batch of articles from configured websites."""

        # Override config with any provided parameters
        websites = kwargs.get("websites", self.websites)
        max_items = kwargs.get("max_items", self.max_items)
        min_points = kwargs.get("min_points", self.min_points)

        all_items = []
        items_per_site = max(1, max_items // len(websites)) if websites else max_items

        for website_url in websites:
            try:
                logger.info(f"Collecting from website: {website_url}")

                # Parse domain from URL
                domain = urlparse(website_url).netloc

                # Get site config
                site_config = self.site_configs.get(domain)
                if not site_config:
                    logger.warning(f"No configuration found for domain: {domain}")
                    continue

                # Add delay to be respectful
                await asyncio.sleep(self.base_delay)

                # Collect based on site method
                if site_config["method"] == "api":
                    articles = await self._collect_via_api(
                        domain, site_config, items_per_site, min_points
                    )
                elif site_config["method"] == "rss":
                    articles = await self._collect_via_rss(
                        domain, site_config, items_per_site, min_points
                    )
                else:
                    logger.warning(
                        f"Unknown collection method for {domain}: {site_config['method']}"
                    )
                    continue

                all_items.extend(articles)
                logger.info(f"Collected {len(articles)} articles from {domain}")

            except Exception as e:
                logger.warning(f"Failed to collect from website {website_url}: {e}")
                # Continue with other websites even if one fails
                continue

        # Limit total items and remove duplicates
        return self._deduplicate_items(all_items)[:max_items]

    async def _collect_via_api(
        self, domain: str, site_config: Dict[str, Any], limit: int, min_points: int
    ) -> List[Dict[str, Any]]:
        """Collect content via API (e.g., Hacker News)."""

        if domain == "news.ycombinator.com":
            return await self._collect_hackernews(site_config, limit, min_points)
        else:
            logger.warning(f"API collection not implemented for {domain}")
            return []

    async def _collect_hackernews(
        self, site_config: Dict[str, Any], limit: int, min_points: int
    ) -> List[Dict[str, Any]]:
        """Collect from Hacker News API."""

        try:
            api_url = site_config["api_url"]

            # Get top story IDs
            response = await self.get_json(f"{api_url}/topstories.json")
            # Get extra to account for filtering
            story_ids = response[: limit * 3]

            articles = []

            # Fetch individual stories
            for story_id in story_ids[:50]:  # Limit API calls
                try:
                    story_data = await self.get_json(f"{api_url}/item/{story_id}.json")

                    # Skip if not a story or deleted
                    if (
                        not story_data
                        or story_data.get("type") != "story"
                        or story_data.get("deleted")
                    ):
                        continue

                    # Check score threshold
                    score = story_data.get("score", 0)
                    if score < min_points:
                        continue

                    # Convert to standardized format
                    article = self._standardize_hackernews_story(story_data)
                    articles.append(article)

                    if len(articles) >= limit:
                        break

                    # Small delay between API calls
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.warning(f"Failed to fetch HN story {story_id}: {e}")
                    continue

            return articles

        except Exception as e:
            raise CollectorError(
                f"Failed to collect from Hacker News: {e}",
                source=self.get_source_name(),
                retryable=True,
            )

    async def _collect_via_rss(
        self, domain: str, site_config: Dict[str, Any], limit: int, min_points: int
    ) -> List[Dict[str, Any]]:
        """Collect content via RSS feed."""

        try:
            rss_url = site_config["rss_url"]

            # Fetch RSS feed
            response = await self.get_response(rss_url)

            # Parse RSS feed
            feed = feedparser.parse(response.text)

            if feed.bozo and feed.bozo_exception:
                logger.warning(
                    f"RSS feed parse warning for {domain}: {feed.bozo_exception}"
                )

            articles = []

            for entry in feed.entries[:limit]:
                try:
                    # Convert to standardized format based on domain
                    if domain == "lobste.rs":
                        article = self._standardize_lobsters_entry(entry, site_config)
                    elif domain == "slashdot.org":
                        article = self._standardize_slashdot_entry(entry, site_config)
                    else:
                        article = self._standardize_generic_rss_entry(
                            entry, site_config, domain
                        )

                    # Check if it meets criteria (if applicable)
                    if article and self._meets_criteria(
                        article, min_points, site_config
                    ):
                        articles.append(article)

                except Exception as e:
                    logger.warning(f"Failed to process RSS entry from {domain}: {e}")
                    continue

            return articles

        except Exception as e:
            raise CollectorError(
                f"Failed to collect from {domain} RSS: {e}",
                source=self.get_source_name(),
                retryable=True,
            )

    def _standardize_hackernews_story(self, story: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Hacker News story to standardized format."""

        # Format timestamp
        timestamp = story.get("time", 0)
        created_at = (
            datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
            if timestamp
            else datetime.now(timezone.utc).isoformat()
        )

        # Build URL
        url = story.get(
            "url", f"https://news.ycombinator.com/item?id={story.get('id')}"
        )

        # Extract text content if available
        content = story.get("text", "")
        if content:
            content = self._clean_html_content(content)

        return {
            "id": f"hn_{story.get('id')}",
            "title": story.get("title", ""),
            "content": content,
            "url": url,
            "author": story.get("by", ""),
            "created_at": created_at,
            "source": self.get_source_name(),
            "metadata": {
                "site": "news.ycombinator.com",
                "site_name": "Hacker News",
                "score": story.get("score", 0),
                "num_comments": story.get("descendants", 0),
                "content_type": "story",
                "story_type": story.get("type", "story"),
                "hn_id": story.get("id"),
                "external_url": (
                    story.get("url")
                    if story.get("url")
                    and not story.get("url").startswith("https://news.ycombinator.com/")
                    else None
                ),
            },
        }

    def _standardize_lobsters_entry(
        self, entry: Any, site_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert Lobsters RSS entry to standardized format."""

        # Extract basic info
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        content = entry.get("summary", entry.get("description", ""))

        # Clean content
        content = self._clean_html_content(content)

        # Extract timestamp
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if published:
            created_at = datetime(*published[:6], tzinfo=timezone.utc).isoformat()
        else:
            created_at = datetime.now(timezone.utc).isoformat()

        # Try to extract score from content (if available in description)
        score = self._extract_score_from_content(content)

        return {
            "id": f"lobsters_{abs(hash(link)) % 1000000}",
            "title": title,
            "content": content[:1000],  # Limit content length
            "url": link,
            "author": entry.get("author", ""),
            "created_at": created_at,
            "source": self.get_source_name(),
            "metadata": {
                "site": "lobste.rs",
                "site_name": "Lobsters",
                "score": score,
                "num_comments": 0,  # Not available in RSS
                "content_type": "story",
                "tags": self._extract_tags_from_entry(entry),
            },
        }

    def _standardize_slashdot_entry(
        self, entry: Any, site_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert Slashdot RSS entry to standardized format."""

        # Extract basic info
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        content = entry.get("summary", entry.get("description", ""))

        # Clean content
        content = self._clean_html_content(content)

        # Extract timestamp
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if published:
            created_at = datetime(*published[:6], tzinfo=timezone.utc).isoformat()
        else:
            created_at = datetime.now(timezone.utc).isoformat()

        return {
            "id": f"slashdot_{abs(hash(link)) % 1000000}",
            "title": title,
            "content": content[:1000],  # Limit content length
            "url": link,
            "author": entry.get("author", ""),
            "created_at": created_at,
            "source": self.get_source_name(),
            "metadata": {
                "site": "slashdot.org",
                "site_name": "Slashdot",
                "score": 0,  # Slashdot doesn't have points
                "num_comments": 0,  # Not available in RSS
                "content_type": "story",
                "department": self._extract_slashdot_department(content),
            },
        }

    def _standardize_generic_rss_entry(
        self, entry: Any, site_config: Dict[str, Any], domain: str
    ) -> Dict[str, Any]:
        """Convert generic RSS entry to standardized format."""

        # Extract basic info
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        content = entry.get("summary", entry.get("description", ""))

        # Clean content
        content = self._clean_html_content(content)

        # Extract timestamp
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if published:
            created_at = datetime(*published[:6], tzinfo=timezone.utc).isoformat()
        else:
            created_at = datetime.now(timezone.utc).isoformat()

        return {
            "id": f"web_{domain.replace('.', '_')}_{abs(hash(link)) % 1000000}",
            "title": title,
            "content": content[:1000],  # Limit content length
            "url": link,
            "author": entry.get("author", ""),
            "created_at": created_at,
            "source": self.get_source_name(),
            "metadata": {
                "site": domain,
                "site_name": site_config.get("name", domain),
                "score": 0,
                "num_comments": 0,
                "content_type": "article",
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

    def _extract_score_from_content(self, content: str) -> int:
        """Try to extract score/points from content text."""
        if not content:
            return 0

        # Look for patterns like "42 points" or "score: 42"
        patterns = [
            r"(\d+)\s+points?",
            r"score:\s*(\d+)",
            r"(\d+)\s+votes?",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue

        return 0

    def _extract_tags_from_entry(self, entry: Any) -> List[str]:
        """Extract tags from RSS entry."""
        tags = []

        if hasattr(entry, "tags") and entry.tags:
            for tag in entry.tags:
                if hasattr(tag, "term") and tag.term:
                    tags.append(tag.term)

        return tags

    def _extract_slashdot_department(self, content: str) -> str:
        """Extract Slashdot department from content."""
        if not content:
            return ""

        # Look for department pattern "from the something-something dept."
        match = re.search(r"from the ([^d]+) dept\.", content, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return ""

    def _meets_criteria(
        self, article: Dict[str, Any], min_points: int, site_config: Dict[str, Any]
    ) -> bool:
        """Check if article meets minimum criteria."""

        # Check minimum score if applicable
        score = article.get("metadata", {}).get("score", 0)
        required_score = site_config.get("min_score", min_points)

        return score >= required_score

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
        """Check web collector accessibility."""

        if not self.websites:
            return False, "No websites configured"

        try:
            # Test Hacker News API as it's most reliable
            test_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            response = await self.get_json(test_url)

            if not response or not isinstance(response, list):
                return False, "Hacker News API returned unexpected format"

            return (
                True,
                f"Web collector healthy - HN API returned {len(response)} stories",
            )

        except Exception as e:
            return False, f"Web collector health check failed: {e}"

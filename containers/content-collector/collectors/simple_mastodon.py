"""
Simplified Mastodon Collector - ACTIVE

CURRENT ARCHITECTURE: Simple, reliable Mastodon content collection
Status: ACTIVE - Replaces complex mastodon.py collector

Uses Mastodon's public API endpoints for hashtags and public timelines.
Designed for reliability and easy testing without complex adaptive strategies.

Features:
- Public Mastodon API access (no auth needed)
- Simple retry logic with exponential backoff
- Configurable instances, hashtags, and collection types
- HTML content stripping and standardized format
- Proper error handling and rate limiting

Simple, reliable Mastodon content collection from public timelines and hashtags.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from collectors.simple_base import CollectorError, HTTPCollector

logger = logging.getLogger(__name__)


class SimpleMastodonCollector(HTTPCollector):
    """Simplified Mastodon collector using public API endpoints."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}

        # Mastodon-specific defaults
        # Mastodon is more lenient than Reddit
        config.setdefault("base_delay", 1.5)
        config.setdefault("max_delay", 300.0)
        config.setdefault("backoff_multiplier", 2.0)
        config.setdefault("max_items", 40)

        super().__init__(config)

        # Mastodon configuration
        self.instances = config.get("instances", ["mastodon.social", "hachyderm.io"])
        self.hashtags = config.get(
            "hashtags", ["technology", "programming", "opensource"]
        )
        self.collection_types = config.get(
            "types", ["hashtags"]
        )  # hashtags, public_timeline

        logger.info(f"Configured Mastodon collector for instances: {self.instances}")

    def get_source_name(self) -> str:
        return "mastodon"

    async def collect_batch(self, **kwargs) -> List[Dict[str, Any]]:
        """Collect a batch of posts from configured Mastodon instances."""

        # Override config with any provided parameters
        instances = kwargs.get("instances", self.instances)
        hashtags = kwargs.get("hashtags", self.hashtags)
        collection_types = kwargs.get("types", self.collection_types)
        max_items = kwargs.get("max_items", self.max_items)

        all_items = []
        items_per_source = max(1, max_items // (len(instances) * len(collection_types)))

        for instance in instances:
            for collection_type in collection_types:
                try:
                    if collection_type == "hashtags":
                        for hashtag in hashtags:
                            items = await self._collect_hashtag(
                                instance, hashtag, items_per_source
                            )
                            all_items.extend(items)
                    elif collection_type == "public_timeline":
                        items = await self._collect_public_timeline(
                            instance, items_per_source
                        )
                        all_items.extend(items)

                except Exception as e:
                    logger.warning(
                        f"Failed to collect {collection_type} from {instance}: {e}"
                    )
                    # Continue with other sources even if one fails
                    continue

        # Remove duplicates by ID and limit total items
        seen_ids = set()
        unique_items = []
        for item in all_items:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                unique_items.append(item)

        return unique_items[:max_items]

    async def _collect_hashtag(
        self, instance: str, hashtag: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Collect posts from a specific hashtag on an instance."""

        logger.info(f"Collecting #{hashtag} from {instance}")

        # Build Mastodon hashtag URL
        url = f"https://{instance}/api/v1/timelines/tag/{hashtag}"
        params = {
            "limit": limit,
            "only_media": "false",
            "local": "false",  # Include federated posts
        }

        # Add delay to be respectful
        await asyncio.sleep(self.base_delay)

        # Fetch data
        posts = await self.get_json(url, params=params)

        # Parse response
        if not isinstance(posts, list):
            raise CollectorError(
                f"Expected list of posts from {instance}, got {type(posts)}",
                source=self.get_source_name(),
                retryable=False,
            )

        items = []
        for post in posts:
            item = self.standardize_mastodon_post(post, instance, f"#{hashtag}")
            items.append(item)

        logger.info(f"Collected {len(items)} posts for #{hashtag} from {instance}")
        return items

    async def _collect_public_timeline(
        self, instance: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Collect posts from public timeline of an instance."""

        logger.info(f"Collecting public timeline from {instance}")

        # Build Mastodon public timeline URL
        url = f"https://{instance}/api/v1/timelines/public"
        params = {
            "limit": limit,
            "only_media": "false",
            "local": "true",  # Only local posts for public timeline
        }

        # Add delay to be respectful
        await asyncio.sleep(self.base_delay)

        # Fetch data
        posts = await self.get_json(url, params=params)

        # Parse response
        if not isinstance(posts, list):
            raise CollectorError(
                f"Expected list of posts from {instance}, got {type(posts)}",
                source=self.get_source_name(),
                retryable=False,
            )

        items = []
        for post in posts:
            item = self.standardize_mastodon_post(post, instance, "public")
            items.append(item)

        logger.info(f"Collected {len(items)} posts from {instance} public timeline")
        return items

    def standardize_mastodon_post(
        self, post: Dict[str, Any], instance: str, source_detail: str
    ) -> Dict[str, Any]:
        """Convert Mastodon post to standardized format."""

        # Extract text content (strip HTML)
        content = self._strip_html(post.get("content", ""))

        # Get account info
        account = post.get("account", {})
        author = account.get("display_name") or account.get("username", "")

        # Parse timestamp
        created_at = post.get("created_at", datetime.now(timezone.utc).isoformat())

        # Build post URL
        username = account.get("username", "unknown")
        post_id = post.get("id", "")
        url = post.get(
            "url",
            f"https://{instance}/@{username}/statuses/{post_id}",
        )

        return {
            "id": f"mastodon_{instance}_{post.get('id', '')}",
            # Use first part as title
            "title": content[:100] + "..." if len(content) > 100 else content,
            "content": content,
            "url": url,
            "author": author,
            "created_at": created_at,
            "source": self.get_source_name(),
            "metadata": {
                "instance": instance,
                "source_detail": source_detail,
                "username": account.get("username", ""),
                "account_url": account.get("url", ""),
                "favourites_count": post.get("favourites_count", 0),
                "reblogs_count": post.get("reblogs_count", 0),
                "replies_count": post.get("replies_count", 0),
                "language": post.get("language"),
                "sensitive": post.get("sensitive", False),
                "tags": [tag.get("name") for tag in post.get("tags", [])],
                "media_attachments": len(post.get("media_attachments", [])),
                "visibility": post.get("visibility", "public"),
            },
        }

    def _strip_html(self, html_content: str) -> str:
        """Simple HTML stripping for Mastodon content."""
        import re

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html_content)

        # Decode common HTML entities
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&amp;", "&")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    async def health_check(self) -> tuple[bool, str]:
        """Check Mastodon instance accessibility."""
        try:
            # Try to fetch instance info from first configured instance
            if not self.instances:
                return False, "No Mastodon instances configured"

            instance = self.instances[0]
            url = f"https://{instance}/api/v1/instance"

            data = await self.get_json(url)

            # Verify response structure
            if "title" not in data:
                msg = f"Mastodon instance {instance} returned unexpected format"
                return False, msg

            title = data.get("title", "Unknown")
            return (
                True,
                f"Mastodon instance {instance} accessible - {title}",
            )

        except Exception as e:
            return False, f"Mastodon health check failed: {e}"


# For backward compatibility with existing code
class MastodonCollector(SimpleMastodonCollector):
    """Alias for backward compatibility."""

    pass

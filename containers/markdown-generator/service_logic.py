"""Core business logic for markdown generator service."""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from libs.blob_storage import (
    BlobContainers,
    BlobStorageClient,
    get_timestamped_blob_name,
)

from config import config

logger = logging.getLogger(__name__)


class MarkdownGenerator:
    """Core markdown generation service logic."""

    def __init__(self, blob_client: BlobStorageClient):
        """Initialize markdown generator with blob storage client."""
        self.blob_client = blob_client

    async def generate_markdown_from_ranked_content(
        self, content_items: List[Dict[str, Any]], template_style: str = "standard"
    ) -> Optional[Dict[str, Any]]:
        """
        Generate markdown files from ranked content items.

        Args:
            content_items: List of ranked content items
            template_style: Markdown template style to use

        Returns:
            Dictionary containing generation result
        """
        try:
            if not content_items:
                raise ValueError("No content items provided for markdown generation")

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

            # Generate individual markdown files
            markdown_files = []
            for i, item in enumerate(content_items[: config.MAX_CONTENT_ITEMS], 1):
                markdown_content = self._generate_post_markdown(
                    item, rank=i, template_style=template_style
                )

                # Create filename and slug
                title = item.get("clean_title", item.get("title", "untitled"))
                slug = self._create_slug(title)

                markdown_files.append(
                    {
                        "slug": slug,
                        "title": item.get("clean_title", item.get("title", "Untitled")),
                        "score": item.get("final_score", 0),
                        "content": markdown_content,
                        "rank": i,
                    }
                )

            # Generate index file
            index_content = self._generate_index_markdown(
                content_items, timestamp, template_style
            )

            # Create publishing manifest
            manifest = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "timestamp": timestamp,
                "total_posts": len(markdown_files),
                "generator": config.SERVICE_NAME,
                "version": config.VERSION,
                "template_style": template_style,
                "index_content": index_content,
                "generation_settings": {
                    "max_content_items": config.MAX_CONTENT_ITEMS,
                    "template_style": template_style,
                },
            }

            # Save to blob storage using standard methods
            manifest_blob = await self._save_generated_markdown_to_blobs(
                markdown_files, manifest, timestamp
            )

            return {
                "status": "success",
                "files_generated": len(markdown_files) + 1,  # +1 for index
                "blob_manifest": manifest_blob,
                "timestamp": timestamp,
                "markdown_files": [
                    {
                        "file": f"markdown/{timestamp}/{mf['slug']}.md",
                        "slug": mf["slug"],
                        "title": mf["title"],
                        "score": mf["score"],
                    }
                    for mf in markdown_files
                ],
            }

        except Exception as e:
            logger.error(f"Error in content watch cycle: {e}")
            return None

    def _generate_post_markdown(
        self, item: Dict[str, Any], rank: int = 1, template_style: str = "standard"
    ) -> str:
        """Generate markdown for a single content item."""
        # Extract key information
        title = item.get("title", "Untitled")
        clean_title = item.get("clean_title", title)
        source_url = item.get("source_url", "")
        content_type = item.get("content_type", "article")

        # Get enrichment data
        ai_summary = item.get("ai_summary", "Summary not available")
        topics = item.get("topics", [])
        sentiment = item.get("sentiment", "neutral")

        # Get scoring data
        final_score = item.get("final_score", 0)
        engagement_score = item.get("engagement_score", 0)

        # Get source metadata
        source_metadata = item.get("source_metadata", {})
        site_name = source_metadata.get("site_name", "Unknown Source")
        published_at = item.get("published_at", datetime.now(timezone.utc).isoformat())

        # Create slug from title
        slug = self._create_slug(clean_title)

        # Generate standard markdown with minimal frontmatter
        return self._generate_standard_markdown(
            clean_title,
            slug,
            ai_summary,
            topics,
            sentiment,
            final_score,
            engagement_score,
            site_name,
            source_url,
            content_type,
            published_at,
            rank,
        )

    def _generate_standard_markdown(
        self,
        clean_title: str,
        slug: str,
        ai_summary: str,
        topics: List[str],
        sentiment: str,
        final_score: float,
        engagement_score: float,
        site_name: str,
        source_url: str,
        content_type: str,
        published_at: str,
        rank: int,
    ) -> str:
        """Generate clean markdown with minimal frontmatter for site-generator processing."""

        # Generate simple YAML frontmatter with essential metadata
        frontmatter = f"""---
title: "{clean_title}"
slug: "{slug}"
date: "{published_at}"
summary: "{ai_summary[:200]}..."
topics: {json.dumps(topics)}
sentiment: "{sentiment}"
source_name: "{site_name}"
source_url: "{source_url}"
content_type: "{content_type}"
ai_score: {final_score:.3f}
engagement_score: {engagement_score:.3f}
rank: {rank}
generated_at: "{datetime.now(timezone.utc).isoformat()}"
---"""

        # Generate clean markdown content
        topics_str = ", ".join(topics) if topics else "General"

        body = f"""# {clean_title}

## Summary

{ai_summary}

## Key Information

**Topics:** {topics_str}
**Sentiment:** {sentiment.title()}
**AI Score:** {final_score:.1f}/100
**Engagement Score:** {engagement_score:.1f}/100

## Source

This content was curated from [{site_name}]({source_url}).

---

*This article was generated by AI Content Farm - an automated content curation system.*"""

        return f"{frontmatter}\n\n{body}"

    def _generate_index_markdown(
        self,
        content_items: List[Dict[str, Any]],
        timestamp: str,
        template_style: str = "standard",
    ) -> str:
        """Generate a clean index markdown file listing all articles."""

        # Generate simple frontmatter
        frontmatter = f"""---
title: "AI Curated Content Index"
type: "index"
date: "{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
generated_at: "{datetime.now(timezone.utc).isoformat()}"
total_articles: {len(content_items)}
timestamp: "{timestamp}"
---"""  # Create article listings
        article_list = ""
        for i, item in enumerate(content_items, 1):
            title = item.get("clean_title", item.get("title", "Untitled"))
            slug = self._create_slug(title)
            score = item.get("final_score", 0)
            topics = ", ".join(item.get("topics", []))

            article_list += f"""
### {i}. [{title}]({slug}.html)

**Score:** {score:.3f} | **Topics:** {topics}

{item.get('ai_summary', 'Summary not available')[:200]}...

"""

        body = f"""# AI Curated Content Index

Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
Total Articles: {len(content_items)}

## Featured Articles
{article_list}

---

*Content curated and generated by AI Content Farm*"""

        return f"{frontmatter}\n\n{body}"

    def _create_slug(self, title: str) -> str:
        """Create URL-friendly slug from title."""
        slug = title.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug.strip("-")[:50]  # Limit length

    async def _save_generated_markdown_to_blobs(
        self,
        markdown_files: List[Dict[str, Any]],
        manifest: Dict[str, Any],
        timestamp: str,
    ) -> str:
        """Save generated markdown files and manifest to blob storage using standard methods."""
        try:
            # Upload individual markdown files
            for md_file in markdown_files:
                if "content" in md_file:
                    blob_name = f"markdown/{timestamp}/{md_file['slug']}.md"

                    # Use standard upload_text method
                    self.blob_client.upload_text(
                        config.GENERATED_CONTENT_CONTAINER,
                        blob_name,
                        md_file["content"],
                    )

                    logger.debug(f"Uploaded markdown file: {blob_name}")

            # Upload index file if present
            if "index_content" in manifest:
                index_blob_name = f"markdown/{timestamp}/index.md"
                self.blob_client.upload_text(
                    config.GENERATED_CONTENT_CONTAINER,
                    index_blob_name,
                    manifest["index_content"],
                )
                manifest["index_blob"] = index_blob_name
                logger.debug(f"Uploaded index file: {index_blob_name}")

            # Update manifest with blob information
            manifest["storage_location"] = (
                f"blob://{config.GENERATED_CONTENT_CONTAINER}/markdown/{timestamp}/"
            )

            # Upload manifest
            manifest_blob_name = f"manifests/{timestamp}_manifest.json"
            self.blob_client.upload_json(
                config.GENERATED_CONTENT_CONTAINER, manifest_blob_name, manifest
            )

            logger.info(f"Uploaded manifest: {manifest_blob_name}")
            return manifest_blob_name

        except Exception as e:
            logger.error(f"Error saving markdown to blobs: {e}")
            raise


class ContentWatcher:
    """Service to watch for new ranked content and trigger markdown generation."""

    def __init__(self, blob_client: BlobStorageClient, generator: MarkdownGenerator):
        """Initialize content watcher."""
        self.blob_client = blob_client
        self.generator = generator
        self.processed_blobs = set()
        self.last_check = datetime.now(timezone.utc)

    async def check_for_new_ranked_content(self) -> Optional[Dict[str, Any]]:
        """
        Check for new ranked content and generate markdown if found.

        Returns:
            Generation result if new content was processed, None otherwise
        """
        try:
            result = await self._get_latest_ranked_content()
            if not result:
                logger.debug("No ranked content found")
                return None

            content_items, blob_name = result

            # Check if we've already processed this blob
            if blob_name in self.processed_blobs:
                logger.debug(f"Already processed blob: {blob_name}")
                return None

            logger.info(
                f"Processing new ranked content: {blob_name} ({len(content_items)} items)"
            )

            # Generate markdown
            generation_result = (
                await self.generator.generate_markdown_from_ranked_content(
                    content_items
                )
            )

            # Mark as processed
            self.processed_blobs.add(blob_name)
            self.last_check = datetime.now(timezone.utc)

            return generation_result

        except Exception as e:
            logger.error(f"Error checking for new ranked content: {e}")
            return None

    def get_watcher_status(self) -> Dict[str, Any]:
        """Get current status of the content watcher."""
        return {
            "watching": True,
            "processed_blobs": len(self.processed_blobs),
            "last_check": self.last_check.isoformat(),
            "watch_interval": config.WATCH_INTERVAL,
        }

    async def _get_latest_ranked_content(
        self,
    ) -> Optional[Tuple[List[Dict[str, Any]], str]]:
        """
        Get the latest ranked content blob.

        Returns:
            Tuple of (content_items, blob_name) if found, None otherwise
        """
        try:
            # List all ranked content blobs (non-async)
            blobs = self.blob_client.list_blobs(
                BlobContainers.PROCESSED_CONTENT, "ranked-content/"
            )
            if not blobs:
                logger.debug("No ranked content blobs found")
                return None

            # Find the most recent blob
            latest_blob = max(blobs, key=lambda b: b.get("last_modified", ""))
            blob_name = latest_blob["name"]

            logger.info(f"Found latest ranked content blob: {blob_name}")

            # Download and parse the content (non-async)
            content_data = self.blob_client.download_json(
                BlobContainers.PROCESSED_CONTENT, blob_name
            )
            if not content_data:
                logger.warning(f"Failed to download content from {blob_name}")
                return None

            # Extract content items from the structure
            if isinstance(content_data, dict) and "content" in content_data:
                content_items = content_data["content"]
            elif isinstance(content_data, list):
                content_items = content_data
            else:
                logger.warning(f"Unexpected content structure in {blob_name}")
                return None

            return content_items, blob_name

        except Exception as e:
            logger.error(f"Error getting latest ranked content: {e}")
            return None

"""
Markdown generation service for Site Generator

Handles conversion from processed JSON articles to markdown files.
Uses project standard libraries for consistency.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

from models import GenerationResponse
from security_utils import SecurityValidator

logger = logging.getLogger(__name__)


class MarkdownService:
    """Service for generating markdown files from processed content."""

    def __init__(self, blob_client, config):
        """
        Initialize MarkdownService.

        Args:
            blob_client: Blob storage client for file operations
            config: Configuration object with container names
        """
        self.blob_client = blob_client
        self.config = config
        self.service_id = str(uuid4())[:8]
        self.security_validator = SecurityValidator()
        logger.debug(f"MarkdownService initialized: {self.service_id}")

    async def generate_batch(
        self,
        source: str = "manual",
        batch_size: int = 10,
        force_regenerate: bool = False,
    ) -> GenerationResponse:
        """Generate markdown files from processed content."""
        start_time = datetime.now(timezone.utc)
        generated_files = []
        errors = []

        try:
            logger.info(
                f"Starting markdown generation: source={source}, batch_size={batch_size}"
            )

            # Get latest processed content
            processed_articles = await self._get_processed_articles(batch_size)

            if not processed_articles:
                logger.info("No processed articles found")
                return self._create_empty_response()

            # Generate markdown for each article
            for article_data in processed_articles:
                try:
                    markdown_filename = await self._generate_single_markdown(
                        article_data
                    )
                    generated_files.append(markdown_filename)
                except Exception as e:
                    error_msg = f"Failed to generate markdown for {article_data.get('topic_id', 'unknown')}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            logger.info(
                f"Markdown generation complete: {len(generated_files)} files generated"
            )

            return GenerationResponse(
                generator_id=self.service_id,
                operation_type="markdown_generation",
                files_generated=len(generated_files),
                processing_time=processing_time,
                output_location=f"blob://{self.config.MARKDOWN_CONTENT_CONTAINER}",
                generated_files=generated_files,
                errors=errors,
            )

        except Exception as e:
            logger.error("Markdown generation failed")
            logger.debug(f"Markdown generation error details: {e}")
            raise

    async def _get_processed_articles(self, limit: int) -> List[Dict]:
        """Get latest processed articles from blob storage."""
        try:
            logger.info(
                f"Attempting to list blobs from container: {self.config.PROCESSED_CONTENT_CONTAINER}"
            )

            # List blobs in processed-content container
            blobs = await self.blob_client.list_blobs(
                container_name=self.config.PROCESSED_CONTENT_CONTAINER
            )

            logger.info(f"Found {len(blobs)} blobs in container")
            if blobs:
                logger.info(f"First blob info: {blobs[0]}")

            articles = []
            # Take only the requested number of blobs and extract blob names properly
            for blob_info in blobs[:limit]:
                # Extract name from blob info dict
                blob_name = blob_info["name"]
                logger.info(f"Processing blob: {blob_name}")
                try:
                    article_data = await self.blob_client.download_json(
                        container_name=self.config.PROCESSED_CONTENT_CONTAINER,
                        blob_name=blob_name,
                    )
                    logger.info(f"Successfully downloaded article data for {blob_name}")
                    articles.append(article_data)
                except Exception as e:
                    logger.error(f"Failed to load article {blob_name}")
                    logger.debug(f"Article loading error details for {blob_name}: {e}")

            # Sort by generated_at timestamp, newest first
            articles.sort(key=lambda x: x.get("generated_at", ""), reverse=True)

            logger.info(f"Returning {len(articles)} processed articles")
            return articles

        except Exception as e:
            logger.error("Failed to get processed articles")
            logger.error(f"Processed articles retrieval error details: {e}")
            return []

    async def _generate_single_markdown(self, article_data: Dict) -> str:
        """Generate markdown file for a single article."""
        # Create slug from title
        title = article_data.get("title", "Untitled")
        slug = self._create_slug(title)

        # Generate filename with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{slug}.md"

        # Create markdown content
        markdown_content = self._create_markdown_content(article_data)

        # Upload to blob storage
        await self.blob_client.upload_text(
            container_name=self.config.MARKDOWN_CONTENT_CONTAINER,
            blob_name=filename,
            content=markdown_content,
            content_type="text/markdown",
        )

        return filename

    def _create_markdown_content(self, article_data: Dict) -> str:
        """Create markdown content with frontmatter."""
        title = article_data.get("title", "Untitled")
        content = article_data.get("article_content", "")
        word_count = article_data.get("word_count", 0)
        quality_score = article_data.get("quality_score", 0)
        cost = article_data.get("cost", 0)
        source = article_data.get("source", "unknown")
        original_url = article_data.get("original_url", "")
        generated_at = article_data.get(
            "generated_at", datetime.now(timezone.utc).isoformat()
        )
        topic_id = article_data.get("topic_id", "")

        # Create slug
        slug = self._create_slug(title)

        # Generate frontmatter
        frontmatter = f"""---
title: "{title}"
slug: "{slug}"
date: "{datetime.now().strftime('%Y-%m-%d')}"
time: "{datetime.now().strftime('%H:%M:%S')}"
summary: "{title}"
tags: ["tech", "ai-curated", "{source}"]
categories: ["tech", "ai-curated"]
source:
  name: "{source}"
  url: "{original_url}"
metadata:
  topic_id: "{topic_id}"
  word_count: {word_count}
  quality_score: {quality_score}
  cost: {cost}
  generated_at: "{generated_at}"
published: true
---

"""

        return frontmatter + content

    def _create_slug(self, title: str) -> str:
        """Create URL-safe slug from title."""
        return self.security_validator.sanitize_filename(
            title.lower().replace(" ", "-")
        )

    def _create_empty_response(self) -> GenerationResponse:
        """Create empty response when no articles found."""
        return GenerationResponse(
            generator_id=self.service_id,
            operation_type="markdown_generation",
            files_generated=0,
            processing_time=0.0,
            output_location=f"blob://{self.config.MARKDOWN_CONTENT_CONTAINER}",
            generated_files=[],
        )

    async def count_markdown_files(self) -> int:
        """Count markdown files in storage."""
        try:
            blobs = await self.blob_client.list_blobs(
                container_name=self.config.MARKDOWN_CONTENT_CONTAINER
            )
            return len(blobs)
        except Exception:
            return 0

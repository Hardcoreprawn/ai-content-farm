"""
Markdown generation service for Site Generator

Handles conversion from processed JSON            return GenerationResponse(
                generator_id=self.service_id,
                operation_type="markdown_generation",
                files_generated=len(generated_files),
                processing_time=processing_time,
                output_location=f"blob://{self.config.MARKDOWN_CONTENT_CONTAINER}",
                generated_files=generated_files,
                errors=[],
            )o markdown files.
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

    def __init__(self):
        """
        Initialize MarkdownService.

        Uses the global configuration system and lazy-initializes blob client.
        """
        self.blob_client = None
        self.service_id = str(uuid4())[:8]
        self.security_validator = SecurityValidator()
        self._initialized = False
        logger.debug(f"MarkdownService initialized: {self.service_id}")

    async def initialize(self):
        """Initialize the service with blob client."""
        if self._initialized:
            return

        from libs.simplified_blob_client import SimplifiedBlobClient

        self.blob_client = SimplifiedBlobClient()
        self._initialized = True
        logger.info("MarkdownService initialized with blob client")

    async def generate_batch(
        self,
        source: str = "manual",
        batch_size: int = 10,
        force_regenerate: bool = False,
    ) -> GenerationResponse:
        """Generate markdown files from processed content."""
        if not self._initialized:
            await self.initialize()

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

            from config import MARKDOWN_CONTENT_CONTAINER

            return GenerationResponse(
                generator_id=self.service_id,
                operation_type="markdown_generation",
                files_generated=len(generated_files),
                processing_time=processing_time,
                output_location=f"blob://{MARKDOWN_CONTENT_CONTAINER()}",
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
            # Use the new configuration system
            container_name = self.config.PROCESSED_CONTENT_CONTAINER
            prefix = self.config.INPUT_PREFIX

            logger.info(
                f"🔍 DEBUG: Using container: {container_name}, prefix: {prefix}"
            )

            logger.info(
                f"Attempting to list blobs from container: {container_name} with prefix: {prefix}"
            )

            # List blobs in processed-content container with prefix
            blobs = await self.blob_client.list_blobs(
                container=container_name, prefix=prefix
            )

            logger.info(
                f"Found {len(blobs)} blobs in container {container_name} with prefix {prefix}"
            )
            if blobs:
                logger.info(f"First blob info: {blobs[0]}")
                # Filter to only JSON files to avoid processing markdown files
                json_blobs = [blob for blob in blobs if blob["name"].endswith(".json")]
                logger.info(f"Filtered to {len(json_blobs)} JSON files")
                blobs = json_blobs
            else:
                # If no files found with prefix, try without prefix (old structure)
                logger.info(
                    "No files found with prefix, trying without prefix (old structure)"
                )
                all_blobs = await self.blob_client.list_blobs(container=container_name)
                # Filter to only JSON files to avoid processing markdown files
                blobs = [blob for blob in all_blobs if blob["name"].endswith(".json")]
                logger.info(
                    f"Found {len(blobs)} JSON files in container {container_name} without prefix"
                )

            articles = []
            # Take only the requested number of blobs and extract blob names properly
            for blob_info in blobs[:limit]:
                # Extract name from blob info dict
                blob_name = blob_info["name"]
                logger.info(f"Processing blob: {blob_name}")
                try:
                    article_data = await self.blob_client.download_json(
                        container_name=container_name,
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
        # Handle both old format (article_content) and new format (content)
        content = article_data.get("article_content") or article_data.get("content", "")
        word_count = article_data.get(
            "word_count", len(content.split()) if content else 0
        )
        quality_score = article_data.get(
            "quality_score", 0.8
        )  # Default reasonable score
        cost = article_data.get("cost", 0)

        # Handle URL field variations
        original_url = article_data.get("original_url") or article_data.get("url") or ""

        # Extract source from URL if not provided
        source = article_data.get("source", "unknown")

        # Improved source detection for new normalized content
        if source == "unknown" and original_url:
            # Enhanced source detection with more site patterns
            url_lower = original_url.lower()
            if "wired.com" in url_lower:
                source = "wired"
            elif "arstechnica" in url_lower:
                source = "arstechnica"
            elif "theregister" in url_lower:
                source = "theregister"
            elif "reddit.com" in url_lower:
                source = "reddit"
            elif "github.com" in url_lower:
                source = "github"
            elif "stackoverflow.com" in url_lower:
                source = "stackoverflow"
            else:
                source = "web"
        if source == "unknown" and original_url:
            if "wired.com" in original_url:
                source = "wired"
            elif "arstechnica" in original_url:
                source = "arstechnica"
            elif "theregister" in original_url:
                source = "theregister"
            else:
                source = "web"

        # Handle timestamp variations
        generated_at = (
            article_data.get("generated_at")
            or article_data.get("timestamp")
            or datetime.now(timezone.utc).isoformat()
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
        """
        Create secure URL-safe slug from title using python-slugify.

        This library handles security, unicode, and edge cases automatically.
        """
        from slugify import slugify

        if not title or not title.strip():
            return "untitled"

        # Use python-slugify with secure defaults
        slug = slugify(
            title.strip(),
            max_length=50,  # Reasonable length limit
            lowercase=True,
            separator="-",
            # Only allow word chars and hyphens (spaces will be converted to hyphens)
            regex_pattern=r"[^-\w]",
        )

        # Final safety check - if somehow empty, provide fallback
        if not slug:
            return "article"

        return slug

    def _create_empty_response(self) -> GenerationResponse:
        """Create empty response when no articles found."""
        return GenerationResponse(
            generator_id=self.service_id,
            operation_type="markdown_generation",
            files_generated=0,
            processing_time=0.0,
            output_location=f"blob://{self.config.MARKDOWN_CONTENT_CONTAINER}",
            generated_files=[],
            errors=[],
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

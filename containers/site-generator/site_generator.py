"""
Core Static Site Generator

Python-based JAMStack generator for AI Content Farm.
Converts processed JSON articles to markdown and static HTML sites.
"""

import asyncio
import json
import logging
import os
import re

# Import blob storage from libs
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import aiofiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from models import (
    ArticleMetadata,
    GenerationResponse,
    SiteManifest,
    SiteMetrics,
    SiteStatus,
)

from config import Config
from libs.blob_storage import BlobStorageClient

sys.path.append("/workspaces/ai-content-farm")

logger = logging.getLogger(__name__)


class SiteGenerator:
    """Python-based static site generator for AI content."""

    def __init__(self):
        self.generator_id = str(uuid4())[:8]
        self.config = Config()
        self.blob_client = BlobStorageClient()

        # Initialize Jinja2 environment
        template_path = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_path),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Site state
        self.current_status = "idle"
        self.current_theme = self.config.DEFAULT_THEME
        self.last_generation = None
        self.error_message = None

    async def check_blob_connectivity(self) -> bool:
        """Check if blob storage is accessible."""
        try:
            # Test by listing containers
            await self.blob_client.list_containers()
            return True
        except Exception as e:
            logger.error(f"Blob connectivity check failed: {e}")
            return False

    async def get_status(self) -> SiteStatus:
        """Get current generator status."""
        try:
            # Count markdown files
            markdown_count = await self._count_markdown_files()

            # Get site metrics if available
            site_metrics = await self._get_site_metrics()

            return SiteStatus(
                generator_id=self.generator_id,
                status=self.current_status,
                current_theme=self.current_theme,
                markdown_files_count=markdown_count,
                site_metrics=site_metrics,
                last_generation=self.last_generation,
                error_message=self.error_message,
            )
        except Exception as e:
            logger.error(f"Status retrieval failed: {e}")
            return SiteStatus(
                generator_id=self.generator_id,
                status="error",
                current_theme=self.current_theme,
                markdown_files_count=0,
                error_message=str(e),
            )

    async def generate_markdown_batch(
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
            self.current_status = "generating"
            logger.info(
                f"Starting markdown generation: source={source}, batch_size={batch_size}"
            )

            # Get latest processed content
            processed_articles = await self._get_processed_articles(batch_size)

            if not processed_articles:
                logger.info("No processed articles found")
                return GenerationResponse(
                    generator_id=self.generator_id,
                    operation_type="markdown_generation",
                    files_generated=0,
                    processing_time=0.0,
                    output_location=f"blob://{self.config.MARKDOWN_CONTENT_CONTAINER}",
                    generated_files=[],
                )

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
            self.last_generation = datetime.now(timezone.utc)
            self.current_status = "idle"

            logger.info(
                f"Markdown generation complete: {len(generated_files)} files generated"
            )

            return GenerationResponse(
                generator_id=self.generator_id,
                operation_type="markdown_generation",
                files_generated=len(generated_files),
                processing_time=processing_time,
                output_location=f"blob://{self.config.MARKDOWN_CONTENT_CONTAINER}",
                generated_files=generated_files,
                errors=errors,
            )

        except Exception as e:
            self.current_status = "error"
            self.error_message = str(e)
            logger.error(f"Markdown generation failed: {e}")
            raise

    async def generate_static_site(
        self, theme: str = "minimal", force_rebuild: bool = False
    ) -> GenerationResponse:
        """Generate complete static HTML site."""
        start_time = datetime.now(timezone.utc)
        generated_files = []

        try:
            self.current_status = "generating"
            self.current_theme = theme
            logger.info(f"Starting static site generation with theme: {theme}")

            # Get all markdown content
            markdown_articles = await self._get_markdown_articles()

            if not markdown_articles:
                logger.info("No markdown articles found for site generation")
                return GenerationResponse(
                    generator_id=self.generator_id,
                    operation_type="site_generation",
                    files_generated=0,
                    pages_generated=0,
                    processing_time=0.0,
                    output_location=f"blob://{self.config.STATIC_SITES_CONTAINER}",
                    generated_files=[],
                )

            # Create temporary directory for site generation
            with tempfile.TemporaryDirectory() as temp_dir:
                site_dir = Path(temp_dir) / "site"
                site_dir.mkdir()

                # Generate individual article pages
                articles_dir = site_dir / "articles"
                articles_dir.mkdir()

                article_pages = []
                for article in markdown_articles:
                    page_path = await self._generate_article_page(
                        article, articles_dir, theme
                    )
                    if page_path:
                        article_pages.append(page_path)
                        generated_files.append(f"articles/{page_path.name}")

                # Generate index page
                index_path = await self._generate_index_page(
                    markdown_articles, site_dir, theme
                )
                if index_path:
                    generated_files.append("index.html")

                # Generate RSS feed
                rss_path = await self._generate_rss_feed(markdown_articles, site_dir)
                if rss_path:
                    generated_files.append("feed.xml")

                # Copy static assets
                await self._copy_static_assets(site_dir, theme)
                generated_files.extend(["style.css", "script.js"])

                # Create site archive and upload
                archive_path = await self._create_site_archive(site_dir, theme)
                await self._upload_site_archive(archive_path)

            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.last_generation = datetime.now(timezone.utc)
            self.current_status = "idle"

            logger.info(
                f"Static site generation complete: {len(generated_files)} files generated"
            )

            return GenerationResponse(
                generator_id=self.generator_id,
                operation_type="site_generation",
                files_generated=len(generated_files),
                pages_generated=len(article_pages) + 1,  # articles + index
                processing_time=processing_time,
                output_location=f"blob://{self.config.STATIC_SITES_CONTAINER}",
                generated_files=generated_files,
            )

        except Exception as e:
            self.current_status = "error"
            self.error_message = str(e)
            logger.error(f"Static site generation failed: {e}")
            raise

    async def get_preview_url(self, site_id: str) -> str:
        """Get preview URL for a generated site."""
        # This would integrate with Azure Static Web Apps or similar
        base_url = f"https://{self.config.SITE_DOMAIN}"
        return f"{base_url}/preview/{site_id}"

    # Private helper methods

    async def _get_processed_articles(self, limit: int) -> List[Dict]:
        """Get latest processed articles from blob storage."""
        try:
            # List blobs in processed-content container
            blobs = await self.blob_client.list_blobs(
                container_name=self.config.PROCESSED_CONTENT_CONTAINER, limit=limit
            )

            articles = []
            for blob_name in blobs[:limit]:
                try:
                    content = await self.blob_client.download_blob(
                        container_name=self.config.PROCESSED_CONTENT_CONTAINER,
                        blob_name=blob_name,
                    )
                    article_data = json.loads(content)
                    articles.append(article_data)
                except Exception as e:
                    logger.error(f"Failed to load article {blob_name}: {e}")

            # Sort by generated_at timestamp, newest first
            articles.sort(key=lambda x: x.get("generated_at", ""), reverse=True)

            return articles

        except Exception as e:
            logger.error(f"Failed to get processed articles: {e}")
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
        await self.blob_client.upload_blob(
            container_name=self.config.MARKDOWN_CONTENT_CONTAINER,
            blob_name=filename,
            data=markdown_content.encode("utf-8"),
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
        slug = title.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"\s+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        slug = slug.strip("-")
        return slug[:50]

    async def _count_markdown_files(self) -> int:
        """Count markdown files in storage."""
        try:
            blobs = await self.blob_client.list_blobs(
                container_name=self.config.MARKDOWN_CONTENT_CONTAINER
            )
            return len(blobs)
        except Exception:
            return 0

    async def _get_site_metrics(self) -> Optional[SiteMetrics]:
        """Get current site metrics."""
        # This would be implemented based on your specific metrics needs
        return None

    async def _get_markdown_articles(self) -> List[ArticleMetadata]:
        """Get all markdown articles for site generation."""
        # This would download and parse markdown files
        # For now, return empty list - implement based on needs
        return []

    async def _generate_article_page(
        self, article: ArticleMetadata, output_dir: Path, theme: str
    ) -> Optional[Path]:
        """Generate HTML page for single article."""
        # Implementation would use Jinja2 templates
        return None

    async def _generate_index_page(
        self, articles: List[ArticleMetadata], output_dir: Path, theme: str
    ) -> Optional[Path]:
        """Generate site index page."""
        # Implementation would use Jinja2 templates
        return None

    async def _generate_rss_feed(
        self, articles: List[ArticleMetadata], output_dir: Path
    ) -> Optional[Path]:
        """Generate RSS feed."""
        # Implementation would create RSS XML
        return None

    async def _copy_static_assets(self, output_dir: Path, theme: str):
        """Copy static CSS/JS assets."""
        # Implementation would copy theme assets
        pass

    async def _create_site_archive(self, site_dir: Path, theme: str) -> Path:
        """Create tar.gz archive of generated site."""
        # Sanitize theme name to prevent path injection
        safe_theme = self._sanitize_filename(theme)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        archive_path = site_dir.parent / f"site_{safe_theme}_{timestamp}.tar.gz"

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(site_dir, arcname=".")

        return archive_path

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path injection."""
        # Remove any path separators and ensure safe filename
        safe_name = os.path.basename(filename)
        # Remove any unsafe characters, keeping only alphanumeric, dots, hyphens, underscores
        safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", safe_name)
        # Ensure it doesn't start with dots or special chars
        safe_name = re.sub(r"^[._-]+", "", safe_name)
        # Limit length
        if not safe_name or len(safe_name) > 50:
            safe_name = "default"
        return safe_name

    def _sanitize_blob_name(self, name: str) -> str:
        """Sanitize blob name to prevent path injection."""
        # Remove any path separators and ensure safe filename
        safe_name = os.path.basename(name)
        # Remove any unsafe characters, keeping only alphanumeric, dots, hyphens, underscores
        safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", safe_name)
        # Ensure it doesn't start with dots or special chars
        safe_name = re.sub(r"^[._-]+", "", safe_name)
        # Limit length and ensure it has an extension
        if not safe_name or len(safe_name) > 100:
            safe_name = f"site_archive_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.tar.gz"
        return safe_name

    async def _upload_site_archive(self, archive_path: Path):
        """Upload site archive to blob storage."""
        # Sanitize the blob name to prevent path injection
        safe_blob_name = self._sanitize_blob_name(archive_path.name)

        with open(archive_path, "rb") as f:
            self.blob_client.upload_binary(
                container_name=self.config.STATIC_SITES_CONTAINER,
                blob_name=safe_blob_name,
                data=f.read(),
                content_type="application/gzip",
            )

"""
Site generation service for Site Generator

Handles creation of complete static HTML sites from markdown content.
Uses project standard libraries for consistency.
"""

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from models import ArticleMetadata, GenerationResponse
from security_utils import SecurityValidator

logger = logging.getLogger(__name__)


class SiteService:
    """Service for generating complete static HTML sites."""

    def __init__(self, blob_client, config, content_manager, archive_manager):
        """
        Initialize SiteService.

        Args:
            blob_client: Blob storage client for file operations
            config: Configuration object with container names
            content_manager: ContentManager for page generation
            archive_manager: ArchiveManager for archive operations
        """
        self.blob_client = blob_client
        self.config = config
        self.content_manager = content_manager
        self.archive_manager = archive_manager
        self.service_id = str(uuid4())[:8]
        self.security_validator = SecurityValidator()
        logger.debug(f"SiteService initialized: {self.service_id}")

    async def generate_site(
        self, theme: str = "minimal", force_rebuild: bool = False
    ) -> GenerationResponse:
        """Generate complete static HTML site."""
        start_time = datetime.now(timezone.utc)
        generated_files = []

        try:
            logger.info(f"Starting static site generation with theme: {theme}")

            # Get all markdown content
            markdown_articles = await self._get_markdown_articles()

            if not markdown_articles:
                logger.info("No markdown articles found for site generation")
                return self._create_empty_response()

            # Create temporary directory for site generation
            with tempfile.TemporaryDirectory() as temp_dir:
                site_dir = Path(temp_dir) / "site"
                site_dir.mkdir()

                # Generate content using ContentManager
                generated_files = await self._generate_site_content(
                    markdown_articles, site_dir, theme
                )

                # Create and upload archive using ArchiveManager
                archive_path = await self.archive_manager.create_site_archive(
                    site_dir, theme
                )
                await self.archive_manager.upload_archive(archive_path)

            # Calculate metrics and return response
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            logger.info(
                f"Static site generation complete: {len(generated_files)} files generated"
            )

            return GenerationResponse(
                generator_id=self.service_id,
                operation_type="site_generation",
                files_generated=len(generated_files),
                pages_generated=len(markdown_articles) + 1,  # articles + index
                processing_time=processing_time,
                output_location=f"blob://{self.config.STATIC_SITES_CONTAINER}",
                generated_files=generated_files,
            )

        except Exception as e:
            logger.error("Static site generation failed")
            logger.debug(f"Static site generation error details: {e}")
            raise

    async def _generate_site_content(
        self, markdown_articles: List[ArticleMetadata], site_dir: Path, theme: str
    ) -> List[str]:
        """Generate all site content and return list of generated files."""
        from file_operations import StaticAssetManager

        generated_files = []

        # Generate individual article pages
        articles_dir = site_dir / "articles"
        articles_dir.mkdir()

        for article in markdown_articles:
            page_path = await self.content_manager.generate_article_page(
                article, articles_dir, theme
            )
            if page_path:
                generated_files.append(f"articles/{page_path.name}")

        # Generate index page
        index_path = await self.content_manager.generate_index_page(
            markdown_articles, site_dir, theme
        )
        if index_path:
            generated_files.append("index.html")

        # Generate RSS feed
        rss_path = await self.content_manager.generate_rss_feed(
            markdown_articles, site_dir
        )
        if rss_path:
            generated_files.append("feed.xml")

        # Generate 404 page
        error_404_path = await self.content_manager.generate_404_page(site_dir, theme)
        if error_404_path:
            generated_files.append("404.html")

        # Copy static assets
        static_files = await StaticAssetManager.copy_static_assets(site_dir, theme)
        generated_files.extend(static_files)

        return generated_files

    async def get_preview_url(self, site_id: str) -> str:
        """Get preview URL for a generated site."""
        # This would integrate with Azure Static Web Apps or similar
        base_url = f"https://{self.config.SITE_DOMAIN}"
        return f"{base_url}/preview/{site_id}"

    async def _get_markdown_articles(self) -> List[ArticleMetadata]:
        """Get all markdown articles for site generation."""
        try:
            # List all markdown files in the container
            markdown_files = await self.blob_client.list_blobs(
                container_name=self.config.MARKDOWN_CONTENT_CONTAINER
            )

            articles = []
            for blob_info in markdown_files:
                if blob_info["name"].endswith(".md"):
                    # Download and parse markdown file
                    content = await self.blob_client.download_text(
                        container_name=self.config.MARKDOWN_CONTENT_CONTAINER,
                        blob_name=blob_info["name"],
                    )

                    # Parse frontmatter and create ArticleMetadata
                    article = self._parse_markdown_frontmatter(
                        blob_info["name"], content
                    )
                    if article:
                        articles.append(article)

            logger.info(f"Found {len(articles)} markdown articles")
            return articles

        except Exception as e:
            logger.error(f"Failed to get markdown articles: {e}")
            return []

    def _create_empty_response(self) -> GenerationResponse:
        """Create response for when no articles are found."""
        return GenerationResponse(
            generator_id=self.service_id,
            operation_type="site_generation",
            files_generated=0,
            pages_generated=0,
            processing_time=0.0,
            output_location=f"blob://{self.config.STATIC_SITES_CONTAINER}",
            generated_files=[],
        )

    def _parse_markdown_frontmatter(
        self, filename: str, content: str
    ) -> Optional[ArticleMetadata]:
        """Parse markdown frontmatter to create ArticleMetadata."""
        try:
            import yaml

            # Split content into frontmatter and body
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter_text = parts[1].strip()
                    frontmatter = yaml.safe_load(frontmatter_text)

                    # Extract metadata from nested structure
                    metadata = frontmatter.get("metadata", {})
                    source_info = frontmatter.get("source", {})

                    # Create ArticleMetadata from frontmatter with required fields
                    return ArticleMetadata(
                        topic_id=metadata.get("topic_id", filename.replace(".md", "")),
                        title=frontmatter.get("title", "Untitled"),
                        slug=frontmatter.get("slug", filename.replace(".md", "")),
                        word_count=metadata.get("word_count", 0),
                        quality_score=metadata.get("quality_score", 0.0),
                        cost=metadata.get("cost", 0.0),
                        source=source_info.get("name", "unknown"),
                        original_url=source_info.get("url", ""),
                        generated_at=datetime.fromisoformat(
                            metadata.get(
                                "generated_at", datetime.now().isoformat()
                            ).replace("Z", "+00:00")
                        ),
                        content=parts[2].strip(),
                    )

            logger.warning(f"No frontmatter found in {filename}")
            return None

        except Exception as e:
            logger.error(f"Failed to parse frontmatter for {filename}: {e}")
            return None

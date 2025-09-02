"""
Core Static Site Generator

Python-based JAMStack generator for AI Content Farm.
Converts processed JSON articles to markdown and static HTML sites.
This refactored version delegates most functionality to specialized services.
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from content_manager import ContentManager
from file_operations import ArchiveManager
from legacy_security import LegacySecurity
from markdown_service import MarkdownService
from models import GenerationResponse, SiteMetrics, SiteStatus
from security_utils import SecurityValidator
from site_service import SiteService

from config import Config
from libs import BlobStorageClient

sys.path.append(str(Path(__file__).parent.parent.parent / "libs"))


# Import our utility modules

sys.path.append("/workspaces/ai-content-farm")

logger = logging.getLogger(__name__)


class SiteGenerator:
    """Python-based static site generator for AI content."""

    def __init__(self):
        """Initialize the site generator with required services."""
        self.generator_id = str(uuid4())[:8]
        self.config = Config()
        self.blob_client = BlobStorageClient()

        # Initialize utility managers
        self.content_manager = ContentManager()
        self.archive_manager = ArchiveManager(self.blob_client)
        self.security_validator = SecurityValidator()

        # Initialize services
        self.markdown_service = MarkdownService(self.blob_client, self.config)
        self.site_service = SiteService(
            self.blob_client, self.config, self.content_manager, self.archive_manager
        )

        # Status tracking
        self.current_status = "idle"
        self.current_theme = "minimal"
        self.last_generation = None
        self.error_message = None

        logger.info(f"SiteGenerator initialized: {self.generator_id}")

    async def check_blob_connectivity(self) -> Dict[str, Any]:
        """Test blob storage connectivity."""
        try:
            # Use synchronous method from shared library (will be async in future)
            result = self.blob_client.test_connection()
            return result
        except Exception as e:
            # Secure error handling - don't expose internal details
            logger.error("Blob connectivity test failed")
            logger.debug(f"Blob connectivity error details: {e}")
            return {"status": "error", "message": "Blob connectivity test failed"}

    async def get_status(self) -> SiteStatus:
        """Get current generator status."""
        try:
            # Try to get markdown count - if this fails, treat as total failure
            markdown_count = await self._count_markdown_files()

            # Try to get site metrics - if this fails, continue with None
            site_metrics = None
            try:
                site_metrics = await self._get_site_metrics()
            except Exception as e:
                # Secure logging - don't expose internal details
                logger.warning("Failed to retrieve site metrics")
                logger.debug(f"Site metrics error details: {e}")

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
            # Secure logging and error handling
            logger.error("Failed to get status")
            logger.debug(f"Status retrieval error details: {e}")
            self._set_error_state("Status retrieval failed")
            return SiteStatus(
                generator_id=self.generator_id,
                status="error",
                current_theme=self.current_theme,
                markdown_files_count=0,
                error_message="Status retrieval failed",
            )

    async def generate_markdown_batch(
        self,
        source: str = "manual",
        batch_size: int = 10,
        force_regenerate: bool = False,
    ) -> GenerationResponse:
        """Generate markdown files from processed content."""
        try:
            self.current_status = "generating"
            self._clear_error_state()
            result = await self.markdown_service.generate_batch(
                source, batch_size, force_regenerate
            )
            self._update_generation_timestamp()
            self.current_status = "idle"
            return result
        except Exception as e:
            # Secure error handling - don't expose internal details
            self._set_error_state("Markdown generation failed")
            logger.error("Markdown generation failed")
            logger.debug(f"Markdown generation error details: {e}")
            raise

    async def generate_markdown(
        self,
        source: str = "manual",
        batch_size: int = 10,
        force_regenerate: bool = False,
    ) -> GenerationResponse:
        """Alias for generate_markdown_batch for backward compatibility."""
        return await self.generate_markdown_batch(source, batch_size, force_regenerate)

    async def generate_static_site(
        self, theme: str = "minimal", force_rebuild: bool = False
    ) -> GenerationResponse:
        """Generate complete static HTML site."""
        try:
            self.current_status = "generating"
            self.current_theme = theme
            self._clear_error_state()
            result = await self.site_service.generate_site(theme, force_rebuild)
            self._update_generation_timestamp()
            self.current_status = "idle"
            return result
        except Exception as e:
            # Secure error handling - don't expose internal details
            self._set_error_state("Static site generation failed")
            logger.error("Static site generation failed")
            logger.debug(f"Static site generation error details: {e}")
            raise

    async def get_preview_url(self, site_id: str) -> str:
        """Get preview URL for a generated site."""
        return await self.site_service.get_preview_url(site_id)

    # Legacy methods for backward compatibility
    def _sanitize_filename(self, filename: str) -> str:
        """Legacy filename sanitization (for backward compatibility)."""
        return LegacySecurity.sanitize_filename(filename)

    def _sanitize_blob_name(self, name: str) -> str:
        """Legacy blob name sanitization (for backward compatibility)."""
        return LegacySecurity.sanitize_blob_name(name)

    def _create_slug(self, title: str) -> str:
        """Legacy slug creation (for backward compatibility)."""
        return self.content_manager.create_slug(title)

    async def _upload_site_archive(self, archive_path):
        """Legacy upload method (for backward compatibility)."""
        LegacySecurity.validate_archive_path(archive_path)
        await self.archive_manager.upload_archive(archive_path)

    async def _create_site_archive(self, site_dir, theme: str):
        """Legacy archive creation (for backward compatibility)."""
        LegacySecurity.validate_site_directory(site_dir)
        return await self.archive_manager.create_site_archive(site_dir, theme)

    async def _get_site_metrics(self) -> Optional[SiteMetrics]:
        """Get current site metrics."""
        try:
            # Count markdown files
            markdown_count = await self.markdown_service.count_markdown_files()

            # Get site files and calculate metrics (using synchronous method from shared library)
            blobs = self.blob_client.list_blobs(
                container_name=self.config.STATIC_SITES_CONTAINER
            )

            total_pages = len(
                [blob for blob in blobs if blob.get("name", "").endswith(".html")]
            )
            total_size_bytes = sum(blob.get("size", 0) for blob in blobs)

            return SiteMetrics(
                total_articles=markdown_count,
                total_pages=total_pages,
                total_size_bytes=total_size_bytes,
                last_build_time=2.5,  # Default value
                build_timestamp=self.last_generation or datetime.now(timezone.utc),
            )
        except Exception as e:
            # Secure logging - don't expose internal details
            logger.error("Error getting site metrics")
            logger.debug(f"Site metrics error details: {e}")
            return None

    def _set_error_state(self, error_message: str):
        """Set the generator to error state."""
        self.current_status = "error"
        self.error_message = error_message
        logger.error(f"Generator error state: {error_message}")

    def _clear_error_state(self):
        """Clear the error state."""
        self.current_status = "idle"
        self.error_message = None

    def _update_generation_timestamp(self):
        """Update the last generation timestamp."""
        self.last_generation = datetime.now(timezone.utc)

    async def _count_markdown_files(self) -> int:
        """Count markdown files (delegated to markdown service)."""
        return await self.markdown_service.count_markdown_files()

    def sanitize_filename(self, filename: str) -> str:
        """Public filename sanitization method."""
        return self._sanitize_filename(filename)

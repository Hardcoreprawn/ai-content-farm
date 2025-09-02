"""
File operations utilities for Site Generator

Provides secure file archiving and upload functionality.
Uses project standard libraries for Azure access and response formatting.
"""

import logging
import os
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from uuid import uuid4

import aiofiles
from security_utils import SecurityValidator

logger = logging.getLogger(__name__)


class ArchiveManager:
    """Manages secure file archiving operations."""

    def __init__(self, blob_client=None):
        """
        Initialize ArchiveManager.

        Args:
            blob_client: Optional blob storage client for uploads
        """
        self.blob_client = blob_client
        self.archive_id = str(uuid4())[:8]
        self.security_validator = SecurityValidator()
        logger.debug(f"ArchiveManager initialized: {self.archive_id}")

    async def create_site_archive(self, site_dir: Path, theme: str) -> Path:
        """
        Create a secure tar.gz archive of the generated site.

        Args:
            site_dir: Directory containing the site files
            theme: Theme name to include in archive filename

        Returns:
            Path to the created archive

        Raises:
            ValueError: If security validation fails
        """
        # Validate site directory
        SecurityValidator.validate_site_directory(site_dir)

        # Sanitize theme name and create safe filename
        safe_theme = SecurityValidator.sanitize_filename(theme)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        archive_filename = f"site_{safe_theme}_{timestamp}.tar.gz"

        # Create archive in controlled location
        temp_base = SecurityValidator.TEMP_BASE_DIR.resolve()
        archive_path = (temp_base / archive_filename).resolve()

        # Validate archive path is safe
        if not SecurityValidator.validate_path_within_base(archive_path, temp_base):
            logger.error("Archive file path is outside allowed base directory")
            raise ValueError("Archive file path is outside allowed base directory")

        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                self._add_files_to_archive(tar, site_dir)
        except Exception as e:
            logger.error(f"Failed to create site archive: {e}")
            raise ValueError(f"Archive creation failed: {str(e)}")

        return archive_path

    def _add_files_to_archive(self, tar: tarfile.TarFile, site_dir: Path) -> None:
        """
        Safely add files to the tar archive.

        Args:
            tar: Open tarfile object
            site_dir: Directory to archive
        """
        for root, dirs, files in os.walk(site_dir):
            # Filter directories to exclude dangerous ones
            safe_dirs = SecurityValidator.filter_safe_files(dirs)
            dirs[:] = safe_dirs

            # Filter and add safe files
            safe_files = SecurityValidator.filter_safe_files(files)
            for file in safe_files:
                file_path = Path(root) / file
                try:
                    # Calculate relative path safely
                    rel_path = file_path.relative_to(site_dir)
                    tar.add(file_path, arcname=str(rel_path))
                except ValueError:
                    logger.warning(f"Skipping file outside site directory: {file_path}")
                    continue

    async def upload_archive(
        self, archive_path: Path, container_name: str | None = None
    ) -> None:
        """
        Upload archive to blob storage with security validation.

        Args:
            archive_path: Path to the archive file
            container_name: Optional container name override

        Raises:
            ValueError: If validation fails or upload fails
        """
        if not self.blob_client:
            raise ValueError("No blob client configured for upload")

        # Validate archive file
        try:
            SecurityValidator.validate_archive_file(archive_path)
        except ValueError as e:
            logger.error(f"Archive validation failed: {e}")
            # Preserve specific error information for debugging while maintaining security
            raise ValueError(f"Archive validation failed: {str(e)}")

        # Use default container if not specified
        if not container_name:
            container_name = "static-sites"  # Default container

        # Sanitize blob name
        safe_blob_name = SecurityValidator.sanitize_blob_name(archive_path.name)

        try:
            async with aiofiles.open(archive_path, "rb") as f:
                data = await f.read()
                await self.blob_client.upload_binary(
                    container_name=container_name,
                    blob_name=safe_blob_name,
                    data=data,
                    content_type="application/gzip",
                )
            logger.info(f"Archive uploaded successfully: {safe_blob_name}")
        except Exception as e:
            logger.error(f"Failed to upload archive: {e}")
            raise ValueError(f"Upload failed: {str(e)}")

    def cleanup_temp_files(self, file_paths: List[Path]) -> None:
        """
        Clean up temporary files safely.

        Args:
            file_paths: List of file paths to clean up
        """
        for file_path in file_paths:
            try:
                if file_path.exists() and SecurityValidator.validate_path_within_base(
                    file_path
                ):
                    file_path.unlink()
            except (OSError, ValueError) as e:
                logger.warning(f"Failed to cleanup temp file {file_path}: {e}")


class StaticAssetManager:
    """Manages static asset operations for site generation."""

    @staticmethod
    async def copy_static_assets(output_dir: Path, theme: str) -> List[str]:
        """
        Copy static assets (CSS, JS) to output directory.

        Args:
            output_dir: Target directory for assets
            theme: Theme name for asset selection

        Returns:
            List of copied asset filenames
        """
        # This is a placeholder for the static asset copying logic
        # In the actual implementation, this would copy CSS, JS files etc.
        copied_files = []

        # Create placeholder files for now (replace with actual asset copying)
        style_css = output_dir / "style.css"
        script_js = output_dir / "script.js"

        try:
            style_css.write_text("/* CSS styles */")
            script_js.write_text("// JavaScript code")
            copied_files.extend(["style.css", "script.js"])
        except Exception as e:
            logger.warning(f"Failed to copy static assets: {e}")

        return copied_files

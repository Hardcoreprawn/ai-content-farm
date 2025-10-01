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
from typing import Dict, List
from uuid import uuid4

import aiofiles
from security_utils import SecurityValidator

from libs import SecureErrorHandler

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("file-operations")


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
        except (OSError, PermissionError) as e:
            error_response = error_handler.handle_error(
                e,
                "filesystem",
                user_message="Archive creation failed due to file system error",
            )
            logger.error(error_response["message"])
            raise ValueError(error_response["message"]) from e
        except Exception as e:
            error_response = error_handler.handle_error(
                e, "general", user_message="Unexpected error during archive creation"
            )
            logger.error(error_response["message"])
            raise RuntimeError(error_response["message"]) from e

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
            logger.error("Archive validation failed")
            logger.debug(f"Archive validation error details: {e}")
            # Preserve specific error information for debugging while maintaining security
            raise ValueError("Archive validation failed")

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
        except (ValueError, TypeError) as e:
            error_response = error_handler.handle_error(
                e, "validation", user_message="Archive upload failed with invalid data"
            )
            logger.error(error_response["message"])
            raise ValueError(error_response["message"]) from e
        except Exception as e:
            error_response = error_handler.handle_error(
                e, "general", user_message="Unexpected error during archive upload"
            )
            logger.error(error_response["message"])
            raise RuntimeError(error_response["message"]) from e

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
    """Manages static asset operations for site generation with theme support."""

    @staticmethod
    async def copy_static_assets(output_dir: Path, theme: str) -> List[str]:
        """
        Copy static assets (CSS, JS) to output directory with theme-specific assets.

        Args:
            output_dir: Target directory for assets
            theme: Theme name for asset selection

        Returns:
            List of copied asset filenames
        """
        copied_files = []

        try:
            # Get the site-generator directory
            site_generator_dir = Path(__file__).parent

            # Theme-specific assets directory
            theme_dir = site_generator_dir / "templates" / theme

            # Global static assets directory
            static_dir = site_generator_dir / "static"

            # Copy theme-specific assets first (they take priority)
            if theme_dir.exists():
                copied_files.extend(
                    await StaticAssetManager._copy_theme_assets(
                        theme_dir, output_dir, theme
                    )
                )

            # Copy global static assets if they don't conflict with theme assets
            if static_dir.exists():
                copied_files.extend(
                    await StaticAssetManager._copy_global_assets(
                        static_dir, output_dir, copied_files
                    )
                )

            logger.info(f"Copied {len(copied_files)} static assets for theme '{theme}'")

        except (OSError, PermissionError) as e:
            error_response = error_handler.handle_error(
                e, "filesystem", context={"theme": theme}
            )
            logger.error(
                f"File system error copying assets for theme '{theme}': {error_response['message']}"
            )
            # Create minimal fallback assets
            copied_files.extend(
                await StaticAssetManager._create_fallback_assets(output_dir)
            )
        except Exception as e:
            error_response = error_handler.handle_error(
                e, "general", context={"theme": theme}
            )
            logger.error(
                f"Unexpected error copying assets for theme '{theme}': {error_response['message']}"
            )
            # Create minimal fallback assets
            copied_files.extend(
                await StaticAssetManager._create_fallback_assets(output_dir)
            )

        return copied_files

    @staticmethod
    async def _copy_theme_assets(
        theme_dir: Path, output_dir: Path, theme: str
    ) -> List[str]:
        """Copy theme-specific assets."""
        copied_files = []

        # Asset extensions to copy
        asset_extensions = [
            ".css",
            ".js",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".ico",
            ".webp",
            ".woff",
            ".woff2",
            ".ttf",
        ]

        for asset_path in theme_dir.iterdir():
            if asset_path.is_file() and asset_path.suffix.lower() in asset_extensions:
                try:
                    target_path = output_dir / asset_path.name

                    # Copy binary files
                    if asset_path.suffix.lower() in [
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".gif",
                        ".ico",
                        ".webp",
                        ".woff",
                        ".woff2",
                        ".ttf",
                    ]:
                        target_path.write_bytes(asset_path.read_bytes())
                    else:
                        # Copy text files (CSS, JS, SVG)
                        content = asset_path.read_text(encoding="utf-8")
                        target_path.write_text(content, encoding="utf-8")

                    copied_files.append(asset_path.name)
                    logger.debug(f"Copied theme asset: {asset_path.name}")

                except Exception as e:
                    logger.warning(f"Failed to copy theme asset {asset_path.name}: {e}")

        return copied_files

    @staticmethod
    async def _copy_global_assets(
        static_dir: Path, output_dir: Path, existing_files: List[str]
    ) -> List[str]:
        """Copy global static assets that don't conflict with theme assets."""
        copied_files = []

        # Asset extensions to copy
        asset_extensions = [
            ".css",
            ".js",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".ico",
            ".webp",
            ".woff",
            ".woff2",
            ".ttf",
        ]

        for asset_path in static_dir.rglob("*"):
            if asset_path.is_file() and asset_path.suffix.lower() in asset_extensions:
                # Calculate relative path for nested assets
                relative_path = asset_path.relative_to(static_dir)
                target_path = output_dir / relative_path

                # Skip if theme already provided this asset
                if (
                    str(relative_path) in existing_files
                    or relative_path.name in existing_files
                ):
                    continue

                try:
                    # Create parent directories if needed
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # Copy binary files
                    if asset_path.suffix.lower() in [
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".gif",
                        ".ico",
                        ".webp",
                        ".woff",
                        ".woff2",
                        ".ttf",
                    ]:
                        target_path.write_bytes(asset_path.read_bytes())
                    else:
                        # Copy text files (CSS, JS, SVG)
                        content = asset_path.read_text(encoding="utf-8")
                        target_path.write_text(content, encoding="utf-8")

                    copied_files.append(str(relative_path))
                    logger.debug(f"Copied global asset: {relative_path}")

                except Exception as e:
                    logger.warning(f"Failed to copy global asset {relative_path}: {e}")

        return copied_files

    @staticmethod
    async def _create_fallback_assets(output_dir: Path) -> List[str]:
        """Create minimal fallback assets when copying fails."""
        copied_files = []

        try:
            # Create minimal CSS
            fallback_css = output_dir / "style.css"
            fallback_css.write_text(
                """
/* Fallback CSS */
body { font-family: sans-serif; margin: 2rem; line-height: 1.6; }
h1, h2, h3 { color: #333; }
a { color: #0066cc; }
.container { max-width: 1200px; margin: 0 auto; }
            """.strip()
            )
            copied_files.append("style.css")

            # Create minimal JS
            fallback_js = output_dir / "script.js"
            fallback_js.write_text(
                """
// Fallback JavaScript
console.log('Site loaded with fallback assets');
            """.strip()
            )
            copied_files.append("script.js")

            logger.info("Created fallback assets")

        except Exception as e:
            logger.error(f"Failed to create fallback assets: {e}")

        return copied_files

    @staticmethod
    async def get_theme_assets(theme: str) -> Dict[str, List[str]]:
        """
        Get list of available assets for a theme.

        Args:
            theme: Theme name

        Returns:
            Dictionary with asset categories and file lists
        """
        try:
            site_generator_dir = Path(__file__).parent
            theme_dir = site_generator_dir / "templates" / theme

            assets = {"css": [], "js": [], "images": [], "fonts": [], "other": []}

            if not theme_dir.exists():
                return assets

            for asset_path in theme_dir.iterdir():
                if asset_path.is_file():
                    ext = asset_path.suffix.lower()
                    name = asset_path.name

                    if ext == ".css":
                        assets["css"].append(name)
                    elif ext == ".js":
                        assets["js"].append(name)
                    elif ext in [
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".gif",
                        ".svg",
                        ".ico",
                        ".webp",
                    ]:
                        assets["images"].append(name)
                    elif ext in [".woff", ".woff2", ".ttf", ".otf"]:
                        assets["fonts"].append(name)
                    else:
                        assets["other"].append(name)

            return assets

        except Exception as e:
            logger.error(f"Failed to get theme assets for '{theme}': {e}")
            return {"css": [], "js": [], "images": [], "fonts": [], "other": []}

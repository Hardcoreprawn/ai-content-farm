"""
Legacy security utilities for Site Generator

Maintains backward compatibility with existing security methods
while integrating with new SecurityValidator system.
"""

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


class LegacySecurity:
    """Legacy security methods for backward compatibility."""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path injection (legacy method)."""
        # Use werkzeug's secure_filename, which strips dangerous characters
        safe_name = secure_filename(str(filename))
        # Remove any remaining path separators (defense in depth)
        safe_name = safe_name.replace("/", "_").replace("\\", "_")
        # Remove directory traversal sequences
        safe_name = safe_name.replace("..", "_")
        # Remove any remaining dots at the beginning
        safe_name = safe_name.lstrip(".")
        # Remove any leading special characters
        safe_name = safe_name.lstrip("_-")
        # Ensure it doesn't start with a dot or is empty, and limit length
        if not safe_name or len(safe_name) > 50:
            safe_name = "default"
        return safe_name

    @staticmethod
    def sanitize_blob_name(name: str) -> str:
        """Sanitize blob name to prevent path injection (legacy method)."""
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

    @staticmethod
    def validate_archive_path(archive_path: Path) -> None:
        """Validate archive path for security (legacy method)."""
        # Validate the original path structure first
        if not archive_path.name.endswith(".tar.gz"):
            raise ValueError("Archive file must have .tar.gz extension")

        # Sanitize the archive path to prevent injection
        sanitized_name = LegacySecurity.sanitize_filename(archive_path.name)
        if not sanitized_name.endswith(".tar.gz"):
            sanitized_name += ".tar.gz"

        # Validate the path doesn't escape expected directory structure
        temp_base = Path("/tmp").resolve()
        normalized_path = archive_path.resolve()
        try:
            normalized_path.relative_to(temp_base)
        except (ValueError, OSError):
            raise ValueError("Archive path is outside allowed directory structure")

        # Check if the file actually exists and is readable
        if not archive_path.exists() or not archive_path.is_file():
            raise ValueError("Archive file does not exist or is not accessible")

        # Additional validation: check file size is reasonable (prevent DoS)
        file_size = archive_path.stat().st_size
        max_size = 100 * 1024 * 1024  # 100MB limit
        if file_size > max_size:
            raise ValueError("Archive file exceeds maximum allowed size")

    @staticmethod
    def validate_site_directory(site_dir: Path) -> None:
        """Validate site directory path for security (legacy method)."""
        try:
            resolved_site_dir = site_dir.resolve()
            temp_base = Path("/tmp")
            resolved_site_dir.relative_to(temp_base)
        except (ValueError, OSError):
            logger.error("Site directory is outside allowed path")
            raise ValueError("Invalid site directory path")

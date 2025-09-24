"""
Security utilities for Site Generator

Provides path validation, filename sanitization, and other security functions.
Uses project standard libraries for consistency.
"""

import logging
import tempfile
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

# Use project standard werkzeug import (already in requirements)
try:
    from werkzeug.utils import secure_filename
except ImportError:
    # Fallback for testing environments
    def secure_filename(filename: str) -> str:
        """Fallback implementation when werkzeug is not available."""
        import re

        # Basic sanitization fallback
        return re.sub(r"[^a-zA-Z0-9._-]", "_", filename)


logger = logging.getLogger(__name__)


class SecurityValidator:
    """Security validation utilities for file operations."""

    # Constants for validation
    MAX_FILENAME_LENGTH = 50
    MAX_ARCHIVE_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_ARCHIVE_EXTENSIONS = [".tar.gz"]
    TEMP_BASE_DIR = Path("/tmp")

    def __init__(self):
        """Initialize security validator with unique instance ID."""
        self.validator_id = str(uuid4())[:8]
        logger.debug(f"SecurityValidator initialized: {self.validator_id}")

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path injection.

        Args:
            filename: The filename to sanitize

        Returns:
            A safe filename with dangerous characters removed
        """
        # Handle None or non-string input
        if filename is None:
            return "default"

        # Convert to string if not already
        filename = str(filename)

        # Use werkzeug's secure_filename, which strips dangerous characters
        safe_name = secure_filename(filename)

        # Remove any remaining path separators (defense in depth)
        safe_name = safe_name.replace("/", "_").replace("\\", "_")

        # Ensure it doesn't start with a dot or is empty, and limit length
        if (
            not safe_name
            or safe_name.startswith(".")
            or len(safe_name) > SecurityValidator.MAX_FILENAME_LENGTH
        ):
            safe_name = "default"

        return safe_name

    @staticmethod
    def sanitize_blob_name(name: str) -> str:
        """
        Sanitize blob name for safe storage operations.

        Args:
            name: The blob name to sanitize

        Returns:
            A safe blob name
        """
        if not name or not name.strip():
            # Generate a default name with timestamp
            from datetime import datetime, timezone

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            return f"site_archive_{timestamp}.tar.gz"

        # Extract extension if present
        name = str(name)
        extension = ""

        # Handle .tar.gz specifically first
        if name.endswith(".tar.gz"):
            name = name[:-7]  # Remove .tar.gz
            extension = ".tar.gz"
        elif name.endswith(".tgz"):
            name = name[:-4]  # Remove .tgz
            extension = ".tar.gz"
        elif "." in name:
            name_part, ext_part = name.rsplit(".", 1)
            if ext_part in ["tar", "zip", "7z"]:
                extension = f".{ext_part}"
            name = name_part

        # Use the same sanitization as filename
        safe_name = SecurityValidator.sanitize_filename(name)

        # Ensure we have an extension
        if not extension:
            extension = ".tar.gz"

        return safe_name + extension

    @staticmethod
    def validate_path_within_base(path: Path, base_dir: Path | None = None) -> bool:
        """
        Validate that a path is within the allowed base directory.

        Args:
            path: The path to validate
            base_dir: The base directory (defaults to /tmp)

        Returns:
            True if path is within base_dir, False otherwise
        """
        if base_dir is None:
            # Use secure temporary directory instead of hardcoded /tmp
            base_dir = Path(tempfile.gettempdir())

        try:
            resolved_path = path.resolve()
            resolved_base = base_dir.resolve()
            resolved_path.relative_to(resolved_base)
            return True
        except (ValueError, OSError):
            return False

    @staticmethod
    def validate_archive_file(archive_path: Path) -> None:
        """
        Validate an archive file for security requirements.

        Args:
            archive_path: Path to the archive file

        Raises:
            ValueError: If validation fails
        """
        # Check file extension
        if not any(
            archive_path.name.endswith(ext)
            for ext in SecurityValidator.ALLOWED_ARCHIVE_EXTENSIONS
        ):
            raise ValueError("Archive file must have .tar.gz extension")

        # Validate path is within allowed directory
        if not SecurityValidator.validate_path_within_base(archive_path):
            raise ValueError("Archive path is outside allowed directory structure")

        # Check if file exists and is readable
        if not archive_path.exists() or not archive_path.is_file():
            raise ValueError("Archive file does not exist or is not accessible")

        # Check file size
        try:
            file_size = archive_path.stat().st_size
            if file_size > SecurityValidator.MAX_ARCHIVE_SIZE:
                raise ValueError("Archive file exceeds maximum allowed size")
        except OSError as e:
            raise ValueError(f"Cannot access archive file: {str(e)}")

    @staticmethod
    def validate_site_directory(site_dir: Path) -> None:
        """
        Validate that a site directory is within allowed bounds.

        Args:
            site_dir: The site directory to validate

        Raises:
            ValueError: If validation fails
        """
        if not SecurityValidator.validate_path_within_base(site_dir):
            raise ValueError("Site directory is outside allowed path")

    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """
        Check if a filename is safe (doesn't contain dangerous patterns).

        Args:
            filename: The filename to check

        Returns:
            True if filename is safe, False otherwise
        """
        # Check for path traversal patterns
        dangerous_patterns = ["..", "/", "\\", ":", "*", "?", '"', "<", ">", "|"]

        for pattern in dangerous_patterns:
            if pattern in filename:
                return False

        return True

    @staticmethod
    def filter_safe_files(files: list) -> list:
        """
        Filter a list of files to only include safe ones.

        Args:
            files: List of filenames to filter

        Returns:
            List of safe filenames
        """
        safe_files = []
        for file in files:
            if (
                not file.startswith(".")
                and not file.startswith("..")
                and SecurityValidator.is_safe_filename(file)
            ):
                safe_files.append(file)
        return safe_files

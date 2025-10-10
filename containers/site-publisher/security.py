"""
Security validation functions for site-publisher.

All pure functions for validating input and preventing attacks.
"""

import re
from pathlib import Path
from typing import List

from models import ValidationResult


def validate_blob_name(blob_name: str) -> ValidationResult:
    """
    Validate blob name for security.

    Prevents:
    - Path traversal (../)
    - Absolute paths (/)
    - Special characters
    - Command injection attempts

    Args:
        blob_name: Blob name to validate

    Returns:
        ValidationResult with errors if invalid
    """
    errors: List[str] = []

    # Check for path traversal
    if ".." in blob_name:
        errors.append("Path traversal detected")

    # Check for absolute paths
    if blob_name.startswith("/"):
        errors.append("Absolute paths not allowed")

    # Check for suspicious patterns
    suspicious = [";", "|", "&", "$", "`", "&&", "||", "\n", "\r"]
    if any(char in blob_name for char in suspicious):
        errors.append("Suspicious characters detected")

    # Validate extension (markdown files only)
    if not blob_name.endswith(".md"):
        errors.append("Only .md files allowed")

    # Check length
    if len(blob_name) > 255:
        errors.append("Blob name too long")

    # Check for empty name
    if not blob_name or blob_name.isspace():
        errors.append("Blob name cannot be empty")

    return ValidationResult(is_valid=(len(errors) == 0), errors=errors)


def validate_path(path: Path, allowed_base: Path) -> ValidationResult:
    """
    Validate that path is within allowed base directory.

    Prevents path traversal attacks by ensuring the resolved path
    is within the allowed base directory.

    Args:
        path: Path to validate
        allowed_base: Base directory that path must be within

    Returns:
        ValidationResult with errors if invalid
    """
    try:
        # Resolve to absolute paths
        resolved_path = path.resolve()
        resolved_base = allowed_base.resolve()

        # Check if path is within base
        if not str(resolved_path).startswith(str(resolved_base)):
            return ValidationResult(
                is_valid=False,
                errors=[f"Path {path} is outside allowed base {allowed_base}"],
            )

        return ValidationResult(is_valid=True, errors=[])

    except Exception as e:
        return ValidationResult(
            is_valid=False, errors=[f"Path validation failed: {type(e).__name__}"]
        )


def sanitize_error_message(error: Exception) -> str:
    """
    Sanitize error message for safe logging.

    Removes:
    - File paths
    - URLs
    - Credentials
    - Sensitive data

    Args:
        error: Exception to sanitize

    Returns:
        Sanitized error message safe for logging
    """
    error_msg = str(error)

    # Remove URLs FIRST (before paths, so URL paths don't get partially matched)
    error_msg = re.sub(r"https?://[^\s]+", "[URL]", error_msg)

    # Remove paths (anything with /)
    error_msg = re.sub(r"/[^\s]+", "[PATH]", error_msg)

    # Remove Windows paths (anything with \)
    error_msg = re.sub(r"\\[^\s]+", "[PATH]", error_msg)

    # Remove potential credentials
    error_msg = re.sub(
        r"(key|token|password|secret|credential)=[^\s&]+",
        r"\1=[REDACTED]",
        error_msg,
        flags=re.IGNORECASE,
    )

    # Remove connection strings
    error_msg = re.sub(
        r"AccountKey=[^\s;]+", "AccountKey=[REDACTED]", error_msg, flags=re.IGNORECASE
    )

    # Limit length
    if len(error_msg) > 200:
        error_msg = error_msg[:200] + "..."

    return error_msg


def validate_hugo_output(output_dir: Path) -> ValidationResult:
    """
    Validate Hugo build output for security and completeness.

    Args:
        output_dir: Directory containing Hugo build output

    Returns:
        ValidationResult with errors if invalid
    """
    errors: List[str] = []

    # Check directory exists
    if not output_dir.exists():
        return ValidationResult(
            is_valid=False, errors=["Output directory does not exist"]
        )

    # Check index.html exists
    if not (output_dir / "index.html").exists():
        errors.append("Missing index.html")

    # Check for suspicious files
    suspicious_extensions = [".exe", ".sh", ".bat", ".ps1", ".dll", ".so"]
    for ext in suspicious_extensions:
        if list(output_dir.rglob(f"*{ext}")):
            errors.append(f"Suspicious file type found: {ext}")

    # Check total size (prevent DOS)
    try:
        total_size = sum(f.stat().st_size for f in output_dir.rglob("*") if f.is_file())
        max_size = 100 * 1024 * 1024  # 100 MB
        if total_size > max_size:
            errors.append(f"Build output too large: {total_size / (1024*1024):.1f} MB")
    except Exception as e:
        errors.append(f"Failed to check output size: {type(e).__name__}")

    # Check file count (prevent DOS)
    try:
        file_count = len(list(output_dir.rglob("*")))
        max_files = 10000
        if file_count > max_files:
            errors.append(f"Too many files in output: {file_count}")
    except Exception as e:
        errors.append(f"Failed to count files: {type(e).__name__}")

    return ValidationResult(is_valid=(len(errors) == 0), errors=errors)

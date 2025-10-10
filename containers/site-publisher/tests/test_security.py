"""
Tests for security validation functions.

Tests path traversal prevention, input validation, and sanitization.
"""

from pathlib import Path

import pytest
from security import (
    sanitize_error_message,
    validate_blob_name,
    validate_hugo_output,
    validate_path,
)


class TestValidateBlobName:
    """Tests for blob name validation."""

    def test_valid_blob_name(self):
        """Test that valid blob names pass validation."""
        result = validate_blob_name("articles/tech-news.md")
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_path_traversal_detected(self):
        """Test that path traversal attempts are blocked."""
        result = validate_blob_name("../../../etc/passwd.md")
        assert result.is_valid is False
        assert "Path traversal detected" in result.errors

    def test_absolute_path_rejected(self):
        """Test that absolute paths are rejected."""
        result = validate_blob_name("/etc/passwd.md")
        assert result.is_valid is False
        assert "Absolute paths not allowed" in result.errors

    def test_suspicious_characters_rejected(self):
        """Test that suspicious characters are rejected."""
        suspicious_names = [
            "test;rm -rf /.md",
            "test|cat /etc/passwd.md",
            "test&&echo bad.md",
            "test`whoami`.md",
        ]
        for name in suspicious_names:
            result = validate_blob_name(name)
            assert result.is_valid is False
            assert "Suspicious characters detected" in result.errors

    def test_non_markdown_rejected(self):
        """Test that non-markdown files are rejected."""
        result = validate_blob_name("test.txt")
        assert result.is_valid is False
        assert "Only .md files allowed" in result.errors

    def test_empty_name_rejected(self):
        """Test that empty names are rejected."""
        result = validate_blob_name("")
        assert result.is_valid is False
        assert "Blob name cannot be empty" in result.errors

    def test_long_name_rejected(self):
        """Test that overly long names are rejected."""
        long_name = "a" * 300 + ".md"
        result = validate_blob_name(long_name)
        assert result.is_valid is False
        assert "Blob name too long" in result.errors


class TestValidatePath:
    """Tests for path validation."""

    def test_valid_path_within_base(self, temp_dir):
        """Test that paths within base directory are valid."""
        base = temp_dir
        valid_path = base / "subdir" / "file.txt"

        result = validate_path(valid_path, base)
        assert result.is_valid is True

    def test_path_traversal_outside_base(self, temp_dir):
        """Test that path traversal outside base is blocked."""
        base = temp_dir / "safe"
        base.mkdir()

        # Try to escape via ..
        dangerous_path = base / ".." / ".." / "etc" / "passwd"

        result = validate_path(dangerous_path, base)
        assert result.is_valid is False
        assert "outside allowed base" in result.errors[0]


class TestSanitizeErrorMessage:
    """Tests for error message sanitization."""

    def test_sanitize_file_paths(self):
        """Test that file paths are removed."""
        error = Exception("File not found: /home/user/secret/data.txt")
        result = sanitize_error_message(error)

        assert "/home/user/secret/data.txt" not in result
        assert "[PATH]" in result

    def test_sanitize_urls(self):
        """Test that URLs are removed."""
        error = Exception("Failed to fetch: https://secret.com/api/key")
        result = sanitize_error_message(error)

        assert "https://secret.com/api/key" not in result
        assert "[URL]" in result

    def test_sanitize_credentials(self):
        """Test that credentials are redacted."""
        error = Exception("Connection failed: password=secret123")
        result = sanitize_error_message(error)

        assert "secret123" not in result
        assert "[REDACTED]" in result

    def test_truncate_long_messages(self):
        """Test that long messages are truncated."""
        long_message = "Error: " + ("x" * 300)
        error = Exception(long_message)
        result = sanitize_error_message(error)

        assert len(result) <= 203  # 200 + "..."


class TestValidateHugoOutput:
    """Tests for Hugo output validation."""

    def test_missing_output_directory(self, temp_dir):
        """Test validation fails if output directory doesn't exist."""
        non_existent = temp_dir / "nonexistent"
        result = validate_hugo_output(non_existent)

        assert result.is_valid is False
        assert "does not exist" in result.errors[0]

    def test_missing_index_html(self, temp_dir):
        """Test validation fails if index.html is missing."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        result = validate_hugo_output(output_dir)

        assert result.is_valid is False
        assert "Missing index.html" in result.errors

    def test_valid_output(self, temp_dir):
        """Test validation passes for valid Hugo output."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        # Create index.html
        (output_dir / "index.html").write_text("<html></html>")

        result = validate_hugo_output(output_dir)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_suspicious_files_detected(self, temp_dir):
        """Test that suspicious file types are detected."""
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        # Create index.html (valid)
        (output_dir / "index.html").write_text("<html></html>")

        # Create suspicious file
        (output_dir / "malware.exe").write_text("bad")

        result = validate_hugo_output(output_dir)

        assert result.is_valid is False
        assert any("Suspicious file type" in error for error in result.errors)

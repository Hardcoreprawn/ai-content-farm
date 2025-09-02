"""
Security tests for Site Generator

Tests path injection vulnerabilities and security fixes.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add the containers path to import the site generator
sys.path.insert(0, "/workspaces/ai-content-farm/containers/site-generator")

from site_generator import SiteGenerator


class TestSiteGeneratorSecurity:
    """Test security aspects of SiteGenerator."""

    @pytest.fixture
    def site_generator(self):
        """Create a SiteGenerator instance for testing."""
        with patch("site_generator.BlobStorageClient"):
            generator = SiteGenerator()
            generator.blob_client = AsyncMock()
            return generator

    @pytest.fixture
    def temp_archive(self):
        """Create a temporary archive file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as f:
            f.write(b"test archive content")
            yield Path(f.name)
        # Cleanup
        try:
            os.unlink(f.name)
        except OSError:
            pass

    def test_sanitize_filename_basic(self, site_generator):
        """Test basic filename sanitization."""
        # Test normal filename
        assert site_generator._sanitize_filename("normal_file.txt") == "normal_file.txt"

        # Test filename with path separators
        assert site_generator._sanitize_filename("../../../etc/passwd") == "passwd"
        assert site_generator._sanitize_filename("path/to/file.txt") == "file.txt"

        # Test filename with dangerous characters (gets heavily sanitized)
        result = site_generator._sanitize_filename("file;rm -rf /.txt")
        # Should be sanitized to remove dangerous characters
        assert ";" not in result
        assert "/" not in result
        assert "rm" not in result or result == "default"  # May be stripped completely

        # Test empty or invalid filename
        assert site_generator._sanitize_filename("") == "default"
        assert site_generator._sanitize_filename("../..") == "default"

    def test_sanitize_filename_path_traversal(self, site_generator):
        """Test filename sanitization against path traversal attacks."""
        dangerous_filenames = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "....//....//etc//passwd",
            "..\\..\\..\\/etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        ]

        for filename in dangerous_filenames:
            sanitized = site_generator._sanitize_filename(filename)
            # Key security checks
            assert ".." not in sanitized, f"Double dots found in: {sanitized}"
            assert "/" not in sanitized, f"Forward slash found in: {sanitized}"
            assert "\\" not in sanitized, f"Backslash found in: {sanitized}"
            # The result should be safe (without path traversal elements)
            assert len(sanitized) <= 50, f"Filename too long: {sanitized}"
            # Should not be empty
            assert sanitized != "", f"Empty result for: {filename}"

    def test_sanitize_blob_name(self, site_generator):
        """Test blob name sanitization."""
        # Test normal blob name
        assert site_generator._sanitize_blob_name("archive.tar.gz") == "archive.tar.gz"

        # Test blob name with path separators
        assert (
            site_generator._sanitize_blob_name("../malicious.tar.gz")
            == "malicious.tar.gz"
        )

        # Test empty blob name gets default
        result = site_generator._sanitize_blob_name("")
        assert result.startswith("site_archive_")
        assert result.endswith(".tar.gz")

    @pytest.mark.asyncio
    async def test_upload_site_archive_path_validation(
        self, site_generator, temp_archive
    ):
        """Test that upload_site_archive validates paths properly."""
        # Test with a file outside /tmp directory (should fail)
        dangerous_path = Path("/etc/passwd")

        with pytest.raises(ValueError, match="Invalid archive path"):
            await site_generator._upload_site_archive(dangerous_path)

    @pytest.mark.asyncio
    async def test_upload_site_archive_file_extension(self, site_generator):
        """Test that upload_site_archive validates file extensions."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test content")
            txt_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Invalid archive path"):
                await site_generator._upload_site_archive(txt_path)
        finally:
            os.unlink(txt_path)

    @pytest.mark.asyncio
    async def test_upload_site_archive_file_size_limit(self, site_generator):
        """Test that upload_site_archive enforces file size limits."""
        # Create a large file that exceeds the limit
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as f:
            # Write more than 100MB (the limit in our code)
            large_data = b"x" * (101 * 1024 * 1024)  # 101MB
            f.write(large_data)
            large_file_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Invalid archive path"):
                await site_generator._upload_site_archive(large_file_path)
        finally:
            os.unlink(large_file_path)

    @pytest.mark.asyncio
    async def test_create_site_archive_path_validation(self, site_generator):
        """Test that _create_site_archive validates paths properly."""
        # Test with a directory outside /tmp (should fail)
        dangerous_dir = Path("/etc")

        with pytest.raises(ValueError, match="Invalid site directory path"):
            await site_generator._create_site_archive(dangerous_dir, "test_theme")

    @pytest.mark.asyncio
    async def test_create_site_archive_theme_sanitization(self, site_generator):
        """Test that _create_site_archive sanitizes theme names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            site_dir = Path(temp_dir) / "site"
            site_dir.mkdir()

            # Create a test file
            test_file = site_dir / "test.html"
            test_file.write_text("<html>test</html>")

            # Test with dangerous theme name
            dangerous_theme = "../../../malicious_theme"

            archive_path = await site_generator._create_site_archive(
                site_dir, dangerous_theme
            )

            # Verify the archive filename is sanitized
            assert ".." not in archive_path.name
            assert "/" not in archive_path.name
            assert (
                "malicious_theme" in archive_path.name or "default" in archive_path.name
            )

    def test_filename_length_limit(self, site_generator):
        """Test that extremely long filenames are handled safely."""
        long_filename = "a" * 200  # Very long filename
        sanitized = site_generator._sanitize_filename(long_filename)
        assert len(sanitized) <= 50

    def test_special_characters_removal(self, site_generator):
        """Test that special characters are properly removed or replaced."""
        special_chars_filename = 'file<>:"|?*name.txt'
        sanitized = site_generator._sanitize_filename(special_chars_filename)

        # Should not contain any of these special characters
        dangerous_chars = ["<", ">", ":", '"', "|", "?", "*"]
        for char in dangerous_chars:
            assert char not in sanitized

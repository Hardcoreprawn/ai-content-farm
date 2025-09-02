"""
Comprehensive Security tests for Site Generator

Tests path injection vulnerabilities, security fixes, and integration with
refactored security utilities for complete coverage.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from file_operations import ArchiveManager
from security_utils import SecurityValidator
from site_generator import SiteGenerator

# Add the containers path to import the site generator and new modules
sys.path.insert(
    0, str((Path(__file__).parent.parent / "containers" / "site-generator").resolve())
)


class TestSiteGeneratorSecurity:
    """Comprehensive security tests for SiteGenerator."""

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

    # ========== Architecture Integration Tests ==========

    def test_site_generator_uses_security_validator(self, site_generator):
        """Test that SiteGenerator uses the SecurityValidator properly."""
        assert hasattr(site_generator, "security_validator")
        assert isinstance(site_generator.security_validator, SecurityValidator)

    def test_site_generator_uses_archive_manager(self, site_generator):
        """Test that SiteGenerator uses the ArchiveManager properly."""
        assert hasattr(site_generator, "archive_manager")
        assert isinstance(site_generator.archive_manager, ArchiveManager)

    def test_generator_id_follows_project_standards(self, site_generator):
        """Test that generator ID follows project UUID standards."""
        assert hasattr(site_generator, "generator_id")
        assert len(site_generator.generator_id) == 8
        assert site_generator.generator_id.isalnum()

    # ========== Legacy Method Security Tests ==========

    def test_sanitize_filename_basic(self, site_generator):
        """Test basic filename sanitization."""
        # Test normal filename
        assert site_generator._sanitize_filename("normal_file.txt") == "normal_file.txt"

        # Test filename with path separators
        assert site_generator._sanitize_filename("../../../etc/passwd") == "etc_passwd"
        assert (
            site_generator._sanitize_filename("path/to/file.txt") == "path_to_file.txt"
        )

        # Test empty and None inputs
        assert site_generator._sanitize_filename("") == "default"
        # Current behavior converts None to string
        assert site_generator._sanitize_filename(None) == "None"

        # Test whitespace
        assert site_generator._sanitize_filename("   ") == "default"

    def test_sanitize_filename_path_traversal(self, site_generator):
        """Test filename sanitization against path traversal attacks."""
        # Test various path traversal attempts
        dangerous_inputs = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "....//....//etc//passwd",
            "../../../../../../etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "..\\..\\..",
            "/../../etc/passwd",
            "\\..\\..\\etc\\passwd",
        ]

        expected_safe_results = {
            "etc_passwd",
            "windowssystem32configsam",
            "2F_2F_2Fetc2Fpasswd",
            "default",
            "etcpasswd",
        }

        for dangerous_input in dangerous_inputs:
            result = site_generator._sanitize_filename(dangerous_input)
            # Should not contain path traversal sequences
            assert ".." not in result
            assert "/" not in result
            assert "\\" not in result
            # Should be one of the expected safe results
            assert result in expected_safe_results

    def test_sanitize_blob_name(self, site_generator):
        """Test blob name sanitization."""
        # Test normal blob name
        assert site_generator._sanitize_blob_name("archive.tar.gz") == "archive.tar.gz"

        # Test path traversal
        result = site_generator._sanitize_blob_name("../../../etc/passwd")
        assert result == "passwd"

        # Test special characters
        result = site_generator._sanitize_blob_name("file@#$%^&*()name.tar.gz")
        assert all(c.isalnum() or c in "._-" for c in result if c != "/")

    async def test_upload_site_archive_path_validation(
        self, site_generator, temp_archive
    ):
        """Test that upload validates archive paths properly."""
        # Should work with valid temp file
        await site_generator._upload_site_archive(temp_archive)

        # Should fail with path outside /tmp
        invalid_path = Path("/etc/passwd")
        with pytest.raises(ValueError, match="Invalid archive path"):
            await site_generator._upload_site_archive(invalid_path)

    async def test_upload_site_archive_file_extension(self, site_generator):
        """Test that upload validates file extensions."""
        # Create a file without .tar.gz extension
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test content")
            invalid_path = Path(f.name)

        try:
            with pytest.raises(
                ValueError, match="Archive file must have .tar.gz extension"
            ):
                await site_generator._upload_site_archive(invalid_path)
        finally:
            os.unlink(invalid_path)

    async def test_upload_site_archive_file_size_limit(self, site_generator):
        """Test that upload enforces file size limits."""
        # Create a large file (over 100MB limit)
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as f:
            # Write 101MB of data
            chunk = b"x" * (1024 * 1024)  # 1MB chunk
            for _ in range(101):
                f.write(chunk)
            large_file = Path(f.name)

        try:
            with pytest.raises(
                ValueError, match="Archive file exceeds maximum allowed size"
            ):
                await site_generator._upload_site_archive(large_file)
        finally:
            os.unlink(large_file)

    async def test_create_site_archive_path_validation(self, site_generator):
        """Test that archive creation validates site directory paths."""
        # Should fail with directory outside /tmp
        invalid_dir = Path("/etc")
        with pytest.raises(ValueError, match="Invalid site directory path"):
            await site_generator._create_site_archive(invalid_dir, "test_theme")

    async def test_create_site_archive_theme_sanitization(self, site_generator):
        """Test that theme names are properly sanitized in archive creation."""
        with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
            site_dir = Path(temp_dir)

            # Create a test file
            test_file = site_dir / "index.html"
            test_file.write_text("<html><body>Test</body></html>")

            # Test with malicious theme name
            malicious_theme = "../../../etc/passwd"
            result = await site_generator._create_site_archive(
                site_dir, malicious_theme
            )

            # Archive should be created safely
            assert result.exists()
            assert result.suffix == ".gz"
            assert "passwd" in result.name or "default" in result.name

            # Cleanup
            os.unlink(result)

    def test_filename_length_limit(self, site_generator):
        """Test that filename length is properly limited."""
        long_filename = "a" * 100  # Very long filename
        result = site_generator._sanitize_filename(long_filename)
        assert len(result) <= 50 or result == "default"

    def test_special_characters_removal(self, site_generator):
        """Test that special characters are properly handled."""
        filename_with_specials = 'file<>:"|?*name.txt'
        result = site_generator._sanitize_filename(filename_with_specials)
        # Should not contain dangerous characters
        dangerous_chars = '<>:"|?*'
        assert not any(char in result for char in dangerous_chars)

    # ========== Integration Tests ==========

    def test_filename_sanitization_integration(self, site_generator):
        """Test filename sanitization through both old and new systems."""
        test_filename = "../../../dangerous/path/file.txt"

        # Test legacy method
        legacy_result = site_generator._sanitize_filename(test_filename)

        # Test SecurityValidator method
        validator_result = site_generator.security_validator.sanitize_filename(
            test_filename
        )

        # Both should be secure (though may differ in implementation)
        assert ".." not in legacy_result
        assert ".." not in validator_result
        assert "/" not in legacy_result
        assert "/" not in validator_result

    def test_blob_name_sanitization_integration(self, site_generator):
        """Test blob name sanitization integration."""
        test_blob = "../../../dangerous/blob.tar.gz"

        # Test legacy method
        legacy_result = site_generator._sanitize_blob_name(test_blob)

        # Test SecurityValidator method
        validator_result = site_generator.security_validator.sanitize_blob_name(
            test_blob
        )

        # Both should be secure
        assert ".." not in legacy_result
        assert ".." not in validator_result

    async def test_archive_creation_security_integration(self, site_generator):
        """Test that archive creation uses security validation properly."""
        with tempfile.TemporaryDirectory(dir="/tmp") as temp_dir:
            site_dir = Path(temp_dir)

            # Create test files
            (site_dir / "index.html").write_text("<html>Test</html>")
            (site_dir / "style.css").write_text("body { margin: 0; }")

            # Test through ArchiveManager
            archive_path = await site_generator.archive_manager.create_archive(
                site_dir, "test_theme"
            )

            assert archive_path.exists()
            assert archive_path.suffix == ".gz"
            assert archive_path.parent == Path("/tmp")

            # Cleanup
            os.unlink(archive_path)

    def test_legacy_security_coverage_maintained(self, site_generator):
        """Test that legacy security methods still provide expected protection."""
        # Path traversal protection
        assert site_generator._sanitize_filename("../../../etc/passwd") == "etc_passwd"

        # Empty/None handling
        assert site_generator._sanitize_filename("") == "default"
        assert site_generator._sanitize_filename(None) == "None"

        # Special character filtering
        result = site_generator._sanitize_filename("file<>name.txt")
        assert "<" not in result and ">" not in result

        # Length limiting
        long_name = "x" * 100
        result = site_generator._sanitize_filename(long_name)
        assert len(result) <= 50 or result == "default"

    def test_security_constants_reasonable(self, site_generator):
        """Test that security constants are within reasonable bounds."""
        # File size limit should be reasonable (100MB)
        # This is tested indirectly through the upload size limit test

        # Filename length limit should be reasonable (50 chars)
        long_filename = "a" * 60
        result = site_generator._sanitize_filename(long_filename)
        assert len(result) <= 50 or result == "default"

        # Generator ID should be reasonable length
        assert 4 <= len(site_generator.generator_id) <= 16

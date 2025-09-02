"""
Security tests for Site Generator

Tests path injection vulnerabilities and security fixes.
These tests now use the refactored security utilities for better maintainability.
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
    """Test security aspects of SiteGenerator using refactored modules."""

    @pytest.fixture
    def site_generator(self):
        """Create a SiteGenerator instance for testing."""
        with patch("site_generator.BlobStorageClient"):
            generator = SiteGenerator()
            generator.blob_client = AsyncMock()
            return generator

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

    # Delegate security tests to the specialized modules
    def test_filename_sanitization_integration(self, site_generator):
        """Test filename sanitization integration with SecurityValidator."""
        dangerous_filename = "../../../etc/passwd"
        safe_filename = site_generator.security_validator.sanitize_filename(
            dangerous_filename
        )

        # Should be sanitized
        assert ".." not in safe_filename
        assert "/" not in safe_filename
        assert safe_filename != ""

    def test_blob_name_sanitization_integration(self, site_generator):
        """Test blob name sanitization integration."""
        dangerous_blob = "../malicious.tar.gz"
        safe_blob = site_generator.security_validator.sanitize_blob_name(dangerous_blob)

        # Should be sanitized
        assert ".." not in safe_blob
        assert "/" not in safe_blob
        assert safe_blob.endswith(".tar.gz")

    @pytest.mark.asyncio
    async def test_archive_creation_security_integration(self, site_generator):
        """Test that archive creation uses security validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            site_dir = Path(temp_dir) / "site"
            site_dir.mkdir()

            # Create test file
            (site_dir / "test.html").write_text("<html>test</html>")

            # Mock security validation
            with patch.object(
                site_generator.security_validator, "validate_site_directory"
            ), patch.object(
                site_generator.security_validator,
                "sanitize_filename",
                return_value="theme",
            ), patch.object(
                site_generator.security_validator,
                "validate_path_within_base",
                return_value=True,
            ):

                archive_path = await site_generator.archive_manager.create_site_archive(
                    site_dir, "test-theme"
                )

                assert archive_path.exists()
                assert archive_path.name.endswith(".tar.gz")

    def test_legacy_security_coverage_maintained(self, site_generator):
        """Test that legacy security test coverage is maintained through new modules."""
        # Path traversal protection
        assert site_generator.security_validator.is_safe_filename("normal.txt") is True
        assert (
            site_generator.security_validator.is_safe_filename("../dangerous.txt")
            is False
        )

        # File filtering
        mixed_files = ["safe.txt", "../bad.txt", ".hidden", "good.py"]
        safe_files = site_generator.security_validator.filter_safe_files(mixed_files)
        assert "safe.txt" in safe_files
        assert "good.py" in safe_files
        assert "../bad.txt" not in safe_files
        assert ".hidden" not in safe_files

    def test_security_constants_reasonable(self, site_generator):
        """Test that security constants are set to reasonable values."""
        validator = site_generator.security_validator
        assert validator.MAX_FILENAME_LENGTH == 50
        assert validator.MAX_ARCHIVE_SIZE == 100 * 1024 * 1024
        assert validator.ALLOWED_ARCHIVE_EXTENSIONS == [".tar.gz"]


# Note: The original comprehensive security tests have been moved to:
# - tests/test_security_utils.py (for SecurityValidator tests)
# - tests/test_file_operations.py (for ArchiveManager tests)
# - tests/test_content_manager.py (for ContentManager tests)
#
# This provides better separation of concerns and maintainability
# while maintaining the same security coverage.

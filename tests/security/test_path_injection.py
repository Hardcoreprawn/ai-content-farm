"""
Security tests for path injection vulnerabilities in site generator.
These tests verify that our fixes prevent directory traversal and path injection attacks.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add containers to path for imports
sys.path.append(
    os.path.join(os.path.dirname(__file__), "..", "..", "containers", "site-generator")
)


class TestPathInjectionSecurity:
    """Test suite for path injection security vulnerabilities."""

    def setup_method(self):
        """Set up test environment with mocked dependencies."""
        # Mock configuration
        self.mock_config = MagicMock()
        self.mock_config.STATIC_SITES_CONTAINER = "static-sites"

        # Mock blob client
        self.mock_blob_client = MagicMock()

    def test_sanitize_filename_basic_cases(self):
        """Test _sanitize_filename method with basic safe inputs."""
        try:
            from site_generator import SiteGenerator

            # Create instance with mocked dependencies
            with patch("site_generator.Config") as mock_config_class:
                mock_config_class.return_value = self.mock_config
                with patch("site_generator.BlobStorageClient") as mock_blob_class:
                    mock_blob_class.return_value = self.mock_blob_client

                    generator = SiteGenerator()

                    # Test basic safe filenames
                    assert generator._sanitize_filename("minimal") == "minimal"
                    assert generator._sanitize_filename("dark-theme") == "dark-theme"
                    assert generator._sanitize_filename("theme_v1.2") == "theme_v1.2"

        except ImportError as e:
            pytest.skip(f"Site generator module not available: {e}")

    def test_sanitize_filename_path_injection_attacks(self):
        """Test _sanitize_filename prevents various path injection attacks."""
        try:
            from site_generator import SiteGenerator

            with patch("site_generator.Config") as mock_config_class:
                mock_config_class.return_value = self.mock_config
                with patch("site_generator.BlobStorageClient") as mock_blob_class:
                    mock_blob_class.return_value = self.mock_blob_client

                    generator = SiteGenerator()

                    # Test directory traversal attacks
                    malicious_inputs = [
                        "../../../etc/passwd",
                        "..\\..\\..\\windows\\system32\\config\\sam",
                        "../../../../../../etc/shadow",
                        "/etc/passwd",
                        "\\windows\\system32\\drivers\\etc\\hosts",
                        "../config.json",
                        "./../../database.sqlite",
                        "theme/../../../secrets.txt",
                        "theme/../../application.log",
                        "theme\\..\\..\\config.ini",
                    ]

                    for malicious_input in malicious_inputs:
                        sanitized = generator._sanitize_filename(malicious_input)

                        # Should not contain path separators
                        assert (
                            "/" not in sanitized
                        ), f"Forward slash found in sanitized input: {sanitized}"
                        assert (
                            "\\" not in sanitized
                        ), f"Backslash found in sanitized input: {sanitized}"
                        assert (
                            ".." not in sanitized
                        ), f"Directory traversal sequence found: {sanitized}"

                        # Should not start with dots
                        assert not sanitized.startswith(
                            "."
                        ), f"Sanitized filename starts with dot: {sanitized}"

                        print(f"✅ {malicious_input} → {sanitized}")

        except ImportError as e:
            pytest.skip(f"Site generator module not available: {e}")

    def test_sanitize_filename_special_characters(self):
        """Test _sanitize_filename removes dangerous special characters."""
        try:
            from site_generator import SiteGenerator

            with patch("site_generator.Config") as mock_config_class:
                mock_config_class.return_value = self.mock_config
                with patch("site_generator.BlobStorageClient") as mock_blob_class:
                    mock_blob_class.return_value = self.mock_blob_client

                    generator = SiteGenerator()

                    # Test special characters that could be dangerous
                    dangerous_chars = [
                        "theme;rm -rf /",
                        "theme|cat /etc/passwd",
                        "theme&whoami",
                        "theme$(id)",
                        "theme`uname -a`",
                        "theme'OR'1'='1",
                        'theme"OR"1"="1',
                        "theme<script>alert(1)</script>",
                        "theme%2e%2e%2f",  # URL encoded ../
                        "theme\x00null",  # Null byte
                        "theme\r\ncarriage-return",  # CRLF injection
                    ]

                    for dangerous_input in dangerous_chars:
                        sanitized = generator._sanitize_filename(dangerous_input)

                        # Should only contain safe characters
                        allowed_chars = set(
                            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
                        )
                        sanitized_chars = set(sanitized)

                        assert sanitized_chars.issubset(
                            allowed_chars
                        ), f"Sanitized filename contains unsafe characters: {sanitized}"

                        print(f"✅ {dangerous_input} → {sanitized}")

        except ImportError as e:
            pytest.skip(f"Site generator module not available: {e}")

    def test_sanitize_filename_edge_cases(self):
        """Test _sanitize_filename handles edge cases properly."""
        try:
            from site_generator import SiteGenerator

            with patch("site_generator.Config") as mock_config_class:
                mock_config_class.return_value = self.mock_config
                with patch("site_generator.BlobStorageClient") as mock_blob_class:
                    mock_blob_class.return_value = self.mock_blob_client

                    generator = SiteGenerator()

                    # Test edge cases
                    edge_cases = [
                        "",  # Empty string
                        ".",  # Just a dot
                        "..",  # Directory traversal
                        "...",  # Multiple dots
                        "---",  # Just dashes
                        "___",  # Just underscores
                        "_._",  # Mixed special chars
                        "a" * 200,  # Very long string
                        "CON",  # Windows reserved name
                        "PRN",  # Windows reserved name
                        "AUX",  # Windows reserved name
                    ]

                    for edge_case in edge_cases:
                        sanitized = generator._sanitize_filename(edge_case)

                        # Should always return a valid, safe string
                        assert isinstance(
                            sanitized, str
                        ), "Sanitized result must be a string"
                        assert len(sanitized) > 0, "Sanitized result must not be empty"
                        assert (
                            len(sanitized) <= 50
                        ), "Sanitized result must not be too long"

                        # Should not start with special characters
                        if sanitized:
                            assert not sanitized.startswith(
                                (".", "_", "-")
                            ), f"Sanitized filename starts with special char: {sanitized}"

                        print(f"✅ '{edge_case}' → '{sanitized}'")

        except ImportError as e:
            pytest.skip(f"Site generator module not available: {e}")

    @pytest.mark.asyncio
    async def test_create_site_archive_path_validation(self):
        """Test that _create_site_archive properly sanitizes theme parameter."""
        try:
            from site_generator import SiteGenerator

            with patch("site_generator.Config") as mock_config_class:
                mock_config_class.return_value = self.mock_config
                with patch("site_generator.BlobStorageClient") as mock_blob_class:
                    mock_blob_class.return_value = self.mock_blob_client

                    generator = SiteGenerator()

                    # Create a temporary directory for testing
                    with tempfile.TemporaryDirectory() as temp_dir:
                        site_dir = Path(temp_dir) / "site"
                        site_dir.mkdir()

                        # Create a test file in the site directory
                        test_file = site_dir / "index.html"
                        test_file.write_text("<html><body>Test</body></html>")

                        # Test with malicious theme names
                        malicious_themes = [
                            "../../../etc/passwd",
                            "..\\..\\config",
                            "/etc/shadow",
                            "theme;rm -rf /",
                            "theme|cat secrets",
                        ]

                        for malicious_theme in malicious_themes:
                            # This should not raise an exception and should create a safe path
                            archive_path = await generator._create_site_archive(
                                site_dir, malicious_theme
                            )

                            # Verify the archive path is safe
                            assert (
                                archive_path.is_absolute()
                            ), "Archive path should be absolute"
                            assert (
                                archive_path.suffix == ".gz"
                            ), "Archive should be .tar.gz"
                            assert archive_path.name.endswith(
                                ".tar.gz"
                            ), "Archive should end with .tar.gz"

                            # Verify the archive path doesn't contain malicious components
                            path_str = str(archive_path)
                            assert (
                                "../" not in path_str
                            ), f"Archive path contains traversal: {path_str}"
                            assert (
                                "..\\" not in path_str
                            ), f"Archive path contains traversal: {path_str}"

                            # Verify the archive file actually exists
                            assert (
                                archive_path.exists()
                            ), f"Archive file should exist: {archive_path}"

                            # Clean up
                            if archive_path.exists():
                                archive_path.unlink()

                            print(
                                f"✅ Safe archive created for malicious theme: {malicious_theme}"
                            )

        except ImportError as e:
            pytest.skip(f"Site generator module not available: {e}")

    @pytest.mark.asyncio
    async def test_upload_site_archive_path_validation(self):
        """Test that _upload_site_archive validates archive paths properly."""
        try:
            from site_generator import SiteGenerator

            with patch("site_generator.Config") as mock_config_class:
                mock_config_class.return_value = self.mock_config
                with patch("site_generator.BlobStorageClient") as mock_blob_class:
                    mock_blob_class.return_value = self.mock_blob_client

                    generator = SiteGenerator()

                    # Test with various malicious paths
                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_path = Path(temp_dir)

                        # Create a legitimate archive file
                        legit_archive = temp_path / "legit_site.tar.gz"
                        legit_archive.write_bytes(b"fake gzip content")

                        # Test legitimate file works
                        try:
                            await generator._upload_site_archive(legit_archive)
                            # Should call upload_binary
                            generator.blob_client.upload_binary.assert_called_once()
                        except Exception as e:
                            # Expected if upload fails, but should not be due to path validation
                            assert "Invalid archive path" not in str(e)

                        # Reset mock
                        generator.blob_client.upload_binary.reset_mock()

                        # Test malicious paths that should be rejected
                        malicious_paths = [
                            Path("/etc/passwd"),
                            Path("../../../etc/shadow"),
                            Path("..\\..\\windows\\system32\\config\\sam"),
                            temp_path / "nonexistent.tar.gz",  # File that doesn't exist
                            temp_path / "not_archive.txt",  # Wrong extension
                        ]

                        for malicious_path in malicious_paths:
                            if malicious_path.name == "not_archive.txt":
                                malicious_path.write_text("not an archive")

                            with pytest.raises(
                                ValueError, match="Invalid archive path"
                            ):
                                await generator._upload_site_archive(malicious_path)

                            # Should not call upload_binary for invalid paths
                            generator.blob_client.upload_binary.assert_not_called()

                            print(f"✅ Rejected malicious path: {malicious_path}")

        except ImportError as e:
            pytest.skip(f"Site generator module not available: {e}")

    @pytest.mark.asyncio
    async def test_symlink_attack_prevention(self):
        """Test that symlink attacks are prevented."""
        try:
            from site_generator import SiteGenerator

            with patch("site_generator.Config") as mock_config_class:
                mock_config_class.return_value = self.mock_config
                with patch("site_generator.BlobStorageClient") as mock_blob_class:
                    mock_blob_class.return_value = self.mock_blob_client

                    generator = SiteGenerator()

                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_path = Path(temp_dir)

                        # Create a legitimate archive
                        real_archive = temp_path / "real_archive.tar.gz"
                        real_archive.write_bytes(b"real archive content")

                        # Try to create a symlink to sensitive file (if possible)
                        try:
                            symlink_path = temp_path / "malicious_link.tar.gz"
                            if os.name != "nt":  # Unix-like systems
                                # Try to create symlink to /etc/passwd
                                if Path("/etc/passwd").exists():
                                    symlink_path.symlink_to("/etc/passwd")

                                    # This should be rejected due to validation
                                    with pytest.raises(
                                        ValueError, match="Invalid archive path"
                                    ):
                                        await generator._upload_site_archive(
                                            symlink_path
                                        )

                                    print("✅ Symlink attack prevented")
                                else:
                                    print(
                                        "⚠️ /etc/passwd not available for symlink test"
                                    )
                            else:
                                print("⚠️ Symlink test skipped on Windows")

                        except (OSError, NotImplementedError):
                            print(
                                "⚠️ Symlink creation not supported in test environment"
                            )

        except ImportError as e:
            pytest.skip(f"Site generator module not available: {e}")


if __name__ == "__main__":
    """Run path injection security tests directly."""
    print("🔒 Running path injection security tests...")

    test_suite = TestPathInjectionSecurity()
    test_suite.setup_method()

    try:
        test_suite.test_sanitize_filename_basic_cases()
        test_suite.test_sanitize_filename_path_injection_attacks()
        test_suite.test_sanitize_filename_special_characters()
        test_suite.test_sanitize_filename_edge_cases()
        print("🎉 All path injection security tests completed!")
    except Exception as e:
        print(f"❌ Tests failed: {e}")
        raise

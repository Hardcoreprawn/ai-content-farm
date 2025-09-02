"""
Comprehensive tests for file operations utilities

Tests archive creation, upload, and file management functionality.
Follows project standards for test coverage (~70%).
"""

import os

# Add the containers path to import the file operations utilities
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from file_operations import ArchiveManager, StaticAssetManager

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))


class TestArchiveManager:
    """Test archive management functionality."""

    @pytest.fixture
    def mock_blob_client(self):
        """Create a mock blob client for testing."""
        mock_client = Mock()
        mock_client.upload_binary = Mock()
        return mock_client

    @pytest.fixture
    def archive_manager(self, mock_blob_client):
        """Create an ArchiveManager instance for testing."""
        return ArchiveManager(blob_client=mock_blob_client)

    @pytest.fixture
    def archive_manager_no_client(self):
        """Create an ArchiveManager without blob client."""
        return ArchiveManager()

    @pytest.fixture
    def temp_site_dir(self):
        """Create a temporary site directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            site_dir = Path(temp_dir) / "site"
            site_dir.mkdir()

            # Create test files
            (site_dir / "index.html").write_text("<html>test</html>")
            (site_dir / "style.css").write_text("body { color: red; }")

            # Create subdirectory with file
            sub_dir = site_dir / "articles"
            sub_dir.mkdir()
            (sub_dir / "article1.html").write_text("<article>content</article>")

            yield site_dir

    def test_archive_manager_initialization(self, archive_manager):
        """Test that ArchiveManager initializes properly."""
        assert hasattr(archive_manager, "archive_id")
        assert len(archive_manager.archive_id) == 8
        assert archive_manager.archive_id.isalnum()
        assert hasattr(archive_manager, "security_validator")
        assert archive_manager.blob_client is not None

    def test_archive_manager_no_client_initialization(self, archive_manager_no_client):
        """Test ArchiveManager initialization without blob client."""
        assert archive_manager_no_client.blob_client is None
        assert hasattr(archive_manager_no_client, "archive_id")

    @pytest.mark.asyncio
    async def test_create_site_archive_success(self, archive_manager, temp_site_dir):
        """Test successful site archive creation."""
        # Mock security validation to pass
        with patch("file_operations.SecurityValidator.validate_site_directory"), patch(
            "file_operations.SecurityValidator.sanitize_filename",
            return_value="test_theme",
        ), patch(
            "file_operations.SecurityValidator.validate_path_within_base",
            return_value=True,
        ):

            archive_path = await archive_manager.create_site_archive(
                temp_site_dir, "test-theme"
            )

            assert archive_path.exists()
            assert archive_path.suffix == ".gz"
            assert archive_path.name.startswith("site_test_theme_")
            assert archive_path.name.endswith(".tar.gz")

    @pytest.mark.asyncio
    async def test_create_site_archive_invalid_directory(self, archive_manager):
        """Test archive creation with invalid site directory."""
        invalid_dir = Path("/etc")

        # Mock security validation to fail
        with patch(
            "file_operations.SecurityValidator.validate_site_directory",
            side_effect=ValueError("Invalid site directory path"),
        ):

            with pytest.raises(ValueError, match="Invalid site directory path"):
                await archive_manager.create_site_archive(invalid_dir, "theme")

    @pytest.mark.asyncio
    async def test_create_site_archive_path_validation_failure(
        self, archive_manager, temp_site_dir
    ):
        """Test archive creation when archive path validation fails."""
        with patch("file_operations.SecurityValidator.validate_site_directory"), patch(
            "file_operations.SecurityValidator.sanitize_filename", return_value="theme"
        ), patch(
            "file_operations.SecurityValidator.validate_path_within_base",
            return_value=False,
        ):

            with pytest.raises(
                ValueError, match="Archive file path is outside allowed base directory"
            ):
                await archive_manager.create_site_archive(temp_site_dir, "theme")

    def test_add_files_to_archive(self, archive_manager, temp_site_dir):
        """Test adding files to archive safely."""
        import tarfile

        # Create a test archive
        with tempfile.NamedTemporaryFile(
            suffix=".tar.gz", delete=False
        ) as temp_archive:
            with tarfile.open(temp_archive.name, "w:gz") as tar:
                archive_manager._add_files_to_archive(tar, temp_site_dir)

            # Verify archive contents
            with tarfile.open(temp_archive.name, "r:gz") as tar:
                members = tar.getnames()
                assert "index.html" in members
                assert "style.css" in members
                assert "articles/article1.html" in members

                # Verify no dangerous paths
                for member in members:
                    assert not member.startswith("/")
                    assert ".." not in member

        os.unlink(temp_archive.name)

    def test_add_files_to_archive_filters_dangerous_files(self, archive_manager):
        """Test that dangerous files are filtered during archive creation."""
        import tarfile

        with tempfile.TemporaryDirectory() as temp_dir:
            site_dir = Path(temp_dir)

            # Create mix of safe and dangerous files
            (site_dir / "safe_file.txt").write_text("safe")
            (site_dir / ".hidden_file").write_text("hidden")
            (site_dir / "..parent_ref").write_text("dangerous")

            # Create dangerous subdirectory
            dangerous_dir = site_dir / "..dangerous"
            dangerous_dir.mkdir(exist_ok=True)
            (dangerous_dir / "file.txt").write_text("should not be included")

            with tempfile.NamedTemporaryFile(
                suffix=".tar.gz", delete=False
            ) as temp_archive:
                with tarfile.open(temp_archive.name, "w:gz") as tar:
                    archive_manager._add_files_to_archive(tar, site_dir)

                # Verify only safe files are included
                with tarfile.open(temp_archive.name, "r:gz") as tar:
                    members = tar.getnames()
                    assert "safe_file.txt" in members

                    # Dangerous files should be filtered
                    dangerous_names = [
                        name for name in members if name.startswith(".") or ".." in name
                    ]
                    assert len(dangerous_names) == 0

            os.unlink(temp_archive.name)

    @pytest.mark.asyncio
    async def test_upload_archive_success(self, archive_manager):
        """Test successful archive upload."""
        # Create a test archive file
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as temp_file:
            temp_file.write(b"test archive content")
            archive_path = Path(temp_file.name)

        try:
            # Mock validation to pass
            with patch(
                "file_operations.SecurityValidator.validate_archive_file"
            ), patch(
                "file_operations.SecurityValidator.sanitize_blob_name",
                return_value="safe_name.tar.gz",
            ):

                await archive_manager.upload_archive(archive_path, "test-container")

                # Verify blob client was called
                archive_manager.blob_client.upload_binary.assert_called_once()
                call_args = archive_manager.blob_client.upload_binary.call_args
                assert call_args[1]["container_name"] == "test-container"
                assert call_args[1]["blob_name"] == "safe_name.tar.gz"
                assert call_args[1]["content_type"] == "application/gzip"
        finally:
            os.unlink(archive_path)

    @pytest.mark.asyncio
    async def test_upload_archive_no_client(self, archive_manager_no_client):
        """Test upload fails when no blob client configured."""
        archive_path = Path("/tmp/test.tar.gz")

        with pytest.raises(ValueError, match="No blob client configured for upload"):
            await archive_manager_no_client.upload_archive(archive_path)

    @pytest.mark.asyncio
    async def test_upload_archive_validation_failure(self, archive_manager):
        """Test upload fails when archive validation fails."""
        archive_path = Path("/tmp/test.tar.gz")

        # Mock validation to fail
        with patch(
            "file_operations.SecurityValidator.validate_archive_file",
            side_effect=ValueError("Invalid archive"),
        ):

            with pytest.raises(
                ValueError, match="Archive validation failed: Invalid archive"
            ):
                await archive_manager.upload_archive(archive_path)

    @pytest.mark.asyncio
    async def test_upload_archive_default_container(self, archive_manager):
        """Test upload with default container name."""
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as temp_file:
            temp_file.write(b"test archive content")
            archive_path = Path(temp_file.name)

        try:
            with patch(
                "file_operations.SecurityValidator.validate_archive_file"
            ), patch(
                "file_operations.SecurityValidator.sanitize_blob_name",
                return_value="safe_name.tar.gz",
            ):

                await archive_manager.upload_archive(
                    archive_path
                )  # No container specified

                # Should use default container
                call_args = archive_manager.blob_client.upload_binary.call_args
                assert call_args[1]["container_name"] == "static-sites"
        finally:
            os.unlink(archive_path)

    @pytest.mark.asyncio
    async def test_upload_archive_blob_client_error(self, archive_manager):
        """Test upload handles blob client errors gracefully."""
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as temp_file:
            temp_file.write(b"test archive content")
            archive_path = Path(temp_file.name)

        try:
            # Mock blob client to raise exception
            archive_manager.blob_client.upload_binary.side_effect = Exception(
                "Upload failed"
            )

            with patch(
                "file_operations.SecurityValidator.validate_archive_file"
            ), patch(
                "file_operations.SecurityValidator.sanitize_blob_name",
                return_value="safe_name.tar.gz",
            ):

                with pytest.raises(ValueError, match="Upload failed: Upload failed"):
                    await archive_manager.upload_archive(archive_path)
        finally:
            os.unlink(archive_path)

    def test_cleanup_temp_files(self, archive_manager):
        """Test temporary file cleanup."""
        # Create temporary test files
        temp_files = []
        for i in range(3):
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_files.append(Path(temp_file.name))
            temp_file.close()

        # Add a non-existent file to test error handling
        temp_files.append(Path("/tmp/nonexistent.txt"))

        # Mock path validation to pass for existing files
        with patch(
            "file_operations.SecurityValidator.validate_path_within_base",
            return_value=True,
        ):
            archive_manager.cleanup_temp_files(temp_files)

        # Verify files were deleted (existing ones)
        for temp_file in temp_files[:3]:  # First 3 should be deleted
            assert not temp_file.exists()


class TestStaticAssetManager:
    """Test static asset management functionality."""

    @pytest.mark.asyncio
    async def test_copy_static_assets(self):
        """Test static asset copying."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            copied_files = await StaticAssetManager.copy_static_assets(
                output_dir, "test-theme"
            )

            # Should return list of copied files
            assert isinstance(copied_files, list)
            assert "style.css" in copied_files
            assert "script.js" in copied_files

            # Files should actually exist
            assert (output_dir / "style.css").exists()
            assert (output_dir / "script.js").exists()

    @pytest.mark.asyncio
    async def test_copy_static_assets_error_handling(self):
        """Test static asset copying with errors."""
        # Use invalid directory to trigger error
        invalid_dir = Path("/nonexistent/directory")

        # Should handle errors gracefully
        copied_files = await StaticAssetManager.copy_static_assets(invalid_dir, "theme")

        # Should return empty list or handle gracefully
        assert isinstance(copied_files, list)
        # Implementation may return empty list on error

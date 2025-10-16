"""
Unit tests for hugo_builder.py

Tests Hugo build, deployment, backup, and rollback operations.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from hugo_builder import (
    backup_current_site,
    build_site_with_hugo,
    deploy_to_web_container,
    get_content_type,
    rollback_deployment,
)


def test_get_content_type_html():
    """Test MIME type detection for HTML files."""
    file_path = Path("/test/index.html")
    content_type = get_content_type(file_path)
    assert content_type == "text/html"


def test_get_content_type_css():
    """Test MIME type detection for CSS files."""
    file_path = Path("/test/style.css")
    content_type = get_content_type(file_path)
    assert content_type == "text/css"


def test_get_content_type_javascript():
    """Test MIME type detection for JavaScript files."""
    file_path = Path("/test/app.js")
    content_type = get_content_type(file_path)
    assert content_type in ["application/javascript", "text/javascript"]


def test_get_content_type_unknown():
    """Test MIME type detection for unknown file types."""
    file_path = Path("/test/file.unknown")
    content_type = get_content_type(file_path)
    assert content_type == "application/octet-stream"


@pytest.mark.asyncio
@patch("hugo_builder.asyncio.create_subprocess_exec")
async def test_build_site_with_hugo_success(
    mock_subprocess, temp_dir, sample_hugo_config
):
    """Test successful Hugo build."""
    # Setup Hugo directory structure
    hugo_dir = temp_dir / "hugo-site"
    hugo_dir.mkdir()
    (hugo_dir / "content").mkdir()
    config_file = hugo_dir / "config.toml"
    config_file.write_text(sample_hugo_config)

    # Create mock public directory with files
    public_dir = hugo_dir / "public"
    public_dir.mkdir()
    (public_dir / "index.html").write_text("<html></html>")
    (public_dir / "style.css").write_text("body { }")

    # Mock successful subprocess
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"", b""))
    mock_subprocess.return_value = mock_process

    # Execute
    result = await build_site_with_hugo(
        hugo_dir=hugo_dir,
        config_file=config_file,
        base_url="https://test.example.com",
    )

    # Assert
    assert result.success
    assert result.output_files == 2
    assert result.duration_seconds > 0
    assert len(result.errors) == 0


@pytest.mark.asyncio
@patch("hugo_builder.asyncio.create_subprocess_exec")
async def test_build_site_with_hugo_missing_directory(mock_subprocess, temp_dir):
    """Test Hugo build with missing directory."""
    hugo_dir = temp_dir / "nonexistent"
    config_file = temp_dir / "config.toml"

    # Execute
    result = await build_site_with_hugo(
        hugo_dir=hugo_dir,
        config_file=config_file,
        base_url="https://test.example.com",
    )

    # Assert
    assert not result.success
    assert any("not found" in error for error in result.errors)


@pytest.mark.asyncio
@patch("hugo_builder.asyncio.create_subprocess_exec")
async def test_build_site_with_hugo_build_failure(
    mock_subprocess, temp_dir, sample_hugo_config
):
    """Test Hugo build failure."""
    # Setup Hugo directory
    hugo_dir = temp_dir / "hugo-site"
    hugo_dir.mkdir()
    config_file = hugo_dir / "config.toml"
    config_file.write_text(sample_hugo_config)

    # Mock failed subprocess
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate = AsyncMock(
        return_value=(b"", b"Error: template not found")
    )
    mock_subprocess.return_value = mock_process

    # Execute
    result = await build_site_with_hugo(
        hugo_dir=hugo_dir,
        config_file=config_file,
        base_url="https://test.example.com",
    )

    # Assert
    assert not result.success
    assert any("Hugo build failed" in error for error in result.errors)


@pytest.mark.asyncio
@patch("hugo_builder.asyncio.wait_for")
@patch("hugo_builder.asyncio.create_subprocess_exec")
async def test_build_site_with_hugo_timeout(
    mock_subprocess, mock_wait_for, temp_dir, sample_hugo_config
):
    """Test Hugo build timeout."""
    # Setup Hugo directory
    hugo_dir = temp_dir / "hugo-site"
    hugo_dir.mkdir()
    config_file = hugo_dir / "config.toml"
    config_file.write_text(sample_hugo_config)

    # Mock process and timeout
    mock_process = AsyncMock()
    mock_process.kill = Mock()
    mock_process.wait = AsyncMock()
    mock_subprocess.return_value = mock_process
    mock_wait_for.side_effect = asyncio.TimeoutError()

    # Execute
    result = await build_site_with_hugo(
        hugo_dir=hugo_dir,
        config_file=config_file,
        base_url="https://test.example.com",
        timeout_seconds=10,
    )

    # Assert
    assert not result.success
    assert any("timeout" in error.lower() for error in result.errors)


@pytest.mark.asyncio
async def test_deploy_to_web_container_success(mock_blob_client, temp_dir):
    """Test successful deployment to web container."""
    # Setup source directory with files
    source_dir = temp_dir / "public"
    source_dir.mkdir()
    (source_dir / "index.html").write_text("<html></html>")
    (source_dir / "style.css").write_text("body { }")

    # Setup mock container client
    mock_container = AsyncMock()
    mock_blob = AsyncMock()
    mock_blob.upload_blob = AsyncMock()
    mock_container.get_blob_client = Mock(return_value=mock_blob)
    mock_blob_client.get_container_client = Mock(return_value=mock_container)

    # Execute
    result = await deploy_to_web_container(
        blob_client=mock_blob_client,
        source_dir=source_dir,
        container_name="$web",
    )

    # Assert
    assert result.files_uploaded == 2
    assert result.duration_seconds > 0
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_deploy_to_web_container_missing_source(mock_blob_client, temp_dir):
    """Test deployment with missing source directory."""
    source_dir = temp_dir / "nonexistent"

    # Execute
    result = await deploy_to_web_container(
        blob_client=mock_blob_client,
        source_dir=source_dir,
        container_name="$web",
    )

    # Assert
    assert result.files_uploaded == 0
    assert any("not found" in error for error in result.errors)


@pytest.mark.asyncio
async def test_deploy_to_web_container_directory_check(mock_blob_client, temp_dir):
    """
    Test deployment with basic directory validation.

    Note: Full Hugo output validation (index.html, size limits, etc.)
    is now performed in site_builder.py before calling this function.
    This test verifies the basic directory existence check only.
    """
    # Setup non-existent source directory
    source_dir = temp_dir / "nonexistent_public"

    # Execute
    result = await deploy_to_web_container(
        blob_client=mock_blob_client,
        source_dir=source_dir,
        container_name="$web",
    )

    # Assert - should fail with directory not found error
    assert result.files_uploaded == 0
    assert any("not found" in error.lower() for error in result.errors)


@pytest.mark.asyncio
async def test_backup_current_site_success(mock_blob_client):
    """Test successful site backup."""
    # Setup mock blobs
    mock_blob1 = Mock()
    mock_blob1.name = "index.html"
    mock_blob2 = Mock()
    mock_blob2.name = "style.css"

    # Setup mock containers
    mock_source = AsyncMock()
    mock_backup = AsyncMock()

    async def blob_iterator():
        yield mock_blob1
        yield mock_blob2

    mock_source.list_blobs = Mock(return_value=blob_iterator())

    # Setup mock blob clients
    mock_source_blob = AsyncMock()
    mock_source_blob.url = "https://test.blob.core.windows.net/web/index.html"
    mock_source.get_blob_client = Mock(return_value=mock_source_blob)

    mock_backup_blob = AsyncMock()
    mock_backup_blob.start_copy_from_url = AsyncMock()
    mock_backup.get_blob_client = Mock(return_value=mock_backup_blob)

    # Setup container client routing
    def get_container(name):
        if name == "$web":
            return mock_source
        return mock_backup

    mock_blob_client.get_container_client = Mock(side_effect=get_container)

    # Execute
    result = await backup_current_site(
        blob_client=mock_blob_client,
        source_container="$web",
        backup_container="$web-backup",
    )

    # Assert
    assert result.files_uploaded == 2
    assert result.duration_seconds > 0
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_backup_current_site_empty_source(mock_blob_client):
    """Test backup with empty source container."""
    # Setup empty source container
    mock_source = AsyncMock()

    async def empty_iterator():
        for _ in []:
            yield

    mock_source.list_blobs = Mock(return_value=empty_iterator())
    mock_blob_client.get_container_client = Mock(return_value=mock_source)

    # Execute
    result = await backup_current_site(
        blob_client=mock_blob_client,
        source_container="$web",
        backup_container="$web-backup",
    )

    # Assert - empty backup is still successful
    assert result.files_uploaded == 0
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_rollback_deployment_success(mock_blob_client):
    """Test successful deployment rollback."""
    # Setup mock backup blobs
    mock_blob1 = Mock()
    mock_blob1.name = "index.html"
    mock_blob2 = Mock()
    mock_blob2.name = "style.css"

    # Setup mock target blob (for deletion)
    mock_target_blob = Mock()
    mock_target_blob.name = "broken.html"

    # Setup mock containers
    mock_backup = AsyncMock()
    mock_target = AsyncMock()

    async def backup_iterator():
        yield mock_blob1
        yield mock_blob2

    async def target_iterator():
        yield mock_target_blob

    mock_backup.list_blobs = Mock(return_value=backup_iterator())
    mock_target.list_blobs = Mock(return_value=target_iterator())
    mock_target.delete_blob = AsyncMock()

    # Setup mock blob clients
    mock_backup_blob = AsyncMock()
    mock_backup_blob.url = "https://test.blob.core.windows.net/backup/index.html"
    mock_backup.get_blob_client = Mock(return_value=mock_backup_blob)

    mock_target_blob_client = AsyncMock()
    mock_target_blob_client.start_copy_from_url = AsyncMock()
    mock_target.get_blob_client = Mock(return_value=mock_target_blob_client)

    # Setup container client routing
    def get_container(name):
        if name == "$web-backup":
            return mock_backup
        return mock_target

    mock_blob_client.get_container_client = Mock(side_effect=get_container)

    # Execute
    result = await rollback_deployment(
        blob_client=mock_blob_client,
        backup_container="$web-backup",
        target_container="$web",
    )

    # Assert
    assert result.files_uploaded == 2
    assert result.duration_seconds > 0
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_rollback_deployment_no_backup(mock_blob_client):
    """Test rollback with no backup files."""
    # Setup empty backup container
    mock_backup = AsyncMock()

    async def empty_iterator():
        for _ in []:
            yield

    mock_backup.list_blobs = Mock(return_value=empty_iterator())
    mock_blob_client.get_container_client = Mock(return_value=mock_backup)

    # Execute
    result = await rollback_deployment(
        blob_client=mock_blob_client,
        backup_container="$web-backup",
        target_container="$web",
    )

    # Assert
    assert result.files_uploaded == 0
    assert any("No backup files" in error for error in result.errors)

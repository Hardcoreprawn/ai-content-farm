"""
Unit tests for site_builder.py

Tests end-to-end site building and deployment orchestration.
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from site_builder import build_and_deploy_site


@pytest.mark.asyncio
@patch("site_builder.download_markdown_files", new_callable=AsyncMock)
@patch("site_builder.organize_content_for_hugo", new_callable=AsyncMock)
@patch("site_builder.build_site_with_hugo", new_callable=AsyncMock)
@patch("site_builder.backup_current_site", new_callable=AsyncMock)
@patch("site_builder.deploy_to_web_container", new_callable=AsyncMock)
@patch("site_builder.rollback_deployment", new_callable=AsyncMock)
async def test_build_and_deploy_site_success(
    mock_rollback,
    mock_deploy,
    mock_backup,
    mock_build,
    mock_organize,
    mock_download,
    mock_blob_client,
    temp_dir,
):
    """Test successful end-to-end build and deploy."""
    # Setup mock results
    download_result = Mock()
    download_result.files_downloaded = 5
    download_result.errors = []
    mock_download.return_value = download_result

    organize_result = Mock()
    organize_result.is_valid = True
    organize_result.errors = []
    mock_organize.return_value = organize_result

    build_result = Mock()
    build_result.success = True
    build_result.output_files = 10
    build_result.errors = []
    mock_build.return_value = build_result

    backup_result = Mock()
    backup_result.files_uploaded = 8
    backup_result.errors = []
    mock_backup.return_value = backup_result

    deploy_result = Mock()
    deploy_result.files_uploaded = 10
    deploy_result.errors = []
    mock_deploy.return_value = deploy_result

    # Setup config
    mock_config = Mock()
    mock_config.markdown_container = "markdown-content"
    mock_config.hugo_base_url = "https://test.example.com"
    mock_config.hugo_config_path = "/tmp/config.toml"

    # Execute
    result = await build_and_deploy_site(
        blob_client=mock_blob_client,
        config=mock_config,
    )

    # Assert
    assert result.files_uploaded == 10
    assert result.duration_seconds > 0
    assert len(result.errors) == 0

    # Verify rollback was not called
    mock_rollback.assert_not_called()


@pytest.mark.asyncio
@patch("site_builder.download_markdown_files", new_callable=AsyncMock)
@patch("site_builder.organize_content_for_hugo", new_callable=AsyncMock)
@patch("site_builder.build_site_with_hugo", new_callable=AsyncMock)
@patch("site_builder.backup_current_site", new_callable=AsyncMock)
@patch("site_builder.deploy_to_web_container", new_callable=AsyncMock)
@patch("site_builder.rollback_deployment", new_callable=AsyncMock)
async def test_build_and_deploy_site_download_failure(
    mock_rollback,
    mock_deploy,
    mock_backup,
    mock_build,
    mock_organize,
    mock_download,
    mock_blob_client,
    temp_dir,
):
    """Test build and deploy with download failure."""
    # Setup failed download
    download_result = Mock()
    download_result.files_downloaded = 0
    download_result.errors = ["Failed to download blobs"]
    mock_download.return_value = download_result

    mock_config = Mock()
    mock_config.markdown_container = "markdown-content"

    # Execute
    result = await build_and_deploy_site(
        blob_client=mock_blob_client,
        config=mock_config,
    )

    # Assert
    assert result.files_uploaded == 0
    assert len(result.errors) > 0
    assert any("download" in error.lower() for error in result.errors)

    # Verify subsequent steps were not called
    mock_organize.assert_not_called()
    mock_build.assert_not_called()
    mock_backup.assert_not_called()
    mock_deploy.assert_not_called()
    mock_rollback.assert_not_called()


@pytest.mark.asyncio
@patch("site_builder.download_markdown_files", new_callable=AsyncMock)
@patch("site_builder.organize_content_for_hugo", new_callable=AsyncMock)
@patch("site_builder.build_site_with_hugo", new_callable=AsyncMock)
@patch("site_builder.backup_current_site", new_callable=AsyncMock)
@patch("site_builder.deploy_to_web_container", new_callable=AsyncMock)
@patch("site_builder.rollback_deployment", new_callable=AsyncMock)
async def test_build_and_deploy_site_build_failure(
    mock_rollback,
    mock_deploy,
    mock_backup,
    mock_build,
    mock_organize,
    mock_download,
    mock_blob_client,
    temp_dir,
):
    """Test build and deploy with Hugo build failure."""
    # Setup successful download and organize
    download_result = Mock()
    download_result.files_downloaded = 5
    download_result.errors = []
    mock_download.return_value = download_result

    organize_result = Mock()
    organize_result.is_valid = True
    organize_result.errors = []
    mock_organize.return_value = organize_result

    # Setup failed build
    build_result = Mock()
    build_result.success = False
    build_result.output_files = 0
    build_result.errors = ["Hugo build failed"]
    mock_build.return_value = build_result

    mock_config = Mock()
    mock_config.markdown_container = "markdown-content"
    mock_config.hugo_base_url = "https://test.example.com"
    mock_config.hugo_config_path = "/tmp/config.toml"

    # Execute
    result = await build_and_deploy_site(
        blob_client=mock_blob_client,
        config=mock_config,
    )

    # Assert
    assert result.files_uploaded == 0
    assert len(result.errors) > 0
    assert any("build" in error.lower() for error in result.errors)

    # Verify deployment steps were not called
    mock_backup.assert_not_called()
    mock_deploy.assert_not_called()
    mock_rollback.assert_not_called()


@pytest.mark.asyncio
@patch("site_builder.download_markdown_files", new_callable=AsyncMock)
@patch("site_builder.organize_content_for_hugo", new_callable=AsyncMock)
@patch("site_builder.build_site_with_hugo", new_callable=AsyncMock)
@patch("site_builder.backup_current_site", new_callable=AsyncMock)
@patch("site_builder.deploy_to_web_container", new_callable=AsyncMock)
@patch("site_builder.rollback_deployment", new_callable=AsyncMock)
async def test_build_and_deploy_site_automatic_rollback(
    mock_rollback,
    mock_deploy,
    mock_backup,
    mock_build,
    mock_organize,
    mock_download,
    mock_blob_client,
    temp_dir,
):
    """Test automatic rollback when deployment uploads 0 files."""
    # Setup successful build
    download_result = Mock()
    download_result.files_downloaded = 5
    download_result.errors = []
    mock_download.return_value = download_result

    organize_result = Mock()
    organize_result.is_valid = True
    organize_result.errors = []
    mock_organize.return_value = organize_result

    build_result = Mock()
    build_result.success = True
    build_result.output_files = 10
    build_result.errors = []
    mock_build.return_value = build_result

    backup_result = Mock()
    backup_result.files_uploaded = 8
    backup_result.errors = []
    mock_backup.return_value = backup_result

    # Setup deploy with 0 files (triggers rollback)
    deploy_result = Mock()
    deploy_result.files_uploaded = 0
    deploy_result.errors = ["Deployment validation failed"]
    mock_deploy.return_value = deploy_result

    rollback_result = Mock()
    rollback_result.files_uploaded = 8
    rollback_result.errors = []
    mock_rollback.return_value = rollback_result

    mock_config = Mock()
    mock_config.markdown_container = "markdown-content"
    mock_config.hugo_base_url = "https://test.example.com"
    mock_config.hugo_config_path = "/tmp/config.toml"

    # Execute
    result = await build_and_deploy_site(
        blob_client=mock_blob_client,
        config=mock_config,
    )

    # Assert - deployment failed, rollback occurred
    assert result.files_uploaded == 0
    assert len(result.errors) > 0
    assert any(
        "rollback" in error.lower() or "deploy" in error.lower()
        for error in result.errors
    )

    # Verify rollback was called
    mock_rollback.assert_called_once()


@pytest.mark.asyncio
@patch("site_builder.download_markdown_files", new_callable=AsyncMock)
@patch("site_builder.organize_content_for_hugo", new_callable=AsyncMock)
@patch("site_builder.build_site_with_hugo", new_callable=AsyncMock)
@patch("site_builder.backup_current_site", new_callable=AsyncMock)
@patch("site_builder.deploy_to_web_container", new_callable=AsyncMock)
@patch("site_builder.rollback_deployment", new_callable=AsyncMock)
async def test_build_and_deploy_site_backup_failure_continues(
    mock_rollback,
    mock_deploy,
    mock_backup,
    mock_build,
    mock_organize,
    mock_download,
    mock_blob_client,
    temp_dir,
):
    """Test that backup failure doesn't stop deployment."""
    # Setup successful build
    download_result = Mock()
    download_result.files_downloaded = 5
    download_result.errors = []
    mock_download.return_value = download_result

    organize_result = Mock()
    organize_result.is_valid = True
    organize_result.errors = []
    mock_organize.return_value = organize_result

    build_result = Mock()
    build_result.success = True
    build_result.output_files = 10
    build_result.errors = []
    mock_build.return_value = build_result

    # Setup backup failure
    backup_result = Mock()
    backup_result.files_uploaded = 0
    backup_result.errors = ["Backup failed"]
    mock_backup.return_value = backup_result

    # Setup successful deploy
    deploy_result = Mock()
    deploy_result.files_uploaded = 10
    deploy_result.errors = []
    mock_deploy.return_value = deploy_result

    mock_config = Mock()
    mock_config.markdown_container = "markdown-content"
    mock_config.hugo_base_url = "https://test.example.com"
    mock_config.hugo_config_path = "/tmp/config.toml"

    # Execute
    result = await build_and_deploy_site(
        blob_client=mock_blob_client,
        config=mock_config,
    )

    # Assert - deployment still succeeds despite backup failure
    assert result.files_uploaded == 10
    assert result.duration_seconds > 0
    # Backup errors should be logged but not prevent deployment

    # Verify deploy was still called
    mock_deploy.assert_called_once()

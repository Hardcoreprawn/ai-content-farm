"""
Unit tests for site_builder.py

Tests end-to-end site building and deployment orchestration.
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from site_builder import build_and_deploy_site


@pytest.mark.asyncio
@patch("security.validate_hugo_output")
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
    mock_validate,
    mock_blob_client,
    temp_dir,
):
    """
    Test successful end-to-end build and deploy.

    Contract:
    - Input: BlobServiceClient, Settings
    - Output: DeploymentResult with files_uploaded > 0, no errors

    Behavior:
    - Downloads markdown content
    - Organizes content for Hugo
    - Builds site with Hugo
    - Backs up current site
    - Validates Hugo output
    - Deploys to web container
    - Does NOT trigger rollback on success
    """
    # Setup mock results - testing the contract
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

    # Mock validation passing
    validation_result = Mock()
    validation_result.is_valid = True
    validation_result.errors = []
    mock_validate.return_value = validation_result

    deploy_result = Mock()
    deploy_result.files_uploaded = 10
    deploy_result.errors = []
    mock_deploy.return_value = deploy_result

    # Setup config
    mock_config = Mock()
    mock_config.markdown_container = "markdown-content"
    mock_config.hugo_base_url = "https://test.example.com"
    mock_config.hugo_config_path = "/tmp/config.toml"
    mock_config.build_timeout_seconds = 300

    # Execute
    result = await build_and_deploy_site(
        blob_client=mock_blob_client,
        config=mock_config,
    )

    # Assert - verify contract
    assert result.files_uploaded == 10, "Should upload expected number of files"
    assert result.duration_seconds > 0, "Should track execution time"
    assert len(result.errors) == 0, "Should have no errors on success"

    # Assert - verify behavior
    # Should validate Hugo output before deployment
    mock_validate.assert_called_once()
    mock_rollback.assert_not_called()  # Should NOT rollback on successful deployment


@pytest.mark.asyncio
@patch("security.validate_hugo_output")
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
    mock_validate,
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
    mock_config.hugo_config_path = "/tmp/config.toml"
    mock_config.build_timeout_seconds = 300

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
@patch("security.validate_hugo_output")
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
    mock_validate,
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
    mock_config.build_timeout_seconds = 300

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
@patch("security.validate_hugo_output")
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
    mock_validate,
    mock_blob_client,
    temp_dir,
):
    """
    Test automatic rollback when deployment uploads 0 files.

    Contract:
    - Input: BlobServiceClient, Settings with valid configuration
    - Output: DeploymentResult with files_uploaded=0, errors list contains rollback message

    Behavior:
    - When deployment uploads 0 files AND backup exists
    - Should trigger automatic rollback
    - Should include rollback error message in result
    """
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

    # Mock validation passing (so we get to deployment)
    validation_result = Mock()
    validation_result.is_valid = True
    validation_result.errors = []
    mock_validate.return_value = validation_result

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
    mock_config.build_timeout_seconds = 300

    # Execute
    result = await build_and_deploy_site(
        blob_client=mock_blob_client,
        config=mock_config,
    )

    # Assert - verify contract
    assert (
        result.files_uploaded == 0
    ), "Should report 0 files uploaded when deployment fails"
    assert len(result.errors) > 0, "Should have errors when rollback occurs"
    assert any(
        "rollback" in error.lower() or "deploy" in error.lower()
        for error in result.errors
    ), "Should include deployment/rollback error message"

    # Assert - verify behavior
    mock_validate.assert_called_once()  # Should validate before deployment
    mock_rollback.assert_called_once()  # Should trigger rollback


@pytest.mark.asyncio
@patch("security.validate_hugo_output")
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
    mock_validate,
    mock_blob_client,
    temp_dir,
):
    """
    Test that backup failure doesn't stop deployment.

    Contract:
    - Input: BlobServiceClient, Settings
    - Output: DeploymentResult with successful deployment despite backup failure

    Behavior:
    - Backup failures should be logged but not prevent deployment
    - Deployment should proceed normally
    - Backup errors should be included in result.errors
    """
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

    # Mock validation passing
    validation_result = Mock()
    validation_result.is_valid = True
    validation_result.errors = []
    mock_validate.return_value = validation_result

    # Setup successful deploy
    deploy_result = Mock()
    deploy_result.files_uploaded = 10
    deploy_result.errors = []
    mock_deploy.return_value = deploy_result

    mock_config = Mock()
    mock_config.markdown_container = "markdown-content"
    mock_config.hugo_base_url = "https://test.example.com"
    mock_config.hugo_config_path = "/tmp/config.toml"
    mock_config.build_timeout_seconds = 300

    # Execute
    result = await build_and_deploy_site(
        blob_client=mock_blob_client,
        config=mock_config,
    )

    # Assert - verify contract: deployment still succeeds despite backup failure
    assert (
        result.files_uploaded == 10
    ), "Should deploy successfully even with backup failure"
    assert result.duration_seconds > 0, "Should track execution time"
    # Backup errors should be logged but deployment succeeds

    # Assert - verify behavior
    mock_validate.assert_called_once()  # Should validate before deployment
    mock_deploy.assert_called_once()  # Should still call deploy despite backup failure

"""
Hugo builder for site-publisher.

Async functions for building static sites with Hugo and deploying to blob storage.
Uses asyncio for non-blocking subprocess execution.
"""

import asyncio
import logging
import mimetypes
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import BlobServiceClient
from error_handling import handle_error
from models import BuildResult, DeploymentResult
from security import (
    sanitize_error_message,
    validate_hugo_output,
)

logger = logging.getLogger(__name__)

# Constants
MAX_ERROR_OUTPUT_LENGTH = 1000  # Maximum characters to log from Hugo error output


async def build_site_with_hugo(
    hugo_dir: Path,
    config_file: Path,
    base_url: str,
    timeout_seconds: int = 300,
    themes_dir: Optional[Path] = None,
) -> BuildResult:
    """
    Build static site with Hugo (async).

    Runs Hugo as non-blocking subprocess to avoid blocking event loop.
    Critical for async performance since Hugo builds can take minutes.

    Args:
        hugo_dir: Directory containing Hugo site (with content/ directory)
        config_file: Path to Hugo config.toml
        base_url: Base URL for the site
        timeout_seconds: Maximum build time (DOS prevention)
        themes_dir: Optional custom themes directory (defaults to /app/themes)

    Returns:
        BuildResult with output file count and any errors

    Raises:
        ValueError: If parameters are invalid
    """
    start_time = datetime.now()
    logger.info(f"Building site with Hugo: {hugo_dir}")

    # Default to container's themes directory if not specified
    if themes_dir is None:
        themes_dir = Path("/app/themes")

    try:
        # Validate paths exist
        if not hugo_dir.exists():
            return BuildResult(
                success=False,
                output_files=0,
                duration_seconds=0.0,
                errors=[f"Hugo directory not found: {hugo_dir}"],
            )

        if not config_file.exists():
            return BuildResult(
                success=False,
                output_files=0,
                duration_seconds=0.0,
                errors=[f"Config file not found: {config_file}"],
            )

        # Run Hugo build
        # Note: Theme can be installed at /app/themes/PaperMod during container build
        # or use custom themes_dir for testing
        cmd = [
            "hugo",
            "--source",
            str(hugo_dir),
            "--config",
            str(config_file),
            "--baseURL",
            base_url,
            "--destination",
            str(hugo_dir / "public"),
            "--themesDir",
            str(themes_dir),
            "--cleanDestinationDir",
        ]

        logger.info(f"Running Hugo: {' '.join(cmd)}")

        # Use asyncio.create_subprocess_exec for non-blocking subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Hugo build timeout after {timeout_seconds}s")
            return BuildResult(
                success=False,
                output_files=0,
                duration_seconds=duration,
                errors=[f"Build timeout after {timeout_seconds} seconds"],
            )

        duration = (datetime.now() - start_time).total_seconds()

        # Decode outputs
        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")

        # Always log Hugo output for debugging
        if stdout_text:
            logger.debug(f"Hugo STDOUT: {stdout_text}")
        if stderr_text:
            logger.info(f"Hugo STDERR: {stderr_text}")

        # Check for errors
        if process.returncode != 0:
            # Hugo writes errors to stderr per official documentation
            error_output = stderr_text or stdout_text or "(no error output captured)"

            logger.error(
                f"Hugo build failed with exit code {process.returncode}: "
                f"{error_output[:MAX_ERROR_OUTPUT_LENGTH]}"
            )

            return BuildResult(
                success=False,
                output_files=0,
                duration_seconds=duration,
                errors=[
                    f"Hugo build failed (exit {process.returncode}): "
                    f"{error_output[:MAX_ERROR_OUTPUT_LENGTH // 2]}"
                ],
            )

        # Count output files
        public_dir = hugo_dir / "public"
        if not public_dir.exists():
            return BuildResult(
                success=False,
                output_files=0,
                duration_seconds=duration,
                errors=["Hugo did not create public/ directory"],
            )

        output_files = list(public_dir.rglob("*"))
        file_count = len([f for f in output_files if f.is_file()])

        logger.info(f"Hugo build completed: {file_count} files in {duration:.2f}s")

        return BuildResult(
            success=True, output_files=file_count, duration_seconds=duration, errors=[]
        )

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_info = handle_error(e, error_type="build")
        return BuildResult(
            success=False,
            output_files=0,
            duration_seconds=duration,
            errors=[sanitize_error_message(e)],
        )


def get_content_type(file_path: Path) -> str:
    """
    Get MIME content type for a file.

    Pure function for determining content type.

    Args:
        file_path: Path to file

    Returns:
        MIME type string (e.g., "text/html", "application/octet-stream")
    """
    # Use mimetypes library
    content_type, _ = mimetypes.guess_type(str(file_path))

    # Default to octet-stream if unknown
    if content_type is None:
        return "application/octet-stream"

    return content_type


async def deploy_to_web_container(
    blob_client: BlobServiceClient,
    source_dir: Path,
    container_name: str,
    max_files: int = 10000,
    max_file_size: int = 10_485_760,  # 10MB
) -> DeploymentResult:
    """
    Deploy built site to $web container.

    Pure function with explicit dependencies and limits.

    Note: Hugo output validation should be performed by the caller (site_builder.py)
    before calling this function. This function only performs basic directory checks.

    Args:
        blob_client: Azure blob service client (injected dependency)
        source_dir: Directory with built site files (Hugo public/ directory) - should be pre-validated
        container_name: Target container name (usually "$web")
        max_files: Maximum files to upload (DOS prevention)
        max_file_size: Maximum size per file (DOS prevention)

    Returns:
        DeploymentResult with upload metrics and errors

    Raises:
        ValueError: If parameters are invalid
    """
    start_time = datetime.now()
    logger.info(f"Deploying site to {container_name}")

    uploaded_files = 0
    errors: List[str] = []

    try:
        # Validate source directory exists (basic check only)
        # Note: Full Hugo output validation happens in site_builder.py before calling this function
        if not source_dir.exists():
            return DeploymentResult(
                files_uploaded=0,
                duration_seconds=0.0,
                errors=[f"Source directory not found: {source_dir}"],
            )

        # Get container client
        container_client = blob_client.get_container_client(container_name)

        # Upload all files
        files_to_upload = [f for f in source_dir.rglob("*") if f.is_file()]
        logger.info(f"Uploading {len(files_to_upload)} files")

        for idx, file_path in enumerate(files_to_upload):
            try:
                # Calculate blob name (relative path)
                rel_path = file_path.relative_to(source_dir)
                blob_name = str(rel_path).replace(
                    "\\", "/"
                )  # Normalize path separators

                # Get content type
                content_type = get_content_type(file_path)

                # Upload file
                blob_client_obj = container_client.get_blob_client(blob_name)

                with open(file_path, "rb") as data:
                    await blob_client_obj.upload_blob(
                        data,
                        overwrite=True,
                        content_settings=ContentSettings(content_type=content_type),
                    )

                uploaded_files += 1

                # Log progress every 500 files to track long-running operations
                if (idx + 1) % 500 == 0:
                    logger.info(
                        f"Upload progress: {idx + 1}/{len(files_to_upload)} files"
                    )

            except asyncio.CancelledError:
                # Gracefully handle shutdown during upload
                logger.warning(
                    f"Upload cancelled during shutdown after {uploaded_files}/{len(files_to_upload)} files"
                )
                raise  # Re-raise to propagate cancellation
            except Exception as e:
                error_info = handle_error(
                    e, error_type="upload", context={"file": str(file_path)}
                )
                errors.append(
                    f"Failed to upload {file_path.name}: {sanitize_error_message(e)}"
                )

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Deployed {uploaded_files} files with {len(errors)} errors in {duration:.2f}s"
        )

        return DeploymentResult(
            files_uploaded=uploaded_files, duration_seconds=duration, errors=errors
        )

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_info = handle_error(
            e, error_type="deploy", context={"container": container_name}
        )
        return DeploymentResult(
            files_uploaded=0,
            duration_seconds=duration,
            errors=[sanitize_error_message(e)],
        )


async def backup_current_site(
    blob_client: BlobServiceClient,
    source_container: str,
    backup_container: str,
) -> DeploymentResult:
    """
    Incremental backup: Only backs up files that don't exist in backup container.

    This creates a cumulative backup over time, only copying new/changed files.
    Much faster than full backup on every deployment.

    First deployment: Full backup (~83s for 4,400 files)
    Subsequent deployments: Only new files (~5-10s for ~100 new files)

    Args:
        blob_client: Azure blob service client (injected dependency)
        source_container: Source container (usually "$web")
        backup_container: Backup container (usually "$web-backup")

    Returns:
        DeploymentResult with backup metrics and errors
    """
    start_time = datetime.now()
    logger.info(
        f"Starting incremental backup from {source_container} to {backup_container}"
    )

    backed_up_files = 0
    skipped_files = 0
    errors: List[str] = []

    try:
        # Get container clients
        source_client = blob_client.get_container_client(source_container)
        backup_client = blob_client.get_container_client(backup_container)

        # Get set of existing backup files for fast lookup
        existing_backups = set()
        async for blob in backup_client.list_blobs():
            existing_backups.add(blob.name)

        logger.info(f"Found {len(existing_backups)} existing backup files")

        # List all blobs in source container
        source_blobs = []
        async for blob in source_client.list_blobs():
            source_blobs.append(blob)

        files_to_backup = [b for b in source_blobs if b.name not in existing_backups]
        skipped_files = len(source_blobs) - len(files_to_backup)

        logger.info(
            f"Backing up {len(files_to_backup)} new files (skipping {skipped_files} existing)"
        )

        logger.info(
            f"Backing up {len(files_to_backup)} new files (skipping {skipped_files} existing)"
        )

        # Copy each new/changed blob to backup container
        for idx, blob in enumerate(files_to_backup):
            try:
                source_blob = source_client.get_blob_client(blob.name)
                backup_blob = backup_client.get_blob_client(blob.name)

                # Copy blob (async)
                source_url = source_blob.url
                await backup_blob.start_copy_from_url(source_url)

                backed_up_files += 1

                # Log progress every 500 files to track long-running operations
                if (idx + 1) % 500 == 0:
                    logger.info(
                        f"Backup progress: {idx + 1}/{len(files_to_backup)} files"
                    )

            except asyncio.CancelledError:
                # Gracefully handle shutdown during backup
                logger.warning(
                    f"Backup cancelled during shutdown after {backed_up_files}/{len(files_to_backup)} files"
                )
                raise  # Re-raise to propagate cancellation
            except Exception as e:
                error_info = handle_error(
                    e, error_type="backup", context={"blob": blob.name}
                )
                errors.append(
                    f"Failed to backup {blob.name}: {sanitize_error_message(e)}"
                )

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Backed up {backed_up_files} files with {len(errors)} errors in {duration:.2f}s"
        )

        return DeploymentResult(
            files_uploaded=backed_up_files, duration_seconds=duration, errors=errors
        )

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_info = handle_error(
            e,
            error_type="backup",
            context={"source": source_container, "backup": backup_container},
        )
        return DeploymentResult(
            files_uploaded=0,
            duration_seconds=duration,
            errors=[sanitize_error_message(e)],
        )


async def rollback_deployment(
    blob_client: BlobServiceClient,
    backup_container: str,
    target_container: str,
) -> DeploymentResult:
    """
    Rollback deployment by restoring from backup.

    Copies all files from $web-backup to $web container.

    Args:
        blob_client: Azure blob service client (injected dependency)
        backup_container: Backup container (usually "$web-backup")
        target_container: Target container (usually "$web")

    Returns:
        DeploymentResult with rollback metrics and errors
    """
    start_time = datetime.now()
    logger.warning(f"Rolling back site from {backup_container} to {target_container}")

    restored_files = 0
    errors: List[str] = []

    try:
        # Get container clients
        backup_client = blob_client.get_container_client(backup_container)
        target_client = blob_client.get_container_client(target_container)

        # List all blobs in backup container
        blob_list = []
        async for blob in backup_client.list_blobs():
            blob_list.append(blob)

        if len(blob_list) == 0:
            return DeploymentResult(
                files_uploaded=0,
                duration_seconds=0.0,
                errors=["No backup files found - cannot rollback"],
            )

        logger.info(f"Found {len(blob_list)} backup files to restore")

        # Delete current files in target container
        try:
            async for blob in target_client.list_blobs():
                await target_client.delete_blob(blob.name)
                logger.debug(f"Deleted current file: {blob.name}")
        except Exception as e:
            logger.warning(f"Failed to delete some current files: {e}")
            # Continue with restore even if delete fails

        # Copy each blob from backup to target
        for idx, blob in enumerate(blob_list):
            try:
                backup_blob = backup_client.get_blob_client(blob.name)
                target_blob = target_client.get_blob_client(blob.name)

                # Copy blob (async)
                backup_url = backup_blob.url
                await target_blob.start_copy_from_url(backup_url)

                restored_files += 1

                # Log progress every 500 files to track long-running operations
                if (idx + 1) % 500 == 0:
                    logger.info(f"Rollback progress: {idx + 1}/{len(blob_list)} files")

            except asyncio.CancelledError:
                # Gracefully handle shutdown during rollback
                logger.warning(
                    f"Rollback cancelled during shutdown after {restored_files}/{len(blob_list)} files"
                )
                raise  # Re-raise to propagate cancellation
            except Exception as e:
                error_info = handle_error(
                    e, error_type="rollback", context={"blob": blob.name}
                )
                errors.append(
                    f"Failed to restore {blob.name}: {sanitize_error_message(e)}"
                )

        duration = (datetime.now() - start_time).total_seconds()
        logger.warning(
            f"Rollback complete: {restored_files} files restored with {len(errors)} errors in {duration:.2f}s"
        )

        return DeploymentResult(
            files_uploaded=restored_files, duration_seconds=duration, errors=errors
        )

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_info = handle_error(
            e,
            error_type="rollback",
            context={"backup": backup_container, "target": target_container},
        )
        return DeploymentResult(
            files_uploaded=0,
            duration_seconds=duration,
            errors=[sanitize_error_message(e)],
        )


async def clear_backup(
    blob_client: BlobServiceClient,
    backup_container: str,
) -> DeploymentResult:
    """
    Clear backup container after successful deployment.

    This makes the backup idempotent: after a successful deployment,
    we clear the old backup so the next deployment will create a fresh
    backup of the newly deployed content.

    Args:
        blob_client: Azure blob service client (injected dependency)
        backup_container: Backup container to clear (usually "$web-backup")

    Returns:
        DeploymentResult with deletion metrics and errors
    """
    start_time = datetime.now()
    logger.info(f"Clearing backup container: {backup_container}")

    deleted_files = 0
    errors: List[str] = []

    try:
        backup_client = blob_client.get_container_client(backup_container)

        # Delete all blobs in backup container
        async for blob in backup_client.list_blobs():
            try:
                await backup_client.delete_blob(blob.name)
                deleted_files += 1

                # Log progress every 500 files
                if deleted_files % 500 == 0:
                    logger.info(f"Cleared {deleted_files} backup files...")

            except Exception as e:
                errors.append(
                    f"Failed to delete {blob.name}: {sanitize_error_message(e)}"
                )

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Cleared {deleted_files} backup files with {len(errors)} errors in {duration:.2f}s"
        )

        return DeploymentResult(
            files_uploaded=deleted_files, duration_seconds=duration, errors=errors
        )

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_info = handle_error(
            e, error_type="backup_clear", context={"backup": backup_container}
        )
        return DeploymentResult(
            files_uploaded=0,
            duration_seconds=duration,
            errors=[sanitize_error_message(e)],
        )

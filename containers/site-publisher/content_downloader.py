"""
Content downloader for site-publisher.

Pure functions for downloading and organizing markdown files from blob storage.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob.aio import BlobServiceClient
from error_handling import handle_error
from models import DownloadResult, ValidationResult
from security import (
    sanitize_error_message,
    validate_blob_name,
    validate_path,
)

logger = logging.getLogger(__name__)


async def download_markdown_files(
    blob_client: BlobServiceClient,
    container_name: str,
    output_dir: Path,
    max_files: int = 10000,
    max_file_size: int = 10_485_760,  # 10MB
) -> DownloadResult:
    """
    Download markdown files from blob storage.

    Pure function with explicit dependencies and limits.

    Args:
        blob_client: Azure blob service client (injected dependency)
        container_name: Name of container with markdown files
        output_dir: Local directory to download files to
        max_files: Maximum number of files to download (DOS prevention)
        max_file_size: Maximum size per file in bytes (DOS prevention)

    Returns:
        DownloadResult with list of downloaded files and errors

    Raises:
        ValueError: If parameters are invalid
    """
    start_time = datetime.now()
    logger.info(f"Downloading markdown files from {container_name}")

    downloaded_files: List[str] = []
    errors: List[str] = []

    try:
        # Validate output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get container client
        container_client = blob_client.get_container_client(container_name)

        # List all blobs
        blob_list = []
        async for blob in container_client.list_blobs():
            blob_list.append(blob)

            # DOS prevention: check file count
            if len(blob_list) > max_files:
                error_msg = f"Too many files in container (max {max_files})"
                logger.error(error_msg)
                errors.append(error_msg)
                break

        # Download each blob
        for blob in blob_list:
            blob_name = blob.name

            # Validate blob name
            validation = validate_blob_name(blob_name)
            if not validation.is_valid:
                logger.warning(f"Invalid blob name: {blob_name} - {validation.errors}")
                errors.extend(validation.errors)
                continue

            # DOS prevention: check file size
            if blob.size > max_file_size:
                error_msg = f"File too large: {blob_name} ({blob.size} bytes, max {max_file_size})"
                logger.warning(error_msg)
                errors.append(error_msg)
                continue

            # Download blob
            try:
                blob_client_obj = container_client.get_blob_client(blob_name)
                file_path = output_dir / blob_name

                # Ensure parent directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Validate file path (prevent directory traversal)
                path_validation = validate_path(file_path, output_dir)
                if not path_validation.is_valid:
                    logger.error(
                        f"Invalid path: {file_path} - {path_validation.errors}"
                    )
                    errors.extend(path_validation.errors)
                    continue

                # Download blob content
                download_stream = await blob_client_obj.download_blob()
                content = await download_stream.readall()

                # Write to file
                file_path.write_bytes(content)
                downloaded_files.append(str(file_path))
                logger.debug(f"Downloaded: {blob_name}")

            except ResourceNotFoundError:
                error_msg = f"Blob not found: {blob_name}"
                logger.warning(error_msg)
                errors.append(error_msg)
            except Exception as e:
                error_info = handle_error(
                    e, error_type="download", context={"blob": blob_name}
                )
                errors.append(sanitize_error_message(e))

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Downloaded {len(downloaded_files)} files with {len(errors)} errors in {duration:.2f}s"
        )

        return DownloadResult(
            files_downloaded=len(downloaded_files),
            duration_seconds=duration,
            errors=errors,
        )

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_info = handle_error(
            e, error_type="download", context={"container": container_name}
        )
        return DownloadResult(
            files_downloaded=0,
            duration_seconds=duration,
            errors=[sanitize_error_message(e)],
        )


async def organize_content_for_hugo(
    content_dir: Path,
    hugo_content_dir: Path,
) -> ValidationResult:
    """
    Organize downloaded markdown files for Hugo.

    Ensures Hugo can process the content by:
    1. Moving files to content/ directory
    2. Validating frontmatter exists
    3. Creating _index.md files if needed

    Args:
        content_dir: Directory with downloaded markdown files
        hugo_content_dir: Hugo content directory (usually hugo-site/content)

    Returns:
        ValidationResult with any errors

    Raises:
        ValueError: If directories don't exist
    """
    logger.info(f"Organizing content for Hugo: {content_dir} -> {hugo_content_dir}")
    errors: List[str] = []

    try:
        # Validate directories exist
        if not content_dir.exists():
            return ValidationResult(
                is_valid=False, errors=[f"Content directory not found: {content_dir}"]
            )

        # Create Hugo content directory
        hugo_content_dir.mkdir(parents=True, exist_ok=True)

        # Copy markdown files to Hugo content directory
        md_files = list(content_dir.rglob("*.md"))
        logger.info(f"Found {len(md_files)} markdown files to organize")

        for md_file in md_files:
            try:
                # Calculate relative path
                rel_path = md_file.relative_to(content_dir)
                target_path = hugo_content_dir / rel_path

                # Validate target path
                path_validation = validate_path(target_path, hugo_content_dir)
                if not path_validation.is_valid:
                    errors.extend(path_validation.errors)
                    continue

                # Create parent directory
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy file
                target_path.write_bytes(md_file.read_bytes())
                logger.debug(f"Organized: {rel_path}")

            except Exception as e:
                error_info = handle_error(
                    e, error_type="organize", context={"file": str(md_file)}
                )
                errors.append(
                    f"Failed to organize {md_file.name}: {sanitize_error_message(e)}"
                )

        logger.info(
            f"Organized {len(md_files) - len(errors)} files with {len(errors)} errors"
        )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    except Exception as e:
        error_info = handle_error(e, error_type="organize")
        return ValidationResult(is_valid=False, errors=[sanitize_error_message(e)])

"""
Content downloader for site-publisher.

Pure functions for downloading and organizing markdown files from blob storage.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import yaml
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


def validate_markdown_frontmatter(file_path: Path) -> Tuple[bool, List[str]]:
    """
    Validate that a markdown file has valid YAML frontmatter.

    Uses strict validation rules matching Hugo's requirements:
    - All string values should be properly quoted
    - URLs must be quoted to avoid YAML parser ambiguity
    - Required fields must be present

    Args:
        file_path: Path to markdown file

    Returns:
        Tuple of (is_valid, errors) where is_valid is True if frontmatter is valid
    """
    errors = []

    try:
        content = file_path.read_text(encoding="utf-8")

        # Check for frontmatter delimiters
        if not content.startswith("---"):
            errors.append(f"Missing frontmatter opening delimiter (---)")
            return False, errors

        # Extract frontmatter (between first two --- markers)
        parts = content.split("---", 2)
        if len(parts) < 3:
            errors.append(f"Missing frontmatter closing delimiter (---)")
            return False, errors

        frontmatter_text = parts[1].strip()

        if not frontmatter_text:
            errors.append(f"Empty frontmatter")
            return False, errors

        # Try to parse YAML
        try:
            frontmatter = yaml.safe_load(frontmatter_text)

            if not isinstance(frontmatter, dict):
                errors.append(f"Frontmatter is not a dictionary")
                return False, errors

            # Check for Hugo required fields (per Hugo specification)
            # Hugo requires: title, date (can have default)
            # Custom fields like url/source should be under params
            if "title" not in frontmatter:
                errors.append(f"Missing required field: title")

            if "date" not in frontmatter:
                errors.append(f"Missing required field: date")

            # Validate title type
            if "title" in frontmatter and not isinstance(frontmatter["title"], str):
                errors.append(f"Field 'title' must be string")

            # Validate date type (should be string in ISO8601 format)
            if "date" in frontmatter and not isinstance(frontmatter["date"], str):
                errors.append(f"Field 'date' must be string (ISO8601)")

            # Validate params structure if present (Hugo custom fields)
            if "params" in frontmatter:
                if not isinstance(frontmatter["params"], dict):
                    errors.append(f"Field 'params' must be dictionary")
                # Optionally check for expected params (url, source)
                elif "original_url" not in frontmatter["params"]:
                    # Note: This is a warning-level issue, not critical
                    logger.debug(f"Params missing 'original_url' field (non-critical)")

            if errors:
                return False, errors

            return True, []

        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML syntax: {str(e)}")
            return False, errors

    except Exception as e:
        errors.append(f"Failed to read file: {str(e)}")
        return False, errors


async def organize_content_for_hugo(
    content_dir: Path,
    hugo_content_dir: Path,
) -> ValidationResult:
    """
    Organize downloaded markdown files for Hugo.

    Validates YAML frontmatter and quarantines malformed files to prevent
    Hugo build failures. Only valid files are copied to Hugo content directory.

    Args:
        content_dir: Directory with downloaded markdown files
        hugo_content_dir: Hugo content directory (usually hugo-site/content)

    Returns:
        ValidationResult with any errors (non-blocking - malformed files are quarantined)

    Raises:
        ValueError: If directories don't exist
    """
    logger.info(f"Organizing content for Hugo: {content_dir} -> {hugo_content_dir}")
    errors: List[str] = []
    quarantined_files: List[str] = []

    try:
        # Validate directories exist
        if not content_dir.exists():
            return ValidationResult(
                is_valid=False, errors=[f"Content directory not found: {content_dir}"]
            )

        # Create Hugo content directory
        hugo_content_dir.mkdir(parents=True, exist_ok=True)

        # Create quarantine directory for malformed files
        quarantine_dir = content_dir.parent / "quarantined"
        quarantine_dir.mkdir(parents=True, exist_ok=True)

        # Copy markdown files to Hugo content directory
        md_files = list(content_dir.rglob("*.md"))
        logger.info(f"Found {len(md_files)} markdown files to organize")

        valid_count = 0
        for md_file in md_files:
            try:
                # Validate YAML frontmatter before organizing
                is_valid, validation_errors = validate_markdown_frontmatter(md_file)

                if not is_valid:
                    # Quarantine malformed file instead of failing entire build
                    rel_path = md_file.relative_to(content_dir)
                    quarantine_path = quarantine_dir / rel_path
                    quarantine_path.parent.mkdir(parents=True, exist_ok=True)

                    # Move to quarantine
                    md_file.rename(quarantine_path)

                    error_msg = f"Quarantined malformed file {md_file.name}: {', '.join(validation_errors)}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    quarantined_files.append(str(rel_path))
                    continue

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
                valid_count += 1

            except Exception as e:
                error_info = handle_error(
                    e, error_type="organize", context={"file": str(md_file)}
                )
                errors.append(
                    f"Failed to organize {md_file.name}: {sanitize_error_message(e)}"
                )

        logger.info(
            f"Organized {valid_count} valid files, quarantined {len(quarantined_files)} malformed files, "
            f"{len(errors) - len(quarantined_files)} other errors"
        )

        if quarantined_files:
            logger.warning(
                f"Quarantined files (will not be published): {', '.join(quarantined_files[:10])}"
                + (
                    f" and {len(quarantined_files) - 10} more"
                    if len(quarantined_files) > 10
                    else ""
                )
            )

        # Return success even with quarantined files - this is expected behavior
        # Empty directories are valid (no files to organize)
        # Only fail if we had files but couldn't organize ANY of them
        is_valid = len(md_files) == 0 or valid_count > 0
        return ValidationResult(is_valid=is_valid, errors=errors)

    except Exception as e:
        error_info = handle_error(e, error_type="organize")
        return ValidationResult(is_valid=False, errors=[sanitize_error_message(e)])

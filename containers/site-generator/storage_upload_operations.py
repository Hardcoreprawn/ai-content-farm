"""
Functional storage upload operations for site generator.

Provides pure functions for uploading content to blob storage
with comprehensive error handling and batch processing.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from libs import SecureErrorHandler

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("storage-upload-operations")


def upload_file_to_blob(
    blob_client,
    container_name: str,
    blob_name: str,
    content: str,
    content_type: str = "text/html",
) -> Dict[str, Any]:
    """
    Upload file content to blob storage.

    Pure function that uploads content to specified blob location.

    Args:
        blob_client: Initialized SimplifiedBlobClient
        container_name: Target container name
        blob_name: Target blob name
        content: File content to upload
        content_type: MIME type for content

    Returns:
        Upload result dictionary with status and metadata

    Raises:
        ValueError: If upload fails
    """
    try:
        # Upload content
        result = blob_client.upload_blob(
            container_name=container_name,
            blob_name=blob_name,
            data=content,
            content_type=content_type,
            overwrite=True,
        )

        if result.get("status") == "success":
            logger.debug(f"Uploaded {blob_name} to {container_name}")
            return {
                "status": "success",
                "container": container_name,
                "blob_name": blob_name,
                "size": len(content.encode("utf-8")),
                "content_type": content_type,
                "uploaded_at": datetime.utcnow().isoformat(),
            }
        else:
            raise ValueError(f"Upload failed: {result.get('message', 'Unknown error')}")

    except (ValueError, TypeError) as e:
        error_response = error_handler.handle_error(
            e,
            "validation",
            context={"blob_name": blob_name, "container": container_name},
        )
        logger.error(f"Failed to upload {blob_name}: {error_response['message']}")
        raise ValueError(error_response["message"]) from e
    except Exception as e:
        error_response = error_handler.handle_error(
            e, "general", context={"blob_name": blob_name, "container": container_name}
        )
        logger.error(
            f"Unexpected upload failure for {blob_name}: {error_response['message']}"
        )
        raise RuntimeError(error_response["message"]) from e


def upload_batch_files(
    blob_client, container_name: str, files: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Upload multiple files to blob storage in batch.

    Pure function that uploads multiple files and returns comprehensive results.

    Args:
        blob_client: Initialized SimplifiedBlobClient
        container_name: Target container name
        files: List of file dictionaries with blob_name, content, content_type

    Returns:
        Batch upload results with success/failure counts and details
    """
    try:
        if not files:
            return {
                "status": "success",
                "total_files": 0,
                "successful": 0,
                "failed": 0,
                "results": [],
            }

        results = []
        successful = 0
        failed = 0

        for file_info in files:
            try:
                # Validate file info
                if not all(key in file_info for key in ["blob_name", "content"]):
                    raise ValueError(
                        f"Missing required fields in file info: {file_info.keys()}"
                    )

                # Upload individual file
                upload_result = upload_file_to_blob(
                    blob_client=blob_client,
                    container_name=container_name,
                    blob_name=file_info["blob_name"],
                    content=file_info["content"],
                    content_type=file_info.get("content_type", "text/html"),
                )

                results.append(upload_result)
                successful += 1

            except Exception as e:
                error_response = error_handler.handle_error(
                    e,
                    "processing",
                    context={"blob_name": file_info.get("blob_name", "unknown")},
                )
                error_result = {
                    "status": "error",
                    "blob_name": file_info.get("blob_name", "unknown"),
                    "error": error_response["message"],
                }
                results.append(error_result)
                failed += 1
                logger.error(
                    f"Failed to upload {file_info.get('blob_name')}: {error_response['message']}"
                )

        # Return batch results
        batch_status = (
            "success" if failed == 0 else "partial" if successful > 0 else "error"
        )

        return {
            "status": batch_status,
            "total_files": len(files),
            "successful": successful,
            "failed": failed,
            "results": results,
            "completed_at": datetime.utcnow().isoformat(),
        }

    except (ValueError, TypeError) as e:
        error_response = error_handler.handle_error(
            e, "validation", context={"total_files": len(files) if files else 0}
        )
        logger.error(f"Batch upload validation failed: {error_response['message']}")
        return {
            "status": "error",
            "total_files": len(files) if files else 0,
            "successful": 0,
            "failed": len(files) if files else 0,
            "error": error_response["message"],
            "completed_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        error_response = error_handler.handle_error(
            e, "general", context={"total_files": len(files) if files else 0}
        )
        logger.error(f"Batch upload operation failed: {error_response['message']}")
        return {
            "status": "error",
            "total_files": len(files) if files else 0,
            "successful": 0,
            "failed": len(files) if files else 0,
            "error": error_response["message"],
            "completed_at": datetime.utcnow().isoformat(),
        }


def upload_static_site_files(
    blob_client,
    container_name: str,
    site_files: Dict[str, str],
    site_id: str = "default",
) -> Dict[str, Any]:
    """
    Upload complete static site files to blob storage.

    Pure function that uploads all site files (HTML, CSS, feeds) in batch.

    Args:
        blob_client: Initialized SimplifiedBlobClient
        container_name: Target container name
        site_files: Dictionary mapping file paths to content
        site_id: Site identifier for organization

    Returns:
        Static site upload results with file details
    """
    try:
        # Prepare files for batch upload
        files_to_upload = []

        for file_path, content in site_files.items():
            # Determine content type based on file extension
            if file_path.endswith(".html"):
                content_type = "text/html"
            elif file_path.endswith(".xml"):
                content_type = "application/xml"
            elif file_path.endswith(".css"):
                content_type = "text/css"
            elif file_path.endswith(".json"):
                content_type = "application/json"
            elif file_path.endswith(".txt"):
                content_type = "text/plain"
            else:
                content_type = "text/html"  # Default

            # Create blob path with site organization
            blob_path = f"sites/{site_id}/{file_path.lstrip('/')}"

            files_to_upload.append(
                {
                    "blob_name": blob_path,
                    "content": content,
                    "content_type": content_type,
                }
            )

        # Upload all files in batch
        batch_result = upload_batch_files(
            blob_client=blob_client,
            container_name=container_name,
            files=files_to_upload,
        )

        # Add site-specific metadata
        batch_result.update(
            {
                "site_id": site_id,
                "site_files": len(site_files),
                "site_url": f"/sites/{site_id}/",
                "files_uploaded": [
                    {
                        "path": file_path,
                        "blob_name": f"sites/{site_id}/{file_path.lstrip('/')}",
                        "size": len(content.encode("utf-8")),
                    }
                    for file_path, content in site_files.items()
                ],
            }
        )

        logger.info(f"Uploaded static site '{site_id}' with {len(site_files)} files")
        return batch_result

    except Exception as e:
        logger.error(f"Static site upload failed: {e}")
        return {
            "status": "error",
            "site_id": site_id,
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat(),
        }


def upload_markdown_files(
    blob_client, container_name: str, markdown_files: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Upload markdown files with frontmatter to blob storage.

    Pure function that uploads markdown content with proper organization.

    Args:
        blob_client: Initialized SimplifiedBlobClient
        container_name: Target container name
        markdown_files: Dictionary mapping file names to markdown data

    Returns:
        Markdown upload results with file details
    """
    try:
        # Prepare markdown files for upload
        files_to_upload = []

        for filename, markdown_data in markdown_files.items():
            # Validate markdown data structure
            if not isinstance(markdown_data, dict) or "content" not in markdown_data:
                logger.warning(f"Invalid markdown data for {filename}")
                continue

            # Ensure filename has .md extension
            if not filename.endswith(".md"):
                filename = f"{filename}.md"

            # Create blob path in markdown directory
            blob_path = f"markdown/{filename}"

            files_to_upload.append(
                {
                    "blob_name": blob_path,
                    "content": markdown_data["content"],
                    "content_type": "text/markdown",
                }
            )

        # Upload all markdown files
        batch_result = upload_batch_files(
            blob_client=blob_client,
            container_name=container_name,
            files=files_to_upload,
        )

        # Add markdown-specific metadata
        batch_result.update(
            {
                "markdown_files": len(markdown_files),
                "files_uploaded": [
                    {
                        "filename": filename,
                        "blob_name": f"markdown/{filename if filename.endswith('.md') else filename + '.md'}",
                        "has_frontmatter": "frontmatter" in data,
                        "size": len(data["content"].encode("utf-8")),
                    }
                    for filename, data in markdown_files.items()
                    if isinstance(data, dict) and "content" in data
                ],
            }
        )

        logger.info(f"Uploaded {len(markdown_files)} markdown files")
        return batch_result

    except Exception as e:
        logger.error(f"Markdown upload failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat(),
        }


def create_upload_summary(upload_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create comprehensive summary of multiple upload operations.

    Pure function that aggregates upload results for reporting.

    Args:
        upload_results: List of upload result dictionaries

    Returns:
        Combined upload operation summary
    """
    try:
        if not upload_results:
            return {
                "status": "success",
                "total_operations": 0,
                "total_files": 0,
                "successful_files": 0,
                "failed_files": 0,
                "operations": [],
            }

        total_files = 0
        successful_files = 0
        failed_files = 0
        operations_summary = []

        for result in upload_results:
            # Extract operation details
            operation_files = result.get("total_files", 0)
            operation_successful = result.get("successful", 0)
            operation_failed = result.get("failed", 0)

            total_files += operation_files
            successful_files += operation_successful
            failed_files += operation_failed

            # Create operation summary
            operation_summary = {
                "type": result.get("type", "upload"),
                "status": result.get("status", "unknown"),
                "files": operation_files,
                "successful": operation_successful,
                "failed": operation_failed,
                "container": result.get("container", "unknown"),
                "completed_at": result.get("completed_at"),
            }

            operations_summary.append(operation_summary)

        # Determine overall status
        overall_status = (
            "success"
            if failed_files == 0
            else "partial" if successful_files > 0 else "error"
        )

        return {
            "status": overall_status,
            "total_operations": len(upload_results),
            "total_files": total_files,
            "successful_files": successful_files,
            "failed_files": failed_files,
            "success_rate": (
                (successful_files / total_files * 100) if total_files > 0 else 0
            ),
            "operations": operations_summary,
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Upload summary creation failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "generated_at": datetime.utcnow().isoformat(),
        }

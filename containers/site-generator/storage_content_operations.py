"""
Functional storage download and content operations for site generator.

Provides pure functions for downloading content from blob storage,
listing articles, and verifying container accessibility.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def download_blob_content(
    blob_client, container_name: str, blob_name: str, encoding: str = "utf-8"
) -> Dict[str, Any]:
    """
    Download blob content as string.

    Pure function that downloads and decodes blob content.

    Args:
        blob_client: Initialized SimplifiedBlobClient
        container_name: Source container name
        blob_name: Source blob name
        encoding: Text encoding for content

    Returns:
        Download result with content and metadata

    Raises:
        ValueError: If download fails or blob doesn't exist
    """
    try:
        # Download blob
        result = blob_client.download_blob(container_name, blob_name)

        if result.get("status") == "success":
            content = result["content"]

            # Decode if bytes
            if isinstance(content, bytes):
                content = content.decode(encoding)

            logger.debug(f"Downloaded {blob_name} from {container_name}")
            return {
                "status": "success",
                "content": content,
                "container": container_name,
                "blob_name": blob_name,
                "size": len(content.encode(encoding)),
                "downloaded_at": datetime.utcnow().isoformat(),
            }
        else:
            raise ValueError(
                f"Download failed: {result.get('message', 'Blob not found')}"
            )

    except Exception as e:
        logger.error(f"Failed to download {blob_name}: {e}")
        raise ValueError(f"Blob download failed: {e}")


def list_processed_articles(
    blob_client,
    container_name: str,
    prefix: str = "",
    max_results: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    List processed articles from blob storage.

    Pure function that retrieves article metadata from blob listings.

    Args:
        blob_client: Initialized SimplifiedBlobClient
        container_name: Container to search
        prefix: Optional blob name prefix filter
        max_results: Optional limit on results

    Returns:
        List of article metadata dictionaries

    Raises:
        ValueError: If listing fails
    """
    try:
        # List blobs
        blobs = blob_client.list_blobs(
            container_name=container_name,
            name_starts_with=prefix,
            max_results=max_results,
        )

        articles = []

        for blob in blobs:
            try:
                # Parse blob name for article info
                blob_name = blob.get("name", "")
                if not blob_name.endswith(".json"):
                    continue

                # Extract article slug from blob name
                article_slug = (
                    blob_name.replace(".json", "").replace(prefix, "").strip("/")
                )
                if not article_slug:
                    continue

                # Get blob metadata
                size = blob.get("size", 0)
                last_modified = blob.get("last_modified")

                article_info = {
                    "slug": article_slug,
                    "blob_name": blob_name,
                    "container": container_name,
                    "size": size,
                    "last_modified": (
                        last_modified.isoformat() if last_modified else None
                    ),
                    "url": f"/articles/{article_slug}/",
                }

                articles.append(article_info)

            except Exception as e:
                logger.warning(
                    f"Error processing blob {blob.get('name', 'unknown')}: {e}"
                )
                continue

        logger.debug(f"Listed {len(articles)} articles from {container_name}")
        return articles

    except Exception as e:
        logger.error(f"Failed to list articles: {e}")
        raise ValueError(f"Article listing failed: {e}")


def load_article_content(
    blob_client, container_name: str, article_slug: str, file_extension: str = ".json"
) -> Dict[str, Any]:
    """
    Load complete article content from blob storage.

    Pure function that downloads and parses article data.

    Args:
        blob_client: Initialized SimplifiedBlobClient
        container_name: Source container name
        article_slug: Article identifier/slug
        file_extension: File extension to append

    Returns:
        Article data dictionary with content and metadata

    Raises:
        ValueError: If article loading fails
    """
    try:
        # Construct blob name
        blob_name = f"{article_slug}{file_extension}"

        # Download content
        download_result = download_blob_content(
            blob_client=blob_client, container_name=container_name, blob_name=blob_name
        )

        if download_result["status"] != "success":
            raise ValueError(
                f"Failed to download article: {download_result.get('error', 'Unknown error')}"
            )

        # Parse JSON content
        content = download_result["content"]
        try:
            article_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in article {article_slug}: {e}")

        # Add metadata
        article_data.update(
            {
                "slug": article_slug,
                "blob_name": blob_name,
                "container": container_name,
                "loaded_at": datetime.utcnow().isoformat(),
            }
        )

        logger.debug(f"Loaded article content for: {article_slug}")
        return article_data

    except Exception as e:
        logger.error(f"Failed to load article {article_slug}: {e}")
        raise ValueError(f"Article loading failed: {e}")


def batch_load_articles(
    blob_client,
    container_name: str,
    article_slugs: List[str],
    file_extension: str = ".json",
) -> Dict[str, Any]:
    """
    Load multiple articles in batch operation.

    Pure function that loads multiple articles and returns comprehensive results.

    Args:
        blob_client: Initialized SimplifiedBlobClient
        container_name: Source container name
        article_slugs: List of article identifiers
        file_extension: File extension to append

    Returns:
        Batch load results with articles and error information
    """
    try:
        if not article_slugs:
            return {
                "status": "success",
                "total_requested": 0,
                "successful": 0,
                "failed": 0,
                "articles": [],
                "errors": [],
            }

        articles = []
        errors = []
        successful = 0

        for slug in article_slugs:
            try:
                article_data = load_article_content(
                    blob_client=blob_client,
                    container_name=container_name,
                    article_slug=slug,
                    file_extension=file_extension,
                )

                articles.append(article_data)
                successful += 1

            except Exception as e:
                error_info = {"slug": slug, "error": str(e)}
                errors.append(error_info)
                logger.error(f"Failed to load article {slug}: {e}")

        failed = len(errors)
        batch_status = (
            "success" if failed == 0 else "partial" if successful > 0 else "error"
        )

        return {
            "status": batch_status,
            "total_requested": len(article_slugs),
            "successful": successful,
            "failed": failed,
            "articles": articles,
            "errors": errors,
            "completed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Batch article loading failed: {e}")
        return {
            "status": "error",
            "total_requested": len(article_slugs) if article_slugs else 0,
            "successful": 0,
            "failed": len(article_slugs) if article_slugs else 0,
            "articles": [],
            "errors": [{"error": str(e)}],
            "completed_at": datetime.utcnow().isoformat(),
        }


def verify_storage_containers(
    blob_client, required_containers: List[str]
) -> Dict[str, Any]:
    """
    Verify that all required storage containers exist and are accessible.

    Pure function that checks container existence and permissions.

    Args:
        blob_client: Initialized SimplifiedBlobClient
        required_containers: List of container names to verify

    Returns:
        Verification results with container status information
    """
    try:
        container_status = {}
        all_accessible = True

        for container_name in required_containers:
            try:
                # Test container access by listing (limit to 1 item)
                blobs = blob_client.list_blobs(container_name, max_results=1)

                # If we can list, container is accessible
                container_status[container_name] = {
                    "exists": True,
                    "accessible": True,
                    "error": None,
                }

                logger.debug(f"Container {container_name} verified")

            except Exception as e:
                container_status[container_name] = {
                    "exists": False,
                    "accessible": False,
                    "error": str(e),
                }
                all_accessible = False
                logger.error(f"Container {container_name} not accessible: {e}")

        return {
            "status": "success" if all_accessible else "error",
            "all_accessible": all_accessible,
            "containers": container_status,
            "verified_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Container verification failed: {e}")
        return {
            "status": "error",
            "all_accessible": False,
            "containers": {
                container: {"exists": False, "accessible": False, "error": str(e)}
                for container in required_containers
            },
            "error": str(e),
            "verified_at": datetime.utcnow().isoformat(),
        }


def search_articles_by_criteria(
    blob_client, container_name: str, search_criteria: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Search for articles based on specific criteria.

    Pure function that searches articles with filtering capabilities.

    Args:
        blob_client: Initialized SimplifiedBlobClient
        container_name: Container to search
        search_criteria: Dictionary with search parameters

    Returns:
        List of matching articles with metadata
    """
    try:
        # Extract search parameters
        title_filter = search_criteria.get("title_contains", "")
        date_from = search_criteria.get("date_from")
        date_to = search_criteria.get("date_to")
        tags_filter = search_criteria.get("tags", [])
        max_results = search_criteria.get("max_results", 50)

        # Get all articles first
        all_articles = list_processed_articles(
            blob_client=blob_client,
            container_name=container_name,
            max_results=max_results * 2,  # Get more to allow for filtering
        )

        matching_articles = []

        for article_info in all_articles:
            try:
                # Load full article content for filtering
                article_data = load_article_content(
                    blob_client=blob_client,
                    container_name=container_name,
                    article_slug=article_info["slug"],
                )

                # Apply filters
                if (
                    title_filter
                    and title_filter.lower()
                    not in article_data.get("title", "").lower()
                ):
                    continue

                # Date filtering (if dates are provided)
                if date_from or date_to:
                    article_date = article_data.get("published_date")
                    if article_date:
                        try:
                            if isinstance(article_date, str):
                                article_datetime = datetime.fromisoformat(
                                    article_date.replace("Z", "+00:00")
                                )
                            else:
                                article_datetime = article_date

                            if date_from and article_datetime < datetime.fromisoformat(
                                date_from
                            ):
                                continue
                            if date_to and article_datetime > datetime.fromisoformat(
                                date_to
                            ):
                                continue
                        except (ValueError, TypeError):
                            # Skip articles with invalid dates
                            continue

                # Tags filtering
                if tags_filter:
                    article_tags = article_data.get("tags", [])
                    if not any(tag in article_tags for tag in tags_filter):
                        continue

                matching_articles.append(article_data)

                # Limit results
                if len(matching_articles) >= max_results:
                    break

            except Exception as e:
                logger.warning(f"Error processing article {article_info['slug']}: {e}")
                continue

        logger.debug(
            f"Found {len(matching_articles)} articles matching search criteria"
        )
        return matching_articles

    except Exception as e:
        logger.error(f"Article search failed: {e}")
        raise ValueError(f"Search operation failed: {e}")


def create_storage_summary(
    container_results: Dict[str, Any], operation_results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create comprehensive storage operation summary.

    Pure function that aggregates storage operation results.

    Args:
        container_results: Container verification results
        operation_results: Storage operation results

    Returns:
        Combined storage operation summary
    """
    try:
        # Calculate totals
        total_containers = len(container_results.get("containers", {}))
        accessible_containers = sum(
            1
            for status in container_results.get("containers", {}).values()
            if status.get("accessible", False)
        )

        total_operations = operation_results.get("total_operations", 0)
        successful_operations = operation_results.get("successful", 0)
        failed_operations = operation_results.get("failed", 0)

        # Determine overall status
        container_ok = container_results.get("all_accessible", False)
        operations_ok = operation_results.get("status") in ["success", "partial"]
        overall_status = "success" if container_ok and operations_ok else "error"

        return {
            "status": overall_status,
            "summary": {
                "containers": {
                    "total": total_containers,
                    "accessible": accessible_containers,
                    "failed": total_containers - accessible_containers,
                },
                "operations": {
                    "total": total_operations,
                    "successful": successful_operations,
                    "failed": failed_operations,
                },
            },
            "container_results": container_results,
            "operation_results": operation_results,
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Storage summary creation failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "container_results": container_results,
            "operation_results": operation_results,
            "generated_at": datetime.utcnow().isoformat(),
        }

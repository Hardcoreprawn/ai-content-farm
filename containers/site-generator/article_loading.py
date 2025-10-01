"""
Article Loading and Search Operations

Pure functions for loading, listing, and searching articles in blob storage.
Extracted from storage_content_operations.py for better maintainability.
"""

import json
import logging
import os

# Import from same directory (site-generator container)
# Use explicit path to avoid conflict with libs.blob_operations
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from content_download_operations import download_blob_content

sys.path.insert(0, os.path.dirname(__file__))
# Import from same directory (site-generator container)
# Import from same directory (site-generator container) - now with clear name

logger = logging.getLogger(__name__)


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

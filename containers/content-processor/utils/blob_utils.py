"""
Blob path utility functions.

Provides standardized blob path generation for Azure Blob Storage
following consistent naming conventions.

Path format: prefix/YYYY/MM/DD/YYYYMMdd_HHMMSS_identifier.extension
"""

from .timestamp_utils import get_utc_timestamp


def generate_blob_path(prefix: str, identifier: str, extension: str = "json") -> str:
    """
    Generate standardized blob path with date hierarchy.

    Creates a path with year/month/day folders and timestamped filename.

    Args:
        prefix: Blob container prefix (e.g., "processed", "collected-content")
        identifier: Unique identifier for the blob (e.g., topic_id, article_id)
        extension: File extension without dot (default: "json")

    Returns:
        str: Blob path in format: prefix/YYYY/MM/DD/YYYYMMdd_HHMMSS_identifier.ext

    Example:
        >>> path = generate_blob_path("processed", "topic-123", "json")
        >>> "processed/" in path and "topic-123.json" in path
        True
        >>> # Result: "processed/2025/10/15/20251015_103000_topic-123.json"
    """
    now = get_utc_timestamp()

    # Date hierarchy: YYYY/MM/DD
    date_part = now.strftime("%Y/%m/%d")

    # Timestamp prefix: YYYYMMdd_HHMMSS
    file_part = now.strftime("%Y%m%d_%H%M%S")

    # Combine: prefix/YYYY/MM/DD/YYYYMMdd_HHMMSS_identifier.ext
    return f"{prefix}/{date_part}/{file_part}_{identifier}.{extension}"


def generate_collection_blob_path(collection_id: str) -> str:
    """
    Generate standardized path for collection blobs.

    Args:
        collection_id: Collection identifier

    Returns:
        str: Collection blob path

    Example:
        >>> path = generate_collection_blob_path("daily-tech")
        >>> "collections/" in path and "daily-tech.json" in path
        True
    """
    return generate_blob_path("collections", collection_id, "json")


def generate_processed_blob_path(topic_id: str) -> str:
    """
    Generate standardized path for processed article blobs.

    Args:
        topic_id: Topic/article identifier

    Returns:
        str: Processed article blob path

    Example:
        >>> path = generate_processed_blob_path("ai-breakthrough")
        >>> "processed/" in path and "ai-breakthrough.json" in path
        True
    """
    return generate_blob_path("processed", topic_id, "json")


def generate_markdown_blob_path(article_id: str) -> str:
    """
    Generate standardized path for markdown output blobs.

    Args:
        article_id: Article identifier

    Returns:
        str: Markdown blob path

    Example:
        >>> path = generate_markdown_blob_path("article-456")
        >>> "markdown/" in path and "article-456.md" in path
        True
    """
    return generate_blob_path("markdown", article_id, "md")

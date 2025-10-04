"""
Application Configuration

Application-specific configuration values including container names,
processing settings, and other application constants.

This module contains configuration that is specific to the AI Content Farm
application and should not be in generic library modules.
"""


class BlobContainers:
    """Standard container names for different content types."""

    COLLECTED_CONTENT = "collected-content"
    PROCESSED_CONTENT = "processed-content"
    MARKDOWN_CONTENT = "markdown-content"
    PIPELINE_LOGS = "pipeline-logs"
    CMS_EXPORTS = "cms-exports"
    COLLECTION_TEMPLATES = "collection-templates"
    # Removed: ENRICHED_CONTENT, RANKED_CONTENT, STATIC_SITES (containers deleted)


class ProcessingConfig:
    """Configuration for content processing pipeline."""

    # Default batch sizes
    DEFAULT_BATCH_SIZE = 32
    MAX_BATCH_SIZE = 32

    # Timeout settings (in seconds)
    DEFAULT_TIMEOUT = 300
    LONG_RUNNING_TIMEOUT = 1800

    # Content quality thresholds
    MIN_CONTENT_LENGTH = 100
    MAX_CONTENT_LENGTH = 50000


__all__ = ["BlobContainers", "ProcessingConfig"]

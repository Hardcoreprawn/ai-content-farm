"""
Standardized Blob Path Management

Provides consistent path naming across all containers for:
- Collections: Date-based hierarchy with source identification
- Processing: Processing state and pipeline stage tracking
- Generated: Final output organization

Usage:
    from libs.blob_paths import BlobPathManager

    path_manager = BlobPathManager()
    collection_path = path_manager.get_collection_path("arstechnica.com")
    # Returns: collections/2025/09/27/08/080026_arstechnica.com.json
"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import urlparse


class BlobPathManager:
    """Standardized blob path management for consistent naming across containers."""

    def __init__(self, base_timezone=timezone.utc):
        self.base_timezone = base_timezone

    def get_collection_path(
        self,
        source_identifier: str,
        timestamp: Optional[datetime] = None,
        container: str = "collected-content",
    ) -> str:
        """
        Generate standardized collection blob path.

        Format: collections/YYYY/MM/DD/HH/HHMMSS_source.json
        Example: collections/2025/09/27/08/080026_arstechnica.com.json

        Args:
            source_identifier: Source domain or identifier (e.g., "arstechnica.com", "reddit.r_technology")
            timestamp: Optional datetime (defaults to now)
            container: Container name (for reference, not included in path)

        Returns:
            str: Standardized blob path
        """
        if timestamp is None:
            timestamp = datetime.now(self.base_timezone)

        # Sanitize source identifier for filename safety
        safe_source = self._sanitize_source_identifier(source_identifier)

        # Format: collections/YYYY/MM/DD/HH/HHMMSS_source.json
        path = (
            f"collections/"
            f"{timestamp.year:04d}/"
            f"{timestamp.month:02d}/"
            f"{timestamp.day:02d}/"
            f"{timestamp.hour:02d}/"
            f"{timestamp.hour:02d}{timestamp.minute:02d}{timestamp.second:02d}_{safe_source}.json"
        )

        return path

    def get_processing_path(
        self,
        collection_source: str,
        processing_stage: str,
        timestamp: Optional[datetime] = None,
        container: str = "processed-content",
    ) -> str:
        """
        Generate processing stage blob path.

        Format: processing/YYYY/MM/DD/stage/HHMMSS_source.json
        Example: processing/2025/09/27/enriched/080026_arstechnica.com.json

        Args:
            collection_source: Original collection source identifier
            processing_stage: Processing stage (e.g., "ranked", "enriched", "generated")
            timestamp: Optional datetime (defaults to now)
            container: Container name (for reference)

        Returns:
            str: Processing stage blob path
        """
        if timestamp is None:
            timestamp = datetime.now(self.base_timezone)

        safe_source = self._sanitize_source_identifier(collection_source)
        safe_stage = self._sanitize_stage_name(processing_stage)

        path = (
            f"processing/"
            f"{timestamp.year:04d}/"
            f"{timestamp.month:02d}/"
            f"{timestamp.day:02d}/"
            f"{safe_stage}/"
            f"{timestamp.hour:02d}{timestamp.minute:02d}{timestamp.second:02d}_{safe_source}.json"
        )

        return path

    def get_generated_path(
        self,
        content_type: str,
        topic_id: str,
        timestamp: Optional[datetime] = None,
        container: str = "generated-content",
    ) -> str:
        """
        Generate final output blob path.

        Format: generated/YYYY/MM/DD/type/topic_id.ext
        Example: generated/2025/09/27/articles/apple-airpods-pro-3-review.md

        Args:
            content_type: Type of generated content (e.g., "articles", "summaries")
            topic_id: Topic identifier (sanitized)
            timestamp: Optional datetime (defaults to now)
            container: Container name (for reference)

        Returns:
            str: Generated content blob path
        """
        if timestamp is None:
            timestamp = datetime.now(self.base_timezone)

        safe_topic = self._sanitize_topic_id(topic_id)
        safe_type = self._sanitize_stage_name(content_type)

        # Determine file extension based on content type
        extension = self._get_extension_for_content_type(content_type)

        path = (
            f"generated/"
            f"{timestamp.year:04d}/"
            f"{timestamp.month:02d}/"
            f"{timestamp.day:02d}/"
            f"{safe_type}/"
            f"{safe_topic}.{extension}"
        )

        return path

    def parse_collection_path(self, blob_path: str) -> Optional[Dict[str, str]]:
        """
        Parse a collection blob path to extract metadata.

        Args:
            blob_path: Blob path to parse

        Returns:
            Dict with keys: year, month, day, hour, minute, second, source, original_path
            None if path doesn't match expected format
        """
        # Pattern: collections/YYYY/MM/DD/HH/HHMMSS_source.json
        pattern = r"collections/(\d{4})/(\d{2})/(\d{2})/(\d{2})/(\d{2})(\d{2})(\d{2})_(.+)\.json$"
        match = re.match(pattern, blob_path)

        if not match:
            return None

        return {
            "year": match.group(1),
            "month": match.group(2),
            "day": match.group(3),
            "hour": match.group(4),
            "minute": match.group(6),
            "second": match.group(7),
            "source": match.group(8),
            "original_path": blob_path,
            "timestamp_str": f"{match.group(1)}-{match.group(2)}-{match.group(3)}T{match.group(4)}:{match.group(6)}:{match.group(7)}+00:00",
        }

    def list_collections_by_date(
        self, year: int, month: int, day: int, hour: Optional[int] = None
    ) -> str:
        """
        Generate blob prefix for listing collections by date.

        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)
            day: Day (1-31)
            hour: Optional hour (0-23) for more specific filtering

        Returns:
            str: Blob prefix for filtering
        """
        prefix = f"collections/{year:04d}/{month:02d}/{day:02d}/"

        if hour is not None:
            prefix += f"{hour:02d}/"

        return prefix

    def list_processing_by_stage(
        self, processing_stage: str, year: int, month: int, day: int
    ) -> str:
        """
        Generate blob prefix for listing processing files by stage and date.

        Args:
            processing_stage: Processing stage to filter by
            year: Year (e.g., 2025)
            month: Month (1-12)
            day: Day (1-31)

        Returns:
            str: Blob prefix for filtering
        """
        safe_stage = self._sanitize_stage_name(processing_stage)
        return f"processing/{year:04d}/{month:02d}/{day:02d}/{safe_stage}/"

    def _sanitize_source_identifier(self, source: str) -> str:
        """Sanitize source identifier for filename safety."""
        # Replace common URL chars with safe equivalents
        safe = source.lower()
        safe = re.sub(r"https?://", "", safe)  # Remove protocol
        safe = re.sub(r"www\.", "", safe)  # Remove www
        safe = re.sub(r"[^a-z0-9._-]", "_", safe)  # Replace unsafe chars
        safe = re.sub(r"_+", "_", safe)  # Collapse multiple underscores
        safe = safe.strip("_")  # Remove leading/trailing underscores

        # Handle special cases
        if safe.startswith("reddit"):
            # reddit.com/r/technology -> reddit.r_technology
            safe = re.sub(r"reddit.*?/r/", "reddit.r_", safe)

        return safe

    def _sanitize_stage_name(self, stage: str) -> str:
        """Sanitize processing stage name."""
        safe = stage.lower()
        safe = re.sub(r"[^a-z0-9_-]", "_", safe)
        safe = re.sub(r"_+", "_", safe)
        return safe.strip("_")

    def _sanitize_topic_id(self, topic_id: str) -> str:
        """Sanitize topic ID for filename safety."""
        safe = topic_id.lower()
        safe = re.sub(r"[^a-z0-9_-]", "-", safe)
        safe = re.sub(r"-+", "-", safe)
        return safe.strip("-")

    def _get_extension_for_content_type(self, content_type: str) -> str:
        """Get appropriate file extension for content type."""
        extensions = {
            "articles": "md",
            "summaries": "md",
            "json": "json",
            "html": "html",
            "text": "txt",
        }
        return extensions.get(content_type.lower(), "txt")


# Convenience instance for common usage
blob_paths = BlobPathManager()


# Helper functions for backward compatibility and ease of use
def get_collection_path(source: str, timestamp: Optional[datetime] = None) -> str:
    """Convenience function for getting collection paths."""
    return blob_paths.get_collection_path(source, timestamp)


def get_processing_path(
    source: str, stage: str, timestamp: Optional[datetime] = None
) -> str:
    """Convenience function for getting processing paths."""
    return blob_paths.get_processing_path(source, stage, timestamp)


def get_generated_path(
    content_type: str, topic_id: str, timestamp: Optional[datetime] = None
) -> str:
    """Convenience function for getting generated content paths."""
    return blob_paths.get_generated_path(content_type, topic_id, timestamp)


def parse_collection_path(blob_path: str) -> Optional[Dict[str, str]]:
    """Convenience function for parsing collection paths."""
    return blob_paths.parse_collection_path(blob_path)

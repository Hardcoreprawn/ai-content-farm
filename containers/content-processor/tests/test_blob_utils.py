"""
Tests for blob path utility functions.

Verifies standardized blob path generation following consistent
naming conventions: prefix/YYYY/MM/DD/YYYYMMdd_HHMMSS_identifier.ext
"""

import re
from datetime import datetime

from freezegun import freeze_time  # type: ignore[import-untyped]
from utils.blob_utils import (
    generate_blob_path,
    generate_collection_blob_path,
    generate_markdown_blob_path,
    generate_processed_blob_path,
)


class TestGenerateBlobPath:
    """Test generate_blob_path() function."""

    @freeze_time("2025-10-15 14:30:45")
    def test_standard_path_format(self):
        """Test that path follows standard format."""
        result = generate_blob_path("processed", "topic-123", "json")

        # Should be: processed/2025/10/15/20251015_143045_topic-123.json
        assert result == "processed/2025/10/15/20251015_143045_topic-123.json"

    @freeze_time("2025-10-15 14:30:45")
    def test_contains_date_hierarchy(self):
        """Test that path contains year/month/day hierarchy."""
        result = generate_blob_path("test", "id-456", "json")

        assert "/2025/" in result
        assert "/10/" in result
        assert "/15/" in result

    @freeze_time("2025-10-15 14:30:45")
    def test_contains_timestamp_prefix(self):
        """Test that filename starts with YYYYMMdd_HHMMSS."""
        result = generate_blob_path("prefix", "identifier", "json")

        assert "20251015_143045" in result

    def test_includes_prefix(self):
        """Test that path includes the specified prefix."""
        result = generate_blob_path("my-prefix", "id", "json")
        assert result.startswith("my-prefix/")

    def test_includes_identifier(self):
        """Test that path includes the identifier."""
        result = generate_blob_path("prefix", "my-identifier", "json")
        assert "my-identifier" in result

    def test_includes_extension(self):
        """Test that path includes the file extension."""
        result = generate_blob_path("prefix", "id", "txt")
        assert result.endswith(".txt")

    def test_default_extension_is_json(self):
        """Test that default extension is 'json'."""
        result = generate_blob_path("prefix", "id")
        assert result.endswith(".json")

    @freeze_time("2025-10-15 14:30:45")
    def test_different_extensions(self):
        """Test path generation with different extensions."""
        json_path = generate_blob_path("prefix", "id", "json")
        md_path = generate_blob_path("prefix", "id", "md")
        txt_path = generate_blob_path("prefix", "id", "txt")

        assert json_path.endswith(".json")
        assert md_path.endswith(".md")
        assert txt_path.endswith(".txt")

        # All should have same path except extension
        assert json_path[:-5] == md_path[:-3] == txt_path[:-4]

    def test_path_format_regex(self):
        """Test that generated path matches expected regex pattern."""
        result = generate_blob_path("processed", "topic-123", "json")

        # Pattern: prefix/YYYY/MM/DD/YYYYMMdd_HHMMSS_identifier.ext
        pattern = r"^processed/\d{4}/\d{2}/\d{2}/\d{8}_\d{6}_topic-123\.json$"
        assert re.match(
            pattern, result
        ), f"Path '{result}' doesn't match expected pattern"

    @freeze_time("2025-01-01 00:00:00")
    def test_midnight_timestamp(self):
        """Test path generation at midnight."""
        result = generate_blob_path("prefix", "id", "json")
        assert "20250101_000000" in result

    @freeze_time("2025-12-31 23:59:59")
    def test_end_of_year_timestamp(self):
        """Test path generation at end of year."""
        result = generate_blob_path("prefix", "id", "json")
        assert "20251231_235959" in result

    def test_special_characters_in_identifier(self):
        """Test that special characters in identifier are preserved."""
        result = generate_blob_path("prefix", "topic-with-dashes_123", "json")
        assert "topic-with-dashes_123" in result

    def test_path_is_sortable_by_time(self):
        """Test that generated paths sort chronologically."""
        import time

        paths = []
        for _ in range(3):
            paths.append(generate_blob_path("prefix", "id", "json"))
            time.sleep(0.01)  # 10ms delay

        # Paths should be in chronological order when sorted as strings
        sorted_paths = sorted(paths)
        assert paths == sorted_paths


class TestGenerateCollectionBlobPath:
    """Test generate_collection_blob_path() function."""

    @freeze_time("2025-10-15 14:30:45")
    def test_collection_path_format(self):
        """Test that collection path uses correct format."""
        result = generate_collection_blob_path("daily-tech")

        assert result == "collections/2025/10/15/20251015_143045_daily-tech.json"

    def test_uses_collections_prefix(self):
        """Test that path starts with 'collections/'."""
        result = generate_collection_blob_path("test-collection")
        assert result.startswith("collections/")

    def test_uses_json_extension(self):
        """Test that collection paths use .json extension."""
        result = generate_collection_blob_path("my-collection")
        assert result.endswith(".json")

    def test_includes_collection_id(self):
        """Test that collection ID is included in path."""
        result = generate_collection_blob_path("special-collection-id")
        assert "special-collection-id" in result

    def test_matches_standard_format(self):
        """Test that collection paths follow standard blob path format."""
        result = generate_collection_blob_path("test")

        # Should match: collections/YYYY/MM/DD/YYYYMMdd_HHMMSS_id.json
        pattern = r"^collections/\d{4}/\d{2}/\d{2}/\d{8}_\d{6}_test\.json$"
        assert re.match(pattern, result)


class TestGenerateProcessedBlobPath:
    """Test generate_processed_blob_path() function."""

    @freeze_time("2025-10-15 14:30:45")
    def test_processed_path_format(self):
        """Test that processed path uses correct format."""
        result = generate_processed_blob_path("ai-breakthrough")

        assert result == "processed/2025/10/15/20251015_143045_ai-breakthrough.json"

    def test_uses_processed_prefix(self):
        """Test that path starts with 'processed/'."""
        result = generate_processed_blob_path("topic-123")
        assert result.startswith("processed/")

    def test_uses_json_extension(self):
        """Test that processed paths use .json extension."""
        result = generate_processed_blob_path("my-topic")
        assert result.endswith(".json")

    def test_includes_topic_id(self):
        """Test that topic ID is included in path."""
        result = generate_processed_blob_path("important-topic")
        assert "important-topic" in result

    def test_matches_standard_format(self):
        """Test that processed paths follow standard blob path format."""
        result = generate_processed_blob_path("test")

        # Should match: processed/YYYY/MM/DD/YYYYMMdd_HHMMSS_id.json
        pattern = r"^processed/\d{4}/\d{2}/\d{2}/\d{8}_\d{6}_test\.json$"
        assert re.match(pattern, result)


class TestGenerateMarkdownBlobPath:
    """Test generate_markdown_blob_path() function."""

    @freeze_time("2025-10-15 14:30:45")
    def test_markdown_path_format(self):
        """Test that markdown path uses correct format."""
        result = generate_markdown_blob_path("article-456")

        assert result == "markdown/2025/10/15/20251015_143045_article-456.md"

    def test_uses_markdown_prefix(self):
        """Test that path starts with 'markdown/'."""
        result = generate_markdown_blob_path("article-123")
        assert result.startswith("markdown/")

    def test_uses_md_extension(self):
        """Test that markdown paths use .md extension."""
        result = generate_markdown_blob_path("my-article")
        assert result.endswith(".md")

    def test_includes_article_id(self):
        """Test that article ID is included in path."""
        result = generate_markdown_blob_path("featured-article")
        assert "featured-article" in result

    def test_matches_standard_format(self):
        """Test that markdown paths follow standard blob path format."""
        result = generate_markdown_blob_path("test")

        # Should match: markdown/YYYY/MM/DD/YYYYMMdd_HHMMSS_id.md
        pattern = r"^markdown/\d{4}/\d{2}/\d{2}/\d{8}_\d{6}_test\.md$"
        assert re.match(pattern, result)


class TestPathConsistency:
    """Test consistency across all blob path functions."""

    @freeze_time("2025-10-15 14:30:45")
    def test_all_functions_use_same_timestamp(self):
        """Test that all helper functions generate same timestamp at same moment."""
        collection_path = generate_collection_blob_path("id1")
        processed_path = generate_processed_blob_path("id2")
        markdown_path = generate_markdown_blob_path("id3")

        # All should contain the same timestamp: 20251015_143045
        timestamp = "20251015_143045"
        assert timestamp in collection_path
        assert timestamp in processed_path
        assert timestamp in markdown_path

    @freeze_time("2025-10-15 14:30:45")
    def test_all_functions_use_same_date_hierarchy(self):
        """Test that all functions use same date folder structure."""
        collection_path = generate_collection_blob_path("id1")
        processed_path = generate_processed_blob_path("id2")
        markdown_path = generate_markdown_blob_path("id3")

        # All should contain: 2025/10/15
        date_hierarchy = "2025/10/15"
        assert date_hierarchy in collection_path
        assert date_hierarchy in processed_path
        assert date_hierarchy in markdown_path

    def test_helper_functions_are_wrappers(self):
        """Test that helper functions are thin wrappers around generate_blob_path."""
        # These should be equivalent
        direct = generate_blob_path("collections", "test-id", "json")
        helper = generate_collection_blob_path("test-id")

        # Both should generate same path
        assert direct == helper


class TestPathProperties:
    """Test properties of generated paths."""

    def test_paths_are_relative_not_absolute(self):
        """Test that paths are relative (no leading slash)."""
        result = generate_blob_path("prefix", "id", "json")
        assert not result.startswith("/")

    def test_paths_use_forward_slashes(self):
        """Test that paths use forward slashes (not backslashes)."""
        result = generate_blob_path("prefix", "id", "json")
        assert "/" in result
        assert "\\" not in result

    def test_no_double_slashes(self):
        """Test that paths don't contain double slashes."""
        result = generate_blob_path("prefix", "id", "json")
        assert "//" not in result

    def test_no_trailing_slash(self):
        """Test that paths don't end with a slash."""
        result = generate_blob_path("prefix", "id", "json")
        assert not result.endswith("/")

    def test_extension_has_no_dot_prefix(self):
        """Test that generated extension doesn't have double dots."""
        result = generate_blob_path("prefix", "id", "json")
        assert ".." not in result

    @freeze_time("2025-10-15 14:30:45")
    def test_path_length_is_reasonable(self):
        """Test that generated paths are not excessively long."""
        result = generate_blob_path("processed", "topic-123", "json")

        # Should be reasonable length (< 200 chars for this example)
        assert len(result) < 200
        # But not too short (should have full structure)
        assert len(result) > 40

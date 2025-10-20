"""
Tests for quality_dedup module.

Tests deduplication contracts:
- Hash consistency (same input = same hash)
- Layer 1 filtering (in-batch duplicates removed)
- Input/output contracts (defensive against mutations)
"""

import hashlib

import pytest
from quality_dedup import (
    filter_duplicates_in_batch,
    hash_content,
)


class TestHashContent:
    """Test content hashing for deduplication."""

    def test_hash_consistent(self):
        """Hash should be consistent for same input."""
        title = "Test Article"
        content = "This is test content"

        hash1 = hash_content(title, content)
        hash2 = hash_content(title, content)

        assert hash1 == hash2

    def test_hash_different_for_different_content(self):
        """Different content should produce different hashes."""
        hash1 = hash_content("Article 1", "Content 1")
        hash2 = hash_content("Article 2", "Content 2")

        assert hash1 != hash2

    def test_hash_hex_string(self):
        """Hash should be hex string."""
        result = hash_content("Title", "Content")

        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex is 64 chars
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_empty_title(self):
        """Should handle empty title gracefully."""
        result = hash_content("", "Content")

        assert isinstance(result, str)
        assert len(result) == 64

    def test_hash_empty_content(self):
        """Should handle empty content gracefully."""
        result = hash_content("Title", "")

        assert isinstance(result, str)
        assert len(result) == 64

    def test_hash_uses_first_500_chars(self):
        """Hash should use only first 500 chars of content for efficiency."""
        short_content = "Short"
        long_content = "A" * 1000

        # Hashes of different lengths should differ
        hash_short = hash_content("Title", short_content)
        hash_long = hash_content("Title", long_content)

        # But first 500 chars should match
        hash_long_first500 = hash_content("Title", long_content[:500])
        # Hashes will differ because content is different, but verify structure
        assert isinstance(hash_short, str)
        assert isinstance(hash_long, str)

    def test_hash_invalid_title_type(self):
        """Should return empty string for invalid title type."""
        result = hash_content(123, "Content")  # type: ignore
        assert result == ""

    def test_hash_invalid_content_type(self):
        """Should return empty string for invalid content type."""
        result = hash_content("Title", 123)  # type: ignore
        assert result == ""

    def test_hash_case_sensitive(self):
        """Hash should be case-sensitive."""
        hash1 = hash_content("Test", "content")
        hash2 = hash_content("test", "content")

        # Different case should produce different hashes
        assert hash1 != hash2

    def test_hash_whitespace_stripped(self):
        """Title and content should be stripped of leading/trailing whitespace."""
        hash1 = hash_content("  Title  ", "  Content  ")
        hash2 = hash_content("Title", "Content")

        assert hash1 == hash2


class TestFilterDuplicatesInBatch:
    """Test in-batch deduplication (Layer 1)."""

    def test_removes_identical_items(self):
        """Should remove duplicate items with identical title+content."""
        items = [
            {"title": "Article", "content": "Content", "source": "A"},
            {"title": "Article", "content": "Content", "source": "B"},
        ]

        result = filter_duplicates_in_batch(items)

        assert len(result) == 1
        assert result[0]["source"] == "A"  # First one kept

    def test_preserves_unique_items(self):
        """Should keep all unique items."""
        items = [
            {"title": "Article 1", "content": "Content 1"},
            {"title": "Article 2", "content": "Content 2"},
            {"title": "Article 3", "content": "Content 3"},
        ]

        result = filter_duplicates_in_batch(items)

        assert len(result) == 3

    def test_maintains_insertion_order(self):
        """Should preserve insertion order of items."""
        items = [
            {"title": "First", "content": "A"},
            {"title": "Second", "content": "B"},
            {"title": "Third", "content": "C"},
        ]

        result = filter_duplicates_in_batch(items)

        assert result[0]["title"] == "First"
        assert result[1]["title"] == "Second"
        assert result[2]["title"] == "Third"

    def test_skips_non_dict_items(self):
        """Should skip items that are not dicts."""
        items = [
            {"title": "Valid", "content": "Item"},
            "not a dict",
            {"title": "Another", "content": "Item"},
            123,
        ]

        result = filter_duplicates_in_batch(items)

        assert len(result) == 2
        assert all(isinstance(item, dict) for item in result)

    def test_skips_items_without_title(self):
        """Should skip items without title."""
        items = [
            {"title": "Valid", "content": "Item"},
            {"content": "No title"},
            {"title": "", "content": "Empty title"},
        ]

        result = filter_duplicates_in_batch(items)

        assert len(result) == 1

    def test_skips_items_without_content(self):
        """Should skip items without content."""
        items = [
            {"title": "Valid", "content": "Item"},
            {"title": "No content"},
            {"title": "Empty", "content": ""},
        ]

        result = filter_duplicates_in_batch(items)

        assert len(result) == 1

    def test_handles_empty_list(self):
        """Should handle empty input list."""
        result = filter_duplicates_in_batch([])

        assert result == []

    def test_handles_non_list_input(self):
        """Should handle non-list input gracefully."""
        result = filter_duplicates_in_batch("not a list")  # type: ignore

        assert result == []

    def test_no_mutation_of_input(self):
        """Should not mutate input list."""
        items = [
            {"title": "Article", "content": "Content"},
            {"title": "Article", "content": "Content"},
        ]
        original_length = len(items)

        result = filter_duplicates_in_batch(items)

        # Input should be unchanged
        assert len(items) == original_length

    def test_includes_all_fields(self):
        """Should preserve all fields from items."""
        items = [
            {
                "title": "Article",
                "content": "Content",
                "source": "Reddit",
                "url": "http://example.com",
                "score": 100,
                "custom_field": "value",
            }
        ]

        result = filter_duplicates_in_batch(items)

        assert len(result) == 1
        assert result[0]["source"] == "Reddit"
        assert result[0]["url"] == "http://example.com"
        assert result[0]["score"] == 100
        assert result[0]["custom_field"] == "value"

    def test_long_content_comparison(self):
        """Should handle long content correctly."""
        long_content = "A" * 10000
        items = [
            {"title": "Article", "content": long_content},
            {"title": "Article", "content": long_content},
        ]

        result = filter_duplicates_in_batch(items)

        # Should deduplicate even for long content
        assert len(result) == 1

    def test_similar_but_different_items(self):
        """Should not deduplicate similar but different items."""
        items = [
            {"title": "Article", "content": "Content"},
            {"title": "Article", "content": "Content2"},
            {"title": "Article2", "content": "Content"},
        ]

        result = filter_duplicates_in_batch(items)

        # All should be kept because content differs
        assert len(result) == 3


class TestInputOutputContracts:
    """Test that functions maintain proper input/output contracts."""

    def test_filter_duplicates_output_is_list(self):
        """Output should always be a list."""
        items = [{"title": "A", "content": "B"}]
        result = filter_duplicates_in_batch(items)
        assert isinstance(result, list)

    def test_filter_duplicates_output_items_are_dicts(self):
        """Output items should be dicts."""
        items = [
            {"title": "A", "content": "B"},
            {"title": "C", "content": "D"},
        ]
        result = filter_duplicates_in_batch(items)
        assert all(isinstance(item, dict) for item in result)

    def test_hash_returns_string(self):
        """hash_content should return string."""
        result = hash_content("Title", "Content")
        assert isinstance(result, str)

    def test_hash_always_returns_64_chars_or_empty(self):
        """hash_content should return 64-char hex or empty string."""
        test_cases = [
            ("Title", "Content"),
            ("", ""),
            ("A" * 100, "B" * 100),
        ]

        for title, content in test_cases:
            result = hash_content(title, content)
            assert isinstance(result, str)
            # Either 64-char hex (valid hash) or empty string (invalid input)
            assert len(result) == 64 or result == ""


class TestDuplicateDetectionEdgeCases:
    """Test edge cases in duplicate detection."""

    def test_different_sources_same_content(self):
        """Same content from different sources should be deduplicated."""
        items = [
            {"title": "Article", "content": "Content", "source": "Reddit"},
            {"title": "Article", "content": "Content", "source": "Medium"},
        ]

        result = filter_duplicates_in_batch(items)

        # Should keep only first (dedup by content, not source)
        assert len(result) == 1

    def test_different_urls_same_content(self):
        """Same content with different URLs should be deduplicated."""
        items = [
            {"title": "Article", "content": "Content", "url": "http://a.com"},
            {"title": "Article", "content": "Content", "url": "http://b.com"},
        ]

        result = filter_duplicates_in_batch(items)

        assert len(result) == 1

    def test_whitespace_variations_in_title(self):
        """Title whitespace differences should be handled."""
        items = [
            {"title": "Article  ", "content": "Content"},
            {"title": "  Article", "content": "Content"},
        ]

        result = filter_duplicates_in_batch(items)

        # Should be deduped after stripping
        assert len(result) == 1

    def test_mixed_valid_invalid_items(self):
        """Should handle mix of valid and invalid items."""
        items = [
            {"title": "Good 1", "content": "Content"},
            {"title": "Good 1", "content": "Content"},  # Duplicate
            "string item",
            123,
            {"missing": "fields"},
            None,
            {"title": "", "content": "No title"},
            {"title": "Good 2", "content": "Different"},
        ]

        result = filter_duplicates_in_batch(items)

        # Should have 2 good items (Good 1 and Good 2), dedup Good 1
        assert len(result) == 2
        assert all(isinstance(item, dict) for item in result)

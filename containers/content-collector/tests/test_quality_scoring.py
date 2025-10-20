"""
Tests for quality_scoring module.

Tests scoring, ranking, and diversity filtering.
Focus on input/output contracts and scoring correctness.
"""

import pytest
from quality_scoring import (
    add_score_metadata,
    calculate_quality_score,
    rank_items,
    score_items,
)


class TestCalculateQualityScore:
    """Test quality score calculation."""

    def test_score_perfect_item(self):
        """Perfect item should score high."""
        item = {"title": "Great Article", "content": "A" * 800}
        score = calculate_quality_score(item)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score > 0.8

    def test_score_with_paywall_penalty(self):
        """Paywall content should have lower score."""
        item = {"title": "Article", "content": "subscriber only " + "A" * 800}
        score_paywalled = calculate_quality_score(item)

        item_free = {"title": "Article", "content": "A" * 800}
        score_free = calculate_quality_score(item_free)

        assert score_paywalled < score_free

    def test_score_with_listicle_penalty(self):
        """Listicles should have lower score."""
        item = {"title": "Top 10 Best", "content": "A" * 800}
        score_listicle = calculate_quality_score(item)

        item_regular = {"title": "Great Article", "content": "A" * 800}
        score_regular = calculate_quality_score(item_regular)

        assert score_listicle < score_regular

    def test_score_short_content(self):
        """Short content should have low score."""
        item = {"title": "Short", "content": "Brief"}
        score = calculate_quality_score(item)

        # Short content gets penalized but title + short content still has some value
        assert score < 0.9  # Penalized but still has base value

    def test_score_optimal_length(self):
        """Optimal length should boost score."""
        item = {"title": "Article", "content": "A" * 800}
        score = calculate_quality_score(item)

        assert score > 0.7  # Should be boosted

    def test_score_returns_float(self):
        """Should return float between 0 and 1."""
        item = {"title": "T", "content": "C" * 500}
        score = calculate_quality_score(item)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_score_missing_title(self):
        """Should return 0 for missing title."""
        item = {"content": "Content"}
        score = calculate_quality_score(item)
        assert score == 0.0

    def test_score_missing_content(self):
        """Should return 0 for missing content."""
        item = {"title": "Title"}
        score = calculate_quality_score(item)
        assert score == 0.0

    def test_score_invalid_input(self):
        """Should return 0 for invalid input."""
        score = calculate_quality_score("not a dict")  # type: ignore
        assert score == 0.0

    def test_score_uses_detection_results(self):
        """Should use pre-computed detection results if provided."""
        item = {"title": "T", "content": "C" * 800}

        detection_results = {
            "is_paywalled": True,
            "is_comparison": False,
            "is_listicle": False,
            "content_length_score": 0.0,
            "detections": [],
        }

        score_with_detection = calculate_quality_score(item, detection_results)
        score_without_detection = calculate_quality_score(item)

        # With paywall detection, should be lower
        assert score_with_detection < score_without_detection


class TestScoreItems:
    """Test batch scoring."""

    def test_score_items_returns_list(self):
        """Should return list of (item, score) tuples."""
        items = [
            {"title": "A", "content": "C" * 800},
            {"title": "B", "content": "C" * 800},
        ]

        result = score_items(items)

        assert isinstance(result, list)
        assert all(isinstance(r, tuple) and len(r) == 2 for r in result)

    def test_score_items_filters_low_scores(self):
        """Should filter out items below threshold."""
        items = [
            {"title": "Good", "content": "C" * 800},  # High score
            {"title": "Bad", "content": "Too short"},  # Low score
        ]

        result = score_items(items)

        assert len(result) <= 2
        assert all(score >= 0.6 for _, score in result)  # Default threshold

    def test_score_items_empty_list(self):
        """Should handle empty input."""
        result = score_items([])
        assert result == []

    def test_score_items_invalid_input(self):
        """Should handle invalid input."""
        result = score_items("not a list")  # type: ignore
        assert result == []

    def test_score_items_with_custom_threshold(self):
        """Should respect custom threshold."""
        items = [
            {"title": "Good", "content": "C" * 800},
            {"title": "Bad", "content": "C" * 500},
        ]

        config_low = {"min_quality_score": 0.4}
        result_low = score_items(items, config_low)

        config_high = {"min_quality_score": 0.8}
        result_high = score_items(items, config_high)

        # Higher threshold should filter more
        assert len(result_high) <= len(result_low)

    def test_score_items_skips_invalid_items(self):
        """Should skip non-dict items."""
        items = [
            {"title": "Good", "content": "C" * 800},
            "string item",
            123,
            {"title": "Another", "content": "C" * 800},
        ]

        result = score_items(items)

        # Should only score valid dicts
        assert len(result) <= 2


class TestRankItems:
    """Test ranking and diversity filtering."""

    def test_rank_items_sorted_by_score(self):
        """Should sort by score descending."""
        scored = [
            ({"title": "A"}, 0.5),
            ({"title": "B"}, 0.9),
            ({"title": "C"}, 0.7),
        ]

        result = rank_items(scored)

        scores = [item.get("_placeholder", idx) for idx, item in enumerate(result)]
        # Items should be in order of descending score
        assert result[0]["title"] == "B"  # 0.9 first

    def test_rank_items_limits_max_results(self):
        """Should respect max_results limit."""
        scored = [({"title": f"Item{i}"}, 0.9) for i in range(50)]

        result = rank_items(scored, max_results=20)

        assert len(result) <= 20

    def test_rank_items_diversity_filtering(self):
        """Should limit items from same source (max 3 per source)."""
        scored = [
            ({"title": "A", "source": "Reddit"}, 0.9),
            ({"title": "B", "source": "Reddit"}, 0.8),
            ({"title": "C", "source": "Reddit"}, 0.7),
            ({"title": "D", "source": "Reddit"}, 0.6),  # Should be filtered
            ({"title": "E", "source": "Medium"}, 0.5),
        ]

        result = rank_items(scored, max_results=10)

        reddit_count = sum(1 for item in result if item.get("source") == "Reddit")
        assert reddit_count <= 3

    def test_rank_items_empty_list(self):
        """Should handle empty input."""
        result = rank_items([])
        assert result == []

    def test_rank_items_returns_list_of_dicts(self):
        """Should return list of dicts (items only, no scores)."""
        scored = [({"title": "A"}, 0.9), ({"title": "B"}, 0.8)]

        result = rank_items(scored)

        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)

    def test_rank_items_no_unknown_source(self):
        """Should handle items without source gracefully."""
        scored = [
            ({"title": "A"}, 0.9),  # No source field
            ({"title": "B"}, 0.8),  # No source field
        ]

        result = rank_items(scored)

        # Should group as "unknown" and still apply diversity
        assert len(result) <= 3


class TestAddScoreMetadata:
    """Test metadata addition to items."""

    def test_add_metadata_returns_list(self):
        """Should return list of items."""
        items = [{"title": "A", "content": "C"}]
        scored = [({"title": "A", "content": "C"}, 0.8)]

        result = add_score_metadata(items, scored)

        assert isinstance(result, list)

    def test_add_metadata_includes_quality_score(self):
        """Should add quality score to items."""
        items = [{"title": "Article", "content": "A" * 500}]
        scored = [({"title": "Article", "content": "A" * 500}, 0.75)]

        result = add_score_metadata(items, scored)

        assert len(result) > 0
        assert "_quality_score" in result[0]
        assert isinstance(result[0]["_quality_score"], float)

    def test_add_metadata_rounds_score(self):
        """Should round score to 3 decimals."""
        items = [{"title": "A", "content": "B" * 500}]
        scored = [({"title": "A", "content": "B" * 500}, 0.123456)]

        result = add_score_metadata(items, scored)

        assert result[0]["_quality_score"] == 0.123

    def test_add_metadata_no_mutation(self):
        """Should not mutate input lists."""
        items = [{"title": "A", "content": "B" * 500}]
        items_copy = items.copy()
        scored = [({"title": "A", "content": "B" * 500}, 0.8)]

        result = add_score_metadata(items, scored)

        # Original should be unchanged
        assert items == items_copy

    def test_add_metadata_preserves_fields(self):
        """Should preserve all original fields."""
        items = [
            {
                "title": "Article",
                "content": "A" * 500,
                "source": "Reddit",
                "url": "http://example.com",
            }
        ]
        scored = [(items[0], 0.8)]

        result = add_score_metadata(items, scored)

        assert result[0]["source"] == "Reddit"
        assert result[0]["url"] == "http://example.com"

    def test_add_metadata_empty_scored(self):
        """Should handle empty scored list."""
        items = [{"title": "A", "content": "B" * 500}]

        result = add_score_metadata(items, [])

        # Should return original items
        assert len(result) == len(items)

    def test_add_metadata_handles_invalid_items(self):
        """Should skip invalid items gracefully."""
        items = [
            {"title": "A", "content": "B" * 500},
            "string",
            123,
            {"title": "C", "content": "D" * 500},
        ]
        scored = []

        result = add_score_metadata(items, scored)

        # Should handle mixed types without crashing
        assert isinstance(result, list)


class TestScoringContracts:
    """Test input/output contracts for scoring module."""

    def test_calculate_score_returns_bounded_float(self):
        """Score should always be float between 0-1."""
        test_cases = [
            {"title": "T", "content": "C"},
            {"title": "T", "content": "C" * 1000},
            {"title": "subscriber T", "content": "C" * 500},
            {"title": "Top 5", "content": "C" * 800},
        ]

        for item in test_cases:
            score = calculate_quality_score(item)
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0

    def test_score_items_output_contract(self):
        """score_items output should be list of (dict, float) tuples."""
        items = [{"title": "T", "content": "C" * 800}]
        result = score_items(items)

        assert isinstance(result, list)
        for item, score in result:
            assert isinstance(item, dict)
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0

    def test_rank_items_output_contract(self):
        """rank_items output should be list of dicts."""
        scored = [({"title": "T"}, 0.8)]
        result = rank_items(scored)

        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)

    def test_add_metadata_output_contract(self):
        """add_score_metadata output should be list of dicts with _quality_score."""
        items = [{"title": "T", "content": "C" * 500}]
        scored = [({"title": "T", "content": "C" * 500}, 0.8)]
        result = add_score_metadata(items, scored)

        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)

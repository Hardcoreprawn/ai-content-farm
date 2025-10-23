"""
Tests for quality_detectors module.

Tests detection functions for unsuitable content:
- Paywall detection
- Comparison detection
- Listicle detection
- Content quality assessment

Focus on input/output contracts and real-world edge cases.
"""

import pytest
from quality.detectors import (
    detect_comparison,
    detect_content_length,
    detect_content_quality,
    detect_listicle,
    detect_paywall,
)


class TestPaywallDetection:
    """Test paywall content detection."""

    def test_paywall_known_domain(self):
        """Should detect known paywall domains."""
        is_paywalled, penalty = detect_paywall(
            "Article", "Content", "https://www.wired.com/story"
        )
        assert is_paywalled is True
        assert penalty > 0.5

    def test_paywall_keyword_detection(self):
        """Should detect paywall keywords in content."""
        is_paywalled, penalty = detect_paywall(
            "Article", "subscriber only content here", "https://example.com"
        )
        assert is_paywalled is True
        assert penalty > 0.5

    def test_paywall_not_detected_free_content(self):
        """Should not flag free content."""
        is_paywalled, penalty = detect_paywall(
            "Free Article", "This is free content", "https://medium.com/story"
        )
        assert is_paywalled is False
        assert penalty == 0.0

    def test_paywall_returns_tuple(self):
        """Should return (bool, float) tuple."""
        result = detect_paywall("Title", "Content", "http://example.com")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], float)

    def test_paywall_penalty_is_numeric(self):
        """Penalty should be numeric between 0 and 1."""
        _, penalty = detect_paywall("Title", "Content", "http://wired.com")
        assert isinstance(penalty, float)
        assert 0.0 <= penalty <= 1.0

    def test_paywall_invalid_inputs(self):
        """Should handle invalid inputs gracefully."""
        result = detect_paywall(123, 456, 789)  # type: ignore
        assert result == (False, 0.0)


class TestComparisonDetection:
    """Test comparison/product review detection."""

    def test_comparison_vs_keyword(self):
        """Should detect 'vs' comparisons."""
        is_comp, penalty = detect_comparison("iPhone vs Android", "Comparison content")
        assert is_comp is True

    def test_comparison_best_products(self):
        """Should detect 'best products' reviews."""
        is_comp, penalty = detect_comparison(
            "Best laptops", "Here are the best products..."
        )
        assert is_comp is True

    def test_comparison_pros_cons(self):
        """Should detect pros and cons sections."""
        is_comp, penalty = detect_comparison(
            "Product Review", "Pros:\n- Great\n\nCons:\n- Expensive"
        )
        assert is_comp is True

    def test_comparison_price_range(self):
        """Should detect price comparisons."""
        is_comp, penalty = detect_comparison("Laptops", "Price: $500 to $2000")
        assert is_comp is True

    def test_comparison_not_detected(self):
        """Should not flag non-comparisons."""
        is_comp, penalty = detect_comparison(
            "Tech News", "Breaking news about technology today"
        )
        assert is_comp is False

    def test_comparison_returns_tuple(self):
        """Should return (bool, float) tuple."""
        result = detect_comparison("Title", "Content")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], float)

    def test_comparison_invalid_inputs(self):
        """Should handle invalid inputs gracefully."""
        result = detect_comparison(123, 456)  # type: ignore
        assert result == (False, 0.0)


class TestListicleDetection:
    """Test listicle detection."""

    def test_listicle_top_n(self):
        """Should detect 'top N' listicles."""
        is_listicle, penalty = detect_listicle("Top 10 Best Tech")
        assert is_listicle is True

    def test_listicle_ways_to(self):
        """Should detect 'N ways to' listicles."""
        is_listicle, penalty = detect_listicle("5 Ways to Improve")
        assert is_listicle is True

    def test_listicle_here_are(self):
        """Should detect 'here are N things' listicles."""
        is_listicle, penalty = detect_listicle("Here are 7 Great Ideas")
        assert is_listicle is True

    def test_listicle_reasons_why(self):
        """Should detect 'N reasons why' listicles."""
        is_listicle, penalty = detect_listicle("3 Reasons Why You Should Read")
        assert is_listicle is True

    def test_listicle_not_detected(self):
        """Should not flag non-listicles."""
        is_listicle, penalty = detect_listicle("Breaking News in Technology")
        assert is_listicle is False

    def test_listicle_case_insensitive(self):
        """Should be case-insensitive."""
        is_listicle1, _ = detect_listicle("TOP 5 BEST")
        is_listicle2, _ = detect_listicle("top 5 best")
        assert is_listicle1 is True
        assert is_listicle2 is True

    def test_listicle_returns_tuple(self):
        """Should return (bool, float) tuple."""
        result = detect_listicle("Title")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], float)

    def test_listicle_invalid_input(self):
        """Should handle invalid input gracefully."""
        result = detect_listicle(123)  # type: ignore
        assert result == (False, 0.0)


class TestContentLengthDetection:
    """Test content length evaluation."""

    def test_content_too_short(self):
        """Should penalize content <300 chars."""
        is_suitable, score = detect_content_length("Short")
        assert is_suitable is False
        assert score < 0  # Penalty

    def test_content_optimal_length(self):
        """Should reward content in optimal range (300-1500 chars)."""
        content = "A" * 800  # Within optimal range
        is_suitable, score = detect_content_length(content)
        assert is_suitable is True
        assert score > 0  # Bonus

    def test_content_too_long(self):
        """Should penalize content >1500 chars."""
        content = "A" * 5000  # Too long
        is_suitable, score = detect_content_length(content)
        assert is_suitable is True  # Still suitable, just penalized
        assert score < 0  # Small penalty

    def test_content_length_returns_tuple(self):
        """Should return (bool, float) tuple."""
        result = detect_content_length("Content")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], float)

    def test_content_length_invalid_input(self):
        """Should handle invalid input gracefully."""
        result = detect_content_length(123)  # type: ignore
        assert result == (False, -0.2)


class TestContentQualityAssessment:
    """Test comprehensive quality detection."""

    def test_quality_assessment_returns_dict(self):
        """Should return dict with required keys."""
        result = detect_content_quality("Title", "Content")

        assert isinstance(result, dict)
        required_keys = [
            "is_paywalled",
            "is_comparison",
            "is_listicle",
            "content_length_score",
            "detections",
            "suitable",
        ]
        for key in required_keys:
            assert key in result

    def test_quality_assessment_valid_content(self):
        """Should pass high-quality content."""
        result = detect_content_quality(
            "Great Article",
            "A" * 800,  # Optimal length
            "https://example.com",
        )

        assert result["suitable"] is True
        assert len(result["detections"]) == 0

    def test_quality_assessment_paywall_content(self):
        """Should detect and flag paywall content."""
        result = detect_content_quality(
            "Article", "subscriber only content", "https://wired.com/story"
        )

        assert result["is_paywalled"] is True
        assert "paywall" in result["detections"]
        assert result["suitable"] is False

    def test_quality_assessment_listicle_content(self):
        """Should detect and flag listicles."""
        result = detect_content_quality(
            "Top 10 Best Things", "A" * 800, "https://example.com"
        )

        assert result["is_listicle"] is True
        assert "listicle" in result["detections"]

    def test_quality_assessment_comparison_content(self):
        """Should detect and flag comparisons."""
        result = detect_content_quality(
            "iPhone vs Android", "Pros and cons of each", "https://example.com"
        )

        assert result["is_comparison"] is True
        assert "comparison" in result["detections"]

    def test_quality_assessment_short_content(self):
        """Should detect and flag short content."""
        result = detect_content_quality("Title", "Too short")

        assert "poor_length" in result["detections"]
        assert result["suitable"] is False

    def test_quality_assessment_multiple_detections(self):
        """Should detect multiple issues."""
        result = detect_content_quality(
            "Top 5 Best vs Products",  # Listicle + comparison
            "A" * 800,
            "https://example.com",
        )

        assert len(result["detections"]) >= 2

    def test_quality_assessment_invalid_input(self):
        """Should handle invalid input gracefully."""
        result = detect_content_quality(123, 456)  # type: ignore

        assert result["suitable"] is False
        assert "invalid_input" in result["detections"]


class TestDetectionOutputContracts:
    """Test input/output contracts for all detection functions."""

    def test_all_detectors_return_correct_types(self):
        """All detectors should return correct types."""
        # Paywall
        result = detect_paywall("T", "C", "U")
        assert isinstance(result, tuple) and len(result) == 2

        # Comparison
        result = detect_comparison("T", "C")
        assert isinstance(result, tuple) and len(result) == 2

        # Listicle
        result = detect_listicle("T")
        assert isinstance(result, tuple) and len(result) == 2

        # Length
        result = detect_content_length("C")
        assert isinstance(result, tuple) and len(result) == 2

        # Quality
        result = detect_content_quality("T", "C")
        assert isinstance(result, dict)

    def test_penalties_are_bounded(self):
        """All penalties should be between 0 and 1."""
        _, paywall_penalty = detect_paywall("T", "C", "U")
        _, comparison_penalty = detect_comparison("T", "C")
        _, listicle_penalty = detect_listicle("T")

        assert 0.0 <= paywall_penalty <= 1.0
        assert 0.0 <= comparison_penalty <= 1.0
        assert 0.0 <= listicle_penalty <= 1.0

    def test_detections_list_only_contains_strings(self):
        """Detections should be list of strings."""
        result = detect_content_quality("Top 5 Articles", "Short")

        assert isinstance(result["detections"], list)
        assert all(isinstance(d, str) for d in result["detections"])

    def test_suitable_flag_is_boolean(self):
        """Suitable flag should always be boolean."""
        result = detect_content_quality("T", "C")
        assert isinstance(result["suitable"], bool)

    def test_length_score_is_numeric(self):
        """Length score should be numeric."""
        result = detect_content_quality("T", "Content")
        assert isinstance(result["content_length_score"], (int, float))

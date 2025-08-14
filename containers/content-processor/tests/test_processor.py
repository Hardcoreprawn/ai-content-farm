#!/usr/bin/env python3
"""
Business Logic Tests for Content Processor

Test the core processing functions in isolation.
Pure functions - no external dependencies, easy to test.
"""

from datetime import datetime, timezone

import pytest

# These imports will fail initially - we'll create processor.py to make them pass
try:
    from processor import (
        calculate_engagement_score,
        clean_title,
        extract_content_type,
        normalize_score,
        transform_reddit_post,
    )
except ImportError:
    # Define placeholder functions for tests to run
    def transform_reddit_post(*args, **kwargs):
        raise NotImplementedError("processor.py not implemented yet")

    def calculate_engagement_score(*args, **kwargs):
        raise NotImplementedError("processor.py not implemented yet")

    def clean_title(*args, **kwargs):
        raise NotImplementedError("processor.py not implemented yet")

    def normalize_score(*args, **kwargs):
        raise NotImplementedError("processor.py not implemented yet")

    def extract_content_type(*args, **kwargs):
        raise NotImplementedError("processor.py not implemented yet")


class TestTransformRedditPost:
    """Test the main transformation function"""

    @pytest.fixture
    def sample_reddit_post(self):
        """Sample Reddit post data"""
        return {
            "title": "  Amazing AI breakthrough in computer vision! 🚀  ",
            "score": 1250,
            "num_comments": 89,
            "created_utc": 1692000000,
            "subreddit": "MachineLearning",
            "url": "https://reddit.com/r/MachineLearning/comments/test123",
            "selftext": "Researchers have developed a new model that outperforms...",
            "id": "test123",
        }

    def test_transform_basic_structure(self, sample_reddit_post):
        """Transformed post must have all required fields"""
        result = transform_reddit_post(sample_reddit_post)

        # Required output fields
        assert "id" in result
        assert "title" in result
        assert "clean_title" in result
        assert "normalized_score" in result
        assert "engagement_score" in result
        assert "source_url" in result
        assert "published_at" in result
        assert "content_type" in result
        assert "source_metadata" in result

    def test_transform_preserves_original_data(self, sample_reddit_post):
        """Original data should be preserved in source_metadata"""
        result = transform_reddit_post(sample_reddit_post)

        metadata = result["source_metadata"]
        assert metadata["original_score"] == 1250
        assert metadata["original_comments"] == 89
        assert metadata["subreddit"] == "MachineLearning"
        assert metadata["reddit_id"] == "test123"


class TestCleanTitle:
    """Test title cleaning and normalization"""

    def test_removes_whitespace(self):
        """Should remove leading/trailing whitespace"""
        result = clean_title("  Amazing breakthrough!  ")
        assert result == "Amazing breakthrough!"

    def test_removes_emojis(self):
        """Should remove emoji characters"""
        result = clean_title("Amazing breakthrough! 🚀🎉")
        assert "🚀" not in result
        assert "🎉" not in result
        assert "Amazing breakthrough!" in result

    def test_normalizes_multiple_spaces(self):
        """Should normalize multiple spaces to single space"""
        result = clean_title("Amazing    breakthrough     here")
        assert "Amazing breakthrough here" == result

    def test_handles_empty_title(self):
        """Should handle empty or whitespace-only titles"""
        result = clean_title("   ")
        assert result == "[No Title]"

        result = clean_title("")
        assert result == "[No Title]"

    def test_handles_special_characters(self):
        """Should handle special characters appropriately"""
        result = clean_title("Amazing [UPDATE] breakthrough (CONFIRMED)")
        # Should preserve meaningful punctuation
        assert "[UPDATE]" in result
        assert "(CONFIRMED)" in result


class TestCalculateEngagementScore:
    """Test engagement score calculation"""

    def test_basic_engagement_calculation(self):
        """Engagement score should be based on score and comments"""
        score = calculate_engagement_score(score=1000, comments=50)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_higher_score_means_higher_engagement(self):
        """Higher Reddit score should result in higher engagement"""
        low_engagement = calculate_engagement_score(score=10, comments=1)
        high_engagement = calculate_engagement_score(score=1000, comments=100)
        assert high_engagement > low_engagement

    def test_comments_factor_into_engagement(self):
        """Comments should factor into engagement calculation"""
        no_comments = calculate_engagement_score(score=100, comments=0)
        many_comments = calculate_engagement_score(score=100, comments=50)
        assert many_comments > no_comments

    def test_handles_zero_values(self):
        """Should handle zero score or comments gracefully"""
        result = calculate_engagement_score(score=0, comments=0)
        assert isinstance(result, float)
        assert result >= 0.0

    def test_handles_negative_scores(self):
        """Should handle negative Reddit scores"""
        result = calculate_engagement_score(score=-10, comments=5)
        assert isinstance(result, float)
        # Negative scores should result in low engagement
        assert result < 0.1


class TestNormalizeScore:
    """Test score normalization"""

    def test_normalizes_to_zero_one_range(self):
        """Normalized score should be between 0 and 1"""
        result = normalize_score(1500)
        assert 0.0 <= result <= 1.0

    def test_higher_scores_normalize_higher(self):
        """Higher original scores should normalize to higher values"""
        low = normalize_score(10)
        high = normalize_score(1000)
        assert high > low

    def test_handles_zero_score(self):
        """Should handle zero score"""
        result = normalize_score(0)
        assert result == 0.0

    def test_handles_negative_scores(self):
        """Should handle negative scores"""
        result = normalize_score(-50)
        assert result == 0.0  # Negative scores should normalize to 0


class TestExtractContentType:
    """Test content type detection"""

    def test_detects_link_posts(self):
        """Should detect link posts (no selftext)"""
        result = extract_content_type(url="https://example.com/article", selftext="")
        assert result == "link"

    def test_detects_text_posts(self):
        """Should detect text posts (has selftext)"""
        result = extract_content_type(
            url="https://reddit.com/r/test/comments/123",
            selftext="This is a text post with content",
        )
        assert result == "text"

    def test_detects_image_posts(self):
        """Should detect image posts from URL"""
        result = extract_content_type(url="https://i.imgur.com/test.jpg", selftext="")
        assert result == "image"

        result = extract_content_type(url="https://example.com/image.png", selftext="")
        assert result == "image"

    def test_detects_video_posts(self):
        """Should detect video posts from URL"""
        result = extract_content_type(
            url="https://youtube.com/watch?v=123", selftext=""
        )
        assert result == "video"

        result = extract_content_type(url="https://v.redd.it/test123", selftext="")
        assert result == "video"

    def test_handles_unknown_content(self):
        """Should have fallback for unknown content types"""
        result = extract_content_type(url="", selftext="")
        assert result == "unknown"


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_handles_missing_fields(self):
        """Should handle Reddit posts with missing fields gracefully"""
        minimal_post = {
            "title": "Test",
            "score": 100
            # Missing other fields
        }
        # Should not raise exception
        result = transform_reddit_post(minimal_post)
        assert "id" in result
        assert "title" in result

    def test_handles_unicode_content(self):
        """Should handle Unicode characters in titles and content"""
        unicode_title = "测试 🌟 Тест العربية"
        result = clean_title(unicode_title)
        # Should not crash and should return string
        assert isinstance(result, str)

"""
Tests for Content Collector core functionality.

Following TDD: Write tests first, then implement the minimal code to pass.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, patch
from datetime import datetime, timezone

# Import the functions we're going to test
from collector import (
    fetch_reddit_posts,
    fetch_from_subreddit,
    normalize_reddit_post,
    collect_content_batch,
    filter_content_by_criteria,
    deduplicate_content,
)


class TestRedditFetching:
    """Test Reddit content fetching functionality."""

    @pytest.mark.unit
    @patch("collector.requests.get")
    def test_fetch_from_subreddit_success(self, mock_get: Mock) -> None:
        """Test successful subreddit fetching."""
        # Mock Reddit API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "Amazing AI breakthrough",
                            "score": 1500,
                            "num_comments": 250,
                            "created_utc": 1692000000,
                            "id": "test123",
                            "permalink": "/r/MachineLearning/comments/test123/",
                            "url": "https://example.com/ai-news",
                            "selftext": "This is the post content...",
                            "author": "researcher123",
                            "subreddit": "MachineLearning",
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        result = fetch_from_subreddit("MachineLearning", limit=10)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == "Amazing AI breakthrough"
        assert result[0]["score"] == 1500
        assert result[0]["subreddit"] == "MachineLearning"

    @pytest.mark.unit
    @patch("collector.requests.get")
    def test_fetch_from_subreddit_empty_response(self, mock_get: Mock) -> None:
        """Test handling of empty subreddit response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"children": []}}
        mock_get.return_value = mock_response

        result = fetch_from_subreddit("EmptySubreddit", limit=10)

        assert result == []

    @pytest.mark.unit
    @patch("collector.requests.get")
    def test_fetch_from_subreddit_api_error(self, mock_get: Mock) -> None:
        """Test handling of Reddit API errors."""
        mock_response = Mock()
        mock_response.status_code = 429  # Rate limited
        mock_response.raise_for_status.side_effect = Exception("Rate limited")
        mock_get.return_value = mock_response

        result = fetch_from_subreddit("MachineLearning", limit=10)

        assert result == []

    @pytest.mark.unit
    def test_fetch_reddit_posts_multiple_subreddits(self) -> None:
        """Test fetching from multiple subreddits."""
        with patch("collector.fetch_from_subreddit") as mock_fetch:
            mock_fetch.side_effect = [
                [{"title": "Tech post", "subreddit": "technology"}],
                [{"title": "Science post", "subreddit": "science"}],
            ]

            result = fetch_reddit_posts(["technology", "science"], limit=5)

            assert len(result) == 2
            assert result[0]["subreddit"] == "technology"
            assert result[1]["subreddit"] == "science"


class TestContentNormalization:
    """Test content normalization functionality."""

    @pytest.mark.unit
    def test_normalize_reddit_post_complete(self) -> None:
        """Test normalization of complete Reddit post."""
        raw_post = {
            "title": "Amazing AI breakthrough! 🚀 [Research]",
            "score": 1500,
            "num_comments": 250,
            "created_utc": 1692000000,
            "id": "test123",
            "permalink": "/r/MachineLearning/comments/test123/",
            "url": "https://example.com/ai-news",
            "selftext": "This is the post content...",
            "author": "researcher123",
            "subreddit": "MachineLearning",
        }

        result = normalize_reddit_post(raw_post)

        assert isinstance(result, dict)
        assert result["id"] == "test123"
        assert result["title"] == "Amazing AI breakthrough! 🚀 [Research]"
        assert result["source"] == "reddit"
        assert result["source_type"] == "subreddit"
        assert result["collected_at"]  # Should have timestamp
        assert result["raw_data"] == raw_post

    @pytest.mark.unit
    def test_normalize_reddit_post_minimal(self) -> None:
        """Test normalization of minimal Reddit post."""
        raw_post = {
            "title": "Simple post",
            "id": "simple123",
            "subreddit": "test",
        }

        result = normalize_reddit_post(raw_post)

        assert result["id"] == "simple123"
        assert result["title"] == "Simple post"
        assert result["score"] == 0  # Default values
        assert result["num_comments"] == 0
        assert result["selftext"] == ""

    @pytest.mark.unit
    def test_normalize_reddit_post_invalid_data(self) -> None:
        """Test handling of invalid post data."""
        with pytest.raises(ValueError, match="Post must have id and title"):
            normalize_reddit_post({"title": "No ID"})

        with pytest.raises(ValueError, match="Post must have id and title"):
            normalize_reddit_post({"id": "no_title"})


class TestContentFiltering:
    """Test content filtering functionality."""

    @pytest.mark.unit
    def test_filter_content_by_criteria_score_threshold(self) -> None:
        """Test filtering by score threshold."""
        posts = [
            {"id": "high1", "score": 1000, "num_comments": 100},
            {"id": "low1", "score": 10, "num_comments": 5},
            {"id": "high2", "score": 500, "num_comments": 50},
        ]

        criteria = {"min_score": 100, "min_comments": 10}
        result = filter_content_by_criteria(posts, criteria)

        assert len(result) == 2
        assert result[0]["id"] == "high1"
        assert result[1]["id"] == "high2"

    @pytest.mark.unit
    def test_filter_content_by_criteria_keywords(self) -> None:
        """Test filtering by keyword inclusion/exclusion."""
        posts = [
            {"id": "ai1", "title": "AI breakthrough in machine learning"},
            {"id": "spam1", "title": "Buy crypto now! Amazing deals!"},
            {"id": "tech1", "title": "New programming framework released"},
        ]

        criteria = {
            "include_keywords": ["AI", "programming", "machine learning"],
            "exclude_keywords": ["buy", "crypto", "deals"],
        }
        result = filter_content_by_criteria(posts, criteria)

        assert len(result) == 2
        assert result[0]["id"] == "ai1"
        assert result[1]["id"] == "tech1"

    @pytest.mark.unit
    def test_filter_content_by_criteria_empty_list(self) -> None:
        """Test filtering empty content list."""
        result = filter_content_by_criteria([], {"min_score": 100})
        assert result == []

    @pytest.mark.unit
    def test_filter_content_by_criteria_no_criteria(self) -> None:
        """Test filtering with no criteria (should return all)."""
        posts = [{"id": "test1"}, {"id": "test2"}]
        result = filter_content_by_criteria(posts, {})
        assert len(result) == 2


class TestContentDeduplication:
    """Test content deduplication functionality."""

    @pytest.mark.unit
    def test_deduplicate_content_by_id(self) -> None:
        """Test deduplication by ID."""
        posts = [
            {"id": "unique1", "title": "First post"},
            {"id": "duplicate", "title": "Duplicate post version 1"},
            {"id": "unique2", "title": "Second post"},
            {"id": "duplicate", "title": "Duplicate post version 2"},
        ]

        result = deduplicate_content(posts)

        assert len(result) == 3
        ids = [post["id"] for post in result]
        assert "unique1" in ids
        assert "unique2" in ids
        assert ids.count("duplicate") == 1  # Only one duplicate should remain

    @pytest.mark.unit
    def test_deduplicate_content_by_title_similarity(self) -> None:
        """Test deduplication by title similarity."""
        posts = [
            {"id": "post1", "title": "Amazing AI breakthrough in 2024"},
            {"id": "post2", "title": "New programming language released"},
            {"id": "post3", "title": "Amazing AI breakthrough in 2024!"},  # Similar
        ]

        result = deduplicate_content(posts, similarity_threshold=0.9)

        assert len(result) == 2  # Should remove one similar title

    @pytest.mark.unit
    def test_deduplicate_content_empty_list(self) -> None:
        """Test deduplication of empty list."""
        result = deduplicate_content([])
        assert result == []


class TestContentBatchCollection:
    """Test batch content collection workflow."""

    @pytest.mark.unit
    def test_collect_content_batch_success(self) -> None:
        """Test successful batch content collection."""
        with patch("collector.fetch_reddit_posts") as mock_fetch:
            mock_fetch.return_value = [
                {
                    "id": "post1",
                    "title": "Tech news",
                    "score": 500,
                    "num_comments": 50,
                    "subreddit": "technology",
                }
            ]

            sources = [
                {
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 10,
                    "criteria": {"min_score": 100},
                }
            ]

            result = collect_content_batch(sources)

            assert isinstance(result, dict)
            assert "collected_items" in result
            assert "metadata" in result
            assert len(result["collected_items"]) == 1
            assert result["metadata"]["total_collected"] == 1

    @pytest.mark.unit
    def test_collect_content_batch_multiple_sources(self) -> None:
        """Test batch collection from multiple sources."""
        with patch("collector.fetch_reddit_posts") as mock_fetch:
            mock_fetch.side_effect = [
                [{"id": "tech1", "title": "Tech News", "subreddit": "technology"}],
                [{"id": "sci1", "title": "Science News", "subreddit": "science"}],
            ]

            sources = [
                {
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 5,
                },
                {
                    "type": "reddit",
                    "subreddits": ["science"],
                    "limit": 5,
                },
            ]

            result = collect_content_batch(sources)

            assert len(result["collected_items"]) == 2
            assert result["metadata"]["total_collected"] == 2
            assert result["metadata"]["sources_processed"] == 2

    @pytest.mark.unit
    def test_collect_content_batch_with_filtering(self) -> None:
        """Test batch collection with filtering applied."""
        with patch("collector.fetch_reddit_posts") as mock_fetch:
            mock_fetch.return_value = [
                {"id": "high1", "title": "High Quality Post",
                    "score": 1000, "num_comments": 100},
                {"id": "low1", "title": "Low Quality Post",
                    "score": 10, "num_comments": 1},
            ]

            sources = [
                {
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 10,
                    "criteria": {"min_score": 500, "min_comments": 50},
                }
            ]

            result = collect_content_batch(sources)

            assert len(result["collected_items"]) == 1
            assert result["collected_items"][0]["id"] == "high1"

    @pytest.mark.unit
    def test_collect_content_batch_empty_sources(self) -> None:
        """Test batch collection with empty sources."""
        result = collect_content_batch([])

        assert result["collected_items"] == []
        assert result["metadata"]["total_collected"] == 0
        assert result["metadata"]["sources_processed"] == 0

    @pytest.mark.unit
    def test_collect_content_batch_error_handling(self) -> None:
        """Test batch collection error handling."""
        with patch("collector.fetch_reddit_posts") as mock_fetch:
            mock_fetch.side_effect = Exception("API Error")

            sources = [
                {
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 10,
                }
            ]

            result = collect_content_batch(sources)

            # Should handle error gracefully
            assert result["collected_items"] == []
            assert result["metadata"]["errors"] > 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.unit
    def test_fetch_from_subreddit_invalid_name(self) -> None:
        """Test handling of invalid subreddit names."""
        result = fetch_from_subreddit("", limit=10)
        assert result == []

        result = fetch_from_subreddit(None, limit=10)  # type: ignore
        assert result == []

    @pytest.mark.unit
    def test_normalize_reddit_post_missing_fields(self) -> None:
        """Test normalization with missing optional fields."""
        minimal_post = {
            "id": "minimal123",
            "title": "Minimal post",
            "subreddit": "test",
        }

        result = normalize_reddit_post(minimal_post)

        # Should provide sensible defaults
        assert result["score"] == 0
        assert result["num_comments"] == 0
        assert result["selftext"] == ""
        assert result["author"] == "unknown"

    @pytest.mark.unit
    def test_collect_content_batch_invalid_source_type(self) -> None:
        """Test handling of invalid source types."""
        sources = [
            {
                "type": "invalid_source",
                "config": {"some": "config"},
            }
        ]

        result = collect_content_batch(sources)

        assert result["collected_items"] == []
        assert result["metadata"]["errors"] > 0

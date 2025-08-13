"""
Test Suite for Container Apps SummaryWomble

This test suite validates the pure functions approach and ensures compatibility
with the original SummaryWomble functionality.
"""

from collectors.reddit_collector import RedditCollector, collect_reddit_content
from core.content_model import (
    ContentItem, CollectionRequest, CollectionResult,
    filter_content_items, transform_collection_result
)
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

# Import our pure functions
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(
    __file__), '../containers/content-processor'))


class TestContentModel:
    """Test the pure content model functions"""

    def test_content_item_creation(self):
        """Test ContentItem creation with defaults"""
        item = ContentItem(
            title="Test Title",
            content="Test content",
            url="https://example.com",
            source="test",
            source_id="123"
        )

        assert item.title == "Test Title"
        assert item.source == "test"
        assert item.tags == []
        assert item.metadata == {}
        assert isinstance(item.created_at, datetime)

    def test_filter_content_items_min_score(self):
        """Test filtering by minimum score"""
        items = [
            ContentItem("Title 1", "Content 1", "url1", "test", "1", score=10),
            ContentItem("Title 2", "Content 2", "url2", "test", "2", score=5),
            ContentItem("Title 3", "Content 3", "url3", "test", "3", score=15),
        ]

        filtered = filter_content_items(items, {"min_score": 8})

        assert len(filtered) == 2
        assert filtered[0].score == 10
        assert filtered[1].score == 15

    def test_filter_content_items_keywords(self):
        """Test filtering by title keywords"""
        items = [
            ContentItem("Python programming",
                        "Content 1", "url1", "test", "1"),
            ContentItem("JavaScript tutorial",
                        "Content 2", "url2", "test", "2"),
            ContentItem("Python data science",
                        "Content 3", "url3", "test", "3"),
        ]

        filtered = filter_content_items(items, {"title_keywords": ["python"]})

        assert len(filtered) == 2
        assert "Python" in filtered[0].title
        assert "Python" in filtered[1].title

    def test_transform_collection_result(self):
        """Test collection result transformation"""
        items = [
            ContentItem("Title A", "Content", "url", "test", "1", score=5),
            ContentItem("Title B", "Content", "url", "test", "2", score=10),
            ContentItem("Title C", "Content", "url", "test", "3", score=8),
        ]

        request = CollectionRequest(source="test", targets=["test"])
        result = CollectionResult(request=request, items=items, success=True)

        # Test sorting and limiting
        transformed = transform_collection_result(result, {
            "sort_by": "score",
            "sort_desc": True,
            "limit": 2
        })

        assert len(transformed.items) == 2
        assert transformed.items[0].score == 10
        assert transformed.items[1].score == 8


class TestRedditCollector:
    """Test the Reddit collector pure functions"""

    def test_validate_request_valid(self):
        """Test request validation with valid input"""
        collector = RedditCollector("id", "secret", "agent")
        request = CollectionRequest(
            source="reddit",
            targets=["programming", "python"],
            limit=25
        )

        is_valid, error = collector.validate_request(request)

        assert is_valid is True
        assert error is None

    def test_validate_request_invalid_source(self):
        """Test request validation with invalid source"""
        collector = RedditCollector("id", "secret", "agent")
        request = CollectionRequest(
            source="twitter",
            targets=["programming"],
            limit=25
        )

        is_valid, error = collector.validate_request(request)

        assert is_valid is False
        assert "not supported" in error

    def test_validate_request_invalid_limit(self):
        """Test request validation with invalid limit"""
        collector = RedditCollector("id", "secret", "agent")
        request = CollectionRequest(
            source="reddit",
            targets=["programming"],
            limit=200  # Too high
        )

        is_valid, error = collector.validate_request(request)

        assert is_valid is False
        assert "between 1 and 100" in error

    @patch('collectors.reddit_collector.praw.Reddit')
    def test_collect_success(self, mock_reddit_class):
        """Test successful Reddit content collection"""
        # Mock Reddit API response
        mock_reddit = Mock()
        mock_reddit_class.return_value = mock_reddit

        mock_subreddit = Mock()
        mock_reddit.subreddit.return_value = mock_subreddit

        # Mock post
        mock_post = Mock()
        mock_post.title = "Test Post"
        mock_post.selftext = "Test content"
        mock_post.permalink = "/r/test/comments/123/test"
        mock_post.id = "123"
        mock_post.author = "test_author"
        mock_post.created_utc = 1600000000
        mock_post.score = 100
        mock_post.num_comments = 50
        mock_post.post_hint = None
        mock_post.domain = "reddit.com"
        mock_post.is_self = True
        mock_post.over_18 = False
        mock_post.spoiler = False
        mock_post.stickied = False

        mock_subreddit.hot.return_value = [mock_post]

        # Test collection
        collector = RedditCollector("id", "secret", "agent")
        request = CollectionRequest(
            source="reddit",
            targets=["test"],
            limit=25
        )

        result = collector.collect(request)

        assert result.success is True
        assert len(result.items) == 1
        assert result.items[0].title == "Test Post"
        assert result.items[0].source == "reddit"
        assert result.items[0].score == 100

    def test_collect_reddit_content_function(self):
        """Test the pure function interface"""
        request = CollectionRequest(
            source="reddit",
            targets=["test"],
            limit=25
        )
        credentials = {
            "client_id": "test_id",
            "client_secret": "test_secret",
            "user_agent": "test_agent"
        }

        # This will fail due to invalid credentials, but should return a proper error
        result = collect_reddit_content(request, credentials)

        assert isinstance(result, CollectionResult)
        assert result.request == request
        # Should fail with authentication error
        assert result.success is False


@pytest.mark.asyncio
class TestSummaryWombleAPI:
    """Test the FastAPI router (when we can import it)"""

    def test_placeholder(self):
        """Placeholder test - will add actual API tests once dependencies are available"""
        # TODO: Add tests for FastAPI endpoints once we can import them
        # This would test the router functions, job processing, etc.
        pass


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])

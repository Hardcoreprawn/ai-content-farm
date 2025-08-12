"""
Shared fixtures for GetHotTopics tests.
Provides test data and utilities specific to the GetHotTopics function.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List


@pytest.fixture
def sample_reddit_topic() -> Dict[str, Any]:
    """Sample Reddit topic data for testing."""
    return {
        "reddit_id": "test_topic_001",
        "title": "Latest developments in machine learning frameworks",
        "subreddit": "MachineLearning",
        "score": 350,
        "num_comments": 85,
        "created_utc": 1705312800.0,  # 2024-01-15T10:00:00Z as Unix timestamp
        "selftext": "Discussion about recent updates to popular ML frameworks like TensorFlow and PyTorch.",
        "url": "https://reddit.com/r/MachineLearning/test_topic_001",
        "author": "ml_researcher",
        "upvote_ratio": 0.87,
        "domain": "self.MachineLearning",
        "is_self": True,
        "stickied": False,
        "over_18": False,
        "spoiler": False,
        "locked": False,
        "archived": False,
        "removed_by_category": None,
        "distinguished": None,
        "edited": False,
        "gilded": 2,
        "permalink": "/r/MachineLearning/comments/test_topic_001/"
    }


@pytest.fixture
def sample_reddit_topics() -> List[Dict[str, Any]]:
    """List of sample Reddit topics for testing."""
    return [
        {
            "reddit_id": "test_topic_001",
            "title": "Latest developments in machine learning frameworks",
            "subreddit": "MachineLearning",
            "score": 350,
            "num_comments": 85,
            "created_utc": 1705312800.0,  # 2024-01-15T10:00:00Z as Unix timestamp
            "url": "https://reddit.com/r/MachineLearning/test_topic_001"
        },
        {
            "reddit_id": "test_topic_002",
            "title": "New AI breakthrough in natural language processing",
            "subreddit": "artificial",
            "score": 245,
            "num_comments": 62,
            "created_utc": 1705311000.0,  # 2024-01-15T09:30:00Z as Unix timestamp
            "url": "https://reddit.com/r/artificial/test_topic_002"
        },
        {
            "reddit_id": "test_topic_003",
            "title": "Python 3.12 performance improvements",
            "subreddit": "Python",
            "score": 180,
            "num_comments": 45,
            "created_utc": 1705309200.0,  # 2024-01-15T09:00:00Z as Unix timestamp
            "url": "https://reddit.com/r/Python/test_topic_003"
        }
    ]


@pytest.fixture
def subreddit_config() -> Dict[str, Any]:
    """Configuration for subreddit data collection testing."""
    return {
        "subreddits": ["MachineLearning", "artificial", "Python", "programming", "technology"],
        "limit": 25,
        "time_filter": "day",
        "sort": "hot",
        "min_score": 10,
        "min_comments": 5
    }


@pytest.fixture
def reddit_client_config() -> Dict[str, Any]:
    """Configuration for Reddit API client testing."""
    return {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "user_agent": "AI Content Farm Bot v1.0 (by /u/test_user)",
        "timeout": 30,
        "check_for_async": False
    }


@pytest.fixture
def mock_reddit_response() -> Dict[str, Any]:
    """Mock response from Reddit API for testing."""
    return {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "test_topic_001",
                        "title": "Latest developments in machine learning frameworks",
                        "subreddit": "MachineLearning",
                        "score": 350,
                        "num_comments": 85,
                        "created_utc": 1705312800,  # 2024-01-15T10:00:00Z
                        "selftext": "Discussion about recent updates to popular ML frameworks.",
                        "url": "https://reddit.com/r/MachineLearning/test_topic_001",
                        "author": "ml_researcher",
                        "upvote_ratio": 0.87,
                        "domain": "self.MachineLearning",
                        "is_self": True
                    }
                },
                {
                    "data": {
                        "id": "test_topic_002",
                        "title": "New AI breakthrough in natural language processing",
                        "subreddit": "artificial",
                        "score": 245,
                        "num_comments": 62,
                        "created_utc": 1705311000,  # 2024-01-15T09:30:00Z
                        "selftext": "",
                        "url": "https://example.com/ai-breakthrough",
                        "author": "ai_enthusiast",
                        "upvote_ratio": 0.92,
                        "domain": "example.com",
                        "is_self": False
                    }
                }
            ]
        }
    }

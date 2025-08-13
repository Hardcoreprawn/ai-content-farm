"""
Shared fixtures for SummaryWomble tests.
Provides test data and utilities specific to the SummaryWomble function.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List


@pytest.fixture
def sample_reddit_topic() -> Dict[str, Any]:
    """Sample Reddit topic data for testing."""
    return {
        "id": "test_topic_001",
        "title": "Latest developments in machine learning frameworks",
        "subreddit": "MachineLearning",
        "score": 350,
        "num_comments": 85,
        "created_utc": "2024-01-15T10:00:00Z",
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
            "id": "test_topic_001",
            "title": "Latest developments in machine learning frameworks",
            "subreddit": "MachineLearning",
            "score": 350,
            "num_comments": 85,
            "created_utc": "2024-01-15T10:00:00Z",
            "url": "https://reddit.com/r/MachineLearning/test_topic_001"
        },
        {
            "id": "test_topic_002",
            "title": "New AI breakthrough in natural language processing",
            "subreddit": "artificial",
            "score": 245,
            "num_comments": 62,
            "created_utc": "2024-01-15T09:30:00Z",
            "url": "https://reddit.com/r/artificial/test_topic_002"
        },
        {
            "id": "test_topic_003",
            "title": "Python 3.12 performance improvements",
            "subreddit": "Python",
            "score": 180,
            "num_comments": 45,
            "created_utc": "2024-01-15T09:00:00Z",
            "url": "https://reddit.com/r/Python/test_topic_003"
        }
    ]


@pytest.fixture
def summary_config() -> Dict[str, Any]:
    """Configuration for summary generation testing."""
    return {
        "max_summary_length": 200,
        "min_summary_length": 50,
        "summary_style": "concise",
        "include_metadata": True,
        "source_attribution": True
    }


@pytest.fixture
def sample_content() -> str:
    """Sample content for summarization testing."""
    return """
    Machine learning has evolved significantly over the past decade, with frameworks like TensorFlow and PyTorch 
    leading the way in democratizing AI development. Recent updates to these frameworks have focused on improving 
    performance, reducing memory usage, and making distributed training more accessible to developers.
    
    TensorFlow 2.x introduced eager execution by default, making it more intuitive for Python developers who are 
    familiar with imperative programming. PyTorch, on the other hand, has always been eager by default and has 
    focused on improving its production deployment capabilities with TorchScript and TorchServe.
    
    The competition between these frameworks has driven innovation across the entire ecosystem, benefiting 
    researchers and practitioners alike. Both frameworks now offer comprehensive solutions for model development, 
    training, and deployment at scale.
    """


@pytest.fixture
def expected_summary() -> str:
    """Expected summary output for testing."""
    return "Machine learning frameworks like TensorFlow and PyTorch have evolved significantly, focusing on performance improvements and accessibility. TensorFlow 2.x introduced eager execution while PyTorch enhanced production deployment capabilities, driving innovation across the AI ecosystem."

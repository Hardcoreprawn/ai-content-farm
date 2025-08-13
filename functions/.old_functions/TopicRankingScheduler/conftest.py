"""
Shared fixtures for TopicRankingScheduler tests.
Provides test data and utilities specific to the TopicRankingScheduler function.
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
def scheduler_config() -> Dict[str, Any]:
    """Configuration for scheduler testing."""
    return {
        "schedule": "0 */6 * * *",  # Every 6 hours
        "timezone": "UTC",
        "max_concurrent_jobs": 3,
        "retry_attempts": 3,
        "retry_delay": 300,  # 5 minutes
        "job_timeout": 1800,  # 30 minutes
        "enable_logging": True,
        "log_level": "INFO"
    }


@pytest.fixture
def timer_trigger_data() -> Dict[str, Any]:
    """Mock Azure Timer trigger data for testing."""
    return {
        "schedule_status": {
            "last": "2024-01-15T10:00:00.000Z",
            "next": "2024-01-15T16:00:00.000Z",
            "last_updated": "2024-01-15T10:00:00.000Z"
        },
        "is_past_due": False,
        "function_metadata": {
            "name": "TopicRankingScheduler",
            "directory": "functions/TopicRankingScheduler",
            "script_file": "__init__.py",
            "entry_point": "main"
        }
    }


@pytest.fixture
def job_queue_config() -> Dict[str, Any]:
    """Configuration for job queue testing."""
    return {
        "queue_name": "topic-ranking-jobs",
        "connection_string": "DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey=testkey;EndpointSuffix=core.windows.net",
        "message_ttl": 3600,  # 1 hour
        "visibility_timeout": 1800,  # 30 minutes
        "max_dequeue_count": 5,
        "enable_dead_letter": True
    }


@pytest.fixture
def sample_job_message() -> Dict[str, Any]:
    """Sample job message for testing."""
    return {
        "job_id": "ranking_job_001",
        "job_type": "topic_ranking",
        "created_at": "2024-01-15T10:00:00Z",
        "priority": "normal",
        "parameters": {
            "subreddits": ["MachineLearning", "artificial", "Python"],
            "time_range": "24h",
            "min_score": 10,
            "max_topics": 100
        },
        "retry_count": 0,
        "timeout": 1800
    }

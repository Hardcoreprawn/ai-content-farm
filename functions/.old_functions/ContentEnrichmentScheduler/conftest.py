"""
Shared fixtures for ContentEnrichmentScheduler tests.
Provides test data and utilities specific to the ContentEnrichmentScheduler function.
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
        "schedule": "0 */4 * * *",  # Every 4 hours
        "timezone": "UTC",
        "max_concurrent_jobs": 5,
        "retry_attempts": 3,
        "retry_delay": 600,  # 10 minutes
        "job_timeout": 3600,  # 1 hour
        "enable_logging": True,
        "log_level": "INFO"
    }


@pytest.fixture
def timer_trigger_data() -> Dict[str, Any]:
    """Mock Azure Timer trigger data for testing."""
    return {
        "schedule_status": {
            "last": "2024-01-15T08:00:00.000Z",
            "next": "2024-01-15T12:00:00.000Z",
            "last_updated": "2024-01-15T08:00:00.000Z"
        },
        "is_past_due": False,
        "function_metadata": {
            "name": "ContentEnrichmentScheduler",
            "directory": "functions/ContentEnrichmentScheduler",
            "script_file": "__init__.py",
            "entry_point": "main"
        }
    }


@pytest.fixture
def enrichment_queue_config() -> Dict[str, Any]:
    """Configuration for enrichment job queue testing."""
    return {
        "queue_name": "content-enrichment-jobs",
        "connection_string": "DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey=testkey;EndpointSuffix=core.windows.net",
        "message_ttl": 7200,  # 2 hours
        "visibility_timeout": 3600,  # 1 hour
        "max_dequeue_count": 3,
        "enable_dead_letter": True,
        "batch_size": 10
    }


@pytest.fixture
def sample_enrichment_job() -> Dict[str, Any]:
    """Sample enrichment job message for testing."""
    return {
        "job_id": "enrichment_job_001",
        "job_type": "content_enrichment",
        "created_at": "2024-01-15T08:00:00Z",
        "priority": "high",
        "parameters": {
            "topic_ids": ["test_topic_001", "test_topic_002", "test_topic_003"],
            "enrichment_types": ["summary", "keywords", "sentiment", "category"],
            "target_length": 200,
            "include_metadata": True
        },
        "retry_count": 0,
        "timeout": 3600,
        "dependencies": ["ranking_job_001"]
    }


@pytest.fixture
def batch_job_config() -> Dict[str, Any]:
    """Configuration for batch processing testing."""
    return {
        "batch_size": 10,
        "max_batch_wait_time": 300,  # 5 minutes
        "parallel_processing": True,
        "max_workers": 4,
        "failure_threshold": 0.2,  # 20% failure rate
        "retry_failed_items": True
    }

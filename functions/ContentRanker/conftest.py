# ContentRanker Test Configuration
# This file enables the co-located test to access shared fixtures

import pytest
import sys
import os
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

# Add project root to path for imports
project_root = os.path.join(os.path.dirname(__file__), '../..')
sys.path.insert(0, project_root)

# Duplicate key fixtures locally for co-located tests


@pytest.fixture
def sample_reddit_topic():
    """Sample Reddit topic data for testing"""
    return {
        "title": "AI Content Generation Best Practices",
        "external_url": "https://example.com/ai-content",
        "reddit_url": "https://reddit.com/r/technology/comments/example",
        "reddit_id": "example123",
        "score": 1500,
        "created_utc": 1692000000.0,
        "num_comments": 125,
        "author": "test_user",
        "subreddit": "technology",
        "fetched_at": "20250812_120000",
        "selftext": "Sample content about AI best practices..."
    }


@pytest.fixture
def sample_reddit_topics(sample_reddit_topic):
    """Multiple Reddit topics for batch testing"""
    topics = []
    for i in range(3):
        topic = sample_reddit_topic.copy()
        topic["reddit_id"] = f"example{i}"
        topic["title"] = f"AI Content Generation Best Practices {i}"  # Make titles unique
        topic["external_url"] = f"https://example.com/ai-content-{i}"  # Make URLs unique
        topic["score"] = 1000 + (i * 200)
        topic["num_comments"] = 50 + (i * 25)
        topics.append(topic)
    return topics


@pytest.fixture
def ranking_config():
    """Standard ranking configuration for testing"""
    return {
        "min_score_threshold": 100,
        "min_comments_threshold": 10,
        "weights": {
            "engagement": 0.3,
            "freshness": 0.2,
            "monetization": 0.3,
            "seo_potential": 0.2
        },
        "engagement_thresholds": {
            "high_score": 1000,
            "high_comments": 100
        },
        "freshness_hours": {
            "very_fresh": 6,
            "fresh": 24,
            "recent": 72
        }
    }

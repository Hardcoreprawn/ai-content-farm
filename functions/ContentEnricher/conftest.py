# ContentEnricher Test Configuration
# This file enables the co-located test to access shared fixtures

import pytest
import sys
import os
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock

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
def enrichment_config():
    """Standard enrichment configuration for testing"""
    return {
        "max_external_sources": 3,
        "content_quality_threshold": 0.7,
        "domain_credibility_threshold": 0.6,
        "research_depth": "standard",
        "citation_format": "apa"
    }

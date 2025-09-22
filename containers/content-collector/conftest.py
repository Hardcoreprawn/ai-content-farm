"""
Clean, Simple Test Configuration for Content-Collector - ACTIVE

CURRENT ARCHITECTURE: Minimal test fixtures for simplified collectors
Status: ACTIVE - Supports the new simplified test architecture

Follows monorepo patterns and provides minimal fixtures.
Replaces complex test fixtures with simple, focused test data.

Features:
- Sample Reddit API response data
- Sample Mastodon API response data
- Mock HTTP response helpers
- Monorepo path setup
- Clean, minimal fixture patterns

Clean, simple conftest for content-collector tests.

Follows monorepo patterns and provides minimal fixtures.
"""

import sys
from pathlib import Path

import pytest

# Ensure shared libs are available
libs_path = Path(__file__).parent.parent.parent.parent / "libs"
if str(libs_path) not in sys.path:
    sys.path.insert(0, str(libs_path))


@pytest.fixture
def sample_reddit_data():
    """Sample Reddit API response for testing."""
    return {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "test123",
                        "title": "Test Post",
                        "selftext": "This is a test post content",
                        "author": "testuser",
                        "created_utc": 1640995200,  # 2022-01-01
                        "permalink": "/r/programming/comments/test123/test_post/",
                        "url": "https://www.reddit.com/r/programming/comments/test123/test_post/",
                        "score": 100,
                        "num_comments": 10,
                        "upvote_ratio": 0.95,
                        "over_18": False,
                        "spoiler": False,
                        "stickied": False,
                        "removed_by_category": None,
                        "link_flair_text": "Discussion",
                    }
                },
                {
                    "data": {
                        "id": "test456",
                        "title": "Another Post",
                        "selftext": "",
                        "author": "anotheruser",
                        "created_utc": 1640995260,
                        "permalink": "/r/technology/comments/test456/another_post/",
                        "url": "https://example.com/external-link",
                        "score": 50,
                        "num_comments": 5,
                        "upvote_ratio": 0.85,
                        "over_18": False,
                        "spoiler": False,
                        "stickied": False,
                        "removed_by_category": None,
                        "link_flair_text": None,
                    }
                },
            ]
        }
    }


@pytest.fixture
def sample_mastodon_data():
    """Sample Mastodon API response for testing."""
    return [
        {
            "id": "post123",
            "content": '<p>This is a test post about <a href="https://example.com">#technology</a></p>',
            "created_at": "2022-01-01T12:00:00Z",
            "url": "https://mastodon.social/@user/post123",
            "account": {
                "username": "testuser",
                "display_name": "Test User",
                "url": "https://mastodon.social/@testuser",
            },
            "favourites_count": 5,
            "reblogs_count": 2,
            "replies_count": 1,
            "language": "en",
            "sensitive": False,
            "tags": [{"name": "technology"}],
            "media_attachments": [],
            "visibility": "public",
        }
    ]


@pytest.fixture
def mock_http_response():
    """Mock HTTP response for testing."""
    from unittest.mock import Mock

    response = Mock()
    response.status_code = 200
    response.headers = {}
    response.json.return_value = {}
    return response

"""
Reddit API Contract - Defines the expected structure of Reddit API responses.

This serves as both documentation and a testing contract to ensure our mocks
match the real Reddit API responses.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RedditPostContract:
    """Contract for a Reddit post response."""

    # Required fields from Reddit API
    id: str
    title: str
    selftext: str  # Post content
    url: str
    score: int
    num_comments: int
    created_utc: float
    subreddit: str
    author: str
    permalink: str

    # Optional fields that may be present
    thumbnail: Optional[str] = None
    preview: Optional[Dict[str, Any]] = None
    is_self: bool = True
    stickied: bool = False

    @classmethod
    def create_mock(cls, **overrides) -> "RedditPostContract":
        """Create a mock Reddit post with realistic data."""
        defaults = {
            "id": "mock_post_123",
            "title": "Mock Reddit Post Title",
            "selftext": "This is mock post content from Reddit API",
            "url": "https://www.reddit.com/r/test/comments/mock_post_123/",
            "score": 42,
            "num_comments": 15,
            "created_utc": datetime.now().timestamp(),
            "subreddit": "technology",
            "author": "mock_user",
            "permalink": "/r/technology/comments/mock_post_123/mock_reddit_post_title/",
            "thumbnail": "self",
            "is_self": True,
            "stickied": False
        }
        defaults.update(overrides)
        return cls(**defaults)


@dataclass
class RedditListingContract:
    """Contract for Reddit listing response (what we get from /r/subreddit.json)."""

    kind: str = "Listing"  # Always "Listing" for Reddit listings
    data: Optional[Dict[str, Any]] = None

    @classmethod
    def create_mock(cls, posts: List[RedditPostContract], after: Optional[str] = None) -> "RedditListingContract":
        """Create a mock Reddit listing response."""
        children = [
            {"kind": "t3", "data": post.__dict__} for post in posts
        ]

        data = {
            "after": after,
            "before": None,
            "children": children,
            "dist": len(posts),
            "modhash": "",
        }

        return cls(kind="Listing", data=data)


def create_realistic_reddit_posts(count: int = 3, subreddit: str = "technology") -> List[RedditPostContract]:
    """Create realistic Reddit posts for testing."""
    posts = []

    # Sample realistic titles and content based on actual Reddit patterns
    sample_data = [
        {
            "title": "New breakthrough in AI language models shows 40% improvement",
            "selftext": "Researchers at MIT have developed a new architecture that significantly improves language understanding...",
            "score": 1247,
            "num_comments": 156,
        },
        {
            "title": "GitHub Copilot usage statistics reveal interesting developer patterns",
            "selftext": "According to the latest GitHub report, developers using Copilot show...",
            "score": 892,
            "num_comments": 203,
        },
        {
            "title": "Apple announces new M4 chip with dedicated AI processing unit",
            "selftext": "Apple's latest silicon includes specialized neural processing units...",
            "score": 2156,
            "num_comments": 421,
        }
    ]

    for i in range(min(count, len(sample_data))):
        data = sample_data[i].copy()
        data.update({
            "id": f"mock_{subreddit}_{i+1}",
            "subreddit": subreddit,
            "url": f"https://www.reddit.com/r/{subreddit}/comments/mock_{i+1}/",
            "permalink": f"/r/{subreddit}/comments/mock_{i+1}/",
        })
        posts.append(RedditPostContract.create_mock(**data))

    # If we need more posts than sample data, create generic ones
    for i in range(len(sample_data), count):
        posts.append(RedditPostContract.create_mock(
            id=f"mock_{subreddit}_{i+1}",
            title=f"Mock Post {i+1} from r/{subreddit}",
            subreddit=subreddit,
            score=100 + i * 50,
            num_comments=10 + i * 5,
        ))

    return posts

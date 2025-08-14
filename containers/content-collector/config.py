"""
Content Collector Configuration

Environment-based configuration for the content collector.
"""

import os
from typing import List, Dict, Any, Optional


class Config:
    """Configuration settings for the content collector."""

    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8004"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Reddit API settings
    REDDIT_CLIENT_ID: Optional[str] = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: Optional[str] = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT: str = os.getenv(
        "REDDIT_USER_AGENT", "ai-content-farm-collector/1.0")

    # Rate limiting
    MAX_REQUESTS_PER_MINUTE: int = int(
        os.getenv("MAX_REQUESTS_PER_MINUTE", "60"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "10"))

    # Content collection settings
    DEFAULT_SUBREDDITS: List[str] = [
        "technology",
        "programming",
        "MachineLearning",
        "datascience",
        "artificial",
        "Futurology"
    ]

    DEFAULT_POSTS_PER_SUBREDDIT: int = int(
        os.getenv("DEFAULT_POSTS_PER_SUBREDDIT", "10"))
    MAX_POSTS_PER_REQUEST: int = int(os.getenv("MAX_POSTS_PER_REQUEST", "100"))

    # Quality filters
    MIN_SCORE_THRESHOLD: int = int(os.getenv("MIN_SCORE_THRESHOLD", "5"))
    MIN_COMMENTS_THRESHOLD: int = int(os.getenv("MIN_COMMENTS_THRESHOLD", "2"))

    # Deduplication
    SIMILARITY_THRESHOLD: float = float(
        os.getenv("SIMILARITY_THRESHOLD", "0.8"))

    # Validation settings
    MAX_TITLE_LENGTH: int = int(os.getenv("MAX_TITLE_LENGTH", "300"))
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH", "10000"))

    @classmethod
    def get_reddit_config(cls) -> Dict[str, Any]:
        """Get Reddit API configuration."""
        return {
            "client_id": cls.REDDIT_CLIENT_ID,
            "client_secret": cls.REDDIT_CLIENT_SECRET,
            "user_agent": cls.REDDIT_USER_AGENT,
            "timeout": cls.REQUEST_TIMEOUT,
        }

    @classmethod
    def get_default_criteria(cls) -> Dict[str, Any]:
        """Get default filtering criteria."""
        return {
            "min_score": cls.MIN_SCORE_THRESHOLD,
            "min_comments": cls.MIN_COMMENTS_THRESHOLD,
            "include_keywords": [],
            "exclude_keywords": ["deleted", "[removed]"],
        }

    @classmethod
    def validate_config(cls) -> List[str]:
        """Validate configuration and return any issues."""
        issues = []

        if not cls.REDDIT_CLIENT_ID:
            issues.append("REDDIT_CLIENT_ID not set")

        if not cls.REDDIT_CLIENT_SECRET:
            issues.append("REDDIT_CLIENT_SECRET not set")

        if cls.MAX_REQUESTS_PER_MINUTE <= 0:
            issues.append("MAX_REQUESTS_PER_MINUTE must be positive")

        if cls.REQUEST_TIMEOUT <= 0:
            issues.append("REQUEST_TIMEOUT must be positive")

        if cls.SIMILARITY_THRESHOLD < 0 or cls.SIMILARITY_THRESHOLD > 1:
            issues.append("SIMILARITY_THRESHOLD must be between 0 and 1")

        return issues

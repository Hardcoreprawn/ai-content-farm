"""
Content Collector Configuration

Environment-based configuration for the content collector.
"""

import os
from typing import List, Dict, Any, Optional
from keyvault_client import health_check_keyvault, get_reddit_credentials_with_fallback


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

        # Check Reddit credentials from Key Vault and environment
        try:
            credentials = get_reddit_credentials_with_fallback()

            if not credentials.get("client_id"):
                issues.append(
                    "Reddit client_id not found in Key Vault or environment variables")

            if not credentials.get("client_secret"):
                issues.append(
                    "Reddit client_secret not found in Key Vault or environment variables")

        except Exception as e:
            issues.append(f"Error checking Reddit credentials: {e}")

        if cls.MAX_REQUESTS_PER_MINUTE <= 0:
            issues.append("MAX_REQUESTS_PER_MINUTE must be positive")

        if cls.REQUEST_TIMEOUT <= 0:
            issues.append("REQUEST_TIMEOUT must be positive")

        if cls.SIMILARITY_THRESHOLD < 0 or cls.SIMILARITY_THRESHOLD > 1:
            issues.append("SIMILARITY_THRESHOLD must be between 0 and 1")

        return issues

    @classmethod
    def get_health_status(cls) -> Dict[str, Any]:
        """Get comprehensive health status including Key Vault."""
        health_status = {
            "config_valid": len(cls.validate_config()) == 0,
            "validation_issues": cls.validate_config(),
            "environment": cls.ENVIRONMENT,
            "debug": cls.DEBUG
        }

        # Add Key Vault health check
        try:
            kv_health = health_check_keyvault()
            health_status["key_vault"] = kv_health
        except Exception as e:
            health_status["key_vault"] = {
                "status": "error",
                "message": f"Key Vault health check failed: {e}"
            }

        return health_status

"""
Reddit Client for Content Womble

Handles Reddit API authentication and data retrieval with Azure Key Vault integration.
"""

import logging
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional

import praw
from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient

from config import config

# Add parent directories to path for imports
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))


logger = logging.getLogger(__name__)


class RedditClient:
    """Reddit client with Azure Key Vault integration."""

    def __init__(self):
        self.reddit = None
        self.environment = config.environment
        self._initialize_reddit()

    def _validate_credentials(
        self, client_id: Optional[str], client_secret: Optional[str]
    ) -> bool:
        """
        Validate Reddit API credentials format and content.

        Args:
            client_id: Reddit application client ID
            client_secret: Reddit application client secret

        Returns:
            bool: True if credentials appear valid, False otherwise
        """
        # Handle None values gracefully
        if client_id is None or client_secret is None:
            return False

        if not client_id or not client_secret:
            return False

        # Basic format validation for client_id
        # Reddit client IDs are typically 14-character alphanumeric strings
        if not re.match(r"^[a-zA-Z0-9_-]{10,20}$", client_id):
            logger.warning("Reddit client_id format appears invalid")
            return False

        # Basic format validation for client_secret
        # Reddit client secrets are typically longer alphanumeric strings
        if not re.match(r"^[a-zA-Z0-9_-]{20,50}$", client_secret):
            logger.warning("Reddit client_secret format appears invalid")
            return False

        # Check for placeholder values
        placeholder_patterns = ["placeholder", "example", "test", "demo", "xxx"]
        for pattern in placeholder_patterns:
            if (
                pattern.lower() in client_id.lower()
                or pattern.lower() in client_secret.lower()
            ):
                logger.warning("Reddit credentials contain placeholder values")
                return False

        return True

    def _sanitize_credentials(
        self, client_id: Optional[str], client_secret: Optional[str]
    ) -> tuple[str, str]:
        """
        Sanitize credentials by removing potential malicious content.

        Args:
            client_id: Reddit application client ID
            client_secret: Reddit application client secret

        Returns:
            tuple: (sanitized_client_id, sanitized_client_secret)
        """
        # Remove any whitespace and limit length for security
        sanitized_id = client_id.strip()[:50] if client_id else ""
        sanitized_secret = client_secret.strip()[:100] if client_secret else ""

        # Remove any potentially dangerous characters (keep only alphanumeric, dash, underscore)
        sanitized_id = re.sub(r"[^a-zA-Z0-9_-]", "", sanitized_id)
        sanitized_secret = re.sub(r"[^a-zA-Z0-9_-]", "", sanitized_secret)

        return sanitized_id, sanitized_secret

    def _initialize_reddit(self):
        """Initialize Reddit client based on environment."""
        try:
            # Check for environment variables first (Container Apps secrets)
            client_id = config.reddit_client_id
            client_secret = config.reddit_client_secret
            user_agent = config.reddit_user_agent

            if client_id and client_secret and user_agent:
                # Sanitize and validate credentials
                client_id, client_secret = self._sanitize_credentials(
                    client_id, client_secret
                )

                if self._validate_credentials(client_id, client_secret):
                    try:
                        # Use environment variables (Container Apps secrets)
                        self._init_reddit_with_creds(
                            client_id, client_secret, user_agent
                        )
                        logger.info(
                            "Reddit client initialized with Container Apps secrets"
                        )
                        return
                    except Exception as cred_error:
                        if self.environment == "development":
                            logger.warning(
                                "Reddit credentials failed in development, falling back to local mode"
                            )
                            self._init_local_reddit()
                            return
                        else:
                            # In production, credential failures should be fatal
                            raise cred_error
                else:
                    logger.error(
                        "Reddit client initialization failed due to invalid credentials"
                    )
                    if self.environment == "development":
                        logger.warning(
                            "Invalid credentials in development, falling back to local mode"
                        )
                        self._init_local_reddit()
                        return
                    else:
                        raise ValueError("Invalid Reddit credentials format")
            elif self.environment == "production":
                # Azure environment - use Key Vault directly
                self._init_azure_reddit()
            else:
                # Local development - anonymous access
                self._init_local_reddit()
        except Exception as e:
            if self.environment == "development":
                # In development, fall back to None/mock mode for robustness
                logger.warning(
                    "Reddit initialization failed in development, using mock data"
                )
                self.reddit = None
            else:
                # Log generic error message to prevent credential exposure
                logger.error(
                    "Reddit client initialization failed due to configuration error"
                )
                raise RuntimeError("Failed to initialize Reddit client") from e

    def _init_reddit_with_creds(
        self, client_id: str, client_secret: str, user_agent: str
    ):
        """Initialize Reddit with provided credentials."""
        if not self._validate_credentials(client_id, client_secret):
            raise ValueError("Invalid Reddit credentials provided")

        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            check_for_async=False,
        )

    def _init_azure_reddit(self):
        """Initialize Reddit with Azure Key Vault credentials."""
        try:
            # Get Key Vault URL from config
            vault_url = config.azure_key_vault_url
            if not vault_url:
                raise ValueError("AZURE_KEY_VAULT_URL not set")

            # Create Key Vault client with managed identity
            credential = DefaultAzureCredential()
            kv_client = SecretClient(vault_url=vault_url, credential=credential)

            # Retrieve Reddit credentials
            client_id = kv_client.get_secret("reddit-client-id").value
            client_secret = kv_client.get_secret("reddit-client-secret").value
            user_agent = kv_client.get_secret("reddit-user-agent").value

            # Sanitize and validate credentials
            client_id, client_secret = self._sanitize_credentials(
                client_id, client_secret
            )

            if not self._validate_credentials(client_id, client_secret):
                raise ValueError("Invalid Reddit credentials retrieved from Key Vault")

            # Initialize PRAW
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                check_for_async=False,
            )

            logger.info("Reddit client initialized with Azure Key Vault credentials")

        except Exception as e:
            # Log generic error message to prevent credential exposure
            logger.error(
                "Failed to initialize Reddit client with Key Vault due to configuration error"
            )
            raise RuntimeError("Key Vault Reddit initialization failed") from e

    def _init_local_reddit(self):
        """
        Initialize Reddit for local development.

        This method provides a fallback mechanism for local development:
        1. First attempts to use environment variables if available
        2. Falls back to anonymous (read-only) access if no credentials
        3. Uses mock data if Reddit is completely unavailable

        Anonymous access limitations:
        - Read-only access to public subreddits
        - Higher rate limits than authenticated access
        - Cannot access private/restricted content
        - Should only be used for development/testing
        """
        try:
            # Check for environment variables (fallback for local development)
            client_id = config.reddit_client_id
            client_secret = config.reddit_client_secret
            user_agent = config.reddit_user_agent or "topic-intelligence-local/1.0"

            if client_id and client_secret:
                # Sanitize and validate credentials
                client_id, client_secret = self._sanitize_credentials(
                    client_id, client_secret
                )

                if self._validate_credentials(client_id, client_secret):
                    self.reddit = praw.Reddit(
                        client_id=client_id,
                        client_secret=client_secret,
                        user_agent=user_agent,
                        check_for_async=False,
                    )
                    logger.info("Reddit client initialized with local credentials")
                else:
                    logger.warning(
                        "Local Reddit credentials are invalid, falling back to anonymous access"
                    )
                    self._init_anonymous_reddit(user_agent)
            else:
                # Anonymous access for local testing
                logger.info(
                    "No Reddit credentials found, initializing anonymous access for development"
                )
                self._init_anonymous_reddit(user_agent)

        except Exception as e:
            # Log generic error message to prevent credential exposure
            logger.warning(
                "Reddit initialization failed, using mock data for development"
            )
            self.reddit = None

    def _init_anonymous_reddit(self, user_agent: str):
        """
        Initialize Reddit in anonymous (read-only) mode.

        This provides limited access to public Reddit content without authentication.
        Used for local development and testing when credentials are not available.
        """
        try:
            self.reddit = praw.Reddit(
                client_id=None,
                client_secret=None,
                user_agent=user_agent,
                check_for_async=False,
            )
            logger.info(
                "Reddit client initialized in read-only mode (anonymous access)"
            )
        except Exception as e:
            logger.warning("Anonymous Reddit access failed, will use mock data")
            self.reddit = None

    def is_available(self) -> bool:
        """Check if Reddit client is available."""
        return self.reddit is not None

    def is_anonymous(self) -> bool:
        """
        Check if Reddit client is running in anonymous mode.

        Returns:
            bool: True if running without authentication, False if authenticated
        """
        if not self.is_available() or self.reddit is None:
            return False

        try:
            # Try to access user info - will fail for anonymous clients
            _ = self.reddit.user.me()
            return False  # Authenticated
        except Exception:
            return True  # Anonymous mode

    def get_trending_posts(
        self, subreddit: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get trending posts from a subreddit."""
        if not self.is_available() or self.reddit is None:
            # Return mock data for testing
            return self._get_mock_posts(subreddit, limit)

        try:
            subreddit_obj = self.reddit.subreddit(subreddit)
            posts = []

            for submission in subreddit_obj.hot(limit=limit):
                posts.append(
                    {
                        "title": submission.title,
                        "score": submission.score,
                        "num_comments": submission.num_comments,
                        "created_utc": submission.created_utc,
                        "url": submission.url,
                        "subreddit": subreddit,
                        "selftext": (
                            submission.selftext[:500] if submission.selftext else ""
                        ),
                    }
                )

            logger.debug(f"Retrieved {len(posts)} posts from r/{subreddit}")
            return posts

        except Exception as e:
            logger.error(f"Failed to get posts from r/{subreddit} due to API error")
            return self._get_mock_posts(subreddit, limit)

    def _get_mock_posts(self, subreddit: str, limit: int) -> List[Dict[str, Any]]:
        """Generate mock posts for testing."""
        mock_topics = {
            "technology": [
                "AI breakthrough in quantum computing announced",
                "New programming language gains developer adoption",
                "Cloud computing costs optimization strategies",
                "Cybersecurity threats in remote work environments",
                "Open source software sustainability discussed",
            ],
            "MachineLearning": [
                "Large language model training efficiency improvements",
                "Computer vision applications in healthcare",
                "Machine learning model interpretability research",
                "AI ethics in automated decision making",
                "Neural network architecture innovations",
            ],
            "science": [
                "Climate change mitigation technology developments",
                "Medical research breakthrough in gene therapy",
                "Space exploration mission updates",
                "Renewable energy storage solutions",
                "Quantum physics experimental results",
            ],
        }

        topics = mock_topics.get(
            subreddit,
            ["General topic discussion", "Technology news", "Research updates"],
        )
        posts = []

        for i in range(min(limit, len(topics) * 2)):
            topic = topics[i % len(topics)]
            posts.append(
                {
                    "title": f"{topic} - Discussion Thread",
                    "score": 100 + (i * 10),
                    "num_comments": 20 + i,
                    "created_utc": time.time() - (i * 3600),
                    "url": f"https://reddit.com/r/{subreddit}/posts/{i}",
                    "subreddit": subreddit,
                    "selftext": f"Mock discussion about {topic.lower()}",
                }
            )

        return posts

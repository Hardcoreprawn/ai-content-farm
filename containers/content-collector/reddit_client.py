"""
Reddit Client for Content Womble

Handles Reddit API authentication and data retrieval with Azure Key Vault integration.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

import praw
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

logger = logging.getLogger(__name__)


class RedditClient:
    """Reddit client with Azure Key Vault integration."""

    def __init__(self):
        self.reddit = None
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        self._initialize_reddit()

    def _initialize_reddit(self):
        """Initialize Reddit client based on environment."""
        try:
            # Check for environment variables first (Container Apps secrets)
            client_id = os.getenv("REDDIT_CLIENT_ID")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            user_agent = os.getenv("REDDIT_USER_AGENT")

            if client_id and client_secret and user_agent:
                # Use environment variables (Container Apps secrets)
                self._init_reddit_with_creds(client_id, client_secret, user_agent)
                logger.info("Reddit client initialized with Container Apps secrets")
            elif self.environment == "production":
                # Azure environment - use Key Vault directly
                self._init_azure_reddit()
            else:
                # Local development - anonymous access
                self._init_local_reddit()
        except Exception as e:
            logger.error(f"Failed to initialize Reddit: {e}")
            raise

    def _init_reddit_with_creds(
        self, client_id: str, client_secret: str, user_agent: str
    ):
        """Initialize Reddit with provided credentials."""
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            check_for_async=False,
        )

    def _init_azure_reddit(self):
        """Initialize Reddit with Azure Key Vault credentials."""
        try:
            # Get Key Vault URL from environment
            vault_url = os.getenv("AZURE_KEY_VAULT_URL")
            if not vault_url:
                raise ValueError("AZURE_KEY_VAULT_URL not set")

            # Create Key Vault client with managed identity
            credential = DefaultAzureCredential()
            kv_client = SecretClient(vault_url=vault_url, credential=credential)

            # Retrieve Reddit credentials
            client_id = kv_client.get_secret("reddit-client-id").value
            client_secret = kv_client.get_secret("reddit-client-secret").value
            user_agent = kv_client.get_secret("reddit-user-agent").value

            # Initialize PRAW
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                check_for_async=False,
            )

            logger.info("Reddit client initialized with Azure Key Vault credentials")

        except Exception as e:
            logger.error(f"Failed to initialize Reddit with Key Vault: {e}")
            raise

    def _init_local_reddit(self):
        """Initialize Reddit for local development (anonymous)."""
        try:
            # Use environment variables if available, otherwise anonymous
            client_id = os.getenv("REDDIT_CLIENT_ID")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            user_agent = os.getenv("REDDIT_USER_AGENT", "topic-intelligence-local/1.0")

            if client_id and client_secret:
                self.reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=user_agent,
                    check_for_async=False,
                )
                logger.info("Reddit client initialized with local credentials")
            else:
                # Anonymous access for local testing
                self.reddit = praw.Reddit(
                    client_id=None,
                    client_secret=None,
                    user_agent=user_agent,
                    check_for_async=False,
                )
                logger.info("Reddit client initialized in read-only mode (no API key)")

        except Exception as e:
            logger.warning(f"Reddit initialization failed, using mock data: {e}")
            self.reddit = None

    def is_available(self) -> bool:
        """Check if Reddit client is available."""
        return self.reddit is not None

    def get_trending_posts(
        self, subreddit: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get trending posts from a subreddit."""
        if not self.is_available():
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
            logger.error(f"Failed to get posts from r/{subreddit}: {e}")
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

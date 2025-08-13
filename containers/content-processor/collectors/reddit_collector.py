"""
Reddit Content Collector

Pure function implementation for collecting content from Reddit using PRAW.
This maintains the same functionality as the original SummaryWomble but in a 
pure, testable, and reusable form.
"""

import praw
from typing import Dict, Any, List
from datetime import datetime

from core.content_model import (
    ContentCollector, CollectionRequest, CollectionResult, ContentItem,
    normalize_content_item
)


class RedditCollector(ContentCollector):
    """Pure Reddit content collector using PRAW"""

    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        """
        Initialize Reddit collector with credentials.

        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret  
            user_agent: Reddit API user agent string
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent

    def validate_request(self, request: CollectionRequest) -> tuple[bool, str | None]:
        """Validate Reddit collection request"""
        if request.source != "reddit":
            return False, f"Source '{request.source}' not supported by RedditCollector"

        if not request.targets:
            return False, "No subreddits specified"

        # Validate subreddit names (basic validation)
        for target in request.targets:
            if not target or not isinstance(target, str):
                return False, f"Invalid subreddit name: {target}"
            if target.startswith('/r/'):
                return False, f"Subreddit name should not include '/r/' prefix: {target}"

        if request.limit < 1 or request.limit > 100:
            return False, "Limit must be between 1 and 100"

        return True, None

    def collect(self, request: CollectionRequest) -> CollectionResult:
        """
        Collect content from Reddit subreddits.

        This is a pure function that returns results without side effects.
        Logging and error handling are done by the caller.
        """
        # Validate request
        is_valid, error_msg = self.validate_request(request)
        if not is_valid:
            return CollectionResult(
                request=request,
                items=[],
                success=False,
                error=error_msg
            )

        try:
            # Initialize Reddit client
            reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
            )

            all_items = []
            collection_metadata = {
                "subreddits_processed": [],
                "subreddits_failed": [],
                "total_items_collected": 0
            }

            # Process each subreddit
            for subreddit_name in request.targets:
                try:
                    subreddit = reddit.subreddit(subreddit_name)

                    # Get posts based on time period
                    if request.time_period == "hot":
                        posts = subreddit.hot(limit=request.limit)
                    elif request.time_period == "new":
                        posts = subreddit.new(limit=request.limit)
                    elif request.time_period == "top":
                        posts = subreddit.top(limit=request.limit)
                    elif request.time_period == "rising":
                        posts = subreddit.rising(limit=request.limit)
                    else:
                        posts = subreddit.hot(
                            limit=request.limit)  # Default to hot

                    # Convert posts to ContentItems
                    subreddit_items = []
                    for post in posts:
                        content_item = self._reddit_post_to_content_item(
                            post, subreddit_name)
                        if content_item:
                            subreddit_items.append(content_item)

                    all_items.extend(subreddit_items)
                    collection_metadata["subreddits_processed"].append({
                        "name": subreddit_name,
                        "items_collected": len(subreddit_items)
                    })

                except Exception as e:
                    collection_metadata["subreddits_failed"].append({
                        "name": subreddit_name,
                        "error": str(e)
                    })

            collection_metadata["total_items_collected"] = len(all_items)

            return CollectionResult(
                request=request,
                items=all_items,
                success=True,
                metadata=collection_metadata
            )

        except Exception as e:
            return CollectionResult(
                request=request,
                items=[],
                success=False,
                error=f"Reddit API error: {str(e)}"
            )

    def _reddit_post_to_content_item(self, post, subreddit_name: str) -> ContentItem | None:
        """
        Convert Reddit post to standardized ContentItem.

        Pure function for data transformation.
        """
        try:
            # Get post content (selftext for text posts, url for links)
            content = ""
            if hasattr(post, 'selftext') and post.selftext:
                content = post.selftext
            elif hasattr(post, 'url') and post.url:
                content = f"Link: {post.url}"

            # Convert created_utc to datetime
            created_at = None
            if hasattr(post, 'created_utc'):
                created_at = datetime.fromtimestamp(post.created_utc)

            return ContentItem(
                title=post.title if hasattr(post, 'title') else "",
                content=content,
                url=f"https://reddit.com{post.permalink}" if hasattr(
                    post, 'permalink') else "",
                source="reddit",
                source_id=post.id if hasattr(post, 'id') else "",
                author=str(post.author) if hasattr(
                    post, 'author') and post.author else None,
                created_at=created_at,
                score=post.score if hasattr(post, 'score') else None,
                comments_count=post.num_comments if hasattr(
                    post, 'num_comments') else None,
                tags=[f"r/{subreddit_name}"],
                metadata={
                    "subreddit": subreddit_name,
                    "post_hint": getattr(post, 'post_hint', None),
                    "domain": getattr(post, 'domain', None),
                    "is_self": getattr(post, 'is_self', False),
                    "over_18": getattr(post, 'over_18', False),
                    "spoiler": getattr(post, 'spoiler', False),
                    "stickied": getattr(post, 'stickied', False)
                }
            )

        except Exception:
            # If we can't parse a post, skip it rather than failing the whole collection
            return None


def create_reddit_collector(credentials: Dict[str, str]) -> RedditCollector:
    """
    Factory function to create Reddit collector with credentials.

    Args:
        credentials: Dict with 'client_id', 'client_secret', 'user_agent'

    Returns:
        Configured RedditCollector instance
    """
    required_keys = ['client_id', 'client_secret', 'user_agent']
    for key in required_keys:
        if key not in credentials:
            raise ValueError(f"Missing required credential: {key}")

    return RedditCollector(
        client_id=credentials['client_id'],
        client_secret=credentials['client_secret'],
        user_agent=credentials['user_agent']
    )


# Pure function for processing Reddit collection requests
def collect_reddit_content(
    request: CollectionRequest,
    credentials: Dict[str, str]
) -> CollectionResult:
    """
    Pure function to collect Reddit content.

    Args:
        request: Collection request specifying subreddits and parameters
        credentials: Reddit API credentials

    Returns:
        Collection result with content items or error
    """
    try:
        collector = create_reddit_collector(credentials)
        return collector.collect(request)
    except Exception as e:
        return CollectionResult(
            request=request,
            items=[],
            success=False,
            error=f"Failed to create Reddit collector: {str(e)}"
        )

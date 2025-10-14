"""
Pure functional topic operations.

Handles conversion of collection items to TopicMetadata and priority scoring.
All functions are pure - no classes, no state.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from models import TopicMetadata

logger = logging.getLogger(__name__)


# ============================================================================
# Topic Conversion - Pure Functions
# ============================================================================


def collection_item_to_topic_metadata(
    item: Dict[str, Any], blob_name: str, collection_data: Dict[str, Any]
) -> Optional[TopicMetadata]:
    """
    Convert a collection item to TopicMetadata.

    Pure function - no side effects.

    Args:
        item: Collection item dict
        blob_name: Source blob name
        collection_data: Complete collection data

    Returns:
        TopicMetadata or None if conversion fails
    """
    try:
        # Debug: log the actual item type and content
        logger.info(f"Processing item type: {type(item)}")
        logger.debug(f"Item content: {item}")

        # Validate that item is a dictionary
        if not isinstance(item, dict):
            logger.error(f"Expected dict, got {type(item)}: {item}")
            return None

        # Extract basic information
        topic_id = item.get("id", f"unknown_{blob_name}")
        title = item.get("title", "Untitled Topic")
        source = item.get("source", "unknown")

        # Parse collected_at timestamp
        collected_at_str = item.get("collected_at") or collection_data.get(
            "metadata", {}
        ).get("timestamp")
        if collected_at_str:
            collected_at = datetime.fromisoformat(
                collected_at_str.replace("Z", "+00:00")
            )
        else:
            collected_at = datetime.now(timezone.utc)

        # Calculate priority score based on content characteristics
        priority_score = calculate_priority_score(item)

        return TopicMetadata(
            topic_id=topic_id,
            title=title,
            source=source,
            collected_at=collected_at,
            priority_score=priority_score,
            subreddit=item.get("subreddit"),  # Optional field
            url=item.get("url"),
            upvotes=item.get("ups") or item.get("upvotes"),
            comments=item.get("num_comments") or item.get("comments"),
        )

    except Exception as e:
        logger.warning(f"Error converting item to TopicMetadata: {e}")
        return None


def calculate_priority_score(item: Dict[str, Any]) -> float:
    """
    Calculate priority score for a topic based on engagement and freshness.

    Pure function - deterministic scoring.

    Args:
        item: Collection item dict

    Returns:
        Priority score (0.0-1.0)
    """
    try:
        score = 0.0

        # Base score from upvotes/score
        item_score = item.get("score", 0)
        if item_score > 0:
            score += min(
                item_score / 100.0, 1.0
            )  # Normalize to 0-1, cap at 100 upvotes

        # Bonus for comments (engagement)
        num_comments = item.get("num_comments", 0)
        if num_comments > 0:
            score += min(
                num_comments / 50.0, 0.5
            )  # Up to 0.5 bonus, cap at 50 comments

        # Freshness bonus (items collected more recently get higher priority)
        collected_at_str = item.get("collected_at")
        if collected_at_str:
            try:
                collected_at = datetime.fromisoformat(
                    collected_at_str.replace("Z", "+00:00")
                )
                hours_ago = (
                    datetime.now(timezone.utc) - collected_at
                ).total_seconds() / 3600
                # Freshness bonus decreases over 24 hours
                if hours_ago < 24:
                    freshness_bonus = (24 - hours_ago) / 24 * 0.3  # Up to 0.3 bonus
                    score += freshness_bonus
            except Exception:
                pass  # Skip freshness bonus if timestamp parsing fails

        # Ensure score is between 0 and 1
        return max(0.0, min(score, 1.0))

    except Exception as e:
        logger.warning(f"Error calculating priority score: {e}")
        return 0.5  # Default score

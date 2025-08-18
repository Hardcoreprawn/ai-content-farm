"""
Trend Score Calculator Module

Simple heuristics to calculate how "trending" content might be.
Based on engagement patterns and time factors.
"""

from typing import Dict, Any
from datetime import datetime, timezone
import math


def calculate_trend_score(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate a trend score for content based on simple heuristics.

    Args:
        content: Content dictionary with metadata

    Returns:
        Dictionary with trend_score and contributing factors
    """
    # Initialize scores
    engagement_score = 0.0
    recency_score = 0.0
    velocity_score = 0.0

    # Engagement score based on upvotes, comments, etc.
    upvotes = content.get("score", 0)
    comments = content.get("num_comments", 0)

    # Simple engagement calculation
    if upvotes > 0:
        # Log scale, cap at 1.0
        engagement_score = min(math.log10(upvotes + 1) / 4, 1.0)

    if comments > 0:
        # Comments weighted slightly higher
        comment_score = min(math.log10(comments + 1) / 3, 1.0)
        engagement_score = max(engagement_score, comment_score)

    # Recency score - how recent is the content
    created_utc = content.get("created_utc")
    if created_utc:
        try:
            if isinstance(created_utc, (int, float)):
                created_time = datetime.fromtimestamp(
                    created_utc, tz=timezone.utc)
            else:
                # Assume it's already a datetime or string
                created_time = datetime.fromisoformat(
                    str(created_utc).replace('Z', '+00:00'))

            now = datetime.now(timezone.utc)
            hours_old = (now - created_time).total_seconds() / 3600

            # Recency score decreases over time
            if hours_old <= 1:
                recency_score = 1.0
            elif hours_old <= 24:
                # Drop to 0.5 over 24 hours
                recency_score = 1.0 - (hours_old - 1) / 23 * 0.5
            elif hours_old <= 168:  # 1 week
                recency_score = 0.5 - (hours_old - 24) / \
                    144 * 0.4  # Drop to 0.1 over week
            else:
                recency_score = 0.1  # Minimum score for old content

        except (ValueError, TypeError):
            recency_score = 0.5  # Default if we can't parse time
    else:
        recency_score = 0.5  # Default if no timestamp

    # Velocity score - ratio of engagement to time
    if created_utc and upvotes > 0:
        try:
            if isinstance(created_utc, (int, float)):
                created_time = datetime.fromtimestamp(
                    created_utc, tz=timezone.utc)
            else:
                created_time = datetime.fromisoformat(
                    str(created_utc).replace('Z', '+00:00'))

            now = datetime.now(timezone.utc)
            # Avoid division by zero
            hours_old = max((now - created_time).total_seconds() / 3600, 0.1)

            # Velocity is engagement per hour
            velocity = (upvotes + comments * 2) / hours_old
            velocity_score = min(velocity / 100, 1.0)  # Scale and cap

        except (ValueError, TypeError):
            velocity_score = 0.0
    else:
        velocity_score = 0.0

    # Calculate age for factors output
    age_hours = None
    if created_utc:
        try:
            if isinstance(created_utc, (int, float)):
                created_time = datetime.fromtimestamp(
                    created_utc, tz=timezone.utc)
            else:
                created_time = datetime.fromisoformat(
                    str(created_utc).replace('Z', '+00:00'))

            age_hours = round((datetime.now(timezone.utc) -
                              created_time).total_seconds() / 3600, 1)
        except (ValueError, TypeError):
            age_hours = None

    # Combine scores with weights
    trend_score = (
        engagement_score * 0.4 +
        recency_score * 0.3 +
        velocity_score * 0.3
    )

    return {
        "trend_score": round(trend_score, 3),
        "engagement_score": round(engagement_score, 3),
        "recency_score": round(recency_score, 3),
        "velocity_score": round(velocity_score, 3),
        "factors": {
            "upvotes": upvotes,
            "comments": comments,
            "age_hours": age_hours
        }
    }

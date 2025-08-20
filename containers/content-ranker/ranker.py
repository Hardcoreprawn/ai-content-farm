"""
Content Ranker - Core Ranking Algorithms

Pure functional implementation for ranking content items.
Multi-factor scoring: engagement + recency + topic relevance.
"""

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def calculate_engagement_score(content_item: Dict[str, Any]) -> float:
    """
    Calculate engagement score from enriched content.

    Args:
        content_item: Enriched content dictionary

    Returns:
        Normalized engagement score (0.0 - 1.0)
    """
    # Get base engagement score from processor
    base_engagement = content_item.get("engagement_score", 0.0)

    # Get normalized score from processor
    normalized_score = content_item.get("normalized_score", 0.0)

    # Get enrichment factors
    trend_analysis = content_item.get("trend_analysis", {})
    trend_score = trend_analysis.get("trend_score", 0.0)

    # Combine engagement factors with weights
    engagement_weight = 0.5
    score_weight = 0.3
    trend_weight = 0.2

    total_engagement = (
        base_engagement * engagement_weight
        + normalized_score * score_weight
        + trend_score * trend_weight
    )

    # Ensure result is in [0, 1] range
    return max(0.0, min(1.0, total_engagement))


def calculate_recency_score(content_item: Dict[str, Any]) -> float:
    """
    Calculate recency score based on content age.

    Args:
        content_item: Content dictionary with timestamp

    Returns:
        Normalized recency score (0.0 - 1.0, higher = more recent)
    """
    published_at = content_item.get("published_at")
    if not published_at:
        return 0.5  # Default for missing timestamp

    try:
        # Parse timestamp (expecting ISO format)
        if isinstance(published_at, str):
            published_time = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        else:
            return 0.5

        current_time = datetime.now(timezone.utc)
        age_hours = (current_time - published_time).total_seconds() / 3600

        # Exponential decay: newer content scores higher
        # Half-life of 24 hours (content loses half value after 24h)
        decay_factor = 24.0
        recency_score = math.exp(-age_hours / decay_factor)

        return max(0.0, min(1.0, recency_score))

    except (ValueError, TypeError):
        return 0.5  # Default for invalid timestamp


def calculate_topic_relevance(
    content_item: Dict[str, Any], target_topics: Optional[List[str]] = None
) -> float:
    """
    Calculate topic relevance score.

    Args:
        content_item: Content with topic classification
        target_topics: List of target topics for relevance (optional)

    Returns:
        Normalized topic relevance score (0.0 - 1.0)
    """
    topic_classification = content_item.get("topic_classification", {})

    if not topic_classification:
        return 0.5  # Default when no topic data

    # Base score from topic classification confidence
    base_confidence = topic_classification.get("confidence", 0.0)

    # If no target topics specified, use base confidence
    if not target_topics:
        return max(0.0, min(1.0, base_confidence))

    # Check for topic matches
    content_topics = topic_classification.get("topics", [])
    primary_topic = topic_classification.get("primary_topic", "")

    # Calculate topic overlap
    content_topic_set = set(
        [t.lower() for t in content_topics] + [primary_topic.lower()]
    )
    target_topic_set = set([t.lower() for t in target_topics])

    overlap = len(content_topic_set.intersection(target_topic_set))
    total_targets = len(target_topic_set)

    if total_targets > 0:
        overlap_score = overlap / total_targets
    else:
        overlap_score = 0.0

    # Combine confidence and topic overlap
    relevance_score = (base_confidence * 0.6) + (overlap_score * 0.4)

    return max(0.0, min(1.0, relevance_score))


def calculate_composite_score(
    content_item: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None,
    target_topics: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Calculate composite ranking score from all factors.

    Args:
        content_item: Enriched content dictionary
        weights: Custom weights for scoring factors
        target_topics: Target topics for relevance scoring

    Returns:
        Dictionary with individual scores and composite score
    """
    # Default weights
    default_weights = {"engagement": 0.4, "recency": 0.35, "topic_relevance": 0.25}

    # Use provided weights or defaults
    final_weights = weights or default_weights

    # Ensure weights sum to 1.0
    weight_sum = sum(final_weights.values())
    if weight_sum > 0:
        final_weights = {k: v / weight_sum for k, v in final_weights.items()}

    # Calculate individual scores
    engagement_score = calculate_engagement_score(content_item)
    recency_score = calculate_recency_score(content_item)
    relevance_score = calculate_topic_relevance(content_item, target_topics)

    # Calculate weighted composite score
    composite_score = (
        engagement_score * final_weights.get("engagement", 0.4)
        + recency_score * final_weights.get("recency", 0.35)
        + relevance_score * final_weights.get("topic_relevance", 0.25)
    )

    return {
        "engagement_score": engagement_score,
        "recency_score": recency_score,
        "topic_relevance_score": relevance_score,
        "composite_score": max(0.0, min(1.0, composite_score)),
        "weights_used": final_weights,
    }


def rank_content_items(
    content_items: List[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
    target_topics: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Rank a list of content items by composite score.

    Args:
        content_items: List of enriched content dictionaries
        weights: Custom weights for scoring factors
        target_topics: Target topics for relevance scoring
        limit: Maximum number of items to return (optional)

    Returns:
        List of content items with ranking scores, sorted by composite score
    """
    if not content_items:
        return []

    # Calculate scores for all items
    ranked_items = []
    for item in content_items:
        # Calculate ranking scores
        scores = calculate_composite_score(item, weights, target_topics)

        # Create ranked item with original content + scores
        ranked_item = item.copy()
        ranked_item["ranking_scores"] = scores
        ranked_item["final_rank_score"] = scores["composite_score"]

        ranked_items.append(ranked_item)

    # Sort by composite score (highest first)
    ranked_items.sort(key=lambda x: x["final_rank_score"], reverse=True)

    # Apply limit if specified
    if limit and limit > 0:
        ranked_items = ranked_items[:limit]

    # Add rank positions
    for i, item in enumerate(ranked_items, 1):
        item["rank_position"] = i

    return ranked_items

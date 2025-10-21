"""
Content scoring utilities for quality ranking.

Calculates quality scores, applies penalties, and ranks articles.
Pure math functions, no side effects.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from quality.config import DETECTION_WEIGHTS, QUALITY_SCORE_THRESHOLD
from quality.detectors import detect_content_quality

logger = logging.getLogger(__name__)


def calculate_quality_score(
    item: Dict[str, Any], detection_results: Optional[Dict] = None
) -> float:
    """
    Calculate quality score for an item (0.0 to 1.0).

    Base score: 1.0
    Penalties applied for:
    - Paywall content (-0.40)
    - Comparison articles (-0.25)
    - Listicles (-0.20)
    - Poor content length (±0.10-0.15)

    Args:
        item: Content item with title, content, url
        detection_results: Pre-computed detection results (optional)

    Returns:
        Quality score as float between 0.0 and 1.0
    """
    if not isinstance(item, dict):
        return 0.0

    title = str(item.get("title", "")).strip()
    content = str(item.get("content", "")).strip()
    source_url = str(item.get("source_url", "")).strip()

    if not title or not content:
        return 0.0

    # Run detections if not provided
    if detection_results is None:
        detection_results = detect_content_quality(title, content, source_url)

    # Start with perfect score
    score = 1.0

    # Apply penalties
    if detection_results.get("is_paywalled", False):
        score += DETECTION_WEIGHTS.get("paywall_penalty", -0.40)

    if detection_results.get("is_comparison", False):
        score += DETECTION_WEIGHTS.get("comparison_penalty", -0.25)

    if detection_results.get("is_listicle", False):
        score += DETECTION_WEIGHTS.get("listicle_penalty", -0.20)

    # Apply length scoring
    length_score = detection_results.get("content_length_score", 0.0)
    score += length_score

    # Clamp to 0-1 range
    return max(0.0, min(1.0, score))


def score_items(
    items: List[Dict[str, Any]], config: Optional[Dict] = None
) -> List[Tuple[Dict, float]]:
    """
    Score all items in batch, returning (item, score) tuples.

    Filters out low-scoring items based on config threshold.

    Args:
        items: List of content items
        config: Configuration dict (contains min_quality_score threshold)

    Returns:
        List of (item, score) tuples for items meeting threshold
    """
    if not isinstance(items, list):
        return []

    config = config or {}
    threshold = config.get("min_quality_score", QUALITY_SCORE_THRESHOLD)

    scored_items = []

    for item in items:
        if not isinstance(item, dict):
            continue

        # Calculate score for this item
        score = calculate_quality_score(item)

        # Only include items above threshold
        if score >= threshold:
            scored_items.append((item, score))

    return scored_items


def rank_items(
    scored_items: List[Tuple[Dict, float]], max_results: int = 20
) -> List[Dict]:
    """
    Rank scored items and apply diversity filtering.

    Ensures no source is over-represented (max 3 articles per source).
    Returns top N items sorted by quality score (highest first).

    Args:
        scored_items: List of (item, score) tuples
        max_results: Maximum items to return (default 20)

    Returns:
        Top N items sorted by score (highest first)
    """
    if not scored_items:
        return []

    # Sort by score descending
    sorted_items = sorted(scored_items, key=lambda x: x[1], reverse=True)

    # Apply diversity: max 3 per source
    source_counts: Dict[str, int] = {}
    ranked = []

    for item, score in sorted_items:
        source = str(item.get("source", "unknown")).strip()

        current_count = source_counts.get(source, 0)

        if current_count < 3:  # Max 3 per source
            source_counts[source] = current_count + 1
            ranked.append(item)

            if len(ranked) >= max_results:
                break

    return ranked


def add_score_metadata(
    items: List[Dict], scored_items: List[Tuple[Dict, float]]
) -> List[Dict]:
    """
    Add quality score and metadata to items.

    Matches items from scored_items to input items, adds score and
    detection metadata to each item for transparency.

    Args:
        items: Original items list
        scored_items: (item, score) tuples with detection info

    Returns:
        Items with added _quality_score and _detections fields
    """
    if not scored_items:
        return items

    # Build map of scored items by content hash for matching
    scored_map = {}
    for item, score in scored_items:
        if isinstance(item, dict):
            # Use title + first 100 chars as simple key
            key = (
                str(item.get("title", ""))[:50],
                str(item.get("content", ""))[:100],
            )
            scored_map[key] = (score, item)

    # Add scores to items
    result = []
    for item in items:
        if isinstance(item, dict):
            key = (
                str(item.get("title", ""))[:50],
                str(item.get("content", ""))[:100],
            )

            if key in scored_map:
                score, scored_item = scored_map[key]
                item_copy = item.copy()
                item_copy["_quality_score"] = round(score, 3)
                result.append(item_copy)
            else:
                result.append(item)
        else:
            result.append(item)

    return result

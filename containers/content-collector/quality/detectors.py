"""
Content detection utilities for quality scoring.

Detects unsuitable content types:
- Paywall: subscription-walled articles
- Comparison: product comparison listicles
- Listicle: "top 10" style articles

Pure functions, defensive coding, reusable across modules.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from quality.config import (
    COMPARISON_KEYWORDS,
    COMPARISON_REGEX,
    LISTICLE_REGEX,
    has_paywall_keyword,
    is_paywall_domain,
)

logger = logging.getLogger(__name__)


def detect_paywall(title: str, content: str, source_url: str) -> Tuple[bool, float]:
    """
    Detect if article is behind paywall.

    Checks:
    - Domain blocklist (wired.com, ft.com, wsj.com, etc.)
    - Content keywords ("subscriber only", "members only", etc.)
    - Returns (is_paywalled, penalty_score)

    Args:
        title: Article title
        content: Article body
        source_url: URL where article came from

    Returns:
        (is_paywalled: bool, penalty: float between 0-1)
    """
    if not isinstance(title, str) or not isinstance(content, str):
        return (False, 0.0)

    # Check domain blocklist first (fast)
    if is_paywall_domain(source_url):
        return (True, 1.0)

    # Check content for paywall keywords
    combined_text = f"{title} {content}".lower()
    if has_paywall_keyword(combined_text):
        return (True, 0.8)

    return (False, 0.0)


def detect_comparison(title: str, content: str) -> Tuple[bool, float]:
    """
    Detect if article is product comparison or "vs" listicle.

    Checks:
    - Title/content keywords ("vs", "best products", "comparison")
    - Regex patterns (price ranges, pros/cons sections)
    - Returns (is_comparison, penalty_score)

    Args:
        title: Article title
        content: Article body

    Returns:
        (is_comparison: bool, penalty: float between 0-1)
    """
    if not isinstance(title, str) or not isinstance(content, str):
        return (False, 0.0)

    combined_text = f"{title} {content}".lower()

    # Check keywords
    keyword_match = any(kw in combined_text for kw in COMPARISON_KEYWORDS)

    # Check regex patterns
    regex_match = any(pattern.search(combined_text) for pattern in COMPARISON_REGEX)

    if keyword_match or regex_match:
        return (True, 0.7)

    return (False, 0.0)


def detect_listicle(title: str) -> Tuple[bool, float]:
    """
    Detect if article is a listicle ("top 10", "best 5", etc.).

    Checks title against patterns like:
    - "10 ways to..."
    - "top 5 best..."
    - "here are 7 things..."

    Args:
        title: Article title

    Returns:
        (is_listicle: bool, penalty: float between 0-1)
    """
    if not isinstance(title, str):
        return (False, 0.0)

    title_lower = title.lower().strip()

    # Check patterns
    for pattern in LISTICLE_REGEX:
        if pattern.search(title_lower):
            return (True, 0.5)

    return (False, 0.0)


def detect_content_length(content: str) -> Tuple[bool, float]:
    """
    Evaluate content length suitability.

    Checks:
    - Too short (<300 chars): spam/stub, penalty
    - Optimal (300-1500 chars): no penalty, small bonus
    - Too long (>1500 chars): bloat/filler, small penalty

    Args:
        content: Article body text

    Returns:
        (is_suitable: bool, score_delta: float between -0.2 and +0.1)
    """
    if not isinstance(content, str):
        return (False, -0.2)

    length = len(content.strip())

    # Too short = stub/spam
    if length < 300:
        return (False, -0.15)

    # Optimal range = good bonus
    if 300 <= length <= 1500:
        return (True, 0.10)

    # Too long = bloat/filler
    if length > 1500:
        return (True, -0.10)

    return (True, 0.0)


def detect_content_quality(
    title: str, content: str, source_url: str = ""
) -> Dict[str, Any]:
    """
    Run all detection checks and return comprehensive quality assessment.

    Orchestrates all detectors and returns structured results for scoring.

    Args:
        title: Article title
        content: Article body
        source_url: URL (optional, for paywall detection)

    Returns:
        Dict with detection results:
        {
            "is_paywalled": bool,
            "is_comparison": bool,
            "is_listicle": bool,
            "content_length_score": float,
            "detections": [...list of detection names...],
            "suitable": bool  # True if passes all checks
        }
    """
    if not isinstance(title, str) or not isinstance(content, str):
        return {
            "is_paywalled": False,
            "is_comparison": False,
            "is_listicle": False,
            "content_length_score": 0.0,
            "detections": ["invalid_input"],
            "suitable": False,
        }

    # Run all detectors
    is_paywalled, _ = detect_paywall(title, content, source_url or "")
    is_comparison, _ = detect_comparison(title, content)
    is_listicle, _ = detect_listicle(title)
    is_length_ok, length_score = detect_content_length(content)

    # Track detections
    detections = []
    if is_paywalled:
        detections.append("paywall")
    if is_comparison:
        detections.append("comparison")
    if is_listicle:
        detections.append("listicle")
    if not is_length_ok:
        detections.append("poor_length")

    # Suitable = not paywalled/comparison/listicle AND reasonable length
    suitable = (
        not is_paywalled and not is_comparison and not is_listicle and is_length_ok
    )

    return {
        "is_paywalled": is_paywalled,
        "is_comparison": is_comparison,
        "is_listicle": is_listicle,
        "content_length_score": length_score,
        "detections": detections,
        "suitable": suitable,
    }

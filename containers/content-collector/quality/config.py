"""
Configuration and constants for quality gate filtering.

Single source of truth for all detection patterns, thresholds, and defaults.
No business logic - only configuration data.
"""

import copy
import re
from typing import Any, Dict, Optional, Set
from urllib.parse import urlparse

# ============================================================================
# PAYWALL DETECTION - Keywords and domain blocklist
# ============================================================================

PAYWALL_KEYWORDS = {
    "subscriber only",
    "subscription required",
    "paywall",
    "members only",
    "sign up to read",
    "log in to continue",
    "registration required",
    "paid content",
    "premium article",
    "this story requires a subscription",
}

PAYWALL_DOMAINS = {
    "wired.com",
    "ft.com",
    "wsj.com",
    "bloomberg.com",
    "economist.com",
    "theguardian.com/international",
    "nytimes.com",
    "medium.com/paywall",
    "patreon.com",
}

# ============================================================================
# COMPARISON DETECTION - Keywords and patterns
# ============================================================================

COMPARISON_KEYWORDS = {
    " vs ",
    " versus ",
    "best products",
    "best options",
    "best choice",
    "how to choose",
    "comparison",
    "head to head",
    "battle of the",
    "showdown",
}

COMPARISON_PATTERNS = [
    r"\$\d+.*\$\d+",  # Price ranges
    r"pros and cons",
    r"pros:",
    r"cons:",
    r"comparison table",
    r"feature comparison",
]

# ============================================================================
# LISTICLE DETECTION - Title patterns
# ============================================================================

LISTICLE_PATTERNS = [
    r"^\d+\s+ways?\s+to",
    r"top\s+\d+",
    r"best\s+\d+",
    r"here are\s+\d+",
    r"\d+\s+reasons?\s+(why|to)",
    r"\d+\s+tips?\s+(for|on)",
    r"\d+\s+things?\s+(you|to)",
    r"the\s+\d+\s+best",
    r"the\s+\d+\s+worst",
]

# ============================================================================
# CONTENT LENGTH - Optimal ranges (in characters)
# ============================================================================

MIN_CONTENT_LENGTH = 300  # Too short = probably spam/stub
OPTIMAL_CONTENT_LENGTH = 1500  # Sweet spot for AI processing
MAX_CONTENT_LENGTH = 5000  # Too long = bloat/filler

# ============================================================================
# QUALITY SCORING - Thresholds and weights
# ============================================================================

QUALITY_SCORE_THRESHOLD = 0.6  # Minimum score to emit to processor (0-1)

DETECTION_WEIGHTS = {
    "paywall_penalty": -0.40,  # Large penalty for paywalled content
    "comparison_penalty": -0.25,  # Medium penalty for comparisons
    "listicle_penalty": -0.20,  # Small penalty for listicles
}

LENGTH_SCORING = {
    "too_short_penalty": -0.15,  # Below MIN_CONTENT_LENGTH
    "optimal_bonus": 0.10,  # Within optimal range
    "too_long_penalty": -0.10,  # Above MAX_CONTENT_LENGTH
}

# ============================================================================
# DEFAULT CONFIGURATION
# ============================================================================

DEFAULT_CONFIG = {
    "enabled": True,
    "min_quality_score": QUALITY_SCORE_THRESHOLD,
    "max_results": 20,  # Top N articles to emit
    "diversity": {
        "enabled": True,
        "max_per_source": 3,  # Limit articles from same source
    },
    "detection": {
        "paywall": {"enabled": True, "weight": DETECTION_WEIGHTS["paywall_penalty"]},
        "comparison": {
            "enabled": True,
            "weight": DETECTION_WEIGHTS["comparison_penalty"],
        },
        "listicle": {"enabled": True, "weight": DETECTION_WEIGHTS["listicle_penalty"]},
        "length": {"enabled": True, "weights": LENGTH_SCORING},
    },
    "deduplication": {
        "enabled": True,
        "check_batch": True,  # Layer 1: in-memory this batch
        "check_today": True,  # Layer 2: published today
        "check_historical": True,  # Layer 3: historical URLs
    },
}

# ============================================================================
# UTILITIES - Helper functions for configuration
# ============================================================================


def compile_regex_patterns(patterns: list) -> list:
    """Pre-compile regex patterns for efficiency."""
    return [re.compile(p, re.IGNORECASE) for p in patterns]


LISTICLE_REGEX = compile_regex_patterns(LISTICLE_PATTERNS)
COMPARISON_REGEX = compile_regex_patterns(COMPARISON_PATTERNS)


def is_paywall_domain(url: Any) -> bool:
    """Check if URL is from known paywall domain using proper hostname extraction.

    Properly validates domain by extracting hostname and path, checking against blocklist.
    This prevents bypass attempts like "wired.com.evil.com" while supporting both:
    - Domain-only blocks: "wired.com"
    - Domain+path blocks: "medium.com/paywall"
    """
    if not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url.lower())
        hostname = parsed.hostname or parsed.netloc or ""
        path = parsed.path or ""

        # Build the full domain:path identifier for matching
        for blocked_entry in PAYWALL_DOMAINS:
            if "/" in blocked_entry:
                # Path-based block like "medium.com/paywall"
                domain, blocked_path = blocked_entry.split("/", 1)
                if (
                    hostname == domain or hostname.endswith("." + domain)
                ) and blocked_path in path:
                    return True
            else:
                # Domain-only block like "wired.com"
                if hostname == blocked_entry or hostname.endswith("." + blocked_entry):
                    return True

        return False
    except (ValueError, AttributeError):
        # If URL parsing fails, be conservative and return False
        return False


def has_paywall_keyword(text: Any) -> bool:
    """Check if text contains paywall keywords."""
    if not isinstance(text, str):
        return False

    text_lower = text.lower()
    return any(keyword in text_lower for keyword in PAYWALL_KEYWORDS)


def get_quality_config(overrides: Optional[Dict] = None) -> Dict:
    """Get configuration with optional overrides."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    if overrides and isinstance(overrides, dict):
        config.update(overrides)
    return config

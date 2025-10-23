"""
Quality module: Item-level content filtering and validation.
"""

# Legacy modules (consolidated here for backward compatibility)
from quality.config import (
    COMPARISON_KEYWORDS,
    COMPARISON_REGEX,
    DEFAULT_CONFIG,
    DETECTION_WEIGHTS,
    LISTICLE_REGEX,
    PAYWALL_DOMAINS,
    PAYWALL_KEYWORDS,
    QUALITY_SCORE_THRESHOLD,
    compile_regex_patterns,
    get_quality_config,
    has_paywall_keyword,
    is_paywall_domain,
)
from quality.dedup import (
    apply_all_dedup_layers,
    filter_duplicates_in_batch,
    hash_content,
)
from quality.detectors import detect_content_quality
from quality.gate import (
    emit_to_processor,
    get_pipeline_status,
    process_items,
    validate_item,
    validate_items,
)
from quality.review import check_readability, check_technical_relevance, review_item
from quality.scoring import (
    add_score_metadata,
    calculate_quality_score,
    rank_items,
    score_items,
)

__all__ = [
    # Config
    "COMPARISON_KEYWORDS",
    "COMPARISON_REGEX",
    "DEFAULT_CONFIG",
    "DETECTION_WEIGHTS",
    "LISTICLE_REGEX",
    "PAYWALL_DOMAINS",
    "PAYWALL_KEYWORDS",
    "QUALITY_SCORE_THRESHOLD",
    "compile_regex_patterns",
    "get_quality_config",
    "has_paywall_keyword",
    "is_paywall_domain",
    # Dedup
    "apply_all_dedup_layers",
    "filter_duplicates_in_batch",
    "hash_content",
    # Detectors
    "detect_content_quality",
    # Gate (main pipeline)
    "emit_to_processor",
    "get_pipeline_status",
    "process_items",
    "validate_item",
    "validate_items",
    # Review
    "check_readability",
    "check_technical_relevance",
    "review_item",
    # Scoring
    "add_score_metadata",
    "calculate_quality_score",
    "rank_items",
    "score_items",
]

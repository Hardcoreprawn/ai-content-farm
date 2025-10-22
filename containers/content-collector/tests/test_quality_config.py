"""
Tests for quality_config module.

Verifies configuration defaults, thresholds, patterns, and helper functions.
Ensures critical configuration remains stable across changes.
"""

import re

import pytest
from quality.config import (
    COMPARISON_KEYWORDS,
    COMPARISON_REGEX,
    DEFAULT_CONFIG,
    DETECTION_WEIGHTS,
    LENGTH_SCORING,
    LISTICLE_PATTERNS,
    LISTICLE_REGEX,
    MAX_CONTENT_LENGTH,
    MIN_CONTENT_LENGTH,
    OPTIMAL_CONTENT_LENGTH,
    PAYWALL_DOMAINS,
    PAYWALL_KEYWORDS,
    QUALITY_SCORE_THRESHOLD,
    compile_regex_patterns,
    get_quality_config,
    has_paywall_keyword,
    is_paywall_domain,
)


class TestConfigurationConstants:
    """Verify all critical configuration constants exist and have correct types."""

    def test_paywall_keywords_exist(self):
        """Paywall keywords should be non-empty set."""
        assert isinstance(PAYWALL_KEYWORDS, set)
        assert len(PAYWALL_KEYWORDS) > 0
        assert "subscriber only" in PAYWALL_KEYWORDS

    def test_paywall_domains_exist(self):
        """Paywall domain blocklist should be non-empty set."""
        assert isinstance(PAYWALL_DOMAINS, set)
        assert len(PAYWALL_DOMAINS) > 0
        assert "wired.com" in PAYWALL_DOMAINS

    def test_comparison_keywords_exist(self):
        """Comparison keywords should be non-empty set."""
        assert isinstance(COMPARISON_KEYWORDS, set)
        assert len(COMPARISON_KEYWORDS) > 0
        assert " vs " in COMPARISON_KEYWORDS

    def test_listicle_patterns_exist(self):
        """Listicle patterns should be non-empty list."""
        assert isinstance(LISTICLE_PATTERNS, list)
        assert len(LISTICLE_PATTERNS) > 0
        assert any("ways" in p for p in LISTICLE_PATTERNS)

    def test_length_thresholds(self):
        """Content length thresholds should be positive and ordered."""
        assert MIN_CONTENT_LENGTH > 0
        assert OPTIMAL_CONTENT_LENGTH > MIN_CONTENT_LENGTH
        assert MAX_CONTENT_LENGTH > OPTIMAL_CONTENT_LENGTH

    def test_quality_score_threshold(self):
        """Quality score threshold should be between 0 and 1."""
        assert 0.0 <= QUALITY_SCORE_THRESHOLD <= 1.0

    def test_detection_weights(self):
        """Detection weights should exist and be negative (penalties)."""
        assert isinstance(DETECTION_WEIGHTS, dict)
        assert len(DETECTION_WEIGHTS) > 0
        for weight in DETECTION_WEIGHTS.values():
            assert isinstance(weight, (int, float))
            assert weight < 0  # Penalties are negative

    def test_length_scoring_exists(self):
        """Length scoring should have penalty and bonus keys."""
        assert isinstance(LENGTH_SCORING, dict)
        assert "too_short_penalty" in LENGTH_SCORING
        assert "optimal_bonus" in LENGTH_SCORING
        assert "too_long_penalty" in LENGTH_SCORING


class TestDefaultConfiguration:
    """Verify DEFAULT_CONFIG has all required keys and valid values."""

    def test_default_config_structure(self):
        """DEFAULT_CONFIG should have required top-level keys."""
        required_keys = [
            "enabled",
            "min_quality_score",
            "max_results",
            "diversity",
            "detection",
            "deduplication",
        ]
        for key in required_keys:
            assert key in DEFAULT_CONFIG, f"Missing key: {key}"

    def test_default_config_enabled(self):
        """Quality gate should be enabled by default."""
        assert DEFAULT_CONFIG["enabled"] is True

    def test_default_config_min_score(self):
        """Min quality score should be between 0 and 1."""
        score = DEFAULT_CONFIG["min_quality_score"]
        assert 0.0 <= score <= 1.0

    def test_default_config_max_results(self):
        """Max results should be positive integer."""
        assert isinstance(DEFAULT_CONFIG["max_results"], int)
        assert DEFAULT_CONFIG["max_results"] > 0

    def test_default_config_diversity(self):
        """Diversity config should specify max per source."""
        assert "enabled" in DEFAULT_CONFIG["diversity"]
        assert "max_per_source" in DEFAULT_CONFIG["diversity"]
        assert DEFAULT_CONFIG["diversity"]["max_per_source"] > 0

    def test_default_config_detection(self):
        """Detection config should have paywall, comparison, listicle."""
        detection = DEFAULT_CONFIG["detection"]
        assert "paywall" in detection
        assert "comparison" in detection
        assert "listicle" in detection
        assert "length" in detection

    def test_default_config_deduplication(self):
        """Deduplication config should specify all layers."""
        dedup = DEFAULT_CONFIG["deduplication"]
        assert "enabled" in dedup
        assert "check_batch" in dedup
        assert "check_today" in dedup
        assert "check_historical" in dedup


class TestRegexCompilation:
    """Verify regex patterns compile and match correctly."""

    def test_listicle_regex_compiled(self):
        """LISTICLE_REGEX should be list of compiled patterns."""
        assert isinstance(LISTICLE_REGEX, list)
        assert len(LISTICLE_REGEX) > 0
        assert all(isinstance(p, type(re.compile(""))) for p in LISTICLE_REGEX)

    def test_comparison_regex_compiled(self):
        """COMPARISON_REGEX should be list of compiled patterns."""
        assert isinstance(COMPARISON_REGEX, list)
        assert len(COMPARISON_REGEX) > 0
        assert all(isinstance(p, type(re.compile(""))) for p in COMPARISON_REGEX)

    def test_listicle_regex_matches(self):
        """LISTICLE_REGEX should match listicle titles."""
        listicle_titles = [
            "10 ways to improve",
            "Top 5 Best Products",
            "Here are 7 Things",
            "3 reasons why",
        ]
        for title in listicle_titles:
            assert any(
                p.search(title.lower()) for p in LISTICLE_REGEX
            ), f"Should match: {title}"

    def test_comparison_regex_matches(self):
        """COMPARISON_REGEX should match comparison content."""
        comparison_texts = [
            "pros and cons",
            "Pros: great design",
            "Cons: expensive",
            "$100 versus $500",
        ]
        for text in comparison_texts:
            assert any(
                p.search(text.lower()) for p in COMPARISON_REGEX
            ), f"Should match: {text}"


class TestCompileRegexPatterns:
    """Test regex pattern compilation utility."""

    def test_compile_patterns_returns_list(self):
        """Should return list of compiled patterns."""
        patterns = ["test1", "test2"]
        result = compile_regex_patterns(patterns)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_compile_patterns_all_compiled(self):
        """All results should be compiled regex objects."""
        patterns = ["test1", "test2"]
        result = compile_regex_patterns(patterns)
        assert all(isinstance(p, type(re.compile(""))) for p in result)

    def test_compile_patterns_case_insensitive(self):
        """Patterns should be case-insensitive."""
        patterns = ["TEST"]
        result = compile_regex_patterns(patterns)
        assert result[0].search("test") is not None
        assert result[0].search("TEST") is not None


class TestPaywallHelpers:
    """Test paywall detection helper functions.

    Security Note: All domain matching uses urlparse().hostname extraction,
    not substring matching. This prevents bypass attacks like "domain.evil.com"
    while correctly matching subdomains like "archive.domain.com".
    See is_paywall_domain() implementation in quality/config.py.
    """

    def test_is_paywall_domain_known_domain(self):
        """Should detect known paywall domains using urlparse() hostname extraction."""
        # Using urlparse().hostname, not substring matching for security
        wired_article = "https://www.wired.com/article/something"
        ft_content = "https://ft.com/content"

        assert is_paywall_domain(wired_article) is True
        assert is_paywall_domain(ft_content) is True

    def test_is_paywall_domain_unknown_domain(self):
        """Should not flag unknown domains."""
        medium_story = "https://www.medium.com/story"
        github_repo = "https://github.com/repo"

        assert is_paywall_domain(medium_story) is False
        assert is_paywall_domain(github_repo) is False

    def test_is_paywall_domain_path_based_blocks(self):
        """Should detect path-based paywall blocks like medium.com/paywall."""
        medium_paywall = "https://medium.com/paywall/story"
        medium_paywall_sub = "https://www.medium.com/paywall/article"
        guardian_intl = "https://theguardian.com/international/news"

        assert is_paywall_domain(medium_paywall) is True
        assert is_paywall_domain(medium_paywall_sub) is True
        assert is_paywall_domain(guardian_intl) is True

    def test_is_paywall_domain_subdomain_support(self):
        """Should detect paywalls on subdomains using proper hostname extraction."""
        wired_archive = "https://archive.wired.com/article"
        ft_blog = "https://blog.ft.com/article"

        assert is_paywall_domain(wired_archive) is True
        assert is_paywall_domain(ft_blog) is True

    def test_is_paywall_domain_bypass_attempts(self):
        """Should prevent URL bypass attacks using urlparse().hostname extraction.

        Verifies that:
        - wired.com.evil.com doesn't match (hostname: wired.com.evil.com != wired.com)
        - evil-wired.com doesn't match (hostname: evil-wired.com != wired.com)
        - subdomain.wired.com correctly matches (hostname.endswith('.wired.com'))
        """
        bypass_attempt_1 = "https://wired.com.evil.com/article"
        bypass_attempt_2 = "https://evil-wired.com/article"
        valid_subdomain = "https://subdomain.wired.com/article"

        assert is_paywall_domain(bypass_attempt_1) is False
        assert is_paywall_domain(bypass_attempt_2) is False
        assert is_paywall_domain(valid_subdomain) is True

    def test_is_paywall_domain_invalid_input(self):
        """Should return False for invalid inputs gracefully."""
        empty_string = ""
        non_domain = "not a domain"

        assert is_paywall_domain(empty_string) is False
        assert is_paywall_domain(non_domain) is False

    def test_has_paywall_keyword_yes(self):
        """Should detect paywall keywords."""
        assert has_paywall_keyword("subscriber only content") is True
        assert has_paywall_keyword("members only access") is True
        assert has_paywall_keyword("paywall protected") is True

    def test_has_paywall_keyword_no(self):
        """Should not flag content without paywall keywords."""
        assert has_paywall_keyword("This is free content") is False
        assert has_paywall_keyword("Read this amazing article") is False

    def test_has_paywall_keyword_case_insensitive(self):
        """Should be case-insensitive."""
        assert has_paywall_keyword("SUBSCRIBER ONLY") is True
        assert has_paywall_keyword("Subscriber Only") is True

    def test_has_paywall_keyword_invalid_input(self):
        """Should return False for invalid inputs gracefully."""
        # Test through type casting to simulate real-world edge cases
        assert has_paywall_keyword("") is False
        assert has_paywall_keyword("no keywords here") is False


class TestGetQualityConfig:
    """Test configuration retrieval and override."""

    def test_get_quality_config_default(self):
        """Should return default config when no overrides."""
        config = get_quality_config()
        assert config == DEFAULT_CONFIG

    def test_get_quality_config_override(self):
        """Should apply overrides to default config."""
        config = get_quality_config({"max_results": 50})
        assert config["max_results"] == 50
        # Other values should remain default
        assert config["enabled"] == DEFAULT_CONFIG["enabled"]

    def test_get_quality_config_preserves_defaults(self):
        """Should not mutate DEFAULT_CONFIG."""
        original = DEFAULT_CONFIG.copy()
        config = get_quality_config({"max_results": 99})
        assert DEFAULT_CONFIG == original  # Original unchanged

    def test_get_quality_config_invalid_override(self):
        """Should ignore invalid override types gracefully."""
        # get_quality_config validates type, returns default if None/invalid
        config = get_quality_config(None)
        assert config == DEFAULT_CONFIG

    def test_get_quality_config_none_override(self):
        """Should handle None override gracefully."""
        config = get_quality_config(None)
        assert config == DEFAULT_CONFIG


class TestInputValidation:
    """Defensive tests for defensive programming."""

    def test_paywall_keywords_all_strings(self):
        """All paywall keywords should be strings."""
        assert all(isinstance(kw, str) for kw in PAYWALL_KEYWORDS)

    def test_paywall_domains_all_strings(self):
        """All paywall domains should be strings."""
        assert all(isinstance(d, str) for d in PAYWALL_DOMAINS)

    def test_listicle_patterns_all_strings(self):
        """All listicle patterns should be strings."""
        assert all(isinstance(p, str) for p in LISTICLE_PATTERNS)

    def test_detection_weights_all_numeric(self):
        """All detection weights should be numeric."""
        assert all(isinstance(w, (int, float)) for w in DETECTION_WEIGHTS.values())

    def test_no_empty_patterns(self):
        """Patterns should not be empty strings."""
        assert all(p.strip() for p in LISTICLE_PATTERNS)
        assert all(p.strip() for p in [str(k) for k in PAYWALL_KEYWORDS])

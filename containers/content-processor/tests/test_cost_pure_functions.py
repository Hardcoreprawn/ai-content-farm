"""
Tests for pure functional cost calculation.

Black box testing: validates inputs and outputs only, not implementation.

Contract Version: 1.0.0
"""

import pytest
from cost_calculator import (
    DEFAULT_PRICING,
    calculate_cost_breakdown,
    calculate_model_cost,
    calculate_token_cost,
    estimate_total_tokens,
    get_model_pricing,
)


class TestCalculateTokenCost:
    """Test basic token cost calculation."""

    def test_zero_tokens(self):
        """Zero tokens returns zero cost."""
        assert calculate_token_cost(0, 0, 0.001, 0.002) == 0.0

    def test_input_tokens_only(self):
        """Input tokens only calculates correctly."""
        cost = calculate_token_cost(1000, 0, 0.001, 0.002)
        assert cost == 0.001

    def test_output_tokens_only(self):
        """Output tokens only calculates correctly."""
        cost = calculate_token_cost(0, 1000, 0.001, 0.002)
        assert cost == 0.002

    def test_combined_tokens(self):
        """Combined input and output tokens calculates correctly."""
        cost = calculate_token_cost(1000, 500, 0.0005, 0.0015)
        assert cost == 0.00125

    def test_large_token_count(self):
        """Large token counts calculate correctly."""
        cost = calculate_token_cost(100000, 50000, 0.001, 0.002)
        assert cost == 0.2

    def test_fractional_pricing(self):
        """Fractional pricing works correctly."""
        cost = calculate_token_cost(1500, 750, 0.0005, 0.0015)
        assert abs(cost - 0.001875) < 0.000001

    def test_negative_input_tokens_raises_error(self):
        """Negative input tokens raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_token_cost(-100, 0, 0.001, 0.002)

    def test_negative_output_tokens_raises_error(self):
        """Negative output tokens raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_token_cost(0, -100, 0.001, 0.002)

    def test_negative_input_price_raises_error(self):
        """Negative input price raises ValueError."""
        with pytest.raises(ValueError, match="Prices must be non-negative"):
            calculate_token_cost(100, 0, -0.001, 0.002)

    def test_negative_output_price_raises_error(self):
        """Negative output price raises ValueError."""
        with pytest.raises(ValueError, match="Prices must be non-negative"):
            calculate_token_cost(0, 100, 0.001, -0.002)


class TestGetModelPricing:
    """Test model pricing retrieval."""

    def test_gpt_35_turbo_pricing(self):
        """GPT-3.5-turbo returns correct pricing."""
        pricing = get_model_pricing("gpt-35-turbo")
        assert pricing["input_per_1k"] == 0.0005
        assert pricing["output_per_1k"] == 0.0015

    def test_gpt_4_pricing(self):
        """GPT-4 returns correct pricing."""
        pricing = get_model_pricing("gpt-4")
        assert pricing["input_per_1k"] == 0.01
        assert pricing["output_per_1k"] == 0.03

    def test_gpt_4o_pricing(self):
        """GPT-4o returns correct pricing."""
        pricing = get_model_pricing("gpt-4o")
        assert pricing["input_per_1k"] == 0.0025
        assert pricing["output_per_1k"] == 0.01

    def test_embedding_model_pricing(self):
        """Embedding model returns correct pricing."""
        pricing = get_model_pricing("text-embedding-ada-002")
        assert pricing["input_per_1k"] == 0.0001
        assert pricing["output_per_1k"] == 0.0

    def test_unknown_model_fallback(self):
        """Unknown model falls back to gpt-35-turbo pricing."""
        pricing = get_model_pricing("unknown-model-xyz")
        assert pricing["input_per_1k"] == 0.0005
        assert pricing["output_per_1k"] == 0.0015

    def test_custom_pricing(self):
        """Custom pricing overrides defaults."""
        custom = {"custom-model": {"input_per_1k": 0.005, "output_per_1k": 0.01}}
        pricing = get_model_pricing("custom-model", custom)
        assert pricing["input_per_1k"] == 0.005
        assert pricing["output_per_1k"] == 0.01

    def test_default_pricing_constant_exists(self):
        """DEFAULT_PRICING constant is accessible and has expected models."""
        assert "gpt-35-turbo" in DEFAULT_PRICING
        assert "gpt-4" in DEFAULT_PRICING
        assert "gpt-4o" in DEFAULT_PRICING


class TestCalculateModelCost:
    """Test model-specific cost calculation."""

    def test_gpt_35_turbo_cost(self):
        """GPT-3.5-turbo calculates correct cost."""
        cost = calculate_model_cost("gpt-35-turbo", 1000, 500)
        assert cost == 0.00125

    def test_gpt_4_cost(self):
        """GPT-4 calculates correct cost."""
        cost = calculate_model_cost("gpt-4", 1000, 500)
        assert cost == 0.025

    def test_gpt_4o_cost(self):
        """GPT-4o calculates correct cost."""
        cost = calculate_model_cost("gpt-4o", 2000, 1000)
        assert cost == 0.015

    def test_embedding_cost(self):
        """Embedding model calculates correct cost (no output cost)."""
        cost = calculate_model_cost("text-embedding-ada-002", 10000, 0)
        assert cost == 0.001

    def test_unknown_model_with_fallback(self):
        """Unknown model uses fallback pricing."""
        cost = calculate_model_cost("unknown-model", 1000, 500)
        assert cost == 0.00125  # Same as gpt-35-turbo

    def test_zero_cost_for_zero_tokens(self):
        """Zero tokens returns zero cost regardless of model."""
        cost = calculate_model_cost("gpt-4", 0, 0)
        assert cost == 0.0

    def test_negative_tokens_raises_error(self):
        """Negative tokens raises ValueError."""
        with pytest.raises(ValueError):
            calculate_model_cost("gpt-35-turbo", -100, 500)

    def test_custom_pricing_in_model_cost(self):
        """Custom pricing works with calculate_model_cost."""
        custom = {"test-model": {"input_per_1k": 0.01, "output_per_1k": 0.02}}
        cost = calculate_model_cost("test-model", 1000, 500, custom)
        assert cost == 0.02


class TestEstimateTotalTokens:
    """Test total token calculation."""

    def test_zero_tokens(self):
        """Zero tokens returns zero."""
        assert estimate_total_tokens(0, 0) == 0

    def test_input_only(self):
        """Input tokens only returns correct total."""
        assert estimate_total_tokens(1000, 0) == 1000

    def test_output_only(self):
        """Output tokens only returns correct total."""
        assert estimate_total_tokens(0, 500) == 500

    def test_combined_tokens(self):
        """Combined tokens returns sum."""
        assert estimate_total_tokens(1000, 500) == 1500

    def test_large_numbers(self):
        """Large token counts work correctly."""
        assert estimate_total_tokens(1000000, 500000) == 1500000

    def test_negative_input_raises_error(self):
        """Negative input tokens raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            estimate_total_tokens(-100, 500)

    def test_negative_output_raises_error(self):
        """Negative output tokens raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            estimate_total_tokens(100, -500)


class TestCalculateCostBreakdown:
    """Test detailed cost breakdown."""

    def test_breakdown_structure(self):
        """Breakdown returns all expected fields."""
        breakdown = calculate_cost_breakdown("gpt-35-turbo", 1000, 500)
        assert "input_cost" in breakdown
        assert "output_cost" in breakdown
        assert "total_cost" in breakdown
        assert "total_tokens" in breakdown
        assert "input_tokens" in breakdown
        assert "output_tokens" in breakdown

    def test_breakdown_values_gpt_35(self):
        """GPT-3.5-turbo breakdown has correct values."""
        breakdown = calculate_cost_breakdown("gpt-35-turbo", 1000, 500)
        assert breakdown["input_cost"] == 0.0005
        assert breakdown["output_cost"] == 0.00075
        assert breakdown["total_cost"] == 0.00125
        assert breakdown["total_tokens"] == 1500
        assert breakdown["input_tokens"] == 1000
        assert breakdown["output_tokens"] == 500

    def test_breakdown_values_gpt_4(self):
        """GPT-4 breakdown has correct values."""
        breakdown = calculate_cost_breakdown("gpt-4", 2000, 1000)
        assert breakdown["input_cost"] == 0.02
        assert breakdown["output_cost"] == 0.03
        assert breakdown["total_cost"] == 0.05
        assert breakdown["total_tokens"] == 3000

    def test_breakdown_zero_tokens(self):
        """Zero tokens returns zero costs."""
        breakdown = calculate_cost_breakdown("gpt-35-turbo", 0, 0)
        assert breakdown["input_cost"] == 0.0
        assert breakdown["output_cost"] == 0.0
        assert breakdown["total_cost"] == 0.0
        assert breakdown["total_tokens"] == 0

    def test_breakdown_with_custom_pricing(self):
        """Custom pricing works in breakdown."""
        custom = {"test": {"input_per_1k": 0.002, "output_per_1k": 0.004}}
        breakdown = calculate_cost_breakdown("test", 1000, 500, custom)
        assert breakdown["input_cost"] == 0.002
        assert breakdown["output_cost"] == 0.002
        assert breakdown["total_cost"] == 0.004

    def test_breakdown_negative_tokens_raises_error(self):
        """Negative tokens raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_cost_breakdown("gpt-35-turbo", -100, 500)


class TestPurityAndDeterminism:
    """Test that functions are pure (deterministic, no side effects)."""

    def test_token_cost_determinism(self):
        """Same inputs always produce same output."""
        cost1 = calculate_token_cost(1000, 500, 0.001, 0.002)
        cost2 = calculate_token_cost(1000, 500, 0.001, 0.002)
        assert cost1 == cost2

    def test_model_pricing_determinism(self):
        """Same model always returns same pricing."""
        pricing1 = get_model_pricing("gpt-4o")
        pricing2 = get_model_pricing("gpt-4o")
        assert pricing1 == pricing2

    def test_model_cost_determinism(self):
        """Same inputs always produce same cost."""
        cost1 = calculate_model_cost("gpt-35-turbo", 1000, 500)
        cost2 = calculate_model_cost("gpt-35-turbo", 1000, 500)
        assert cost1 == cost2

    def test_total_tokens_determinism(self):
        """Same inputs always produce same total."""
        total1 = estimate_total_tokens(1000, 500)
        total2 = estimate_total_tokens(1000, 500)
        assert total1 == total2

    def test_breakdown_determinism(self):
        """Same inputs always produce same breakdown."""
        breakdown1 = calculate_cost_breakdown("gpt-4", 2000, 1000)
        breakdown2 = calculate_cost_breakdown("gpt-4", 2000, 1000)
        assert breakdown1 == breakdown2

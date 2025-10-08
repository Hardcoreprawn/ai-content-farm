"""
Pure functional cost calculation for OpenAI API usage.

This module provides stateless functions for calculating costs based on
token usage and model pricing.

Contract Version: 1.0.0
"""

from typing import Dict, Optional

# Model pricing constants (UK South region, updated Sept 2025)
DEFAULT_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-35-turbo": {
        "input_per_1k": 0.0005,  # $0.50 per 1M tokens
        "output_per_1k": 0.0015,  # $1.50 per 1M tokens
    },
    "gpt-4": {
        "input_per_1k": 0.01,  # $10 per 1M tokens
        "output_per_1k": 0.03,  # $30 per 1M tokens
    },
    "gpt-4o": {
        "input_per_1k": 0.0025,  # $2.50 per 1M tokens
        "output_per_1k": 0.01,  # $10 per 1M tokens
    },
    "text-embedding-ada-002": {
        "input_per_1k": 0.0001,  # $0.10 per 1M tokens
        "output_per_1k": 0.0,  # No output cost for embeddings
    },
}


def calculate_token_cost(
    input_tokens: int,
    output_tokens: int,
    input_price_per_1k: float,
    output_price_per_1k: float,
) -> float:
    """
    Calculate cost for token usage given pricing rates.

    Pure function with no side effects. Calculates cost based on the formula:
    cost = (input_tokens / 1000 * input_price) + (output_tokens / 1000 * output_price)

    Args:
        input_tokens: Number of input tokens used (must be >= 0)
        output_tokens: Number of output tokens generated (must be >= 0)
        input_price_per_1k: Cost per 1000 input tokens in USD (must be >= 0)
        output_price_per_1k: Cost per 1000 output tokens in USD (must be >= 0)

    Returns:
        float: Total cost in USD, rounded to 6 decimal places

    Raises:
        ValueError: If any value is negative

    Examples:
        >>> calculate_token_cost(1000, 500, 0.0005, 0.0015)
        0.0013
        >>> calculate_token_cost(0, 0, 0.01, 0.03)
        0.0
        >>> calculate_token_cost(-100, 0, 0.01, 0.03)
        Traceback (most recent call last):
        ...
        ValueError: Token counts must be non-negative
    """
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("Token counts must be non-negative")

    if input_price_per_1k < 0 or output_price_per_1k < 0:
        raise ValueError("Prices must be non-negative")

    input_cost = (input_tokens / 1000) * input_price_per_1k
    output_cost = (output_tokens / 1000) * output_price_per_1k
    total_cost = input_cost + output_cost

    return round(total_cost, 6)


def get_model_pricing(
    model_name: str, custom_pricing: Optional[Dict[str, Dict[str, float]]] = None
) -> Dict[str, float]:
    """
    Get pricing information for a specific model.

    Pure function that returns pricing data from either custom pricing
    or default pricing constants.

    Args:
        model_name: Name of the OpenAI model (e.g., "gpt-4o", "gpt-35-turbo")
        custom_pricing: Optional custom pricing dictionary to use instead of defaults

    Returns:
        Dict with "input_per_1k" and "output_per_1k" pricing rates

    Examples:
        >>> pricing = get_model_pricing("gpt-35-turbo")
        >>> pricing["input_per_1k"]
        0.0005
        >>> pricing = get_model_pricing("unknown-model")
        >>> pricing["input_per_1k"]  # Falls back to gpt-35-turbo
        0.0005
    """
    pricing_source = custom_pricing if custom_pricing is not None else DEFAULT_PRICING

    # Try exact match first
    if model_name in pricing_source:
        return pricing_source[model_name]

    # Fallback to gpt-35-turbo for unknown models
    return pricing_source.get(
        "gpt-35-turbo", {"input_per_1k": 0.0005, "output_per_1k": 0.0015}
    )


def calculate_model_cost(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    custom_pricing: Optional[Dict[str, Dict[str, float]]] = None,
) -> float:
    """
    Calculate cost for a specific model given token usage.

    Convenience function that combines get_model_pricing and calculate_token_cost.

    Args:
        model_name: Name of the OpenAI model
        input_tokens: Number of input tokens used (must be >= 0)
        output_tokens: Number of output tokens generated (must be >= 0)
        custom_pricing: Optional custom pricing to use instead of defaults

    Returns:
        float: Total cost in USD, rounded to 6 decimal places

    Raises:
        ValueError: If token counts are negative

    Examples:
        >>> calculate_model_cost("gpt-35-turbo", 1000, 500)
        0.0013
        >>> calculate_model_cost("gpt-4o", 2000, 1000)
        0.015
        >>> calculate_model_cost("unknown-model", 1000, 500)  # Uses gpt-35-turbo fallback
        0.0013
    """
    pricing = get_model_pricing(model_name, custom_pricing)

    return calculate_token_cost(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_price_per_1k=pricing["input_per_1k"],
        output_price_per_1k=pricing["output_per_1k"],
    )


def estimate_total_tokens(input_tokens: int, output_tokens: int) -> int:
    """
    Calculate total token usage.

    Simple utility function for calculating total tokens used in a request.

    Args:
        input_tokens: Number of input tokens (must be >= 0)
        output_tokens: Number of output tokens (must be >= 0)

    Returns:
        int: Total tokens used

    Raises:
        ValueError: If any value is negative

    Examples:
        >>> estimate_total_tokens(1000, 500)
        1500
        >>> estimate_total_tokens(0, 0)
        0
    """
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("Token counts must be non-negative")

    return input_tokens + output_tokens


def calculate_cost_breakdown(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    custom_pricing: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, float]:
    """
    Calculate detailed cost breakdown for token usage.

    Returns comprehensive cost information including separate input/output costs.

    Args:
        model_name: Name of the OpenAI model
        input_tokens: Number of input tokens used (must be >= 0)
        output_tokens: Number of output tokens generated (must be >= 0)
        custom_pricing: Optional custom pricing to use instead of defaults

    Returns:
        Dict containing:
            - input_cost: Cost for input tokens
            - output_cost: Cost for output tokens
            - total_cost: Combined cost
            - total_tokens: Total token count
            - input_tokens: Input token count (for reference)
            - output_tokens: Output token count (for reference)

    Raises:
        ValueError: If token counts are negative

    Examples:
        >>> breakdown = calculate_cost_breakdown("gpt-35-turbo", 1000, 500)
        >>> breakdown["input_cost"]
        0.0005
        >>> breakdown["output_cost"]
        0.00075
        >>> breakdown["total_cost"]
        0.00125
    """
    pricing = get_model_pricing(model_name, custom_pricing)

    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("Token counts must be non-negative")

    input_cost = round((input_tokens / 1000) * pricing["input_per_1k"], 6)
    output_cost = round((output_tokens / 1000) * pricing["output_per_1k"], 6)
    total_cost = round(input_cost + output_cost, 6)
    total_tokens = input_tokens + output_tokens

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
        "total_tokens": total_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }

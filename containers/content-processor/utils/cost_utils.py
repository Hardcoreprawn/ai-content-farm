"""
Cost calculation utilities for Azure OpenAI API

Simple, inline cost calculations without external dependencies.
Pricing based on UK South region, updated October 2025.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Azure OpenAI pricing (UK South region, Oct 2025)
# Source: https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/
OPENAI_PRICING: Dict[str, Dict[str, float]] = {
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
    "gpt-4o-mini": {
        "input_per_1k": 0.00015,  # $0.15 per 1M tokens
        "output_per_1k": 0.0006,  # $0.60 per 1M tokens
    },
}


def calculate_openai_cost(
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """
    Calculate Azure OpenAI API cost in USD.

    Pure function - no external dependencies, no async overhead.

    Args:
        model_name: Model identifier (e.g., "gpt-35-turbo", "gpt-4")
        prompt_tokens: Number of input/prompt tokens
        completion_tokens: Number of output/completion tokens

    Returns:
        Total cost in USD

    Examples:
        >>> calculate_openai_cost("gpt-35-turbo", 1000, 500)
        0.00125

        >>> calculate_openai_cost("gpt-4", 500, 1500)
        0.05
    """
    try:
        # Get pricing for model (default to gpt-35-turbo if unknown)
        pricing = OPENAI_PRICING.get(model_name, OPENAI_PRICING["gpt-35-turbo"])

        # Calculate costs
        input_cost = (prompt_tokens / 1000) * pricing["input_per_1k"]
        output_cost = (completion_tokens / 1000) * pricing["output_per_1k"]
        total_cost = input_cost + output_cost

        logger.debug(
            f"Cost: {model_name} - "
            f"{prompt_tokens} input + {completion_tokens} output = "
            f"${total_cost:.6f}"
        )

        return total_cost

    except Exception as e:
        logger.error(f"Error calculating cost: {e}")
        # Emergency fallback - approximate average cost
        return (prompt_tokens + completion_tokens) / 1000 * 0.002


def get_model_pricing(model_name: str) -> Dict[str, float]:
    """
    Get pricing information for a specific model.

    Args:
        model_name: Model identifier

    Returns:
        Dict with input_per_1k and output_per_1k rates
    """
    return OPENAI_PRICING.get(model_name, OPENAI_PRICING["gpt-35-turbo"])

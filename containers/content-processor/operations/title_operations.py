"""
Pure functional title generation operations.

All functions are pure and async where needed - no side effects, deterministic outputs.
Follows the established pattern from article_operations.py.
"""

import logging
import re
from typing import Optional, Tuple

from openai import AsyncAzureOpenAI
from utils.cost_utils import calculate_openai_cost

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

MAX_TITLE_LENGTH = 80
TITLE_MODEL = "gpt-4o-mini"  # Cost-optimized: $0.000035/title
TITLE_MAX_TOKENS = 25  # Titles are short
TITLE_TEMPERATURE = 0.7  # Balanced creativity


# ============================================================================
# Title Cleaning (Pure Functions)
# ============================================================================


def has_date_prefix(title: str) -> bool:
    """
    Check if title has date prefix like "(15 Oct)".

    Pure function - deterministic output.

    Args:
        title: Title to check

    Returns:
        True if title starts with date prefix

    Examples:
        >>> has_date_prefix("(15 Oct) Article Title")
        True
        >>> has_date_prefix("Article Title")
        False
        >>> has_date_prefix("(2025-10-15) News")
        True
    """
    # Match patterns: (15 Oct), (Oct 15), (2025-10-15), etc.
    date_patterns = [
        r"^\(\d{1,2}\s+\w{3}\)",  # (15 Oct)
        r"^\(\w{3}\s+\d{1,2}\)",  # (Oct 15)
        r"^\(\d{4}-\d{2}-\d{2}\)",  # (2025-10-15)
        r"^\[\d{1,2}\s+\w{3}\]",  # [15 Oct]
    ]

    return any(re.match(pattern, title) for pattern in date_patterns)


def remove_date_prefix(title: str) -> str:
    """
    Remove date prefix from title if present.

    Pure function - deterministic output.

    Args:
        title: Title to clean

    Returns:
        Title with date prefix removed

    Examples:
        >>> remove_date_prefix("(15 Oct) Article Title")
        'Article Title'
        >>> remove_date_prefix("Article Title")
        'Article Title'
    """
    # Remove all date prefix patterns
    date_patterns = [
        r"^\(\d{1,2}\s+\w{3}\)\s*",
        r"^\(\w{3}\s+\d{1,2}\)\s*",
        r"^\(\d{4}-\d{2}-\d{2}\)\s*",
        r"^\[\d{1,2}\s+\w{3}\]\s*",
    ]

    cleaned = title
    for pattern in date_patterns:
        cleaned = re.sub(pattern, "", cleaned)

    return cleaned.strip()


def is_truncated(title: str) -> bool:
    """
    Check if title appears truncated.

    Pure function - checks for truncation indicators.

    Args:
        title: Title to check

    Returns:
        True if title appears truncated

    Examples:
        >>> is_truncated("This is a long title that...")
        True
        >>> is_truncated("This is a complete title")
        False
        >>> is_truncated("Title ending with ht")
        True
    """
    # Check for common truncation indicators
    truncation_indicators = [
        r"\.\.\.?\s*$",  # Ends with ... or ..
        r"\s+ht$",  # Ends with " ht" (truncated https)
        r"\s+https?$",  # Ends with " http" or " https"
        r"\s[a-z]$",  # Ends with space + single lowercase letter (suspicious)
    ]

    return any(re.search(pattern, title) for pattern in truncation_indicators)


def needs_ai_generation(title: str) -> bool:
    """
    Determine if title needs AI generation.

    Pure function - deterministic decision based on title characteristics.

    Args:
        title: Title to check

    Returns:
        True if AI generation should be used

    Examples:
        >>> needs_ai_generation("(15 Oct) Short")
        True
        >>> needs_ai_generation("Clear Complete Title")
        False
        >>> needs_ai_generation("This is a very long title that exceeds the maximum length limit...")
        True
    """
    # Need AI if:
    # 1. Has date prefix (but not after removal)
    # 2. Appears truncated
    # 3. Too long
    # 4. Too short (likely truncated metadata)

    # Check the cleaned version (without date prefix)
    cleaned = remove_date_prefix(title)

    if is_truncated(cleaned):
        return True

    if len(cleaned) > MAX_TITLE_LENGTH:
        return True

    if len(cleaned) < 15:  # Suspiciously short (but not catching normal titles)
        return True

    return False


# ============================================================================
# AI Title Generation
# ============================================================================


async def generate_clean_title(
    original_title: str,
    content_summary: str,
    azure_openai_client: AsyncAzureOpenAI,
) -> Tuple[str, float]:
    """
    Generate clean, concise title using AI if needed.

    Pure async function with explicit dependencies.

    Rules:
    1. If title < 80 chars and no issues: return cleaned version (no AI cost)
    2. If title has date prefix: remove it first, check again
    3. If title > 80 chars or truncated: use AI to create concise version
    4. Never truncate mid-word

    Args:
        original_title: Original title from source
        content_summary: Article content summary (first ~500 chars)
        azure_openai_client: Configured Azure OpenAI client

    Returns:
        Tuple[cleaned_title, cost_usd]

    Examples:
        >>> client = await create_openai_client("https://my-resource.openai.azure.com")
        >>> title, cost = await generate_clean_title(
        ...     "(15 Oct) Short Title",
        ...     "Article summary...",
        ...     client
        ... )
        >>> title
        'Short Title'
        >>> cost
        0.0
    """
    try:
        # First, remove any date prefixes
        cleaned = remove_date_prefix(original_title)

        # If clean enough after prefix removal, return it (no AI cost)
        if not needs_ai_generation(cleaned):
            logger.info(f"Title already clean, no AI needed: {cleaned[:50]}")
            return cleaned, 0.0

        # Use AI to generate concise title
        logger.info(
            f"Generating clean title with {TITLE_MODEL} for: {original_title[:50]}..."
        )

        response = await azure_openai_client.chat.completions.create(
            model=TITLE_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional editor. Create concise, engaging article titles without date prefixes.",
                },
                {
                    "role": "user",
                    "content": f"""Generate a concise title (max {MAX_TITLE_LENGTH} characters):

Original: {original_title}
Content: {content_summary[:200]}

Requirements:
- Maximum {MAX_TITLE_LENGTH} characters
- Remove date prefixes like (15 Oct) or [Oct 15]
- Clear and engaging
- No truncation with "..."
- SEO-friendly
- Professional tone""",
                },
            ],
            max_tokens=TITLE_MAX_TOKENS,
            temperature=TITLE_TEMPERATURE,
        )

        # Defensive: Check response structure
        if not response.choices or not response.choices[0].message.content:
            raise ValueError("Empty response from OpenAI API")

        if not response.usage:
            raise ValueError("Missing usage data from OpenAI API")

        # Calculate cost for tracking
        cost = calculate_openai_cost(
            model_name=TITLE_MODEL,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )

        clean_title = response.choices[0].message.content.strip()

        # Remove any quotes that AI might add
        clean_title = clean_title.strip("\"'")

        # Ensure title isn't too long (safety check)
        if len(clean_title) > MAX_TITLE_LENGTH:
            clean_title = clean_title[:MAX_TITLE_LENGTH].rsplit(" ", 1)[0].strip()

        logger.info(
            f"Generated title: {clean_title} (cost: ${cost:.6f}, "
            f"tokens: {response.usage.prompt_tokens}+{response.usage.completion_tokens})"
        )

        # Calculate cost for tracking
        cost = calculate_openai_cost(
            model_name=TITLE_MODEL,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )

        clean_title = response.choices[0].message.content.strip()

        # Remove any quotes that AI might add
        clean_title = clean_title.strip("\"'")

        # Ensure title isn't too long (safety check)
        if len(clean_title) > MAX_TITLE_LENGTH:
            clean_title = clean_title[:MAX_TITLE_LENGTH].rsplit(" ", 1)[0].strip()

        logger.info(
            f"Generated title: {clean_title} (cost: ${cost:.6f}, "
            f"tokens: {response.usage.prompt_tokens}+{response.usage.completion_tokens})"
        )

        return clean_title, cost

    except Exception as e:
        logger.error(f"Title generation failed: {e}, using cleaned original")
        # Fallback: return cleaned original title
        cleaned = remove_date_prefix(original_title)
        if len(cleaned) > MAX_TITLE_LENGTH:
            cleaned = cleaned[:MAX_TITLE_LENGTH].rsplit(" ", 1)[0].strip()
        return cleaned, 0.0


def build_title_prompt(original_title: str, content_summary: str) -> str:
    """
    Build prompt for title generation.

    Pure function - deterministic output from inputs.
    Separated for testing.

    Args:
        original_title: Original title
        content_summary: Content summary

    Returns:
        Formatted prompt string
    """
    return f"""Generate a concise title (max {MAX_TITLE_LENGTH} characters):

Original: {original_title}
Content: {content_summary[:200]}

Requirements:
- Maximum {MAX_TITLE_LENGTH} characters
- Remove date prefixes like (15 Oct) or [Oct 15]
- Clear and engaging
- No truncation with "..."
- SEO-friendly
- Professional tone"""

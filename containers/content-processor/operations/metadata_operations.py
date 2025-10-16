"""
Pure functional metadata generation operations.

All functions are pure - no side effects, deterministic outputs.
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from aiolimiter import AsyncLimiter
from models import TopicMetadata
from openai import AsyncAzureOpenAI
from operations.openai_operations import generate_completion
from operations.title_operations import generate_clean_title
from utils.cost_utils import calculate_openai_cost

from libs.openai_rate_limiter import call_with_rate_limit

logger = logging.getLogger(__name__)


# ============================================================================
# Metadata Generation
# ============================================================================


async def generate_metadata_with_cost(
    openai_client: AsyncAzureOpenAI,
    title: str,
    content_preview: str,
    published_date: str,
    config: Dict[str, str],
    rate_limiter: Optional[AsyncLimiter] = None,
) -> Dict[str, Any]:
    """
    Generate SEO metadata for article with AI title generation.

    Pure async function.

    Args:
        openai_client: Configured Azure OpenAI client
        title: Original article title
        content_preview: First 500 chars of content
        published_date: ISO format date string
        config: OpenAI config (model_name, etc)
        rate_limiter: Optional rate limiter

    Returns:
        Dict with title, slug, filename, url, cost_usd, tokens_used
    """
    try:
        total_cost = 0.0
        total_tokens = 0

        # Step 1: Generate clean title (removes date prefixes, handles truncation)
        clean_title_result, title_cost = await generate_clean_title(
            original_title=title,
            content_summary=content_preview,
            azure_openai_client=openai_client,
        )
        total_cost += title_cost

        if title_cost > 0:
            logger.info(
                f"AI title generation used: ${title_cost:.6f} - "
                f"'{title[:50]}...' -> '{clean_title_result}'"
            )

        # Step 2: Check if translation needed (for non-English content)
        needs_translation = detect_non_english_or_hashtags(clean_title_result)

        if needs_translation:
            # Generate AI metadata (translation + SEO description)
            ai_metadata, prompt_tokens, completion_tokens = await generate_ai_metadata(
                openai_client, clean_title_result, content_preview, config, rate_limiter
            )

            seo_title = ai_metadata["title"]
            description = ai_metadata["description"]
            language = ai_metadata["language"]

            # Calculate additional cost for translation
            translation_cost = calculate_openai_cost(
                model_name=config["model_name"],
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
            total_cost += translation_cost
            total_tokens = prompt_tokens + completion_tokens
        else:
            # No translation needed - use cleaned title
            seo_title = clean_title_result
            description = f"{seo_title[:140]}..."  # Simple description
            language = "en"

        # Generate slug, filename, URL
        slug = create_slug(seo_title)
        filename = create_filename(slug, published_date)
        url = create_url(filename)

        return {
            "original_title": title,
            "title": seo_title,
            "description": description,
            "language": language,
            "slug": slug,
            "filename": filename,
            "url": url,
            "cost_usd": total_cost,
            "tokens_used": total_tokens,
        }

    except Exception as e:
        logger.error(f"Metadata generation failed: {e}")
        # Fallback to simple cleaning
        slug = create_slug(title)
        filename = create_filename(slug, published_date)
        return {
            "original_title": title,
            "title": clean_title_text(title),
            "description": f"{title[:140]}...",
            "language": "en",
            "slug": slug,
            "filename": filename,
            "url": create_url(filename),
            "cost_usd": 0.0,
            "tokens_used": 0,
        }


async def generate_ai_metadata(
    openai_client: AsyncAzureOpenAI,
    title: str,
    content_preview: str,
    config: Dict[str, str],
    rate_limiter: Optional[AsyncLimiter] = None,
) -> Tuple[Dict[str, str], int, int]:
    """
    Generate AI-powered metadata (translation + SEO).

    Pure async function.

    Args:
        openai_client: Configured Azure OpenAI client
        title: Cleaned title
        content_preview: Content preview
        config: OpenAI config
        rate_limiter: Optional rate limiter

    Returns:
        Tuple[metadata_dict, prompt_tokens, completion_tokens]
    """
    prompt = f"""Article Title: {title}

Content Preview: {content_preview}

Generate:
1. Clean engaging title (45-60 characters, no hashtags/emoji/special chars)
2. SEO description (140-160 characters)

Return ONLY valid JSON:
{{"title": "...", "description": "...", "language": "en"}}"""

    # Generate with rate limiting if configured
    if rate_limiter:
        result_content, prompt_tokens, completion_tokens = await call_with_rate_limit(
            rate_limiter,
            generate_completion,
            client=openai_client,
            model_name=config["model_name"],
            prompt=prompt,
            max_tokens=200,
            temperature=0.3,
        )
    else:
        result_content, prompt_tokens, completion_tokens = await generate_completion(
            client=openai_client,
            model_name=config["model_name"],
            prompt=prompt,
            max_tokens=200,
            temperature=0.3,
        )

    if not result_content:
        raise ValueError("No content returned from OpenAI")

    # Parse JSON response
    result_text = result_content.strip()

    # Extract JSON if wrapped in markdown code blocks
    if "```json" in result_text:
        result_text = result_text.split("```json")[1].split("```")[0].strip()
    elif "```" in result_text:
        result_text = result_text.split("```")[1].split("```")[0].strip()

    metadata = json.loads(result_text)

    # Validate required fields
    required_fields = ["title", "description", "language"]
    for field in required_fields:
        if field not in metadata:
            raise ValueError(f"Missing required field: {field}")

    # Truncate if needed
    if len(metadata["title"]) > 70:
        metadata["title"] = metadata["title"][:60].rsplit(" ", 1)[0]

    if len(metadata["description"]) > 170:
        metadata["description"] = metadata["description"][:160].rsplit(" ", 1)[0]

    return metadata, prompt_tokens, completion_tokens


# ============================================================================
# Text Processing - Pure Functions
# ============================================================================


def clean_title_text(title: str) -> str:
    """
    Clean title by removing hashtags and special characters.

    Pure function.

    Args:
        title: Original title

    Returns:
        Cleaned title
    """
    # Remove hashtags
    title = re.sub(r"#\w+", "", title)

    # Remove emoji and special Unicode characters
    title = re.sub(r"[^\w\s\-.,!?()]", "", title)

    # Normalize whitespace
    title = " ".join(title.split())

    return title.strip()


def detect_non_english_or_hashtags(title: str) -> bool:
    """
    Detect if title needs AI processing (non-English or has hashtags).

    Pure function.

    Args:
        title: Title to check

    Returns:
        True if needs AI processing
    """
    # Check for hashtags
    if "#" in title:
        return True

    # Check for non-ASCII characters (indicates non-English)
    if not all(ord(c) < 128 for c in title):
        return True

    # Check for Japanese, Chinese, Korean characters
    if re.search(
        r"[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uff9f\u4e00-\u9faf\u3400-\u4dbf\uac00-\ud7a3]",
        title,
    ):
        return True

    return False


def create_slug(title: str) -> str:
    """
    Create URL-safe slug from title.

    Pure function.

    Args:
        title: Title to slugify

    Returns:
        URL-safe slug (kebab-case)
    """
    # Lowercase
    slug = title.lower()

    # Remove special characters
    slug = re.sub(r"[^\w\s-]", "", slug)

    # Replace whitespace with hyphens
    slug = re.sub(r"[-\s]+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    # Truncate to reasonable length
    if len(slug) > 100:
        slug = slug[:100].rsplit("-", 1)[0]

    return slug


def create_filename(slug: str, published_date: str) -> str:
    """
    Create filename from slug and date.

    Pure function.

    Args:
        slug: URL slug
        published_date: ISO format date string

    Returns:
        Filename (YYYY-MM-DD-slug.html)
    """
    try:
        # Parse date
        if isinstance(published_date, str):
            date_obj = datetime.fromisoformat(published_date.replace("Z", "+00:00"))
        else:
            date_obj = published_date

        date_str = date_obj.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        # Fallback to current date
        date_str = datetime.now().strftime("%Y-%m-%d")

    return f"{date_str}-{slug}.html"


def create_url(filename: str) -> str:
    """
    Create URL path from filename.

    Pure function.

    Args:
        filename: Article filename

    Returns:
        URL path (/articles/filename)
    """
    return f"/articles/{filename}"

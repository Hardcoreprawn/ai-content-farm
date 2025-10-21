"""
Pure functional content processing operations.

Orchestrates article generation pipeline using pure functions.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from models import TopicMetadata
from openai import AsyncAzureOpenAI
from operations.article_operations import generate_article_with_cost, get_openai_config
from operations.metadata_operations import generate_metadata_with_cost
from utils.rate_limiter import AsyncLimiter  # type: ignore[import]

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


def get_processing_config() -> Dict[str, Any]:
    """
    Get processing configuration from environment.

    Pure function - reads env vars once, returns dict.

    Returns:
        Dict with target_word_count, quality_threshold, etc.
    """
    import os

    return {
        "target_word_count": int(os.getenv("TARGET_WORD_COUNT", "3000")),
        "quality_threshold": float(os.getenv("QUALITY_THRESHOLD", "0.5")),
        "processor_version": os.getenv("PROCESSOR_VERSION", "2.0.0"),
    }


# ============================================================================
# Article Processing Pipeline
# ============================================================================


async def process_topic_to_article(
    openai_client: AsyncAzureOpenAI,
    topic_metadata: TopicMetadata,
    processor_id: str,
    session_id: str,
    rate_limiter: Optional[AsyncLimiter] = None,
) -> Optional[Dict[str, Any]]:
    """
    Process a topic into a complete article with metadata.

    Pure async function - coordinates article generation and metadata creation.

    Args:
        openai_client: Configured Azure OpenAI client
        topic_metadata: Topic to process
        processor_id: Processor identifier
        session_id: Session identifier
        rate_limiter: Optional rate limiter

    Returns:
        Complete article result dict or None on failure
    """
    start_time = datetime.now(timezone.utc)

    try:
        logger.info(
            f"PROCESSING: '{topic_metadata.title}' "
            f"(ID: {topic_metadata.topic_id}, priority: {topic_metadata.priority_score})"
        )

        # Get configuration
        openai_config = get_openai_config()
        processing_config = get_processing_config()

        # Generate article content
        article_content, prompt_tokens, completion_tokens, article_cost = (
            await generate_article_with_cost(
                openai_client=openai_client,
                topic_metadata=topic_metadata,
                config=openai_config,
                rate_limiter=rate_limiter,
            )
        )

        if not article_content:
            logger.error(f"ARTICLE-GENERATION: Failed for '{topic_metadata.title}'")
            return None

        logger.info(
            f"ARTICLE-GENERATION: '{topic_metadata.title}' - cost: ${article_cost:.6f}"
        )

        # Generate metadata (title translation, slug, SEO)
        content_preview = article_content[:500]
        published_date = datetime.now(timezone.utc).isoformat()

        metadata = await generate_metadata_with_cost(
            openai_client=openai_client,
            title=topic_metadata.title,
            content_preview=content_preview,
            published_date=published_date,
            config=openai_config,
            rate_limiter=rate_limiter,
        )

        # Calculate word count and quality
        word_count = len(article_content.split())
        quality_score = calculate_article_quality(
            article_content,
            word_count,
            processing_config["target_word_count"],
        )

        # Calculate total cost
        total_cost = article_cost + metadata.get("cost_usd", 0.0)
        total_tokens = (
            prompt_tokens + completion_tokens + metadata.get("tokens_used", 0)
        )
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        # Build complete result
        result = build_article_result(
            article_content=article_content,
            metadata=metadata,
            topic_metadata=topic_metadata,
            word_count=word_count,
            quality_score=quality_score,
            cost=total_cost,
            tokens_used=total_tokens,
            processing_time=processing_time,
            processor_id=processor_id,
            session_id=session_id,
            published_date=published_date,
            processing_config=processing_config,
        )

        logger.info(
            f"COMPLETE: '{metadata['title']}' - "
            f"{word_count} words, quality {quality_score:.2f}, "
            f"${total_cost:.6f}, {processing_time:.2f}s"
        )

        return result

    except Exception as e:
        logger.error(f"ERROR processing {topic_metadata.topic_id}: {e}")
        return None


# ============================================================================
# Quality Assessment
# ============================================================================


def calculate_article_quality(
    article_content: str,
    word_count: int,
    target_word_count: int,
) -> float:
    """
    Calculate article quality score.

    Pure function.

    Args:
        article_content: Generated article text
        word_count: Word count
        target_word_count: Target word count

    Returns:
        Quality score (0.0-1.0)
    """
    # Length score (70% - meets target word count)
    length_ratio = min(word_count / target_word_count, 1.5)
    if length_ratio < 0.8:
        length_score = length_ratio / 0.8 * 0.7
    elif length_ratio > 1.2:
        length_score = 0.7 * (1.0 - (length_ratio - 1.2) / 0.3)
    else:
        length_score = 0.7

    # Content structure score (30% - has paragraphs and sections)
    paragraphs = article_content.split("\n\n")
    paragraph_count = len([p for p in paragraphs if len(p.strip()) > 50])

    if paragraph_count >= 8:
        structure_score = 0.3
    elif paragraph_count >= 5:
        structure_score = 0.2
    else:
        structure_score = 0.1

    total_score = length_score + structure_score
    return min(total_score, 1.0)


def build_article_result(
    article_content: str,
    metadata: Dict[str, Any],
    topic_metadata: TopicMetadata,
    word_count: int,
    quality_score: float,
    cost: float,
    tokens_used: int,
    processing_time: float,
    processor_id: str,
    session_id: str,
    published_date: str,
    processing_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build complete article result structure.

    Pure function.

    Args:
        article_content: Generated article text
        metadata: SEO metadata dict
        topic_metadata: Source topic metadata
        word_count: Article word count
        quality_score: Calculated quality score
        cost: Total processing cost
        tokens_used: Total tokens consumed
        processing_time: Processing duration (seconds)
        processor_id: Processor identifier
        session_id: Session identifier
        published_date: ISO format date string
        processing_config: Processing configuration

    Returns:
        Complete article result dict ready for storage
    """
    return {
        "article_result": {
            "article_id": f"article_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "topic_id": topic_metadata.topic_id,
            "title": metadata["title"],
            "slug": metadata["slug"],
            "filename": metadata["filename"],
            "url": metadata["url"],
            "published_date": published_date,
            "language": metadata.get("language", "en"),
            "content": article_content,
            "word_count": word_count,
            "quality_score": quality_score,
            "source_metadata": {
                "source": topic_metadata.source,
                "source_url": topic_metadata.url,
                "subreddit": topic_metadata.subreddit,
                "priority_score": topic_metadata.priority_score,
                "engagement": {
                    "upvotes": topic_metadata.upvotes,
                    "comments": topic_metadata.comments,
                },
                "original_title": metadata.get("original_title", topic_metadata.title),
                "collection_timestamp": topic_metadata.collected_at,
                "enhanced_metadata": topic_metadata.enhanced_metadata,
            },
            "processing_metadata": {
                "processor_id": processor_id,
                "session_id": session_id,
                "processor_version": processing_config.get(
                    "processor_version", "2.0.0"
                ),
                "processing_time_seconds": processing_time,
                "tokens_used": tokens_used,
                "cost_usd": cost,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            },
        },
        "article_content": article_content,
        "word_count": word_count,
        "quality_score": quality_score,
        "cost": cost,
        "metadata": metadata,
    }

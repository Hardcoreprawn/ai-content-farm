"""
Pure functional article generation operations.

All functions are pure - no side effects, deterministic outputs.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from aiolimiter import AsyncLimiter
from models import TopicMetadata
from openai import AsyncAzureOpenAI
from operations.openai_operations import generate_article_content
from utils.cost_utils import calculate_openai_cost

from libs.openai_rate_limiter import call_with_rate_limit

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


def get_openai_config() -> Dict[str, str]:
    """
    Get OpenAI configuration from environment.

    Pure function - reads environment only.

    Returns:
        Dict with endpoint, api_version, model_name
    """
    return {
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-07-01-preview"),
        "model_name": os.getenv("AZURE_OPENAI_CHAT_MODEL", "gpt-35-turbo"),
    }


# ============================================================================
# Article Generation
# ============================================================================


async def generate_article_with_cost(
    openai_client: AsyncAzureOpenAI,
    topic_metadata: TopicMetadata,
    config: Dict[str, str],
    rate_limiter: Optional[AsyncLimiter] = None,
) -> Tuple[Optional[str], int, int, float]:
    """
    Generate article content from topic with cost calculation.

    Pure async function.

    Args:
        openai_client: Configured Azure OpenAI client
        topic_metadata: Topic to generate article for
        config: OpenAI config (model_name, etc)
        rate_limiter: Optional rate limiter

    Returns:
        Tuple[content, prompt_tokens, completion_tokens, cost_usd]
        Returns (None, 0, 0, 0.0) on error
    """
    try:
        # Prepare research content
        research_content = prepare_research_content(topic_metadata)

        # Generate article with rate limiting if configured
        if rate_limiter:
            article_content, prompt_tokens, completion_tokens = (
                await call_with_rate_limit(
                    rate_limiter,
                    generate_article_content,
                    client=openai_client,
                    model_name=config["model_name"],
                    topic_title=topic_metadata.title,
                    research_content=research_content,
                    target_word_count=3000,
                    quality_requirements={
                        "source": topic_metadata.source,
                        "priority_score": topic_metadata.priority_score,
                        "engagement": f"{topic_metadata.upvotes or 0} upvotes, {topic_metadata.comments or 0} comments",
                    },
                )
            )
        else:
            article_content, prompt_tokens, completion_tokens = (
                await generate_article_content(
                    client=openai_client,
                    model_name=config["model_name"],
                    topic_title=topic_metadata.title,
                    research_content=research_content,
                    target_word_count=3000,
                    quality_requirements={
                        "source": topic_metadata.source,
                        "priority_score": topic_metadata.priority_score,
                        "engagement": f"{topic_metadata.upvotes or 0} upvotes, {topic_metadata.comments or 0} comments",
                    },
                )
            )

        if not article_content:
            return None, 0, 0, 0.0

        # Calculate cost
        cost_usd = calculate_openai_cost(
            model_name=config["model_name"],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        return article_content, prompt_tokens, completion_tokens, cost_usd

    except Exception as e:
        logger.error(f"Article generation failed: {e}")
        return None, 0, 0, 0.0


def prepare_research_content(topic_metadata: TopicMetadata) -> str:
    """
    Prepare research content for article generation.

    Pure function - deterministic output from input.

    Args:
        topic_metadata: Topic to prepare content for

    Returns:
        Formatted research content string
    """
    try:
        research_lines = []
        enhanced_context = []

        # Basic topic information
        research_lines.append(f"Title: {topic_metadata.title}")
        research_lines.append(f"Source: {topic_metadata.source}")

        if topic_metadata.url:
            research_lines.append(f"Original URL: {topic_metadata.url}")

        # Engagement metrics
        if topic_metadata.upvotes is not None:
            research_lines.append(f"Upvotes: {topic_metadata.upvotes}")

        if topic_metadata.comments is not None:
            research_lines.append(f"Comments: {topic_metadata.comments}")

        # Priority and timing
        research_lines.append(f"Priority Score: {topic_metadata.priority_score:.3f}")

        if topic_metadata.collected_at:
            research_lines.append(
                f"Collected At: {topic_metadata.collected_at.isoformat()}"
            )

        # Additional context
        if hasattr(topic_metadata, "subreddit") and topic_metadata.subreddit:
            research_lines.append(f"Subreddit: {topic_metadata.subreddit}")

        # Enhanced metadata processing
        if (
            hasattr(topic_metadata, "enhanced_metadata")
            and topic_metadata.enhanced_metadata
        ):
            enhanced = topic_metadata.enhanced_metadata

            # Extract scores
            if enhanced.get("quality_score"):
                enhanced_context.append(
                    f"Content Quality Score: {enhanced['quality_score']:.3f}"
                )
            if enhanced.get("relevance_score"):
                enhanced_context.append(
                    f"Topic Relevance Score: {enhanced['relevance_score']:.3f}"
                )
            if enhanced.get("engagement_score"):
                enhanced_context.append(
                    f"Engagement Score: {enhanced['engagement_score']:.3f}"
                )

            # Topics and keywords
            if enhanced.get("topics"):
                enhanced_context.append(
                    f"Extracted Topics: {', '.join(enhanced['topics'])}"
                )
            if enhanced.get("keywords"):
                enhanced_context.append(
                    f"SEO Keywords: {', '.join(enhanced['keywords'])}"
                )
            if enhanced.get("entities"):
                enhanced_context.append(
                    f"Named Entities: {', '.join(enhanced['entities'])}"
                )
            if enhanced.get("sentiment"):
                enhanced_context.append(f"Content Sentiment: {enhanced['sentiment']}")

            # Source metadata
            source_meta = enhanced.get("source_metadata")
            if source_meta:
                if hasattr(source_meta, "reddit_data") and source_meta.reddit_data:
                    enhanced_context.append(
                        f"Reddit Context: {source_meta.reddit_data}"
                    )
                if hasattr(source_meta, "mastodon_data") and source_meta.mastodon_data:
                    enhanced_context.append(
                        f"Mastodon Context: {source_meta.mastodon_data}"
                    )
                if hasattr(source_meta, "rss_data") and source_meta.rss_data:
                    enhanced_context.append(f"RSS Context: {source_meta.rss_data}")

            # Custom fields
            if enhanced.get("custom_fields"):
                enhanced_context.append(
                    f"Additional Context: {enhanced['custom_fields']}"
                )

            # Provenance
            if enhanced.get("provenance_entries"):
                prov_count = len(enhanced["provenance_entries"])
                enhanced_context.append(
                    f"Processing History: {prov_count} processing steps"
                )

                ai_models = [
                    p.ai_model
                    for p in enhanced["provenance_entries"]
                    if hasattr(p, "ai_model") and p.ai_model
                ]
                if ai_models:
                    enhanced_context.append(
                        f"Previous AI Models: {', '.join(set(ai_models))}"
                    )

        # Combine all research content
        all_research_lines = research_lines + enhanced_context
        research_content = "\n".join(all_research_lines)

        # Add instructions
        context_instructions = f"""
Research Context:
{research_content}

Instructions: Use this information to create a comprehensive, well-researched article that:
1. Provides valuable insights on the topic
2. Maintains factual accuracy
3. Engages readers with clear, informative content
4. Incorporates relevant context from the source material
5. Leverages extracted topics, keywords, and entities for SEO optimization
6. Respects the content sentiment and engagement patterns
7. Aims for approximately 3000 words with good structure and flow
8. Uses source-specific context to enhance authenticity and relevance
"""

        return context_instructions

    except Exception as e:
        logger.warning(f"Error preparing research content: {e}")
        return f"Title: {topic_metadata.title}\nSource: {topic_metadata.source}"


def calculate_quality_score(article_content: str, word_count: int) -> float:
    """
    Calculate quality score for generated article.

    Pure function - deterministic scoring.

    Args:
        article_content: Generated article content
        word_count: Number of words

    Returns:
        Quality score between 0.0 and 1.0
    """
    try:
        if not article_content or word_count == 0:
            return 0.0

        score = 0.0

        # Word count scoring (target ~3000 words)
        target_words = 3000
        if word_count >= target_words * 0.7:
            word_score = min(1.0, word_count / target_words)
            if word_count > target_words * 1.2:
                word_score *= 0.9
            score += word_score * 0.3

        # Structure indicators
        paragraphs = article_content.count("\n\n")
        if paragraphs >= 5:
            score += min(0.2, paragraphs / 20.0)

        # Content variety
        sentences = (
            article_content.count(".")
            + article_content.count("!")
            + article_content.count("?")
        )
        if sentences > 10:
            sentence_variety_score = min(0.15, sentences / 100.0)
            score += sentence_variety_score

        # Information density
        unique_words = len(set(article_content.lower().split()))
        if word_count > 0:
            vocabulary_ratio = unique_words / word_count
            if vocabulary_ratio > 0.3:
                score += min(0.2, vocabulary_ratio)

        # Quality indicators
        quality_indicators = [
            "however",
            "therefore",
            "moreover",
            "furthermore",
            "additionally",
            "research",
            "study",
            "analysis",
            "evidence",
            "data",
            "important",
            "significant",
            "effective",
            "impact",
            "benefits",
        ]

        content_lower = article_content.lower()
        indicator_count = sum(1 for ind in quality_indicators if ind in content_lower)
        score += min(0.15, indicator_count / len(quality_indicators))

        return max(0.0, min(1.0, score))

    except Exception as e:
        logger.warning(f"Error calculating quality score: {e}")
        return 0.5


# ============================================================================
# Article Result Building
# ============================================================================


def build_article_result(
    topic_metadata: TopicMetadata,
    article_content: str,
    word_count: int,
    quality_score: float,
    cost_usd: float,
    tokens_used: int,
    processing_time: float,
    metadata: Dict[str, Any],
    processor_id: str,
    session_id: str,
    model_name: str,
    start_time: datetime,
) -> Dict[str, Any]:
    """
    Build complete article result dictionary.

    Pure function - no side effects.

    Args:
        All required data for building result

    Returns:
        Complete article result dictionary
    """
    # Extract metadata fields
    original_title = metadata["original_title"]
    seo_title = metadata["title"]
    slug = metadata["slug"]
    filename = metadata["filename"]
    url = metadata["url"]
    metadata_cost = metadata.get("cost_usd", 0.0)
    metadata_tokens = metadata.get("tokens_used", 0)

    # Calculate total cost
    total_cost_usd = cost_usd + metadata_cost

    # Base article result
    article_result = {
        "topic_id": topic_metadata.topic_id,
        "original_title": original_title,
        "title": seo_title,
        "slug": slug,
        "filename": filename,
        "url": url,
        "article_content": article_content,
        "word_count": word_count,
        "quality_score": quality_score,
        "cost": cost_usd,
        "metadata_cost": metadata_cost,
        "total_cost": total_cost_usd,
        "tokens_used": tokens_used,
        "metadata_tokens": metadata_tokens,
        "processing_time": processing_time,
        "source_priority": topic_metadata.priority_score,
        "source": topic_metadata.source,
        "original_url": topic_metadata.url,
        "generated_at": start_time.isoformat(),
        "metadata": {
            "processor_id": processor_id,
            "session_id": session_id,
            "openai_model": model_name,
            "original_upvotes": topic_metadata.upvotes or 0,
            "original_comments": topic_metadata.comments or 0,
            "content_type": "generated_article",
        },
    }

    # Add enhanced metadata if available
    if (
        hasattr(topic_metadata, "enhanced_metadata")
        and topic_metadata.enhanced_metadata
    ):
        enhanced = topic_metadata.enhanced_metadata

        # Convert source metadata
        source_metadata = enhanced.get("source_metadata")
        source_metadata_dict = source_metadata.model_dump() if source_metadata else None

        article_result["enhanced_metadata"] = {
            "source_metadata": source_metadata_dict,
            "quality_scores": {
                "content_quality": enhanced.get("quality_score"),
                "relevance_score": enhanced.get("relevance_score"),
                "engagement_score": enhanced.get("engagement_score"),
                "generated_quality": quality_score,
            },
            "extracted_context": {
                "topics": enhanced.get("topics", []),
                "keywords": enhanced.get("keywords", []),
                "entities": enhanced.get("entities", []),
                "sentiment": enhanced.get("sentiment"),
            },
            "custom_fields": enhanced.get("custom_fields", {}),
        }

        # Provenance chain
        previous_provenance = enhanced.get("provenance_entries", [])
        previous_provenance_dicts = [
            p.model_dump() if hasattr(p, "model_dump") else p
            for p in previous_provenance
        ]

        article_result["provenance_chain"] = {
            "previous_steps": len(previous_provenance_dicts),
            "total_previous_cost": sum(
                p.get("cost_usd", 0) for p in previous_provenance_dicts if p
            ),
            "current_step": {
                "stage": "processing",
                "service_name": "content-processor",
                "operation": "article_generation",
                "processor_id": processor_id,
                "ai_model": model_name,
                "cost_usd": cost_usd,
                "tokens_used": tokens_used,
                "processing_time_ms": int(processing_time * 1000),
                "timestamp": start_time.isoformat(),
            },
            "metadata_generation": {
                "stage": "processing",
                "service_name": "content-processor",
                "operation": "metadata_generation",
                "ai_model": model_name,
                "cost_usd": metadata_cost,
                "tokens_used": metadata_tokens,
                "original_title": original_title,
                "translated_title": seo_title,
                "slug": slug,
                "filename": filename,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    return {
        "article_result": article_result,
        "article_content": article_content,
        "word_count": word_count,
        "quality_score": quality_score,
        "cost": total_cost_usd,
    }

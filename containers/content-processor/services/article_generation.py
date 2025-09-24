"""
Article Generation Service

Handles OpenAI integration and article creation logic.
Extracted from ContentProcessor to improve maintainability.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from models import TopicMetadata
from openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class ArticleGenerationService:
    """Service for generating articles from topics using OpenAI."""

    def __init__(self, openai_client: Optional[OpenAIClient] = None):
        self.openai_client = openai_client or OpenAIClient()

    async def generate_article_from_topic(
        self, topic_metadata: TopicMetadata, processor_id: str, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Generate an article from a topic using OpenAI."""
        try:
            logger.info(f"Processing topic: {topic_metadata.title}")
            start_time = datetime.now(timezone.utc)

            # Prepare research content from the topic
            research_content = self._prepare_research_content(topic_metadata)

            # Generate article using OpenAI
            article_content, cost_usd, tokens_used = (
                await self.openai_client.generate_article(
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
                logger.error(
                    f"Failed to generate article for topic: {topic_metadata.title}"
                )
                return None

            # Calculate article metadata
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            word_count = len(article_content.split())
            quality_score = self._calculate_quality_score(article_content, word_count)

            # Prepare article result
            article_result = {
                "topic_id": topic_metadata.topic_id,
                "title": topic_metadata.title,
                "article_content": article_content,
                "word_count": word_count,
                "quality_score": quality_score,
                "cost": cost_usd,
                "tokens_used": tokens_used,
                "processing_time": processing_time,
                "source_priority": topic_metadata.priority_score,
                "source": topic_metadata.source,
                "original_url": topic_metadata.url,
                "generated_at": start_time.isoformat(),
                "metadata": {
                    "processor_id": processor_id,
                    "session_id": session_id,
                    "openai_model": getattr(
                        self.openai_client, "model_name", "unknown"
                    ),
                    "original_upvotes": topic_metadata.upvotes or 0,
                    "original_comments": topic_metadata.comments or 0,
                    "content_type": "generated_article",
                },
            }

            logger.info(
                f"Article generated successfully: {word_count} words, "
                f"${cost_usd:.4f} cost, {processing_time:.2f}s processing time"
            )

            return {
                "article_result": article_result,
                "article_content": article_content,
                "word_count": word_count,
                "quality_score": quality_score,
                "cost": cost_usd,
            }

        except Exception as e:
            logger.error(f"Error processing topic {topic_metadata.topic_id}: {e}")
            return None

    def _prepare_research_content(self, topic_metadata: TopicMetadata) -> str:
        """
        Prepare research content for article generation.

        Args:
            topic_metadata: The topic to prepare content for

        Returns:
            str: Formatted research content for OpenAI prompt
        """
        try:
            # Build comprehensive research content from topic metadata
            research_lines = []

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
            research_lines.append(
                f"Priority Score: {topic_metadata.priority_score:.3f}"
            )

            if topic_metadata.collected_at:
                research_lines.append(
                    f"Collected At: {topic_metadata.collected_at.isoformat()}"
                )

            # Additional context if available
            if hasattr(topic_metadata, "subreddit") and topic_metadata.subreddit:
                research_lines.append(f"Subreddit: {topic_metadata.subreddit}")

            # Create structured research content
            research_content = "\n".join(research_lines)

            # Add context instructions for better article generation
            context_instructions = f"""
Research Context:
{research_content}

Instructions: Use this information to create a comprehensive, well-researched article that:
1. Provides valuable insights on the topic
2. Maintains factual accuracy
3. Engages readers with clear, informative content
4. Incorporates relevant context from the source material
5. Aims for approximately 3000 words with good structure and flow
"""

            return context_instructions

        except Exception as e:
            logger.warning(f"Error preparing research content: {e}")
            return f"Title: {topic_metadata.title}\nSource: {topic_metadata.source}"

    def _calculate_quality_score(self, article_content: str, word_count: int) -> float:
        """
        Calculate quality score for generated article.

        Pure function that assesses:
        - Word count adequacy
        - Content structure indicators
        - Readability measures
        - Information density

        Args:
            article_content: The generated article content
            word_count: Number of words in the article

        Returns:
            float: Quality score between 0.0 and 1.0
        """
        try:
            if not article_content or word_count == 0:
                return 0.0

            score = 0.0

            # Word count scoring (target around 3000 words)
            target_words = 3000
            if word_count >= target_words * 0.7:  # At least 70% of target
                word_score = min(1.0, word_count / target_words)
                if word_count > target_words * 1.2:  # Penalty for being too long
                    word_score *= 0.9
                score += word_score * 0.3

            # Structure indicators (paragraphs, sections)
            paragraphs = article_content.count("\n\n")
            if paragraphs >= 5:  # Well-structured articles have multiple paragraphs
                score += min(0.2, paragraphs / 20.0)  # Up to 0.2 for structure

            # Content variety (different sentence lengths, punctuation)
            sentences = (
                article_content.count(".")
                + article_content.count("!")
                + article_content.count("?")
            )
            if sentences > 10:
                sentence_variety_score = min(0.15, sentences / 100.0)
                score += sentence_variety_score

            # Information density (avoid repetitive content)
            unique_words = len(set(article_content.lower().split()))
            if word_count > 0:
                vocabulary_ratio = unique_words / word_count
                if vocabulary_ratio > 0.3:  # Good vocabulary diversity
                    score += min(0.2, vocabulary_ratio)

            # Content quality indicators
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
            indicator_count = sum(
                1 for indicator in quality_indicators if indicator in content_lower
            )
            score += min(0.15, indicator_count / len(quality_indicators))

            # Ensure score is between 0.0 and 1.0
            final_score = max(0.0, min(1.0, score))

            logger.debug(
                f"Quality assessment - Words: {word_count}, Paragraphs: {paragraphs}, "
                f"Sentences: {sentences}, Unique words: {unique_words}, Score: {final_score:.3f}"
            )

            return final_score

        except Exception as e:
            logger.warning(f"Error calculating quality score: {e}")
            return 0.5  # Default middle score if calculation fails

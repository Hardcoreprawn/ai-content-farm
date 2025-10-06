"""
Article Generation Service

Handles OpenAI integration and article creation logic.
Extracted from ContentProcessor to improve maintainability.
Includes SEO metadata generation for clean URLs and titles.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from metadata_generator import MetadataGenerator
from models import TopicMetadata
from openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class ArticleGenerationService:
    """Service for generating articles from topics using OpenAI."""

    def __init__(self, openai_client: Optional[OpenAIClient] = None):
        """
        Initialize the Article Generation Service.

        Args:
            openai_client: Optional OpenAI client. If not provided, creates default.
        """
        self.openai_client = openai_client or OpenAIClient()
        self.metadata_generator = MetadataGenerator(self.openai_client)
        logger.info("ArticleGenerationService initialized with metadata generation")

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

            # Generate SEO metadata (title translation, slug, filename, URL)
            logger.info(f"Generating SEO metadata for: {topic_metadata.title}")

            # Extract date from topic (prefer collected_at, fallback to current date)
            published_date = getattr(topic_metadata, "collected_at", start_time)
            if isinstance(published_date, str):
                published_date_str = published_date
            elif isinstance(published_date, datetime):
                published_date_str = published_date.isoformat()
            else:
                published_date_str = start_time.isoformat()

            # Get first 500 chars of article for metadata context
            content_preview = article_content[:500] if article_content else ""

            # Generate metadata with AI translation and slug creation
            metadata = await self.metadata_generator.generate_metadata(
                title=topic_metadata.title,
                content_preview=content_preview,
                published_date=published_date_str,
            )

            # Extract metadata fields
            original_title = metadata["original_title"]
            seo_title = metadata["title"]  # AI-translated and optimized
            slug = metadata["slug"]
            filename = metadata["filename"]
            url = metadata["url"]
            metadata_cost = metadata.get("cost_usd", 0.0)  # Optional cost tracking
            metadata_tokens = metadata.get("tokens_used", 0)  # Optional token tracking

            # Calculate total cost
            total_cost_usd = cost_usd + metadata_cost

            logger.info(
                f"Metadata generated: slug='{slug}', cost=${metadata_cost:.6f}, "
                f"tokens={metadata_tokens}, total_cost=${total_cost_usd:.6f}"
            )

            # Prepare enhanced article result with provenance tracking
            article_result = {
                "topic_id": topic_metadata.topic_id,
                # Original (possibly non-English)
                "original_title": original_title,
                "title": seo_title,  # AI-translated and SEO-optimized
                "slug": slug,  # URL-safe slug (kebab-case)
                "filename": filename,  # YYYY-MM-DD-slug.html
                "url": url,  # /articles/YYYY-MM-DD-slug.html
                "article_content": article_content,
                "word_count": word_count,
                "quality_score": quality_score,
                "cost": cost_usd,  # Article generation cost only
                "metadata_cost": metadata_cost,  # Metadata generation cost
                "total_cost": total_cost_usd,  # Combined cost
                "tokens_used": tokens_used,  # Article tokens only
                "metadata_tokens": metadata_tokens,  # Metadata tokens
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

            # Add enhanced metadata and provenance if available
            if (
                hasattr(topic_metadata, "enhanced_metadata")
                and topic_metadata.enhanced_metadata
            ):
                enhanced = topic_metadata.enhanced_metadata

                # Convert SourceMetadata Pydantic object to dict for JSON serialization
                source_metadata = enhanced.get("source_metadata")
                source_metadata_dict = (
                    source_metadata.model_dump() if source_metadata else None
                )

                # Include enhanced metadata in article result
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

                # Create provenance chain
                # Convert ProvenanceEntry Pydantic objects to dicts for JSON serialization
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
                        "ai_model": getattr(
                            self.openai_client, "model_name", "unknown"
                        ),
                        "cost_usd": cost_usd,
                        "tokens_used": tokens_used,
                        "processing_time_ms": int(processing_time * 1000),
                        "timestamp": start_time.isoformat(),
                    },
                    "metadata_generation": {
                        "stage": "processing",
                        "service_name": "content-processor",
                        "operation": "metadata_generation",
                        "ai_model": getattr(
                            self.openai_client, "model_name", "unknown"
                        ),
                        "cost_usd": metadata_cost,
                        "tokens_used": metadata_tokens,
                        "original_title": original_title,
                        "translated_title": seo_title,
                        "slug": slug,
                        "filename": filename,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                }

                logger.info(
                    f"📋 PROVENANCE: Added article generation + metadata provenance for {topic_metadata.topic_id}"
                )
            else:
                logger.info(
                    f"📋 LEGACY: Processing legacy topic without enhanced metadata for {topic_metadata.topic_id}"
                )

            logger.info(
                f"Article generated successfully: {word_count} words, "
                f"${total_cost_usd:.4f} total cost (article: ${cost_usd:.4f}, metadata: ${metadata_cost:.6f}), "
                f"{processing_time:.2f}s processing time"
            )

            return {
                "article_result": article_result,
                "article_content": article_content,
                "word_count": word_count,
                "quality_score": quality_score,
                "cost": total_cost_usd,  # Return combined cost
            }

        except Exception as e:
            logger.error(f"Error processing topic {topic_metadata.topic_id}: {e}")
            return None

    def _prepare_research_content(self, topic_metadata: TopicMetadata) -> str:
        """
        Prepare research content for article generation with enhanced metadata support.

        Args:
            topic_metadata: The topic to prepare content for

        Returns:
            str: Formatted research content for OpenAI prompt
        """
        try:
            # Build comprehensive research content from topic metadata
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

            # Enhanced metadata processing
            if (
                hasattr(topic_metadata, "enhanced_metadata")
                and topic_metadata.enhanced_metadata
            ):
                enhanced = topic_metadata.enhanced_metadata
                logger.info(
                    f"📋 ARTICLE-GEN: Using enhanced metadata for {topic_metadata.topic_id}"
                )

                # Extract quality and relevance scores
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

                # Add extracted topics and keywords for better context
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
                    enhanced_context.append(
                        f"Content Sentiment: {enhanced['sentiment']}"
                    )

                # Add source-specific metadata
                source_meta = enhanced.get("source_metadata")
                if source_meta:
                    if hasattr(source_meta, "reddit_data") and source_meta.reddit_data:
                        enhanced_context.append(
                            f"Reddit Context: {source_meta.reddit_data}"
                        )
                    if (
                        hasattr(source_meta, "mastodon_data")
                        and source_meta.mastodon_data
                    ):
                        enhanced_context.append(
                            f"Mastodon Context: {source_meta.mastodon_data}"
                        )
                    if hasattr(source_meta, "rss_data") and source_meta.rss_data:
                        enhanced_context.append(f"RSS Context: {source_meta.rss_data}")

                # Add custom fields if available
                if enhanced.get("custom_fields"):
                    enhanced_context.append(
                        f"Additional Context: {enhanced['custom_fields']}"
                    )

                # Add provenance information for transparency
                if enhanced.get("provenance_entries"):
                    prov_count = len(enhanced["provenance_entries"])
                    enhanced_context.append(
                        f"Processing History: {prov_count} processing steps"
                    )

                    # Extract AI models used in provenance
                    ai_models = [
                        p.ai_model
                        for p in enhanced["provenance_entries"]
                        if hasattr(p, "ai_model") and p.ai_model
                    ]
                    if ai_models:
                        enhanced_context.append(
                            f"Previous AI Models: {', '.join(set(ai_models))}"
                        )

            # Combine basic and enhanced research content
            all_research_lines = research_lines + enhanced_context
            research_content = "\n".join(all_research_lines)

            # Enhanced context instructions based on available metadata
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

"""
Content generation functionality integrated into content processor.

This module provides AI-powered content generation capabilities including:
- TLDR articles (200-400 words)
- Blog posts (600-1000 words)
- Deep dive analysis (1200+ words)
- Batch generation processing
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GenerationRequest(BaseModel):
    """Request for single content generation."""

    topic: str = Field(..., description="Topic to generate content about")
    content_type: str = Field(..., description="Type of content: tldr, blog, deepdive")
    writer_personality: str = Field(default="professional", description="Writing style")
    sources: List[Dict[str, Any]] = Field(default=[], description="Source materials")


class GeneratedContent(BaseModel):
    """Generated content response."""

    title: str = Field(..., description="Generated title")
    content: str = Field(..., description="Generated content")
    content_type: str = Field(..., description="Type of content generated")
    writer_personality: str = Field(..., description="Writing style used")
    generation_time: datetime = Field(default_factory=datetime.utcnow)
    word_count: int = Field(..., description="Word count of generated content")
    sources_used: int = Field(..., description="Number of sources used")


class BatchGenerationRequest(BaseModel):
    """Request for batch content generation."""

    topics: List[str] = Field(..., description="Topics to generate content about")
    content_type: str = Field(..., description="Type of content for all topics")
    writer_personality: str = Field(default="professional", description="Writing style")
    batch_id: Optional[str] = Field(
        default_factory=lambda: str(uuid4()), description="Batch ID"
    )


class BatchGenerationResponse(BaseModel):
    """Response for batch generation request."""

    batch_id: str = Field(..., description="Batch processing ID")
    total_topics: int = Field(..., description="Total topics to process")
    status: str = Field(default="started", description="Batch status")
    estimated_completion_time: Optional[datetime] = None


class GenerationStatus(BaseModel):
    """Status of batch generation."""

    batch_id: str = Field(..., description="Batch ID")
    status: str = Field(..., description="Processing status")
    completed_count: int = Field(default=0, description="Number completed")
    total_count: int = Field(..., description="Total to process")
    current_topic: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    results: List[GeneratedContent] = Field(default=[], description="Generated content")


class ContentGenerator:
    """AI-powered content generation service."""

    def __init__(self):
        """Initialize content generator."""
        self.active_batches: Dict[str, GenerationStatus] = {}
        logger.info("Content generator initialized")

    def has_sufficient_content(self, sources: List[Dict], content_type: str) -> bool:
        """Check if we have enough source material for the requested content type."""
        source_count = len(sources)
        total_content_length = sum(
            len(source.get("summary", "")) + len(source.get("title", ""))
            for source in sources
        )

        # Minimum requirements for each content type
        if content_type == "tldr":
            return source_count >= 1 and total_content_length >= 100
        elif content_type == "blog":
            return source_count >= 2 and total_content_length >= 300
        elif content_type == "deepdive":
            return source_count >= 3 and total_content_length >= 500

        return False

    def parse_ai_response(self, response: str) -> tuple[str, str]:
        """Parse AI response to extract title and content."""
        if "TITLE:" in response and "CONTENT:" in response:
            parts = response.split("CONTENT:", 1)
            title_part = parts[0].replace("TITLE:", "").strip()
            content_part = parts[1].strip()
            return title_part, content_part
        else:
            # Fallback: use first line as title, rest as content
            lines = response.strip().split("\n")
            title = lines[0] if lines else "Generated Content"
            content = "\n".join(lines[1:]) if len(lines) > 1 else ""
            return title, content

    def build_prompt(
        self,
        topic: str,
        content_type: str,
        writer_personality: str,
        sources: List[Dict],
    ) -> str:
        """Build generation prompt based on content type."""
        sources_text = "\n".join(
            [
                f"- {source.get('title', 'Untitled')}: {source.get('summary', 'No summary')}"
                for source in sources[:5]  # Limit to top 5 sources
            ]
        )

        personality_instructions = {
            "professional": "Use professional, clear language suitable for business contexts.",
            "casual": "Use conversational, accessible language that's easy to understand.",
            "expert": "Use technical depth and industry-specific terminology.",
            "skeptical": "Approach with healthy skepticism and critical analysis.",
            "enthusiast": "Show excitement and passion for the topic.",
        }

        personality_instruction = personality_instructions.get(
            writer_personality, "Use clear, informative language."
        )

        if content_type == "tldr":
            word_target = "200-400 words"
            style_note = (
                "Create a concise, informative summary that captures the key insights."
            )
        elif content_type == "blog":
            word_target = "600-1000 words"
            style_note = (
                "Write an engaging, comprehensive article with clear structure."
            )
        elif content_type == "deepdive":
            word_target = "1200+ words"
            style_note = (
                "Provide thorough analysis with detailed insights and implications."
            )
        else:
            word_target = "400-600 words"
            style_note = "Write clear, informative content."

        return f"""TITLE: Create a compelling title for this topic
CONTENT: Write a {content_type} article ({word_target}) about: {topic}

{personality_instruction}
{style_note}

Source material:
{sources_text}

Focus on providing value to readers with actionable insights."""

    async def generate_content(self, request: GenerationRequest) -> GeneratedContent:
        """Generate content for a single topic."""
        try:
            # Check if we have sufficient source material
            if not self.has_sufficient_content(request.sources, request.content_type):
                logger.warning(
                    f"Insufficient source material for {request.content_type} on topic: {request.topic}"
                )

            # Build the generation prompt
            prompt = self.build_prompt(
                request.topic,
                request.content_type,
                request.writer_personality,
                request.sources,
            )

            # Simulate AI generation (replace with actual AI client call)
            generated_text = await self._simulate_ai_generation(
                prompt, request.content_type
            )

            # Parse the response
            title, content = self.parse_ai_response(generated_text)

            # Count words
            word_count = len(content.split())

            return GeneratedContent(
                title=title,
                content=content,
                content_type=request.content_type,
                writer_personality=request.writer_personality,
                word_count=word_count,
                sources_used=len(request.sources),
            )

        except Exception as e:
            logger.error(
                f"Content generation failed for topic '{request.topic}': {str(e)}"
            )
            raise

    async def _simulate_ai_generation(self, prompt: str, content_type: str) -> str:
        """Simulate AI content generation (replace with actual AI client)."""
        # Simulate processing time
        await asyncio.sleep(0.5)

        # Return mock content based on type
        if content_type == "tldr":
            return f"""TITLE: Quick Overview: Latest Developments
CONTENT: This is a simulated TLDR article that would normally be generated by an AI model.
The content would be concise and focused, providing key insights in approximately 200-400 words.
This mock response demonstrates the expected format and structure."""
        elif content_type == "blog":
            return f"""TITLE: Comprehensive Analysis: Understanding the Trends
CONTENT: This is a simulated blog post that would be generated by an AI model.
It would typically be 600-1000 words with detailed analysis, structured sections,
and comprehensive coverage of the topic. The content would be engaging and informative,
suitable for a general audience while maintaining depth and accuracy."""
        elif content_type == "deepdive":
            return f"""TITLE: Deep Dive: Complete Analysis and Implications
CONTENT: This is a simulated deep dive analysis that would be generated by an AI model.
Such content typically exceeds 1200 words and provides thorough examination of the topic,
including background context, detailed analysis, implications, and forward-looking insights.
The content would be suitable for expert audiences requiring comprehensive understanding."""
        else:
            return f"""TITLE: Generated Content
CONTENT: This is simulated content for the requested topic. In production,
this would be generated by an AI model based on the provided prompt and sources."""

    async def start_batch_generation(
        self, request: BatchGenerationRequest
    ) -> BatchGenerationResponse:
        """Start batch content generation."""
        try:
            batch_id = request.batch_id or str(uuid4())

            # Initialize batch status
            status = GenerationStatus(
                batch_id=batch_id,
                status="processing",
                total_count=len(request.topics),
                estimated_completion=datetime.utcnow(),
            )

            self.active_batches[batch_id] = status

            # Start background processing
            asyncio.create_task(self._process_batch(request, status))

            return BatchGenerationResponse(
                batch_id=batch_id, total_topics=len(request.topics), status="started"
            )

        except Exception as e:
            logger.error(f"Failed to start batch generation: {str(e)}")
            raise

    async def _process_batch(
        self, request: BatchGenerationRequest, status: GenerationStatus
    ):
        """Process batch generation in background."""
        try:
            for i, topic in enumerate(request.topics):
                # Update current processing status
                status.current_topic = topic
                status.completed_count = i

                # Generate content for this topic
                gen_request = GenerationRequest(
                    topic=topic,
                    content_type=request.content_type,
                    writer_personality=request.writer_personality,
                    sources=[],  # In production, would fetch relevant sources
                )

                generated = await self.generate_content(gen_request)
                status.results.append(generated)

                logger.info(
                    f"Batch {request.batch_id}: Completed {i+1}/{len(request.topics)} - {topic}"
                )

            # Mark batch as completed
            status.status = "completed"
            status.completed_count = len(request.topics)
            status.current_topic = None

            logger.info(f"Batch generation completed: {request.batch_id}")

        except Exception as e:
            logger.error(f"Batch processing failed for {request.batch_id}: {str(e)}")
            status.status = "failed"

    def get_batch_status(self, batch_id: str) -> Optional[GenerationStatus]:
        """Get status of batch generation."""
        return self.active_batches.get(batch_id)


# Global generator instance
_generator_instance: Optional[ContentGenerator] = None


def get_content_generator() -> ContentGenerator:
    """Get or create content generator instance."""
    global _generator_instance

    if _generator_instance is None:
        _generator_instance = ContentGenerator()

    return _generator_instance

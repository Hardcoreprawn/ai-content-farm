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
from datetime import datetime, timezone
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
    generation_time: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO format timestamp",
    )
    word_count: int = Field(..., description="Word count of generated content")
    sources_used: int = Field(..., description="Number of sources used")

    # Source attribution fields
    original_url: Optional[str] = Field(
        None, description="URL of original source content"
    )
    source_platform: Optional[str] = Field(
        None, description="Platform name (reddit, rss, mastodon, web)"
    )
    author: Optional[str] = Field(None, description="Original content author")
    original_date: Optional[str] = Field(None, description="Original publication date")


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
    estimated_completion: Optional[str] = None  # ISO format timestamp
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

    def _extract_source_attribution(
        self, sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract source attribution from the primary source.

        Extracts URL, platform, author, and date from the first/primary source.
        Falls back gracefully if fields are missing.

        Args:
            sources: List of source dictionaries

        Returns:
            Dictionary with original_url, source_platform, author, original_date
        """
        attribution: Dict[str, Any] = {
            "original_url": None,
            "source_platform": None,
            "author": None,
            "original_date": None,
        }

        if not sources:
            return attribution

        # Use the first source as primary
        primary_source = sources[0]

        # Validate that primary_source is a dict
        if not isinstance(primary_source, dict):
            return attribution

        # Extract URL (try multiple field names)
        attribution["original_url"] = (
            primary_source.get("url")
            or primary_source.get("link")
            or primary_source.get("source_url")
        )

        # Extract source platform (normalize to lowercase)
        source_platform = (
            primary_source.get("source")
            or primary_source.get("source_type")
            or primary_source.get("platform")
        )
        if source_platform:
            attribution["source_platform"] = str(source_platform).lower()

        # Extract author
        attribution["author"] = primary_source.get("author")

        # Extract date (try multiple field names)
        date_value = (
            primary_source.get("created_at")
            or primary_source.get("published")
            or primary_source.get("created_utc")
            or primary_source.get("date")
        )
        if date_value:
            # Convert to ISO format if it's a timestamp
            if isinstance(date_value, (int, float)):
                try:
                    # Validate timestamp is reasonable (between 1970 and 2100)
                    if 0 <= date_value < 4102444800:  # Jan 1, 2100
                        attribution["original_date"] = datetime.fromtimestamp(
                            date_value, tz=timezone.utc
                        ).isoformat()
                    else:
                        attribution["original_date"] = None
                except (ValueError, OSError):
                    attribution["original_date"] = None
            else:
                attribution["original_date"] = str(date_value)

        return attribution

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

            # Generate content using Azure OpenAI
            generated_text = await self._generate_with_azure_openai(
                prompt, request.content_type
            )

            # Parse the response
            title, content = self.parse_ai_response(generated_text)

            # Count words
            word_count = len(content.split())

            # Extract source attribution from primary source
            source_attribution = self._extract_source_attribution(request.sources)

            return GeneratedContent(
                title=title,
                content=content,
                content_type=request.content_type,
                writer_personality=request.writer_personality,
                word_count=word_count,
                sources_used=len(request.sources),
                original_url=source_attribution.get("original_url"),
                source_platform=source_attribution.get("source_platform"),
                author=source_attribution.get("author"),
                original_date=source_attribution.get("original_date"),
            )

        except Exception as e:
            logger.error(
                f"Content generation failed for topic '{request.topic}': {str(e)}"
            )
            raise

    async def _generate_with_azure_openai(self, prompt: str, content_type: str) -> str:
        """Generate content using Azure OpenAI with fallback to simulation."""
        try:
            # Import the external API client
            from dependencies import get_api_client

            api_client = get_api_client()

            # Set model and parameters based on content type
            model_settings = {
                "tldr": {"max_tokens": 600, "temperature": 0.3, "model": "gpt-4"},
                "blog": {"max_tokens": 1200, "temperature": 0.5, "model": "gpt-4"},
                "deepdive": {"max_tokens": 2000, "temperature": 0.4, "model": "gpt-4"},
            }

            settings = model_settings.get(
                content_type, {"max_tokens": 800, "temperature": 0.4, "model": "gpt-4"}
            )

            # Format the prompt as a chat message
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert content writer. Generate high-quality, engaging content based on the user's request.",
                },
                {"role": "user", "content": prompt},
            ]

            # Call Azure OpenAI through the external API client
            response = await api_client.chat_completion(
                messages=messages,
                model=settings["model"],
                max_tokens=settings["max_tokens"],
                temperature=settings["temperature"],
            )

            # Extract the generated text from the response
            generated_text = (
                response.get("choices", [{}])[0].get("message", {}).get("content", "")
            )

            if not generated_text:
                raise Exception("Empty response from Azure OpenAI")

            logger.info(
                f"Successfully generated {content_type} content using Azure OpenAI"
            )
            return generated_text

        except Exception as e:
            logger.warning(
                f"Azure OpenAI generation failed, falling back to simulation: {e}"
            )
            # Fallback to simulation if Azure OpenAI fails
            return await self._simulate_ai_generation(prompt, content_type)

    async def _simulate_ai_generation(self, prompt: str, content_type: str) -> str:
        """Simulate AI content generation (fallback when Azure OpenAI unavailable)."""
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
                estimated_completion=datetime.now(timezone.utc).isoformat(),
            )

            self.active_batches[batch_id] = status

            # Start background processing
            asyncio.create_task(self._process_batch(request, status))

            return BatchGenerationResponse(
                batch_id=batch_id, total_topics=len(request.topics), status="started"
            )

        except Exception as e:
            logger.error("Failed to start batch generation")
            logger.debug(f"Batch generation start error details: {str(e)}")
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
            logger.error(f"Batch processing failed for {request.batch_id}")
            logger.debug(
                f"Batch processing error details for {request.batch_id}: {str(e)}"
            )
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

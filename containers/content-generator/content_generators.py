"""Content generation logic for different content types"""

import logging
from datetime import datetime
from typing import Optional

from ai_clients import AIClientManager

from config import config
from models import GeneratedContent, RankedTopic

# Configure logging
logger = logging.getLogger(__name__)


class ContentGenerators:
    """Handles content generation for different content types"""

    def __init__(self, ai_client_manager: AIClientManager):
        self.ai_clients = ai_client_manager

    def has_sufficient_content(self, topic: RankedTopic, content_type: str) -> bool:
        """Check if we have enough source material for the requested content type"""
        source_count = len(topic.sources)
        total_content_length = sum(
            len(source.summary or "") + len(source.title) for source in topic.sources
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
        """Parse AI response to extract title and content"""
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

    def build_tldr_prompt(self, topic: RankedTopic, writer_personality: str) -> str:
        """Build prompt for TLDR content generation"""
        sources_text = "\n".join(
            [f"- {source.title}: {source.summary}" for source in topic.sources[:3]]
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

        return f"""TITLE: Create a compelling title for this topic
CONTENT: Write a focused TLDR article (200-400 words) about: {topic.topic}

{personality_instruction}

Source material:
{sources_text}

Create a concise, informative summary that captures the key insights. Focus on what readers need to know immediately."""

    def build_blog_prompt(self, topic: RankedTopic, writer_personality: str) -> str:
        """Build prompt for blog content generation"""
        sources_text = "\n".join(
            [f"- {source.title}: {source.summary}" for source in topic.sources]
        )

        personality_instructions = {
            "professional": "Write in a professional, authoritative tone suitable for industry publications.",
            "casual": "Use a conversational, friendly tone that engages readers personally.",
            "expert": "Demonstrate deep technical knowledge and industry expertise.",
            "skeptical": "Present balanced analysis with critical evaluation of claims.",
            "enthusiast": "Show passion and excitement while maintaining credibility.",
        }

        personality_instruction = personality_instructions.get(
            writer_personality, "Write in a clear, engaging style."
        )

        return f"""TITLE: Create an engaging title for this comprehensive article
CONTENT: Write a detailed blog article (600-1000 words) about: {topic.topic}

{personality_instruction}

Source material:
{sources_text}

Structure the article with:
1. Introduction that hooks the reader
2. Main analysis with supporting details
3. Implications and future outlook
4. Conclusion with key takeaways

Focus on providing value through analysis, context, and actionable insights."""

    def build_deepdive_prompt(self, topic: RankedTopic, writer_personality: str) -> str:
        """Build prompt for deep dive content generation"""
        sources_text = "\n".join(
            [
                f"- {source.title}: {source.summary or source.content[:200] + '...'}"
                for source in topic.sources
            ]
        )

        return f"""TITLE: Create a comprehensive title for this in-depth analysis
CONTENT: Write a comprehensive deep-dive analysis (1000+ words) about: {topic.topic}

Use expert-level analysis with the {writer_personality} perspective.

Source material:
{sources_text}

Structure as a comprehensive report with:
## Executive Summary
Brief overview of key findings

## Detailed Analysis  
In-depth examination of the topic with supporting evidence

## Technical Implications
Technical details and implementation considerations

## Market/Industry Impact
Broader implications for the industry or market

## Future Outlook
Predictions and long-term implications

## Conclusion
Summary of key insights and recommendations

Focus on depth, accuracy, and providing expert-level insights that go beyond surface-level coverage."""

    async def generate_tldr(
        self, topic: RankedTopic, writer_personality: str
    ) -> GeneratedContent:
        """Generate focused tl;dr article (200-400 words)"""
        prompt = self.build_tldr_prompt(topic, writer_personality)

        # Use GPT-3.5 for cost efficiency on short content
        response = await self.ai_clients.call_openai(
            prompt, model="gpt-3.5-turbo", max_tokens=600
        )

        # Parse response and extract title/content
        title, content = self.parse_ai_response(response)

        return GeneratedContent(
            topic=topic.topic,
            content_type="tldr",
            title=title,
            content=content,
            word_count=len(content.split()),
            tags=topic.tags,
            sources=topic.sources,
            generation_time=datetime.utcnow(),
            ai_model="gpt-3.5-turbo",
            writer_personality=writer_personality,
            metadata={
                "original_rank": topic.rank,
                "ai_score": topic.ai_score,
                "sentiment": topic.sentiment,
                "personality_used": writer_personality,
            },
        )

    async def generate_blog(
        self, topic: RankedTopic, writer_personality: str
    ) -> GeneratedContent:
        """Generate blog article (600-1000 words) - only if sufficient content"""
        if not self.has_sufficient_content(topic, "blog"):
            raise ValueError(f"Insufficient content for blog article on {topic.topic}")

        prompt = self.build_blog_prompt(topic, writer_personality)

        # Use GPT-4 for better quality on longer content
        response = await self.ai_clients.call_openai(
            prompt, model="gpt-4", max_tokens=1200
        )

        # Parse response and extract title/content
        title, content = self.parse_ai_response(response)

        return GeneratedContent(
            topic=topic.topic,
            content_type="blog",
            title=title,
            content=content,
            word_count=len(content.split()),
            tags=topic.tags,
            sources=topic.sources,
            generation_time=datetime.utcnow(),
            ai_model="gpt-4",
            writer_personality=writer_personality,
            metadata={
                "original_rank": topic.rank,
                "ai_score": topic.ai_score,
                "sentiment": topic.sentiment,
                "personality_used": writer_personality,
            },
        )

    async def generate_deepdive(
        self, topic: RankedTopic, writer_personality: str
    ) -> GeneratedContent:
        """Generate deep dive analysis (1000+ words) - requires substantial content"""
        if not self.has_sufficient_content(topic, "deepdive"):
            raise ValueError(
                f"Insufficient content for deepdive article on {topic.topic}"
            )

        prompt = self.build_deepdive_prompt(topic, writer_personality)

        # Use Claude for deep analysis due to larger context window
        response = await self.ai_clients.call_claude(prompt, max_tokens=4000)

        # Parse response and extract title/content
        title, content = self.parse_ai_response(response)

        return GeneratedContent(
            topic=topic.topic,
            content_type="deepdive",
            title=title,
            content=content,
            word_count=len(content.split()),
            tags=topic.tags,
            sources=topic.sources,
            generation_time=datetime.utcnow(),
            ai_model="claude-3-sonnet",
            writer_personality=writer_personality,
            metadata={
                "original_rank": topic.rank,
                "ai_score": topic.ai_score,
                "sentiment": topic.sentiment,
                "personality_used": writer_personality,
            },
        )

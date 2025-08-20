import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import anthropic
import httpx
import openai
from blob_events import BlobEventProcessor
from config import config
from models import (
    BatchGenerationRequest,
    BatchGenerationResponse,
    GeneratedContent,
    GenerationRequest,
    GenerationStatus,
    RankedTopic,
)

from libs.blob_storage import get_blob_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentGeneratorService:
    """Core content generation service focused on short-form articles"""

    def __init__(self):
        self.blob_client = get_blob_client()
        self.is_running = False
        self.watch_task = None
        self.event_processor = BlobEventProcessor(self)

        # Initialize Azure OpenAI client (preferred)
        if config.AZURE_OPENAI_ENDPOINT and config.AZURE_OPENAI_API_KEY:
            self.azure_openai_client = openai.AsyncAzureOpenAI(
                azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                api_key=config.AZURE_OPENAI_API_KEY,
                api_version=config.AZURE_OPENAI_API_VERSION,
            )
            logger.info("Initialized Azure OpenAI client")
        else:
            self.azure_openai_client = None

        # Fallback to OpenAI direct API
        self.openai_client = (
            openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY)
            if config.OPENAI_API_KEY
            else None
        )

        self.claude_client = (
            anthropic.AsyncAnthropic(api_key=config.CLAUDE_API_KEY)
            if config.CLAUDE_API_KEY
            else None
        )
        self.active_generations: Dict[str, GenerationStatus] = {}
        self.http_client = httpx.AsyncClient(timeout=config.VERIFICATION_TIMEOUT)

    async def generate_content(
        self,
        topic: RankedTopic,
        content_type: str = "tldr",
        writer_personality: str = "professional",
    ) -> GeneratedContent:
        """Generate content for a single topic with specified personality"""
        try:
            logger.info(
                f"Generating {content_type} content for topic: {topic.topic} with {writer_personality} voice"
            )

            # Only generate if we have enough source material
            if not self._has_sufficient_content(topic, content_type):
                raise ValueError(
                    f"Insufficient source material for {content_type} article on {topic.topic}"
                )

            # Verify sources if enabled
            verification_status = "pending"
            fact_check_notes = []

            if config.ENABLE_SOURCE_VERIFICATION:
                verification_status, fact_check_notes = await self._verify_sources(
                    topic.sources
                )

            # Generate the content
            if content_type == "tldr":
                content = await self._generate_tldr(topic, writer_personality)
            elif content_type == "blog":
                content = await self._generate_blog(topic, writer_personality)
            elif content_type == "deepdive":
                content = await self._generate_deepdive(topic, writer_personality)
            else:
                raise ValueError(f"Unknown content type: {content_type}")

            # Add verification results
            content.verification_status = verification_status
            content.fact_check_notes = fact_check_notes
            content.writer_personality = writer_personality

            return content

        except Exception as e:
            logger.error(f"Error generating content for {topic.topic}: {str(e)}")
            raise

    def _has_sufficient_content(self, topic: RankedTopic, content_type: str) -> bool:
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

    async def _verify_sources(self, sources: List) -> tuple[str, List[str]]:
        """Verify that sources are real and accessible"""
        verification_notes = []
        verified_count = 0

        for source in sources[:3]:  # Limit verification to top 3 sources
            try:
                response = await self.http_client.head(
                    source.url, follow_redirects=True
                )
                if response.status_code == 200:
                    verified_count += 1
                    verification_notes.append(f"✅ {source.name}: Source accessible")
                else:
                    verification_notes.append(
                        f"⚠️ {source.name}: HTTP {response.status_code}"
                    )
            except Exception as e:
                verification_notes.append(
                    f"❌ {source.name}: Verification failed - {str(e)[:50]}"
                )

        # Determine overall verification status
        if verified_count == len(sources[:3]):
            status = "verified"
        elif verified_count > 0:
            status = "partially_verified"
        else:
            status = "unverified"

        return status, verification_notes

    async def _generate_tldr(
        self, topic: RankedTopic, writer_personality: str
    ) -> GeneratedContent:
        """Generate focused tl;dr article (200-400 words)"""
        prompt = self._build_tldr_prompt(topic, writer_personality)

        # Use GPT-3.5 for cost efficiency on short content
        response = await self._call_openai(
            prompt, model="gpt-3.5-turbo", max_tokens=600
        )

        # Parse response and extract title/content
        title, content = self._parse_ai_response(response)

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

    async def _generate_blog(
        self, topic: RankedTopic, writer_personality: str
    ) -> GeneratedContent:
        """Generate blog article (600-1000 words) - only if sufficient content"""
        if not self._has_sufficient_content(topic, "blog"):
            raise ValueError(f"Insufficient content for blog article on {topic.topic}")

        prompt = self._build_blog_prompt(topic, writer_personality)

        # Use GPT-4 for higher quality on longer content
        response = await self._call_openai(prompt, model="gpt-4", max_tokens=1500)

        title, content = self._parse_ai_response(response)

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

    async def _generate_deepdive(
        self, topic: RankedTopic, writer_personality: str
    ) -> GeneratedContent:
        """Generate deep dive (1500-2500 words) - only if substantial content available"""
        if not self._has_sufficient_content(topic, "deepdive"):
            raise ValueError(f"Insufficient content for deep dive on {topic.topic}")

        prompt = self._build_deepdive_prompt(topic, writer_personality)

        # Use Claude for analytical deep content
        response = await self._call_claude(prompt, max_tokens=3000)

        title, content = self._parse_ai_response(response)

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

    def _build_tldr_prompt(self, topic: RankedTopic, writer_personality: str) -> str:
        """Build prompt for tl;dr article generation with personality"""
        sources_text = "\n".join(
            [
                f"- {source.name}: {source.title}\n  URL: {source.url}\n  Summary: {source.summary or 'No summary available'}"
                for source in topic.sources[:2]  # Focus on top 2 sources for tl;dr
            ]
        )

        personality_prompt = config.WRITER_PERSONALITIES.get(
            writer_personality, config.WRITER_PERSONALITIES["professional"]
        )

        return f"""Write a focused tl;dr article about: {topic.topic}

WRITER PERSONALITY: {writer_personality} - {personality_prompt}
TARGET: Busy professionals who need quick, valuable insights
LENGTH: 200-400 words (strict limit)
STRUCTURE: Compelling title, hook introduction, 2-3 key points, actionable conclusion

SOURCE MATERIAL TO VERIFY AND REFERENCE:
{sources_text}

REQUIREMENTS:
- Start with the most important insight or implication
- Reference sources explicitly (e.g., "According to TechCrunch...")
- Include original URL references where relevant
- Write in {writer_personality} voice throughout
- Focus on what this means for readers TODAY
- Include one actionable takeaway
- Keep it punchy and scannable

VERIFICATION NOTES:
- These sources have been checked for accessibility
- Cite the publication name and reference key facts
- If you question any claims, note it explicitly

Format your response as:
TITLE: [Compelling, {writer_personality}-voice title]

CONTENT:
[Your tl;dr article in {writer_personality} voice]"""

    def _build_blog_prompt(self, topic: RankedTopic, writer_personality: str) -> str:
        """Build prompt for blog article generation with personality"""
        sources_text = "\n".join(
            [
                f"- {source.name}: {source.title}\n  URL: {source.url}\n  Summary: {source.summary or 'No summary available'}"
                for source in topic.sources[:4]  # More sources for blog content
            ]
        )

        personality_prompt = config.WRITER_PERSONALITIES.get(
            writer_personality, config.WRITER_PERSONALITIES["professional"]
        )

        return f"""Write a comprehensive blog article about: {topic.topic}

WRITER PERSONALITY: {writer_personality} - {personality_prompt}
TARGET: Engaged readers who want detailed analysis
LENGTH: 600-1000 words
STRUCTURE: Engaging title, introduction, 3-4 main sections, conclusion with implications

SOURCE MATERIAL TO VERIFY AND REFERENCE:
{sources_text}

REQUIREMENTS:
- Write entirely in {writer_personality} voice and perspective
- Reference all sources explicitly with publication names
- Include original analysis beyond just summarizing sources
- Add context and implications specific to your {writer_personality} viewpoint
- Use subheadings for better readability
- Include concrete examples where possible
- End with forward-looking insights

Format your response as:
TITLE: [Comprehensive {writer_personality}-voice title]

CONTENT:
[Your detailed blog article in {writer_personality} voice with clear sections]"""

    def _build_deepdive_prompt(
        self, topic: RankedTopic, writer_personality: str
    ) -> str:
        """Build prompt for deep dive article generation with personality"""
        sources_text = "\n".join(
            [
                f"- {source.name}: {source.title}\n  URL: {source.url}\n  Summary: {source.summary or 'No summary available'}"
                for source in topic.sources  # All sources for deep dive
            ]
        )

        personality_prompt = config.WRITER_PERSONALITIES.get(
            writer_personality, config.WRITER_PERSONALITIES["professional"]
        )

        return f"""Write an analytical deep dive about: {topic.topic}

WRITER PERSONALITY: {writer_personality} - {personality_prompt}
TARGET: Subject matter experts and decision-makers
LENGTH: 1500-2500 words
STRUCTURE: Executive summary, background, detailed analysis, implications, conclusion

SOURCE MATERIAL TO VERIFY AND REFERENCE:
{sources_text}

REQUIREMENTS:
- Maintain {writer_personality} perspective throughout
- Provide comprehensive source attribution
- Include multiple viewpoints and counterarguments
- Add substantial original analysis from {writer_personality} perspective
- Use data and specific examples extensively
- Include historical context where relevant
- Discuss future trends and implications
- Structure with clear headings and subheadings

Format your response as:
TITLE: [Analytical {writer_personality}-voice title]

CONTENT:
[Your comprehensive deep dive in {writer_personality} voice with clear structure]"""

    async def _call_openai(
        self, prompt: str, model: str = "gpt-3.5-turbo", max_tokens: int = 1500
    ) -> str:
        """Call OpenAI API - preferably Azure OpenAI Service"""
        # Try Azure OpenAI first (preferred for Azure hosting)
        if self.azure_openai_client:
            try:
                response = await self.azure_openai_client.chat.completions.create(
                    model=config.AZURE_OPENAI_DEPLOYMENT_NAME,  # Use deployment name for Azure
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert content writer specializing in technology and business analysis.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(
                    f"Azure OpenAI API error, falling back to OpenAI direct: {str(e)}"
                )

        # Fallback to OpenAI direct API
        if not self.openai_client:
            raise ValueError("No OpenAI client configured (Azure or direct)")

        try:
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert content writer specializing in technology and business analysis.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise

    async def _call_claude(self, prompt: str, max_tokens: int = 4000) -> str:
        """Call Claude API"""
        if not self.claude_client:
            raise ValueError("Claude client not configured")

        try:
            response = await self.claude_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude API error: {str(e)}")
            raise

    def _parse_ai_response(self, response: str) -> tuple[str, str]:
        """Parse AI response to extract title and content"""
        if "TITLE:" in response and "CONTENT:" in response:
            parts = response.split("CONTENT:", 1)
            title_part = parts[0].replace("TITLE:", "").strip()
            content_part = parts[1].strip()
            return title_part, content_part
        else:
            # Fallback: use first line as title
            lines = response.strip().split("\n")
            title = lines[0].strip("# ").strip()
            content = "\n".join(lines[1:]).strip()
            return title, content

    async def process_batch(
        self, batch_request: BatchGenerationRequest
    ) -> BatchGenerationResponse:
        """Process batch generation request"""
        batch_id = batch_request.batch_id
        topics = batch_request.ranked_topics

        # Initialize status tracking
        self.active_generations[batch_id] = GenerationStatus(
            batch_id=batch_id,
            status="processing",
            total_topics=len(topics),
            started_at=datetime.utcnow(),
        )

        generated_content = []

        try:
            # Process topics (limit concurrency)
            semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_GENERATIONS)

            async def generate_with_semaphore(topic):
                async with semaphore:
                    return await self.generate_content(topic)

            # Generate content for all topics
            tasks = [generate_with_semaphore(topic) for topic in topics]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Failed to generate content for topic {i}: {str(result)}"
                    )
                else:
                    generated_content.append(result)

                # Update progress
                self.active_generations[batch_id].completed_topics = i + 1
                self.active_generations[batch_id].progress = (i + 1) / len(topics)

            # Mark as completed
            self.active_generations[batch_id].status = "completed"
            self.active_generations[batch_id].completed_at = datetime.utcnow()

            response = BatchGenerationResponse(
                batch_id=batch_id,
                generated_content=generated_content,
                total_articles=len(generated_content),
                generation_time=datetime.utcnow(),
                stats={
                    "requested_topics": len(topics),
                    "generated_articles": len(generated_content),
                    "success_rate": len(generated_content) / len(topics),
                    "avg_word_count": sum(c.word_count for c in generated_content)
                    / len(generated_content)
                    if generated_content
                    else 0,
                },
            )

            # Save to blob storage
            await self._save_generated_content(response)

            return response

        except Exception as e:
            self.active_generations[batch_id].status = "failed"
            self.active_generations[batch_id].error_message = str(e)
            logger.error(f"Batch generation failed for {batch_id}: {str(e)}")
            raise

    async def _save_generated_content(self, response: BatchGenerationResponse):
        """Save generated content to blob storage"""
        try:
            # Create blob name with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            blob_name = f"generator_{timestamp}_{response.batch_id}.json"

            # Convert to JSON data
            content_data = response.model_dump(mode="json")

            # Upload to blob storage using shared library
            self.blob_client.upload_json(
                container_name=config.GENERATED_CONTENT_CONTAINER,
                blob_name=blob_name,
                data=content_data,
                metadata={
                    "batch_id": response.batch_id,
                    "generation_type": "content_generator",
                    "article_count": str(len(response.generated_content)),
                },
            )

            logger.info(f"Generated content saved to blob: {blob_name}")

        except Exception as e:
            logger.error(f"Failed to save generated content: {str(e)}")
            raise

    def get_generation_status(self, batch_id: str) -> Optional[GenerationStatus]:
        """Get status of a generation batch"""
        return self.active_generations.get(batch_id)

    async def start_watching(self):
        """Start watching for new ranked content using Service Bus events or polling fallback"""
        if not self.is_running:
            self.is_running = True

            # Try to start Service Bus event processor first
            service_bus_started = await self.event_processor.start()

            if service_bus_started:
                logger.info("Started real-time blob event processing via Service Bus")
            else:
                # Fallback to polling if Service Bus is not available
                self.watch_task = asyncio.create_task(
                    self._watch_for_new_ranked_content()
                )
                logger.info("Started polling-based blob watching (fallback)")

    async def stop_watching(self):
        """Stop watching for new content"""
        self.is_running = False

        # Stop Service Bus event processor
        await self.event_processor.stop()

        # Stop polling task if running
        if self.watch_task:
            self.watch_task.cancel()
            try:
                await self.watch_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped watching for new ranked content")

    async def _watch_for_new_ranked_content(self):
        """Watch for new ranked content blobs and automatically generate content"""
        last_processed_time = (
            datetime.utcnow().timestamp() - 3600
        )  # Start from 1 hour ago

        while self.is_running:
            try:
                logger.debug("Checking for new ranked content...")

                # List blobs in ranked-content container
                blobs = self.blob_client.list_blobs(config.RANKED_CONTENT_CONTAINER)

                new_blobs = []
                for blob in blobs:
                    # Check if blob is newer than last processed time
                    blob_time = blob.get("last_modified")
                    if blob_time and hasattr(blob_time, "timestamp"):
                        if blob_time.timestamp() > last_processed_time:
                            new_blobs.append(blob)

                # Process new blobs
                for blob in new_blobs:
                    try:
                        await self._process_ranked_content_blob(blob["name"])
                        last_processed_time = max(
                            last_processed_time, blob["last_modified"].timestamp()
                        )
                        logger.info(f"Processed ranked content blob: {blob['name']}")
                    except Exception as e:
                        logger.error(f"Failed to process blob {blob['name']}: {e}")

                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in ranked content watcher: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _process_ranked_content_blob(self, blob_name: str):
        """Process a single ranked content blob and generate content"""
        try:
            # Download and parse the ranked content
            ranked_data = self.blob_client.download_json(
                config.RANKED_CONTENT_CONTAINER, blob_name
            )

            if not ranked_data or "topics" not in ranked_data:
                logger.warning(f"No topics found in blob {blob_name}")
                return

            # Convert to RankedTopic objects
            topics = []
            for topic_data in ranked_data["topics"]:
                try:
                    topic = RankedTopic(**topic_data)
                    topics.append(topic)
                except Exception as e:
                    logger.warning(f"Failed to parse topic from {blob_name}: {e}")
                    continue

            if not topics:
                logger.warning(f"No valid topics found in blob {blob_name}")
                return

            # Generate content for each topic
            generated_content = []
            # Limit to top 5 topics to avoid overwhelming AI services
            for topic in topics[:5]:
                try:
                    # Determine best content type based on topic complexity
                    content_type = self._determine_content_type(topic)

                    # Generate content
                    content = await self.generate_content(
                        topic=topic,
                        content_type=content_type,
                        writer_personality="professional",
                    )
                    generated_content.append(content)

                except Exception as e:
                    logger.error(
                        f"Failed to generate content for topic '{topic.topic}': {e}"
                    )
                    continue

            if generated_content:
                # Create batch response
                batch_id = f"auto_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                response = BatchGenerationResponse(
                    batch_id=batch_id,
                    generated_content=generated_content,
                    total_articles=len(generated_content),
                    generation_time=datetime.utcnow(),
                    stats={
                        "source_blob": blob_name,
                        "trigger": "blob_event",
                        "processed_topics": len(topics),
                        "generated_articles": len(generated_content),
                    },
                )

                # Save to blob storage
                await self._save_generated_content(response)
                logger.info(
                    f"Generated {len(generated_content)} articles from {blob_name}"
                )

        except Exception as e:
            logger.error(f"Failed to process ranked content blob {blob_name}: {e}")
            raise

    def _determine_content_type(self, topic: RankedTopic) -> str:
        """Determine the best content type based on topic characteristics"""
        # Simple heuristic - could be made more sophisticated
        source_count = len(topic.sources)

        if source_count >= 3:
            return "deepdive"  # Rich sources = detailed article
        elif source_count >= 2:
            return "blog"  # Medium sources = blog post
        else:
            return "tldr"  # Limited sources = short summary


# Global service instance
content_generator = ContentGeneratorService()

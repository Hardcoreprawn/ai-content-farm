import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from ai_clients import AIClientManager
from blob_events import BlobEventProcessor
from content_generators import ContentGenerators

from libs.blob_storage import BlobStorageClient, get_blob_client

from config import config
from models import (
    BatchGenerationRequest,
    BatchGenerationResponse,
    GeneratedContent,
    GenerationRequest,
    GenerationStatus,
    RankedTopic,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentGeneratorService:
    """Core content generation service focused on short-form articles"""

    def __init__(
        self,
        blob_client: Optional[BlobStorageClient] = None,
        azure_openai_client: Optional[Any] = None,
        openai_client: Optional[Any] = None,
        claude_client: Optional[Any] = None,
        http_client: Optional[Any] = None,
    ):
        """Initialize the content generator service.

        Args:
            blob_client: Optional blob storage client for dependency injection.
            azure_openai_client: Optional Azure OpenAI client.
            openai_client: Optional OpenAI client.
            claude_client: Optional Claude client.
            http_client: Optional HTTP client.
        """
        # Initialize blob storage client
        if blob_client:
            self.blob_client = blob_client
        elif os.getenv("PYTEST_CURRENT_TEST"):  # Running in pytest
            from tests.mocks import MockBlobStorageClient

            self.blob_client = MockBlobStorageClient()
        else:
            self.blob_client = get_blob_client()

        self.is_running = False
        self.watch_task = None
        self.event_processor = BlobEventProcessor(self)

        # Initialize AI client manager
        self.ai_clients = AIClientManager(
            azure_openai_client=azure_openai_client,
            openai_client=openai_client,
            claude_client=claude_client,
            http_client=http_client,
        )

        # Initialize content generators
        self.content_generators = ContentGenerators(self.ai_clients)

        # Initialize tracking data
        self.active_generations: Dict[str, GenerationStatus] = {}

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
            if not self.content_generators.has_sufficient_content(topic, content_type):
                raise ValueError(
                    f"Insufficient source material for {content_type} article on {topic.topic}"
                )

            # Verify sources if enabled
            verification_status = "pending"
            fact_check_notes = []

            if config.ENABLE_SOURCE_VERIFICATION:
                verification_status, fact_check_notes = (
                    await self.ai_clients.verify_sources(topic.sources)
                )

            # Generate the content
            if content_type == "tldr":
                content = await self.content_generators.generate_tldr(
                    topic, writer_personality
                )
            elif content_type == "blog":
                content = await self.content_generators.generate_blog(
                    topic, writer_personality
                )
            elif content_type == "deepdive":
                content = await self.content_generators.generate_deepdive(
                    topic, writer_personality
                )
            else:
                raise ValueError(f"Unknown content type: {content_type}")

            # Add verification results
            content.verification_status = verification_status
            content.fact_check_notes = fact_check_notes

            return content

        except Exception as e:
            logger.error(f"Error generating content for {topic.topic}: {str(e)}")
            raise e

    async def process_batch_generation(
        self, request: BatchGenerationRequest
    ) -> BatchGenerationResponse:
        """Process a batch of content generation requests.

        Args:
            request: The batch generation request

        Returns:
            BatchGenerationResponse with all generated content
        """
        logger.info(
            f"Processing batch generation for {len(request.ranked_topics)} topics"
        )

        batch_id = request.batch_id

        # Track batch progress
        self.active_generations[batch_id] = GenerationStatus(
            batch_id=batch_id,
            status="processing",
            total_topics=len(request.ranked_topics),
            started_at=datetime.utcnow(),
        )

        generated_content = []
        failed_topics = []

        try:
            # Process topics with concurrency control
            semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_GENERATIONS)

            async def generate_single(topic: RankedTopic) -> Optional[GeneratedContent]:
                async with semaphore:
                    try:
                        # Extract generation parameters from config
                        content_type = request.generation_config.get(
                            "content_type", "tldr"
                        )
                        writer_personality = request.generation_config.get(
                            "writer_personality", "professional"
                        )

                        content = await self.generate_content(
                            topic,
                            content_type=content_type,
                            writer_personality=writer_personality,
                        )
                        self.active_generations[batch_id].completed_topics += 1
                        return content
                    except Exception as e:
                        logger.error(
                            f"Failed to generate content for {topic.topic}: {str(e)}"
                        )
                        failed_topics.append(topic.topic)
                        return None

            # Execute all generations concurrently
            tasks = [generate_single(topic) for topic in request.ranked_topics]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out None results and exceptions
            generated_content = [
                result for result in results if isinstance(result, GeneratedContent)
            ]

            # Update final status
            self.active_generations[batch_id].status = "completed"
            self.active_generations[batch_id].completed_at = datetime.utcnow()

            logger.info(
                f"Batch {batch_id} completed: {len(generated_content)} succeeded, {len(failed_topics)} failed"
            )

            return BatchGenerationResponse(
                batch_id=batch_id,
                generated_content=generated_content,
                total_articles=len(request.ranked_topics),
                generation_time=datetime.utcnow(),
                stats={
                    "success_count": len(generated_content),
                    "failure_count": len(failed_topics),
                    "total_count": len(request.ranked_topics),
                    "failed_topics": failed_topics,
                },
            )

        except Exception as e:
            # Update status on failure
            self.active_generations[batch_id].status = "failed"
            self.active_generations[batch_id].completed_at = datetime.utcnow()
            self.active_generations[batch_id].error_message = str(e)
            logger.error(f"Batch {batch_id} failed: {str(e)}")
            raise e

    def get_generation_status(self, batch_id: str) -> Optional[GenerationStatus]:
        """Get the status of a specific batch generation"""
        return self.active_generations.get(batch_id)

    def list_active_generations(self) -> List[GenerationStatus]:
        """List all active generations"""
        return list(self.active_generations.values())

    async def stop_generation(self, batch_id: str) -> bool:
        """Stop a running batch generation"""
        if batch_id in self.active_generations:
            self.active_generations[batch_id].status = "failed"
            self.active_generations[batch_id].completed_at = datetime.utcnow()
            self.active_generations[batch_id].error_message = "Cancelled by user"
            logger.info(f"Stopped batch generation {batch_id}")
            return True
        return False

    # Legacy method aliases for backward compatibility
    async def _call_openai(
        self, prompt: str, model: str = "gpt-3.5-turbo", max_tokens: int = 1500
    ) -> str:
        """Legacy method - use ai_clients.call_openai instead"""
        return await self.ai_clients.call_openai(prompt, model, max_tokens)

    async def _call_claude(self, prompt: str, max_tokens: int = 4000) -> str:
        """Legacy method - use ai_clients.call_claude instead"""
        return await self.ai_clients.call_claude(prompt, max_tokens)

    def _has_sufficient_content(self, topic: RankedTopic, content_type: str) -> bool:
        """Legacy method - use content_generators.has_sufficient_content instead"""
        return self.content_generators.has_sufficient_content(topic, content_type)

    def _parse_ai_response(self, response: str) -> tuple[str, str]:
        """Legacy method - use content_generators.parse_ai_response instead"""
        return self.content_generators.parse_ai_response(response)

    async def _generate_tldr(
        self, topic: RankedTopic, writer_personality: str
    ) -> GeneratedContent:
        """Legacy method - use content_generators.generate_tldr instead"""
        return await self.content_generators.generate_tldr(topic, writer_personality)

    async def _generate_blog(
        self, topic: RankedTopic, writer_personality: str
    ) -> GeneratedContent:
        """Legacy method - use content_generators.generate_blog instead"""
        return await self.content_generators.generate_blog(topic, writer_personality)

    async def _generate_deepdive(
        self, topic: RankedTopic, writer_personality: str
    ) -> GeneratedContent:
        """Legacy method - use content_generators.generate_deepdive instead"""
        return await self.content_generators.generate_deepdive(
            topic, writer_personality
        )

    async def cleanup(self):
        """Clean up resources"""
        await self.ai_clients.cleanup()


# Global service instance for backward compatibility with main.py
# Only create if not in test mode and environment is properly configured
def get_content_generator():
    """Get or create the global content generator instance."""
    global _content_generator
    if "_content_generator" not in globals():
        _content_generator = ContentGeneratorService()
    return _content_generator


# Lazy initialization for backward compatibility
try:
    if not os.getenv("PYTEST_CURRENT_TEST") and not os.getenv("SKIP_GLOBAL_INIT"):
        content_generator = ContentGeneratorService()
    else:
        content_generator = None
except Exception:
    # In case of configuration issues during module import
    content_generator = None

#!/usr/bin/env python3
"""
Content Processing Service

Implements the core content processing logic with AI integration.
Uses tenacity for retry logic and supports multi-region OpenAI endpoints.

Features:
- Content analysis and enhancement
- Multi-model AI processing
- Quality scoring and evaluation
- Cost tracking and optimization
- Error recovery and fallback
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from external_api_client import ExternalAPIClient, OpenAIAPIError

from config import ContentProcessorSettings

logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    """Content processing status."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ProcessingResult:
    """Result of content processing operation."""

    topic_id: str
    status: ProcessingStatus
    processed_content: Optional[str] = None
    quality_score: Optional[float] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    model_used: Optional[str] = None
    cost_estimate: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ProcessingRequest:
    """Content processing request."""

    topic_id: str
    content: str
    metadata: Dict[str, Any]
    max_tokens: int = 1000
    temperature: float = 0.7
    model_preference: Optional[str] = None


class ContentProcessingService:
    """
    Core content processing service with AI integration.

    Handles content enhancement, analysis, and quality evaluation.
    """

    def __init__(self, settings: ContentProcessorSettings):
        self.settings = settings
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize external API client
        self.api_client = ExternalAPIClient(settings)

        # Processing stats
        self.processing_stats = {
            "total_processed": 0,
            "successful_completions": 0,
            "failed_completions": 0,
            "total_cost": 0.0,
            "average_quality": 0.0,
            "average_processing_time": 0.0,
        }

        # Quality thresholds
        self.quality_threshold = settings.quality_threshold
        self.max_retries = 2

    async def close(self):
        """Close external resources."""
        await self.api_client.close()

    async def process_content(self, request: ProcessingRequest) -> ProcessingResult:
        """
        Process content with AI enhancement and quality evaluation.

        Args:
            request: Processing request with content and parameters

        Returns:
            Processing result with enhanced content and metrics
        """
        start_time = time.time()

        self.logger.info(f"Starting processing for topic: {request.topic_id}")

        try:
            # Validate request
            if not request.content.strip():
                return ProcessingResult(
                    topic_id=request.topic_id,
                    status=ProcessingStatus.FAILED,
                    error_message="Empty content provided",
                    processing_time=time.time() - start_time,
                )

            # Choose model based on content characteristics
            model = self._select_optimal_model(request)

            # Generate enhanced content
            enhanced_content = await self._enhance_content(request, model)

            # Evaluate quality
            quality_score = await self._evaluate_quality(
                enhanced_content, request.content
            )

            # Check if quality meets threshold
            if quality_score < self.quality_threshold:
                self.logger.warning(
                    f"Quality score {quality_score:.2f} below threshold {self.quality_threshold} "
                    f"for {request.topic_id}"
                )

                # Retry with different model if quality is low
                if self.max_retries > 0:
                    self.logger.info(
                        f"Retrying with different model for {request.topic_id}"
                    )
                    fallback_model = self._get_fallback_model(model)
                    enhanced_content = await self._enhance_content(
                        request, fallback_model
                    )
                    quality_score = await self._evaluate_quality(
                        enhanced_content, request.content
                    )

            # Calculate cost estimate
            cost_estimate = self._estimate_cost(enhanced_content, model)

            # Track stats
            processing_time = time.time() - start_time
            self._update_processing_stats(
                quality_score, processing_time, cost_estimate, True
            )

            result = ProcessingResult(
                topic_id=request.topic_id,
                status=ProcessingStatus.COMPLETED,
                processed_content=enhanced_content,
                quality_score=quality_score,
                processing_time=processing_time,
                model_used=model,
                cost_estimate=cost_estimate,
                metadata={
                    "original_length": len(request.content),
                    "enhanced_length": len(enhanced_content),
                    "enhancement_ratio": len(enhanced_content)
                    / max(len(request.content), 1),
                    "processing_timestamp": time.time(),
                },
            )

            self.logger.info(
                f"Completed processing for {request.topic_id}: "
                f"quality={quality_score:.2f}, time={processing_time:.2f}s"
            )

            return result

        except asyncio.TimeoutError:
            processing_time = time.time() - start_time
            self._update_processing_stats(0.0, processing_time, 0.0, False)

            return ProcessingResult(
                topic_id=request.topic_id,
                status=ProcessingStatus.TIMEOUT,
                error_message=f"Processing timeout after {self.settings.processing_timeout_seconds}s",
                processing_time=processing_time,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            self._update_processing_stats(0.0, processing_time, 0.0, False)

            self.logger.error(f"Processing failed for {request.topic_id}: {e}")

            return ProcessingResult(
                topic_id=request.topic_id,
                status=ProcessingStatus.FAILED,
                error_message=str(e),
                processing_time=processing_time,
            )

    def _select_optimal_model(self, request: ProcessingRequest) -> str:
        """Select optimal AI model based on content characteristics."""
        # Use preference if provided
        if request.model_preference:
            return request.model_preference

        content_length = len(request.content)

        # Select model based on content length and complexity
        if content_length < 500:
            return "gpt-3.5-turbo"  # Fast and cost-effective for short content
        elif content_length < 2000:
            return "gpt-4"  # Balanced for medium content
        else:
            return "gpt-4-turbo"  # Best quality for long content

    def _get_fallback_model(self, current_model: str) -> str:
        """Get fallback model for quality improvement."""
        fallback_map = {
            "gpt-3.5-turbo": "gpt-4",
            "gpt-4": "gpt-4-turbo",
            "gpt-4-turbo": "gpt-4",  # Fallback to standard GPT-4
        }
        return fallback_map.get(current_model, "gpt-4")

    async def _enhance_content(self, request: ProcessingRequest, model: str) -> str:
        """Enhance content using AI with timeout protection."""

        # Create enhancement prompt
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a professional content editor and writer. "
                    "Enhance the provided content by improving clarity, structure, "
                    "and readability while maintaining the original meaning and intent. "
                    "Add relevant details and insights where appropriate."
                ),
            },
            {
                "role": "user",
                "content": f"Please enhance this content:\n\n{request.content}",
            },
        ]

        # Use timeout protection
        try:
            response = await asyncio.wait_for(
                self.api_client.chat_completion(
                    messages=messages,
                    model=model,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                ),
                timeout=self.settings.processing_timeout_seconds,
            )

            # Extract content from response
            if "choices" in response and len(response["choices"]) > 0:
                enhanced_content = response["choices"][0]["message"]["content"]
                return enhanced_content.strip()
            else:
                raise OpenAIAPIError("No valid response from OpenAI API")

        except asyncio.TimeoutError:
            self.logger.error(f"Content enhancement timeout for {request.topic_id}")
            raise
        except Exception as e:
            self.logger.error(f"Content enhancement failed for {request.topic_id}: {e}")
            raise

    async def _evaluate_quality(
        self, enhanced_content: str, original_content: str
    ) -> float:
        """Evaluate content quality using AI analysis."""

        try:
            # Simple quality metrics for now
            # TODO: Implement sophisticated AI-based quality evaluation

            # Basic quality indicators
            length_improvement = len(enhanced_content) / max(len(original_content), 1)
            structure_score = self._assess_structure(enhanced_content)
            readability_score = self._assess_readability(enhanced_content)

            # Weighted quality score
            quality_score = (
                min(length_improvement, 2.0) * 0.3  # Cap at 2x length improvement
                + structure_score * 0.4
                + readability_score * 0.3
            )

            return min(quality_score, 1.0)  # Cap at 1.0

        except Exception as e:
            self.logger.warning(f"Quality evaluation failed: {e}")
            return 0.5  # Default moderate score

    def _assess_structure(self, content: str) -> float:
        """Assess content structure quality."""
        # Simple structure assessment
        lines = content.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        # Check for paragraphs
        paragraph_score = min(len(non_empty_lines) / 5, 1.0)  # Prefer 5+ paragraphs

        # Check for proper sentence structure
        sentences = content.split(".")
        sentence_score = min(len(sentences) / 10, 1.0)  # Prefer 10+ sentences

        return (paragraph_score + sentence_score) / 2

    def _assess_readability(self, content: str) -> float:
        """Assess content readability."""
        # Simple readability assessment
        words = content.split()
        sentences = content.split(".")

        if len(sentences) == 0:
            return 0.0

        # Average words per sentence (ideal: 15-20)
        avg_words_per_sentence = len(words) / len(sentences)
        readability_score = 1.0 - abs(avg_words_per_sentence - 17.5) / 17.5

        return max(0.0, min(1.0, readability_score))

    def _estimate_cost(self, content: str, model: str) -> float:
        """Estimate processing cost based on tokens and model."""
        # Rough token estimation (1 token ≈ 4 characters for English)
        estimated_tokens = len(content) / 4

        # Pricing per 1K tokens (approximate)
        pricing = {
            "gpt-3.5-turbo": 0.0015,  # $0.0015 per 1K tokens
            "gpt-4": 0.03,  # $0.03 per 1K tokens
            "gpt-4-turbo": 0.01,  # $0.01 per 1K tokens
        }

        rate = pricing.get(model, 0.01)
        return (estimated_tokens / 1000) * rate

    def _update_processing_stats(
        self, quality: float, processing_time: float, cost: float, success: bool
    ):
        """Update processing statistics."""
        self.processing_stats["total_processed"] += 1

        if success:
            self.processing_stats["successful_completions"] += 1

            # Update averages
            total_successful = self.processing_stats["successful_completions"]

            self.processing_stats["average_quality"] = (
                self.processing_stats["average_quality"] * (total_successful - 1)
                + quality
            ) / total_successful

            self.processing_stats["average_processing_time"] = (
                self.processing_stats["average_processing_time"]
                * (total_successful - 1)
                + processing_time
            ) / total_successful
        else:
            self.processing_stats["failed_completions"] += 1

        self.processing_stats["total_cost"] += cost

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics."""
        api_stats = self.api_client.get_stats()

        return {
            **self.processing_stats,
            "success_rate": (
                self.processing_stats["successful_completions"]
                / max(self.processing_stats["total_processed"], 1)
            )
            * 100,
            "api_client_stats": api_stats,
        }

    async def process_batch(
        self, requests: List[ProcessingRequest]
    ) -> List[ProcessingResult]:
        """
        Process multiple requests concurrently.

        Args:
            requests: List of processing requests

        Returns:
            List of processing results
        """
        self.logger.info(f"Processing batch of {len(requests)} requests")

        # Limit concurrent processing
        semaphore = asyncio.Semaphore(self.settings.max_concurrent_processes)

        async def process_with_semaphore(
            request: ProcessingRequest,
        ) -> ProcessingResult:
            async with semaphore:
                return await self.process_content(request)

        # Process all requests concurrently
        results = await asyncio.gather(
            *[process_with_semaphore(req) for req in requests],
            return_exceptions=True,
        )

        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    ProcessingResult(
                        topic_id=requests[i].topic_id,
                        status=ProcessingStatus.FAILED,
                        error_message=str(result),
                    )
                )
            else:
                processed_results.append(result)

        self.logger.info(
            f"Batch processing completed: {len(processed_results)} results"
        )
        return processed_results

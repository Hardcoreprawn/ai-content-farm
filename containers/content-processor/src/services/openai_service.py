#!/usr/bin/env python3
"""
OpenAI Service for Content Processing

Provides robust OpenAI integration with multi-region support, retry logic,
and intelligent model selection based on content complexity.

This replaces the mock processing with real AI-powered content generation.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import openai
from src.config import settings
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class ProcessingType(Enum):
    """Content processing types with different complexity levels."""

    GENERAL = "general"
    ARTICLE_GENERATION = "article_generation"
    CONTENT_ANALYSIS = "content_analysis"
    TOPIC_EXPANSION = "topic_expansion"
    QUALITY_ASSESSMENT = "quality_assessment"


class ModelTier(Enum):
    """AI model tiers for different processing requirements."""

    STANDARD = "standard"  # Cost-efficient models (UK South)
    ADVANCED = "advanced"  # High-quality models (West Europe)
    PREMIUM = "premium"  # Latest models for complex tasks


class ContentProcessor:
    """
    AI-powered content processor with multi-region OpenAI support.

    Features:
    - Intelligent model selection based on content complexity
    - Multi-region failover (UK South -> West Europe)
    - Retry logic with exponential backoff
    - Cost tracking and quality assessment
    - Voice consistency management
    """

    def __init__(self):
        self.client = None
        self.model_configs = self._setup_model_configurations()
        self.processing_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_cost": 0.0,
            "region_usage": {"uk_south": 0, "west_europe": 0, "primary": 0},
        }

    def _setup_model_configurations(self) -> Dict[str, Dict]:
        """Configure available AI models with cost and capability info."""
        return {
            "gpt-3.5-turbo": {
                "tier": ModelTier.STANDARD,
                "cost_per_1k_tokens": 0.0015,  # Input tokens
                "max_tokens": 4096,
                "suitable_for": [
                    ProcessingType.GENERAL,
                    ProcessingType.CONTENT_ANALYSIS,
                ],
                "region": "uk_south",
            },
            "gpt-4": {
                "tier": ModelTier.ADVANCED,
                "cost_per_1k_tokens": 0.03,
                "max_tokens": 8192,
                "suitable_for": [
                    ProcessingType.ARTICLE_GENERATION,
                    ProcessingType.QUALITY_ASSESSMENT,
                ],
                "region": "west_europe",
            },
            "gpt-4-turbo": {
                "tier": ModelTier.PREMIUM,
                "cost_per_1k_tokens": 0.01,
                "max_tokens": 128000,
                "suitable_for": [
                    ProcessingType.TOPIC_EXPANSION,
                    ProcessingType.ARTICLE_GENERATION,
                ],
                "region": "west_europe",
            },
        }

    async def _initialize_client(self, region: str = "primary") -> bool:
        """Initialize OpenAI client for specified region."""
        try:
            endpoint = settings.get_openai_endpoint_for_region(region)

            if not endpoint and region == "primary":
                endpoint = settings.azure_openai_endpoint

            if not endpoint:
                logger.warning(f"No endpoint configured for region: {region}")
                return False

            # Initialize Azure OpenAI client
            self.client = openai.AsyncAzureOpenAI(
                azure_endpoint=endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )

            logger.info(f"OpenAI client initialized for region: {region}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client for {region}: {e}")
            return False

    def _select_model_for_processing(
        self, processing_type: ProcessingType, content_length: int
    ) -> str:
        """Intelligently select AI model based on processing type and content complexity."""

        # Content complexity assessment
        is_complex = content_length > 1000 or processing_type in [
            ProcessingType.ARTICLE_GENERATION,
            ProcessingType.TOPIC_EXPANSION,
        ]

        # Model selection logic
        if processing_type == ProcessingType.QUALITY_ASSESSMENT:
            return "gpt-4"  # Need advanced reasoning for quality assessment
        elif is_complex and processing_type == ProcessingType.ARTICLE_GENERATION:
            return "gpt-4-turbo"  # Large context for article generation
        elif processing_type in [
            ProcessingType.GENERAL,
            ProcessingType.CONTENT_ANALYSIS,
        ]:
            return "gpt-3.5-turbo"  # Cost-efficient for simpler tasks
        else:
            return "gpt-4"  # Default to advanced model for unknown complexity

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(
            (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _make_openai_request(
        self, model: str, messages: List[Dict], region: str
    ) -> Dict[str, Any]:
        """Make OpenAI request with retry logic and error handling."""

        if not self.client:
            if not await self._initialize_client(region):
                raise Exception(f"Failed to initialize client for region: {region}")

        try:
            start_time = time.time()

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=2000,
                temperature=0.7,
                top_p=0.9,
            )

            processing_time = time.time() - start_time

            # Extract response content
            content = response.choices[0].message.content
            usage = response.usage

            # Calculate cost (simplified)
            model_config = self.model_configs.get(model, {})
            estimated_cost = (usage.total_tokens / 1000) * model_config.get(
                "cost_per_1k_tokens", 0.002
            )

            # Update statistics
            self.processing_stats["total_requests"] += 1
            self.processing_stats["successful_requests"] += 1
            self.processing_stats["total_cost"] += estimated_cost
            self.processing_stats["region_usage"][region] += 1

            return {
                "content": content,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                },
                "model_used": model,
                "region": region,
                "processing_time": processing_time,
                "estimated_cost": estimated_cost,
                "timestamp": time.time(),
            }

        except openai.RateLimitError as e:
            logger.warning(f"Rate limit hit for {model} in {region}: {e}")
            self.processing_stats["failed_requests"] += 1
            raise
        except openai.APITimeoutError as e:
            logger.warning(f"API timeout for {model} in {region}: {e}")
            self.processing_stats["failed_requests"] += 1
            raise
        except Exception as e:
            logger.error(f"OpenAI request failed for {model} in {region}: {e}")
            self.processing_stats["failed_requests"] += 1
            raise

    async def _try_regions_in_order(
        self, model: str, messages: List[Dict]
    ) -> Dict[str, Any]:
        """Try multiple regions for failover capability."""

        model_config = self.model_configs.get(model, {})
        preferred_region = model_config.get("region", "primary")

        # Define region order based on model preference
        regions_to_try = [preferred_region]
        if preferred_region != "primary":
            regions_to_try.append("primary")
        if preferred_region != "uk_south":
            regions_to_try.append("uk_south")
        if preferred_region != "west_europe" and len(regions_to_try) < 2:
            regions_to_try.append("west_europe")

        last_exception = None

        for region in regions_to_try:
            try:
                logger.info(f"Attempting {model} request in region: {region}")
                result = await self._make_openai_request(model, messages, region)
                return result
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Failed to process in {region}, trying next region: {e}"
                )
                # Reset client for next region attempt
                self.client = None

        # If all regions failed, raise the last exception
        logger.error(f"All regions failed for model {model}")
        raise last_exception or Exception("No regions available for processing")

    def _create_processing_prompt(
        self, content: str, processing_type: ProcessingType, options: Dict[str, Any]
    ) -> List[Dict]:
        """Create appropriate prompt based on processing type."""

        system_prompts = {
            ProcessingType.GENERAL: "You are a helpful AI assistant that improves and analyzes content while maintaining its original intent.",
            ProcessingType.ARTICLE_GENERATION: "You are a professional content writer who creates engaging, well-structured articles based on provided topics and guidelines.",
            ProcessingType.CONTENT_ANALYSIS: "You are a content analyst who provides detailed insights about text quality, readability, and effectiveness.",
            ProcessingType.TOPIC_EXPANSION: "You are a research assistant who expands topics into comprehensive, detailed content with multiple perspectives.",
            ProcessingType.QUALITY_ASSESSMENT: "You are a quality assessor who evaluates content on multiple dimensions and provides actionable feedback.",
        }

        # Get writing voice/style from options
        voice = options.get("voice", "professional")
        target_audience = options.get("target_audience", "general")
        max_length = options.get("max_length", 1000)

        user_prompt = self._build_user_prompt(
            content, processing_type, voice, target_audience, max_length
        )

        return [
            {
                "role": "system",
                "content": system_prompts.get(
                    processing_type, system_prompts[ProcessingType.GENERAL]
                ),
            },
            {"role": "user", "content": user_prompt},
        ]

    def _build_user_prompt(
        self,
        content: str,
        processing_type: ProcessingType,
        voice: str,
        audience: str,
        max_length: int,
    ) -> str:
        """Build detailed user prompt for specific processing type."""

        base_prompt = f"Content to process:\n\n{content}\n\n"

        if processing_type == ProcessingType.ARTICLE_GENERATION:
            return f"""{base_prompt}
Please create a comprehensive article based on this topic. Requirements:
- Writing voice: {voice}
- Target audience: {audience}
- Maximum length: approximately {max_length} words
- Include engaging introduction, detailed body sections, and strong conclusion
- Use clear headings and structure
- Maintain factual accuracy and provide valuable insights
"""
        elif processing_type == ProcessingType.CONTENT_ANALYSIS:
            return f"""{base_prompt}
Please analyze this content and provide detailed feedback on:
- Content quality and clarity
- Structure and organization
- Engagement potential
- Target audience alignment
- Suggestions for improvement
- Readability score estimation
"""
        elif processing_type == ProcessingType.QUALITY_ASSESSMENT:
            return f"""{base_prompt}
Please assess this content's quality on a scale of 0-1 and provide:
- Overall quality score with justification
- Strengths and weaknesses
- Specific improvement recommendations
- Compliance with {voice} voice and {audience} audience
"""
        elif processing_type == ProcessingType.TOPIC_EXPANSION:
            return f"""{base_prompt}
Please expand this topic into comprehensive content including:
- Multiple perspectives and angles
- Supporting details and examples
- Relevant context and background
- Writing voice: {voice}
- Target audience: {audience}
- Aim for approximately {max_length} words
"""
        else:  # GENERAL
            return f"""{base_prompt}
Please improve and refine this content while maintaining its original intent:
- Enhance clarity and readability
- Maintain {voice} voice for {audience} audience
- Fix any grammar or style issues
- Keep approximately the same length unless expansion is needed for clarity
"""

    def _assess_quality_score(
        self, processed_content: str, original_content: str, processing_metadata: Dict
    ) -> float:
        """Assess quality score based on various factors."""

        # Basic quality metrics (simplified for now)
        length_score = min(
            len(processed_content) / 500, 1.0
        )  # Prefer substantial content
        processing_time = processing_metadata.get("processing_time", 0)
        time_score = max(
            0.5, 1.0 - (processing_time / 30)
        )  # Prefer reasonable processing time

        # Model-based scoring (higher tier models get slight quality boost)
        model_used = processing_metadata.get("model_used", "")
        model_bonus = 0.0
        if "gpt-4" in model_used:
            model_bonus = 0.1
        elif "turbo" in model_used:
            model_bonus = 0.05

        base_score = 0.7  # Conservative base score
        quality_score = min(
            1.0, base_score + (length_score * 0.2) + (time_score * 0.1) + model_bonus
        )

        return round(quality_score, 2)

    async def process_content(
        self,
        content: str,
        processing_type: str = "general",
        options: Dict[str, Any] = None,
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Main content processing method with real OpenAI integration.

        Returns:
            Tuple of (processed_content, quality_score, processing_metadata)
        """
        if options is None:
            options = {}

        try:
            # Convert string to enum
            proc_type = ProcessingType(processing_type)
        except ValueError:
            proc_type = ProcessingType.GENERAL

        # Select appropriate model
        model = self._select_model_for_processing(proc_type, len(content))

        # Create processing prompt
        messages = self._create_processing_prompt(content, proc_type, options)

        # Process with retry and failover
        result = await self._try_regions_in_order(model, messages)

        # Extract processed content
        processed_content = result["content"]

        # Assess quality
        quality_score = self._assess_quality_score(processed_content, content, result)

        # Build comprehensive metadata
        processing_metadata = {
            "processing_type": processing_type,
            "options": options,
            "model_used": result["model_used"],
            "region": result["region"],
            "processing_time": result["processing_time"],
            "estimated_cost": result["estimated_cost"],
            "token_usage": result["usage"],
            "quality_score": quality_score,
            "timestamp": result["timestamp"],
            "status": "completed",
            "voice": options.get("voice", "professional"),
            "target_audience": options.get("target_audience", "general"),
        }

        logger.info(
            f"Content processed successfully using {model} in {result['region']} "
            f"(quality: {quality_score}, cost: ${result['estimated_cost']:.4f})"
        )

        return processed_content, quality_score, processing_metadata

    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get current processing statistics for monitoring."""
        return {
            **self.processing_stats,
            "success_rate": (
                self.processing_stats["successful_requests"]
                / max(self.processing_stats["total_requests"], 1)
            ),
            "average_cost_per_request": (
                self.processing_stats["total_cost"]
                / max(self.processing_stats["successful_requests"], 1)
            ),
        }


# Global processor instance
processor = ContentProcessor()

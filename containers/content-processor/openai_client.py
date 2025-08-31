"""
OpenAI Client for Content Generation

Clean, functional wrapper around Azure OpenAI for article generation.
Includes cost tracking and error handling following agent instructions.
"""

import logging
import os
from typing import Any, Dict, Optional, Tuple

import openai
from openai import AzureOpenAI

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    Functional OpenAI client with cost tracking.

    Uses Azure OpenAI for article generation with comprehensive
    cost monitoring and secure error handling.
    """

    def __init__(self):
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.model_name = os.getenv("AZURE_OPENAI_MODEL_NAME", "gpt-4")

        # Cost tracking (approximate pricing)
        self.cost_per_1k_tokens = {
            "gpt-4": 0.03,  # Input tokens
            "gpt-4-output": 0.06,  # Output tokens
            "gpt-35-turbo": 0.002,  # Input tokens
            "gpt-35-turbo-output": 0.002,  # Output tokens
        }

        self.client = None
        if self.api_key and self.endpoint:
            try:
                self.client = AzureOpenAI(
                    api_key=self.api_key,
                    api_version=self.api_version,
                    azure_endpoint=self.endpoint,
                )
                logger.info("Azure OpenAI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        else:
            logger.warning("Azure OpenAI credentials not available - using mock mode")

    async def test_connection(self) -> bool:
        """Test OpenAI connectivity with minimal request."""
        if not self.client:
            return False

        try:
            # Simple test completion
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=10,
            )
            return True

        except Exception as e:
            logger.error(f"OpenAI connectivity test failed: {e}")
            return False

    async def generate_article(
        self,
        topic_title: str,
        research_content: Optional[str] = None,
        target_word_count: int = 3000,
        quality_requirements: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[str], float, int]:
        """
        Generate article from topic with cost tracking.

        Returns:
            Tuple[article_content, cost_usd, tokens_used]
        """
        if not self.client:
            logger.warning("OpenAI client not available - returning mock article")
            return self._generate_mock_article(topic_title), 0.0, 0

        try:
            # Build prompt for article generation
            prompt = self._build_article_prompt(
                topic_title, research_content, target_word_count, quality_requirements
            )

            # Generate article
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert writer creating trustworthy, unbiased articles for a personal content curation platform.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4000,  # ~3000 words
                temperature=0.7,
            )

            # Extract results
            article_content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            cost_usd = self._calculate_cost(tokens_used, response.usage.prompt_tokens)

            logger.info(f"Article generated: {tokens_used} tokens, ${cost_usd:.4f}")
            return article_content, cost_usd, tokens_used

        except Exception as e:
            logger.error(f"Article generation failed: {e}", exc_info=True)
            return None, 0.0, 0

    def _build_article_prompt(
        self,
        topic_title: str,
        research_content: Optional[str],
        target_word_count: int,
        quality_requirements: Optional[Dict[str, Any]],
    ) -> str:
        """Build comprehensive prompt for article generation."""
        prompt_parts = [
            f"Write a comprehensive, trustworthy article about: {topic_title}",
            f"Target length: {target_word_count} words",
            "",
            "Requirements:",
            "- Honest and unbiased perspective",
            "- Well-researched with clear sources",
            "- Easy to read for daily content consumption",
            "- Structured with clear headings and sections",
            "- Engaging but not sensationalized",
            "",
        ]

        if research_content:
            prompt_parts.extend(
                [
                    "Research context:",
                    research_content,
                    "",
                ]
            )

        if quality_requirements:
            prompt_parts.append("Additional requirements:")
            for req, value in quality_requirements.items():
                prompt_parts.append(f"- {req}: {value}")
            prompt_parts.append("")

        prompt_parts.extend(
            [
                "Structure the article with:",
                "1. Engaging introduction",
                "2. Main content with clear headings",
                "3. Key insights and analysis",
                "4. Conclusion with takeaways",
                "",
                "Focus on creating content that's valuable for a personal reading grid.",
            ]
        )

        return "\n".join(prompt_parts)

    def _calculate_cost(self, total_tokens: int, prompt_tokens: int) -> float:
        """Calculate approximate cost based on token usage."""
        try:
            output_tokens = total_tokens - prompt_tokens

            # Get base model name for pricing
            base_model = self.model_name.lower()
            if "gpt-4" in base_model:
                input_cost = (prompt_tokens / 1000) * self.cost_per_1k_tokens["gpt-4"]
                output_cost = (output_tokens / 1000) * self.cost_per_1k_tokens[
                    "gpt-4-output"
                ]
            else:
                # Default to GPT-3.5 pricing
                input_cost = (prompt_tokens / 1000) * self.cost_per_1k_tokens[
                    "gpt-35-turbo"
                ]
                output_cost = (output_tokens / 1000) * self.cost_per_1k_tokens[
                    "gpt-35-turbo-output"
                ]

            return input_cost + output_cost

        except Exception as e:
            logger.error(f"Cost calculation failed: {e}")
            return 0.0

    def _generate_mock_article(self, topic_title: str) -> str:
        """Generate mock article for testing when OpenAI unavailable."""
        return f"""
# {topic_title}

This is a mock article generated for testing purposes when Azure OpenAI is not available.

## Introduction

The topic of {topic_title} is an important area that deserves comprehensive coverage. This article provides an overview of the key aspects and considerations.

## Main Content

In this section, we would normally provide detailed analysis and research-based content about {topic_title}.

### Key Points

- Comprehensive research would be conducted
- Multiple sources would be consulted
- Fact-checking would be performed
- Quality assessment would be applied

## Analysis

Real articles would include deeper analysis and insights based on current information and expert perspectives.

## Conclusion

This mock article demonstrates the structure and approach that would be used for real content generation.

---

*This is a test article generated when Azure OpenAI services are not available.*
        """.strip()

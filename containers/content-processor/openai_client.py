"""
OpenAI Client for Content Generation

Clean, functional wrapper around Azure OpenAI for article generation.
Includes cost tracking and error handling following agent instructions.
Uses Azure Managed Identity for secure authentication.
"""

import logging
import os
from typing import Any, Dict, Optional, Tuple

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from markdown_cleaner import fix_malformed_headings
from openai import AsyncAzureOpenAI
from pricing_service import PricingService

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    Functional OpenAI client with cost tracking.

    Uses Azure OpenAI for article generation with comprehensive
    cost monitoring and secure error handling.
    """

    def __init__(self):
        # Azure configuration
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-07-01-preview")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        # Note: For Azure OpenAI, this should be the deployment name, not the model name
        self.model_name = os.getenv("AZURE_OPENAI_CHAT_MODEL", "gpt-35-turbo")

        # Initialize pricing service for accurate cost tracking
        self.pricing_service = PricingService()

        self.client = None
        if self.endpoint:
            try:
                # Use Azure Managed Identity for authentication (Microsoft recommended pattern)
                token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(),
                    "https://cognitiveservices.azure.com/.default",
                )

                self.client = AsyncAzureOpenAI(
                    api_version=self.api_version,
                    azure_endpoint=self.endpoint,
                    azure_ad_token_provider=token_provider,
                )
                logger.info("Azure OpenAI client initialized with managed identity")
            except Exception as e:
                logger.error(
                    f"Failed to initialize OpenAI client with managed identity: {e}"
                )
        else:
            logger.warning("Azure OpenAI endpoint not available - using mock mode")

    async def test_connection(self) -> bool:
        """Test OpenAI connectivity with minimal request."""
        if not self.client:
            return False

        try:
            # Simple test completion
            await self.client.chat.completions.create(
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
            logger.info(f"🤖 OPENAI: Generating article for topic: '{topic_title}'")
            logger.info(
                f"🤖 OPENAI: Using model: {self.model_name}, endpoint: {self.endpoint}"
            )
            logger.info(f"🤖 OPENAI: Target word count: {target_word_count}")

            # Build prompt for article generation
            prompt = self._build_article_prompt(
                topic_title, research_content, target_word_count, quality_requirements
            )
            logger.info(f"📝 PROMPT: Built prompt with {len(prompt)} characters")

            # Generate article
            logger.info("🚀 OPENAI: Sending request to Azure OpenAI...")
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert writer creating trustworthy, "
                            "unbiased articles for a personal content curation platform."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4000,  # ~3000 words
                temperature=0.7,
            )
            logger.info("✅ OPENAI: Received response from Azure OpenAI")

            # Extract results
            article_content = response.choices[0].message.content

            # Clean up malformed headings (fix AI tendency to create paragraph-length H2s)
            if article_content:
                article_content = fix_malformed_headings(article_content)

            tokens_used = response.usage.total_tokens if response.usage else 0
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            content_length = len(article_content) if article_content else 0
            completion_tokens = tokens_used - prompt_tokens
            logger.info(
                f"📊 OPENAI: Generated article with {content_length} characters, "
                f"{tokens_used} tokens ({prompt_tokens} prompt + {completion_tokens} completion)"
            )

            cost_usd = await self._calculate_cost(tokens_used, prompt_tokens)
            logger.info(f"💰 COST: Article generation cost: ${cost_usd:.6f}")

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
                "Structure the article with markdown headings:",
                "IMPORTANT: Use H2 (##) for main sections, H3-H6 (###-######) for subsections.",
                "NEVER use H1 (#) - the page title is already H1.",
                "Keep all headings concise (under 100 characters).",
                "",
                "CRITICAL: After the final H2 conclusion heading, write regular paragraphs.",
                "Do NOT create additional H2 headings that start with 'In conclusion' or 'Ultimately'.",
                "The conclusion content should be normal paragraph text, not headings.",
                "",
                "1. Engaging introduction (paragraph text, no heading needed)",
                "2. Main content with clear H2/H3 section headings",
                "3. Key insights and analysis (H2 heading)",
                "4. Conclusion section (H2 heading) followed by paragraph text",
                "",
                "Focus on creating content that's valuable for a personal reading grid.",
            ]
        )

        return "\n".join(prompt_parts)

    async def _calculate_cost(self, total_tokens: int, prompt_tokens: int) -> float:
        """Calculate accurate cost using cached pricing data."""
        try:
            output_tokens = total_tokens - prompt_tokens

            # Use pricing service for accurate cost calculation
            cost = await self.pricing_service.calculate_cost(
                model_name=self.model_name,
                input_tokens=prompt_tokens,
                output_tokens=output_tokens,
            )

            return cost

        except Exception as e:
            logger.error(f"Cost calculation failed: {e}")
            # Emergency fallback
            return (total_tokens / 1000) * 0.002

    def _generate_mock_article(self, topic_title: str) -> str:
        """Generate mock article for testing when OpenAI unavailable."""
        return f"""
# {topic_title}

This is a mock article generated for testing purposes when Azure OpenAI is not
available.

## Introduction

The topic of {topic_title} is an important area that deserves comprehensive
coverage. This article provides an overview of the key aspects and considerations.

## Main Content

In this section, we would normally provide detailed analysis and research-based
content about {topic_title}.

### Key Points

- Comprehensive research would be conducted
- Multiple sources would be consulted
- Fact-checking would be performed
- Quality assessment would be applied

## Analysis

Real articles would include deeper analysis and insights based on current
information and expert perspectives.

## Conclusion

This mock article demonstrates the structure and approach that would be used for
real content generation.

---

*This is a test article generated when Azure OpenAI services are not available.*
        """.strip()

    async def generate_completion(
        self,
        prompt: str,
        max_tokens: int = 200,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Generate a simple completion for metadata/utility tasks.

        Lightweight method for non-article generation tasks like
        metadata generation, title translation, etc.

        Args:
            prompt: The prompt text
            max_tokens: Maximum tokens to generate (default: 200)
            temperature: Sampling temperature (default: 0.3 for consistency)

        Returns:
            Dict with 'content', 'tokens_used', 'cost_usd'

        Examples:
            >>> response = await client.generate_completion(
            ...     prompt="Translate to English: 米政権内の対中強硬派",
            ...     max_tokens=50
            ... )
            >>> response['content']
            'US China hawks in the administration'
        """
        if not self.client:
            logger.warning("OpenAI client not available - returning mock response")
            return {
                "content": (
                    '{"title": "Mock Title", "description": "Mock description", '
                    '"language": "en"}'
                ),
                "tokens_used": 0,
                "cost_usd": 0.0,
            }

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0

            cost_usd = await self._calculate_cost(tokens_used, prompt_tokens)

            return {
                "content": content,
                "tokens_used": tokens_used,
                "cost_usd": cost_usd,
            }

        except Exception as e:
            logger.error(f"Completion generation failed: {e}")
            return {
                "content": (
                    '{"title": "Error", "description": "Failed to generate", '
                    '"language": "en"}'
                ),
                "tokens_used": 0,
                "cost_usd": 0.0,
            }

    async def close(self):
        """Close the async OpenAI client properly."""
        if self.client:
            await self.client.close()
            logger.info("🔌 OPENAI: Client connection closed")

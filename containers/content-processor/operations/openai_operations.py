"""
Pure functional wrappers for OpenAI API operations.

Stateless functions that wrap Azure OpenAI SDK calls for article generation
and metadata tasks. All configuration passed explicitly, no stored state.

Contract Version: 1.0.0
"""

import logging
from typing import Any, Dict, Optional, Tuple

from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)


# ============================================================================
# Client Factory (Pure function that creates configured client)
# ============================================================================


async def create_openai_client(
    endpoint: str,
    api_version: str = "2024-07-01-preview",
) -> AsyncAzureOpenAI:
    """
    Create configured Azure OpenAI client with managed identity.

    Pure function that creates a new client instance with Azure AD auth.
    Does not store any state.

    Args:
        endpoint: Azure OpenAI endpoint URL
        api_version: Azure OpenAI API version

    Returns:
        Configured AsyncAzureOpenAI client

    Examples:
        >>> client = await create_openai_client(
        ...     endpoint="https://my-resource.openai.azure.com",
        ...     api_version="2024-07-01-preview"
        ... )
        >>> # Use client for API calls
        >>> await client.close()
    """
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )

    return AsyncAzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
    )


# ============================================================================
# Article Generation
# ============================================================================


async def generate_article_content(
    client: AsyncAzureOpenAI,
    model_name: str,
    topic_title: str,
    research_content: Optional[str] = None,
    target_word_count: int = 3000,
    quality_requirements: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[str], int, int]:
    """
    Generate article content from topic using OpenAI.

    Pure async function with no side effects beyond API call.

    Args:
        client: Configured AsyncAzureOpenAI client
        model_name: Azure OpenAI deployment name
        topic_title: Article topic title
        research_content: Optional research context
        target_word_count: Desired article length
        quality_requirements: Optional quality constraints

    Returns:
        Tuple[content, prompt_tokens, completion_tokens]
        Returns (None, 0, 0) on error

    Examples:
        >>> client = await create_openai_client("https://my-resource.openai.azure.com")
        >>> content, prompt_tokens, completion_tokens = await generate_article_content(
        ...     client=client,
        ...     model_name="gpt-4o",
        ...     topic_title="Understanding Quantum Computing",
        ...     target_word_count=2000
        ... )
        >>> len(content) > 1000
        True
    """
    try:
        prompt = build_article_prompt(
            topic_title, research_content, target_word_count, quality_requirements
        )

        response = await client.chat.completions.create(
            model=model_name,
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

        content = response.choices[0].message.content
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0

        return content, prompt_tokens, completion_tokens

    except Exception as e:
        logger.error(f"Article generation failed: {e}")
        return None, 0, 0


async def generate_completion(
    client: AsyncAzureOpenAI,
    model_name: str,
    prompt: str,
    max_tokens: int = 200,
    temperature: float = 0.3,
) -> Tuple[Optional[str], int, int]:
    """
    Generate simple completion for utility tasks.

    Pure async function for lightweight operations like metadata generation,
    translation, etc.

    Args:
        client: Configured AsyncAzureOpenAI client
        model_name: Azure OpenAI deployment name
        prompt: Prompt text
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0-1.0)

    Returns:
        Tuple[content, prompt_tokens, completion_tokens]
        Returns (None, 0, 0) on error

    Examples:
        >>> client = await create_openai_client("https://my-resource.openai.azure.com")
        >>> content, p_tokens, c_tokens = await generate_completion(
        ...     client=client,
        ...     model_name="gpt-4o",
        ...     prompt="Translate to English: Bonjour le monde",
        ...     max_tokens=50
        ... )
        >>> "hello world" in content.lower()
        True
    """
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        content = response.choices[0].message.content
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0

        return content, prompt_tokens, completion_tokens

    except Exception as e:
        logger.error(f"Completion generation failed: {e}")
        return None, 0, 0


async def check_openai_connection(
    client: AsyncAzureOpenAI,
    model_name: str,
) -> bool:
    """
    Check OpenAI connectivity with minimal request.

    Pure async function that returns connection status.

    Args:
        client: Configured AsyncAzureOpenAI client
        model_name: Azure OpenAI deployment name

    Returns:
        bool: True if connection successful, False otherwise

    Examples:
        >>> client = await create_openai_client("https://my-resource.openai.azure.com")
        >>> is_connected = await check_openai_connection(client, "gpt-4o")
        >>> isinstance(is_connected, bool)
        True
    """
    try:
        await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=10,
        )
        return True

    except Exception as e:
        logger.error(f"OpenAI connectivity test failed: {e}")
        return False


# ============================================================================
# Prompt Building (Pure Functions)
# ============================================================================


def build_article_prompt(
    topic_title: str,
    research_content: Optional[str] = None,
    target_word_count: int = 3000,
    quality_requirements: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build comprehensive prompt for article generation.

    Pure function with deterministic output for given inputs.

    Args:
        topic_title: Article topic title
        research_content: Optional research context
        target_word_count: Desired article length
        quality_requirements: Optional quality constraints

    Returns:
        str: Formatted prompt text

    Examples:
        >>> prompt = build_article_prompt(
        ...     topic_title="AI Safety",
        ...     target_word_count=2000,
        ...     quality_requirements={"tone": "technical"}
        ... )
        >>> "AI Safety" in prompt
        True
        >>> "2000 words" in prompt
        True
    """
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
            "1. Engaging introduction",
            "2. Main content with clear H2/H3 section headings",
            "3. Key insights and analysis",
            "4. Conclusion with takeaways",
            "",
            "Focus on creating content that's valuable for a personal reading grid.",
        ]
    )

    return "\n".join(prompt_parts)


def generate_mock_article(topic_title: str) -> str:
    """
    Generate mock article for testing when OpenAI unavailable.

    Pure function with deterministic output.

    Args:
        topic_title: Article topic title

    Returns:
        str: Mock article content

    Examples:
        >>> article = generate_mock_article("Testing Article Generation")
        >>> "Testing Article Generation" in article
        True
        >>> len(article) > 100
        True
    """
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

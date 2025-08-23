"""AI client management for content generation"""

import logging
import os
from typing import Optional

import anthropic
import httpx
import openai
from config import config

# Configure logging
logger = logging.getLogger(__name__)


class AIClientManager:
    """Manages all AI service clients with dependency injection support"""

    def __init__(
        self,
        azure_openai_client: Optional[openai.AsyncAzureOpenAI] = None,
        openai_client: Optional[openai.AsyncOpenAI] = None,
        claude_client: Optional[anthropic.AsyncAnthropic] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        """Initialize AI clients with dependency injection support"""

        # Initialize Azure OpenAI client
        if azure_openai_client:
            self.azure_openai_client = azure_openai_client
        elif os.getenv("PYTEST_CURRENT_TEST"):
            from tests.mocks import MockAzureOpenAI

            self.azure_openai_client = MockAzureOpenAI()
        elif config.AZURE_OPENAI_ENDPOINT and config.AZURE_OPENAI_API_KEY:
            self.azure_openai_client = openai.AsyncAzureOpenAI(
                azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                api_key=config.AZURE_OPENAI_API_KEY,
                api_version=config.AZURE_OPENAI_API_VERSION,
            )
            logger.info("Initialized Azure OpenAI client")
        else:
            self.azure_openai_client = None

        # Initialize OpenAI client
        if openai_client:
            self.openai_client = openai_client
        elif os.getenv("PYTEST_CURRENT_TEST"):
            from tests.mocks import MockOpenAI

            self.openai_client = MockOpenAI()
        elif config.OPENAI_API_KEY:
            self.openai_client = openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        else:
            self.openai_client = None

        # Initialize Claude client
        if claude_client:
            self.claude_client = claude_client
        elif os.getenv("PYTEST_CURRENT_TEST"):
            from tests.mocks import MockClaude

            self.claude_client = MockClaude()
        elif config.CLAUDE_API_KEY:
            self.claude_client = anthropic.AsyncAnthropic(api_key=config.CLAUDE_API_KEY)
        else:
            self.claude_client = None

        # Initialize HTTP client
        if http_client:
            self.http_client = http_client
        elif os.getenv("PYTEST_CURRENT_TEST"):
            from tests.mocks import MockHTTPClient

            self.http_client = MockHTTPClient()
        else:
            self.http_client = httpx.AsyncClient(timeout=config.VERIFICATION_TIMEOUT)

    async def call_openai(
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

    async def call_claude(self, prompt: str, max_tokens: int = 4000) -> str:
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

    async def verify_sources(self, sources: list) -> tuple[str, list[str]]:
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
            return "verified", verification_notes
        elif verified_count > 0:
            return "partial", verification_notes
        else:
            return "unverified", verification_notes

    async def cleanup(self):
        """Clean up HTTP client resources"""
        if hasattr(self.http_client, "aclose"):
            await self.http_client.aclose()

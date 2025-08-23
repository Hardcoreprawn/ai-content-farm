"""
OpenAI API Contract - Defines expected OpenAI API behavior for content processing.

This ensures our mocks behave exactly like OpenAI, including
response formats, token usage, and error conditions.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json


@dataclass
class OpenAIResponseContract:
    """Contract for OpenAI API responses."""

    id: str
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]
    created: int
    object: str = "chat.completion"

    @classmethod
    def create_mock_processing_response(cls, processed_content: str, **overrides) -> "OpenAIResponseContract":
        """Create mock OpenAI response for content processing."""
        defaults = {
            "id": "chatcmpl-mock123456",
            "model": "gpt-4o-mini",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": processed_content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 200,
                "total_tokens": 350
            },
            "created": 1692800000
        }
        defaults.update(overrides)
        return cls(**defaults)


class MockOpenAIClient:
    """Contract-based mock for OpenAI API that behaves like the real service."""

    def __init__(self):
        """Initialize with realistic AI processing behavior."""
        self.request_count = 0
        self.total_tokens_used = 0

    async def chat_completions_create(self, model: str, messages: List[Dict[str, str]], **kwargs) -> OpenAIResponseContract:
        """Mock chat completion that processes content realistically."""
        self.request_count += 1

        # Extract the content to process from messages
        user_message = next((msg["content"] for msg in messages if msg["role"] == "user"), "")

        # Simulate AI processing based on the prompt
        if "title" in user_message.lower():
            processed_content = self._process_title(user_message)
        elif "summarize" in user_message.lower():
            processed_content = self._create_summary(user_message)
        elif "extract" in user_message.lower():
            processed_content = self._extract_insights(user_message)
        else:
            processed_content = "Processed content with AI enhancements"

        # Create realistic token usage
        prompt_tokens = len(user_message.split()) * 1.3  # Approximate tokenization
        completion_tokens = len(processed_content.split()) * 1.3
        total_tokens = int(prompt_tokens + completion_tokens)
        self.total_tokens_used += total_tokens

        return OpenAIResponseContract.create_mock_processing_response(
            processed_content=processed_content,
            usage={
                "prompt_tokens": int(prompt_tokens),
                "completion_tokens": int(completion_tokens),
                "total_tokens": total_tokens
            },
            model=model
        )

    def _process_title(self, content: str) -> str:
        """Simulate AI title processing."""
        return "AI-Enhanced: Revolutionary Breakthrough in Technology"

    def _create_summary(self, content: str) -> str:
        """Simulate AI summarization."""
        return "This article discusses significant developments in AI technology with practical applications for content processing and analysis."

    def _extract_insights(self, content: str) -> str:
        """Simulate AI insight extraction."""
        return json.dumps({
            "key_insights": [
                "Technology advancement accelerating",
                "Practical applications emerging",
                "Industry transformation expected"
            ],
            "sentiment": "positive",
            "complexity_score": 7.5,
            "readability_grade": "college"
        })


# Helper functions for creating realistic test data
def create_realistic_reddit_post() -> Dict[str, Any]:
    """Create realistic Reddit post data for testing."""
    return {
        "id": "test_post_123",
        "title": "Revolutionary AI breakthrough changes everything",
        "selftext": "Scientists at leading university have developed groundbreaking AI system that can process content with human-like understanding...",
        "score": 1247,
        "num_comments": 89,
        "created_utc": 1692800000,
        "subreddit": "technology",
        "author": "tech_researcher",
        "url": "https://example.com/ai-breakthrough",
        "upvote_ratio": 0.94
    }


def create_realistic_processing_prompt(reddit_post: Dict[str, Any]) -> str:
    """Create realistic AI processing prompt."""
    return f"""Process this Reddit post for content analysis:

Title: {reddit_post['title']}
Content: {reddit_post['selftext'][:500]}...
Score: {reddit_post['score']}
Comments: {reddit_post['num_comments']}

Please enhance the title, create a summary, and extract key insights."""

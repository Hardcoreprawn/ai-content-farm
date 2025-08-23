"""
OpenAI API Contract - Defines expected OpenAI API behavior.

This ensures our mocks behave exactly like OpenAI API, including
response formats, error conditions, and rate limiting behavior.
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class OpenAIUsageContract:
    """Contract for OpenAI API usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    @classmethod
    def create_mock(cls, **overrides) -> "OpenAIUsageContract":
        """Create mock usage data."""
        defaults = {
            "prompt_tokens": 50,
            "completion_tokens": 25,
            "total_tokens": 75,
        }
        defaults.update(overrides)
        return cls(**defaults)


@dataclass
class OpenAIChoiceContract:
    """Contract for OpenAI API choice data."""

    text: str
    index: int
    finish_reason: str
    logprobs: Optional[Dict[str, Any]] = None

    @classmethod
    def create_mock(
        cls, text: str = "Mock response", **overrides
    ) -> "OpenAIChoiceContract":
        """Create mock choice data."""
        defaults = {
            "text": text,
            "index": 0,
            "finish_reason": "stop",
            "logprobs": None,
        }
        defaults.update(overrides)
        return cls(**defaults)


@dataclass
class OpenAICompletionContract:
    """Contract for OpenAI API completion response."""

    id: str
    object: str
    created: int
    model: str
    choices: List[OpenAIChoiceContract]
    usage: OpenAIUsageContract

    @classmethod
    def create_mock_sentiment_response(
        cls, sentiment: str = "positive"
    ) -> "OpenAICompletionContract":
        """Create realistic sentiment analysis response."""
        sentiment_responses = {
            "positive": '{"sentiment": "positive", "confidence": 0.85, "scores": {"positive": 0.85, "neutral": 0.10, "negative": 0.05}}',
            "negative": '{"sentiment": "negative", "confidence": 0.90, "scores": {"positive": 0.05, "neutral": 0.05, "negative": 0.90}}',
            "neutral": '{"sentiment": "neutral", "confidence": 0.75, "scores": {"positive": 0.30, "neutral": 0.50, "negative": 0.20}}',
        }

        response_text = sentiment_responses.get(
            sentiment, sentiment_responses["neutral"]
        )

        return cls(
            id="cmpl-mock-sentiment-123",
            object="text_completion",
            created=1629800000,
            model="text-davinci-003",
            choices=[OpenAIChoiceContract.create_mock(text=response_text)],
            usage=OpenAIUsageContract.create_mock(),
        )

    @classmethod
    def create_mock_topic_response(
        cls, topics: Optional[List[str]] = None
    ) -> "OpenAICompletionContract":
        """Create realistic topic classification response."""
        if topics is None:
            topics = ["technology", "artificial intelligence"]

        response_text = json.dumps(
            {
                "primary_topic": topics[0] if topics else "general",
                "confidence": 0.88,
                "topics": topics,
                "categories": topics[:3],  # Limit to top 3
            }
        )

        return cls(
            id="cmpl-mock-topic-456",
            object="text_completion",
            created=1629800100,
            model="text-davinci-003",
            choices=[OpenAIChoiceContract.create_mock(text=response_text)],
            usage=OpenAIUsageContract.create_mock(
                prompt_tokens=75, completion_tokens=30
            ),
        )

    @classmethod
    def create_mock_summary_response(
        cls, summary: Optional[str] = None
    ) -> "OpenAICompletionContract":
        """Create realistic content summarization response."""
        if summary is None:
            summary = "This article discusses recent advances in artificial intelligence technology, focusing on machine learning applications and their potential impact on various industries."

        response_text = json.dumps(
            {
                "summary": summary,
                "word_count": len(summary.split()),
                "key_points": [
                    "AI technology advances",
                    "Machine learning applications",
                    "Industry impact",
                ],
            }
        )

        return cls(
            id="cmpl-mock-summary-789",
            object="text_completion",
            created=1629800200,
            model="text-davinci-003",
            choices=[OpenAIChoiceContract.create_mock(text=response_text)],
            usage=OpenAIUsageContract.create_mock(
                prompt_tokens=200, completion_tokens=75
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format matching OpenAI API response."""
        return {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "choices": [
                {
                    "text": choice.text,
                    "index": choice.index,
                    "finish_reason": choice.finish_reason,
                    "logprobs": choice.logprobs,
                }
                for choice in self.choices
            ],
            "usage": {
                "prompt_tokens": self.usage.prompt_tokens,
                "completion_tokens": self.usage.completion_tokens,
                "total_tokens": self.usage.total_tokens,
            },
        }


class MockOpenAIClient:
    """Mock OpenAI client that responds with contract-based data."""

    def __init__(self):
        self.call_count = 0
        self.last_request = None

    def completions_create(self, **kwargs) -> Dict[str, Any]:
        """Mock completions.create with intelligent response based on prompt."""
        self.call_count += 1
        self.last_request = kwargs

        prompt = kwargs.get("prompt", "").lower()

        # Route to appropriate response based on prompt content
        if "sentiment" in prompt or "feeling" in prompt or "emotion" in prompt:
            if "amazing" in prompt or "fantastic" in prompt or "great" in prompt:
                return OpenAICompletionContract.create_mock_sentiment_response(
                    "positive"
                ).to_dict()
            elif "terrible" in prompt or "awful" in prompt or "bad" in prompt:
                return OpenAICompletionContract.create_mock_sentiment_response(
                    "negative"
                ).to_dict()
            else:
                return OpenAICompletionContract.create_mock_sentiment_response(
                    "neutral"
                ).to_dict()

        elif "topic" in prompt or "classify" in prompt or "category" in prompt:
            if "science" in prompt or "climate" in prompt:
                return OpenAICompletionContract.create_mock_topic_response(
                    ["science", "environment"]
                ).to_dict()
            elif "technology" in prompt or "ai" in prompt:
                return OpenAICompletionContract.create_mock_topic_response(
                    ["technology", "artificial intelligence"]
                ).to_dict()
            else:
                return OpenAICompletionContract.create_mock_topic_response(
                    ["general"]
                ).to_dict()

        elif "summarize" in prompt or "summary" in prompt:
            return OpenAICompletionContract.create_mock_summary_response().to_dict()

        else:
            # Default response for unrecognized prompts
            return OpenAICompletionContract.create_mock_sentiment_response(
                "neutral"
            ).to_dict()

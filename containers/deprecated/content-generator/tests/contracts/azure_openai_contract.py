"""Azure OpenAI API contract for testing"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AzureOpenAIChoiceContract:
    """Azure OpenAI choice structure"""

    message: Dict[str, str]
    finish_reason: str = "stop"
    index: int = 0


@dataclass
class AzureOpenAIUsageContract:
    """Azure OpenAI usage structure"""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class AzureOpenAIResponseContract:
    """Azure OpenAI API response structure"""

    choices: List[AzureOpenAIChoiceContract]
    usage: AzureOpenAIUsageContract
    model: str
    id: str
    object: str = "chat.completion"
    created: int = 1677652288

    @classmethod
    def create_mock_response(
        cls,
        content: str = "Generated content",
        content_type: str = "generic",
        prompt_tokens: int = 100,
        completion_tokens: int = 200,
    ) -> Dict[str, Any]:
        """Create realistic mock response based on content type"""

        # Content templates based on type
        content_templates = {
            "tldr": f"# Quick Take: {{topic}}\n\n{content}\n\n**Key Points:**\n- Main insight\n- Supporting detail\n- Conclusion",
            "blog": f"# {{topic}}: A Comprehensive Look\n\n{content}\n\n## Analysis\n\nDetailed analysis here.\n\n## Conclusion\n\nFinal thoughts.",
            "deepdive": f"# Deep Dive: {{topic}}\n\n## Executive Summary\n\n{content}\n\n## Detailed Analysis\n\nComprehensive research...\n\n## Implications\n\nLong-term effects...",
            "generic": content,
        }

        final_content = content_templates.get(content_type, content)

        return {
            "choices": [
                {
                    "message": {"content": final_content, "role": "assistant"},
                    "finish_reason": "stop",
                    "index": 0,
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "model": "gpt-4",
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
        }

    @classmethod
    def create_tldr_response(cls, topic: str = "AI Technology") -> Dict[str, Any]:
        """Create TLDR response"""
        content = f"AI technology is advancing rapidly with significant implications for various industries."
        return cls.create_mock_response(
            content=content.format(topic=topic),
            content_type="tldr",
            prompt_tokens=80,
            completion_tokens=150,
        )

    @classmethod
    def create_blog_response(cls, topic: str = "AI Technology") -> Dict[str, Any]:
        """Create blog response"""
        return cls.create_mock_response(
            content_type="blog", prompt_tokens=120, completion_tokens=300
        )

    @classmethod
    def create_deepdive_response(cls, topic: str = "AI Technology") -> Dict[str, Any]:
        """Create deep dive response"""
        return cls.create_mock_response(
            content_type="deepdive", prompt_tokens=200, completion_tokens=800
        )

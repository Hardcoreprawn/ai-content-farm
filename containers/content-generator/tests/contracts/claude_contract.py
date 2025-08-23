"""Claude/Anthropic API contract for testing"""

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class ClaudeContentContract:
    """Claude content block structure"""
    text: str
    type: str = "text"


@dataclass
class ClaudeUsageContract:
    """Claude usage structure"""
    input_tokens: int
    output_tokens: int


@dataclass
class ClaudeResponseContract:
    """Claude API response structure"""
    content: List[ClaudeContentContract]
    usage: ClaudeUsageContract
    model: str
    id: str
    type: str = "message"
    role: str = "assistant"

    @classmethod
    def create_mock_response(
        cls,
        content: str = "Generated content using Claude",
        content_type: str = "generic",
        input_tokens: int = 100,
        output_tokens: int = 200
    ) -> Dict[str, Any]:
        """Create realistic Claude mock response"""

        # Content templates based on type
        content_templates = {
            "tldr": f"# Quick Analysis: {{topic}}\n\n{content}\n\n**Essential Points:**\n- Core insight\n- Key finding\n- Bottom line",
            "blog": f"# Understanding {{topic}}\n\n{content}\n\n## Deep Analysis\n\nDetailed examination...\n\n## Takeaways\n\nKey insights.",
            "deepdive": f"# Comprehensive Analysis: {{topic}}\n\n## Overview\n\n{content}\n\n## In-Depth Research\n\nExtensive investigation...\n\n## Future Outlook\n\nProjections and implications...",
            "generic": content
        }

        final_content = content_templates.get(content_type, content)

        return {
            "content": [
                {
                    "text": final_content,
                    "type": "text"
                }
            ],
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            },
            "model": "claude-3-haiku-20240307",
            "id": "msg_claude_123",
            "type": "message",
            "role": "assistant"
        }

    @classmethod
    def create_tldr_response(cls, topic: str = "AI Technology") -> Dict[str, Any]:
        """Create TLDR response"""
        content = "Claude provides concise analysis of AI developments with focus on practical implications."
        return cls.create_mock_response(
            content=content,
            content_type="tldr",
            input_tokens=75,
            output_tokens=125
        )

    @classmethod
    def create_blog_response(cls, topic: str = "AI Technology") -> Dict[str, Any]:
        """Create blog response"""
        return cls.create_mock_response(
            content_type="blog",
            input_tokens=110,
            output_tokens=280
        )

    @classmethod
    def create_deepdive_response(cls, topic: str = "AI Technology") -> Dict[str, Any]:
        """Create deep dive response"""
        return cls.create_mock_response(
            content_type="deepdive",
            input_tokens=180,
            output_tokens=750
        )

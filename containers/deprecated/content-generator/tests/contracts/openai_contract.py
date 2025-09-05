"""OpenAI API contract for testing"""

from dataclasses import dataclass
from typing import Any, Dict, List

from .azure_openai_contract import AzureOpenAIResponseContract


@dataclass
class OpenAIResponseContract(AzureOpenAIResponseContract):
    """OpenAI API response structure (similar to Azure OpenAI)"""

    @classmethod
    def create_mock_response(
        cls,
        content: str = "Generated content using OpenAI",
        content_type: str = "generic",
        prompt_tokens: int = 100,
        completion_tokens: int = 200,
    ) -> Dict[str, Any]:
        """Create realistic OpenAI mock response"""

        # Reuse Azure OpenAI structure with OpenAI-specific model
        response = super().create_mock_response(
            content=content,
            content_type=content_type,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        # Update model to OpenAI-specific
        response["model"] = "gpt-4-turbo-preview"
        response["id"] = "chatcmpl-openai-123"

        return response

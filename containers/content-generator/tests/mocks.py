"""Mock classes for content-generator testing"""

import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class MockResponse:
    """Mock response structure for AI services"""
    content: str
    usage: Dict[str, int] = None

    def __post_init__(self):
        if self.usage is None:
            self.usage = {"prompt_tokens": 100, "completion_tokens": 200}


class MockBlobStorageClient:
    """Mock blob storage client for testing"""

    def __init__(self):
        self.stored_data = {}

    def upload_text(self, container_name: str, blob_name: str, content: str, **kwargs):
        """Mock text upload"""
        key = f"{container_name}/{blob_name}"
        self.stored_data[key] = content
        return {"status": "success", "path": key}

    def download_text(self, container_name: str, blob_name: str) -> str:
        """Mock text download"""
        key = f"{container_name}/{blob_name}"
        return self.stored_data.get(key, "")

    def list_blobs(self, container_name: str, prefix: str = "") -> List[Dict[str, str]]:
        """Mock blob listing"""
        return [
            {"name": f"{prefix}test-blob-1.json"},
            {"name": f"{prefix}test-blob-2.json"}
        ]

    def health_check(self) -> Dict[str, str]:
        """Mock health check"""
        return {"status": "healthy", "service": "mock-blob-storage"}


class MockChoice:
    """Mock OpenAI choice object"""

    def __init__(self, content: str):
        self.message = MockMessage(content)


class MockMessage:
    """Mock OpenAI message object"""

    def __init__(self, content: str):
        self.content = content


class MockUsage:
    """Mock OpenAI usage object"""

    def __init__(self):
        self.prompt_tokens = 100
        self.completion_tokens = 200
        self.total_tokens = 300


class MockAzureOpenAI:
    """Mock Azure OpenAI client"""

    def __init__(self):
        self.chat = MockChatCompletions()


class MockChatCompletions:
    """Mock chat completions endpoint"""

    def __init__(self):
        self.completions = self

    async def create(self, **kwargs) -> Any:
        """Mock chat completion creation"""
        messages = kwargs.get("messages", [])
        content_type = self._detect_content_type(messages)
        max_tokens = kwargs.get("max_tokens", 1500)

        # Generate content based on type and token limit
        if content_type == "tldr":
            content = """TITLE: AI Healthcare Breakthrough: Quick Take

CONTENT: Revolutionary AI system transforms medical diagnosis with 95% accuracy in detecting rare diseases. This breakthrough represents a significant advance in artificial intelligence applications for healthcare, with potential to revolutionize patient care and medical research worldwide.

Key impacts include faster diagnosis, reduced medical errors, and improved patient outcomes through advanced machine learning algorithms and comprehensive data analysis."""
        elif content_type == "blog":
            content = """TITLE: Understanding AI in Healthcare: A Comprehensive Look

CONTENT: Artificial intelligence is revolutionizing healthcare through advanced diagnostic capabilities and personalized treatment options. This comprehensive analysis explores the technological innovations, clinical applications, and future implications of AI in medical practice.

## Analysis

The integration of machine learning and medical expertise is creating unprecedented opportunities for improving patient care. Advanced algorithms can process vast amounts of medical data to identify patterns and predict outcomes with remarkable accuracy.

## Conclusion

AI systems are becoming essential tools for medical professionals, enhancing their capabilities and improving patient care quality."""
        elif content_type == "deepdive":
            content = """TITLE: Deep Dive: AI Healthcare Revolution

CONTENT: ## Executive Summary

Artificial intelligence systems are fundamentally transforming healthcare delivery through sophisticated diagnostic algorithms and predictive analytics.

## Detailed Analysis

The implementation of AI in healthcare encompasses multiple domains including medical imaging, clinical decision support, and personalized medicine. Advanced machine learning models demonstrate remarkable accuracy in disease detection and prognosis.

## Future Implications

The long-term impact of AI in healthcare will reshape medical practice, improve patient outcomes, and optimize healthcare resource allocation. This transformation represents one of the most significant advances in modern medicine."""
        else:
            content = """TITLE: Generated Content

CONTENT: This is generated content based on the provided topic and requirements. The content includes relevant information and analysis suitable for the requested format."""

        mock_response = type('MockResponse', (), {
            'choices': [MockChoice(content)],
            'usage': MockUsage()
        })()

        return mock_response

    def _detect_content_type(self, messages: List[Dict[str, Any]]) -> str:
        """Detect content type from messages"""
        prompt = str(messages).lower()
        if "tldr" in prompt:
            return "tldr"
        elif "blog" in prompt:
            return "blog"
        elif "deepdive" in prompt or "deep dive" in prompt:
            return "deepdive"
        return "generic"


class MockOpenAI:
    """Mock OpenAI client"""

    def __init__(self):
        self.chat = MockChatCompletions()


class MockClaudeContent:
    """Mock Claude content object"""

    def __init__(self, text: str):
        self.text = text


class MockClaudeUsage:
    """Mock Claude usage object"""

    def __init__(self):
        self.input_tokens = 100
        self.output_tokens = 200


class MockClaude:
    """Mock Claude/Anthropic client"""

    def __init__(self):
        self.messages = self

    async def create(self, **kwargs) -> Any:
        """Mock message creation"""
        messages = kwargs.get("messages", [])
        content_type = self._detect_content_type(messages)

        if content_type == "tldr":
            text = """TITLE: AI Healthcare Analysis: Quick Take

CONTENT: Claude provides concise analysis of AI developments with focus on practical implications. The healthcare AI breakthrough demonstrates significant potential for improving diagnostic accuracy and patient outcomes through advanced machine learning systems."""
        elif content_type == "blog":
            text = """TITLE: Understanding AI in Healthcare

CONTENT: ## Deep Analysis

Claude examines the transformative impact of artificial intelligence in healthcare settings. The technology enables more accurate diagnoses, personalized treatment plans, and improved clinical workflows.

## Key Insights

AI systems are becoming essential tools for medical professionals, enhancing their capabilities and improving patient care quality through data-driven insights."""
        elif content_type == "deepdive":
            text = """TITLE: Comprehensive Analysis: AI Healthcare Revolution

CONTENT: ## Overview

Claude provides comprehensive research on AI implementation in healthcare including technological foundations, clinical applications, and regulatory considerations.

## In-Depth Research

Extensive investigation reveals the multifaceted impact of AI systems on medical practice, from diagnostic imaging to treatment optimization.

## Future Outlook

Projections indicate continued growth in AI adoption across healthcare sectors, with significant implications for medical education and practice."""
        else:
            text = """TITLE: Generated Content

CONTENT: Generated content using Claude with focus on accuracy and depth. This content addresses the key aspects of the requested topic with comprehensive analysis and detailed information. The response includes thorough investigation of relevant factors, comprehensive review of applicable methodologies, and extensive discussion of important considerations for practical implementation and effective utilization."""

        mock_response = type('MockResponse', (), {
            'content': [MockClaudeContent(text)],
            'usage': MockClaudeUsage()
        })()

        return mock_response

    def _detect_content_type(self, messages: List[Dict[str, Any]]) -> str:
        """Detect content type from messages"""
        prompt = str(messages).lower()
        if "tldr" in prompt:
            return "tldr"
        elif "blog" in prompt:
            return "blog"
        elif "deepdive" in prompt or "deep dive" in prompt:
            return "deepdive"
        return "generic"


class MockHTTPClient:
    """Mock HTTP client for source verification"""

    def __init__(self):
        pass

    async def get(self, url: str, **kwargs) -> Any:
        """Mock HTTP GET request"""
        mock_response = type('MockResponse', (), {
            'status_code': 200,
            'text': 'Mock webpage content',
            'headers': {'content-type': 'text/html'}
        })()

        return mock_response

    async def head(self, url: str, **kwargs) -> Any:
        """Mock HTTP HEAD request for source verification"""
        mock_response = type('MockResponse', (), {
            'status_code': 200,
            'headers': {'content-type': 'text/html'}
        })()

        return mock_response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

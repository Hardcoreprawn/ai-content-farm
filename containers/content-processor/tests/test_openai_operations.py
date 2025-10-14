"""
Tests for pure functional OpenAI operations.

Black box testing: validates inputs and outputs only, not implementation.

Contract Version: 1.0.0
"""

from unittest.mock import AsyncMock, Mock

import pytest
from operations.openai_operations import (
    build_article_prompt,
    check_openai_connection,
    generate_article_content,
    generate_completion,
    generate_mock_article,
)


class TestBuildArticlePrompt:
    """Test article prompt building."""

    def test_minimal_prompt(self):
        """Minimal prompt with just title."""
        prompt = build_article_prompt(topic_title="AI Safety", target_word_count=2000)
        assert "AI Safety" in prompt
        assert "2000 words" in prompt
        assert "trustworthy" in prompt.lower()

    def test_prompt_with_research(self):
        """Prompt includes research content."""
        prompt = build_article_prompt(
            topic_title="Quantum Computing",
            research_content="Key research: qubits enable superposition",
            target_word_count=3000,
        )
        assert "Research context:" in prompt
        assert "qubits enable superposition" in prompt

    def test_prompt_with_quality_requirements(self):
        """Prompt includes quality requirements."""
        prompt = build_article_prompt(
            topic_title="Climate Change",
            quality_requirements={"tone": "technical", "audience": "experts"},
            target_word_count=2500,
        )
        assert "Additional requirements:" in prompt
        assert "tone: technical" in prompt
        assert "audience: experts" in prompt

    def test_prompt_is_deterministic(self):
        """Same inputs produce same prompt."""
        prompt1 = build_article_prompt("Test", target_word_count=1000)
        prompt2 = build_article_prompt("Test", target_word_count=1000)
        assert prompt1 == prompt2


class TestGenerateMockArticle:
    """Test mock article generation."""

    def test_mock_includes_title(self):
        """Mock article includes topic title."""
        article = generate_mock_article("Testing Mock Generation")
        assert "Testing Mock Generation" in article

    def test_mock_has_structure(self):
        """Mock article has expected structure."""
        article = generate_mock_article("Test Topic")
        assert "# Test Topic" in article
        assert "## Introduction" in article
        assert "## Main Content" in article
        assert "## Conclusion" in article

    def test_mock_is_deterministic(self):
        """Same topic produces same mock article."""
        article1 = generate_mock_article("Same Topic")
        article2 = generate_mock_article("Same Topic")
        assert article1 == article2

    def test_mock_is_substantial(self):
        """Mock article has meaningful content."""
        article = generate_mock_article("Any Topic")
        assert len(article) > 500


@pytest.mark.asyncio
class TestGenerateArticleContent:
    """Test article content generation."""

    async def test_successful_generation(self):
        """Successful article generation returns content and tokens."""
        # Mock client
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="Generated article content"))
        ]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=500)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        content, prompt_tokens, completion_tokens = await generate_article_content(
            client=mock_client, model_name="gpt-4o", topic_title="Test Topic"
        )

        assert content == "Generated article content"
        assert prompt_tokens == 100
        assert completion_tokens == 500

    async def test_generation_with_research(self):
        """Generation includes research content in prompt."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Article with research"))]
        mock_response.usage = Mock(prompt_tokens=150, completion_tokens=600)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        content, _, _ = await generate_article_content(
            client=mock_client,
            model_name="gpt-4o",
            topic_title="Research Topic",
            research_content="Important research findings",
        )

        # Verify API was called
        assert mock_client.chat.completions.create.called
        call_args = mock_client.chat.completions.create.call_args
        prompt_text = call_args.kwargs["messages"][1]["content"]
        assert "Important research findings" in prompt_text

    async def test_generation_failure(self):
        """Generation failure returns None and zero tokens."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )

        content, prompt_tokens, completion_tokens = await generate_article_content(
            client=mock_client, model_name="gpt-4o", topic_title="Test Topic"
        )

        assert content is None
        assert prompt_tokens == 0
        assert completion_tokens == 0

    async def test_custom_word_count(self):
        """Custom word count is used in prompt."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Custom length article"))]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=400)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        await generate_article_content(
            client=mock_client,
            model_name="gpt-4o",
            topic_title="Test Topic",
            target_word_count=5000,
        )

        call_args = mock_client.chat.completions.create.call_args
        prompt_text = call_args.kwargs["messages"][1]["content"]
        assert "5000 words" in prompt_text


@pytest.mark.asyncio
class TestGenerateCompletion:
    """Test completion generation."""

    async def test_successful_completion(self):
        """Successful completion returns content and tokens."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Completion result"))]
        mock_response.usage = Mock(prompt_tokens=20, completion_tokens=30)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        content, prompt_tokens, completion_tokens = await generate_completion(
            client=mock_client, model_name="gpt-4o", prompt="Test prompt"
        )

        assert content == "Completion result"
        assert prompt_tokens == 20
        assert completion_tokens == 30

    async def test_completion_with_custom_params(self):
        """Completion uses custom max_tokens and temperature."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Custom completion"))]
        mock_response.usage = Mock(prompt_tokens=10, completion_tokens=50)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        await generate_completion(
            client=mock_client,
            model_name="gpt-4o",
            prompt="Test prompt",
            max_tokens=100,
            temperature=0.5,
        )

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["max_tokens"] == 100
        assert call_args.kwargs["temperature"] == 0.5

    async def test_completion_failure(self):
        """Completion failure returns None and zero tokens."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )

        content, prompt_tokens, completion_tokens = await generate_completion(
            client=mock_client, model_name="gpt-4o", prompt="Test prompt"
        )

        assert content is None
        assert prompt_tokens == 0
        assert completion_tokens == 0


@pytest.mark.asyncio
class TestCheckOpenAIConnection:
    """Test OpenAI connection checking."""

    async def test_connection_success(self):
        """Successful connection returns True."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await check_openai_connection(mock_client, "gpt-4o")

        assert result is True
        assert mock_client.chat.completions.create.called

    async def test_connection_failure(self):
        """Failed connection returns False."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        result = await check_openai_connection(mock_client, "gpt-4o")

        assert result is False


class TestPurityAndDeterminism:
    """Test that functions are pure (deterministic, no side effects)."""

    def test_prompt_determinism(self):
        """Same inputs produce same prompt."""
        prompt1 = build_article_prompt("Topic", target_word_count=2000)
        prompt2 = build_article_prompt("Topic", target_word_count=2000)
        assert prompt1 == prompt2

    def test_mock_article_determinism(self):
        """Same topic produces same mock article."""
        article1 = generate_mock_article("Test")
        article2 = generate_mock_article("Test")
        assert article1 == article2

    def test_prompt_with_none_research(self):
        """Prompt handles None research content gracefully."""
        prompt = build_article_prompt("Topic", research_content=None)
        assert "Research context:" not in prompt

    def test_prompt_with_empty_quality_requirements(self):
        """Prompt handles empty quality requirements."""
        prompt = build_article_prompt("Topic", quality_requirements={})
        assert "Additional requirements:" not in prompt

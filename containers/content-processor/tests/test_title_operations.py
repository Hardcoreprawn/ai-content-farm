"""
Tests for pure functional title generation operations.

Black box testing: validates inputs and outputs only, not implementation.
Follows established test patterns from test_openai_operations.py.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from operations.title_operations import (
    build_title_prompt,
    generate_clean_title,
    has_date_prefix,
    is_truncated,
    needs_ai_generation,
    remove_date_prefix,
)


class TestDatePrefixDetection:
    """Test date prefix detection (pure functions)."""

    def test_detects_standard_date_format(self):
        """Detects (DD MMM) format."""
        assert has_date_prefix("(15 Oct) Article Title")
        assert has_date_prefix("(1 Jan) News")

    def test_detects_reverse_date_format(self):
        """Detects (MMM DD) format."""
        assert has_date_prefix("(Oct 15) Article Title")
        assert has_date_prefix("(Jan 1) News")

    def test_detects_iso_date_format(self):
        """Detects (YYYY-MM-DD) format."""
        assert has_date_prefix("(2025-10-15) Article Title")
        assert has_date_prefix("(2025-01-01) News")

    def test_detects_bracket_date_format(self):
        """Detects [DD MMM] format."""
        assert has_date_prefix("[15 Oct] Article Title")
        assert has_date_prefix("[1 Jan] News")

    def test_no_date_prefix(self):
        """No false positives for clean titles."""
        assert not has_date_prefix("Article Title")
        assert not has_date_prefix("Windows Security Update")
        assert not has_date_prefix("10 Reasons to Use AI")


class TestDatePrefixRemoval:
    """Test date prefix removal (pure functions)."""

    def test_removes_standard_format(self):
        """Removes (DD MMM) format."""
        assert remove_date_prefix("(15 Oct) Article Title") == "Article Title"
        assert remove_date_prefix("(1 Jan) News") == "News"

    def test_removes_reverse_format(self):
        """Removes (MMM DD) format."""
        assert remove_date_prefix("(Oct 15) Article Title") == "Article Title"

    def test_removes_iso_format(self):
        """Removes (YYYY-MM-DD) format."""
        assert remove_date_prefix("(2025-10-15) Article Title") == "Article Title"

    def test_removes_bracket_format(self):
        """Removes [DD MMM] format."""
        assert remove_date_prefix("[15 Oct] Article Title") == "Article Title"

    def test_no_change_when_no_prefix(self):
        """Returns original when no prefix."""
        assert remove_date_prefix("Article Title") == "Article Title"
        assert remove_date_prefix("Windows Security") == "Windows Security"

    def test_handles_extra_whitespace(self):
        """Handles extra whitespace after prefix."""
        assert remove_date_prefix("(15 Oct)   Article Title") == "Article Title"


class TestTruncationDetection:
    """Test truncation detection (pure functions)."""

    def test_detects_triple_dot_truncation(self):
        """Detects ... truncation."""
        assert is_truncated("This is a long title that...")
        assert is_truncated("Title ending with dots...")

    def test_detects_double_dot_truncation(self):
        """Detects .. truncation."""
        assert is_truncated("This is truncated..")

    def test_detects_url_truncation(self):
        """Detects truncated URLs."""
        assert is_truncated("Article title ending with ht")
        assert is_truncated("Check this out http")
        assert is_truncated("See https")

    def test_no_false_positives(self):
        """No false positives for complete titles."""
        assert not is_truncated("Complete Article Title")
        assert not is_truncated("Windows Zero-Day Vulnerabilities")
        assert not is_truncated("AI Safety Research Progress")


class TestAIGenerationNeeds:
    """Test AI generation decision logic (pure functions)."""

    def test_needs_ai_for_date_prefix(self):
        """Needs AI when date prefix present."""
        assert needs_ai_generation("(15 Oct) Article")
        assert needs_ai_generation("[Oct 15] News")

    def test_needs_ai_for_truncation(self):
        """Needs AI when truncated."""
        assert needs_ai_generation("Long title that...")
        assert needs_ai_generation("Article ending with ht")

    def test_needs_ai_for_too_long(self):
        """Needs AI when exceeds max length."""
        long_title = "A" * 100  # 100 chars, exceeds MAX_TITLE_LENGTH (80)
        assert needs_ai_generation(long_title)

    def test_needs_ai_for_too_short(self):
        """Needs AI when suspiciously short."""
        assert needs_ai_generation("Short")
        assert needs_ai_generation("AI")

    def test_no_ai_for_clean_title(self):
        """No AI needed for clean, appropriate-length titles."""
        assert not needs_ai_generation("Windows Security Update Released")
        assert not needs_ai_generation("AI Research Makes Progress")


class TestBuildTitlePrompt:
    """Test title prompt building (pure functions)."""

    def test_includes_original_title(self):
        """Prompt includes original title."""
        prompt = build_title_prompt("Original Title", "Content summary here")
        assert "Original Title" in prompt

    def test_includes_content_summary(self):
        """Prompt includes content summary."""
        prompt = build_title_prompt("Title", "Important content summary")
        assert "Important content summary" in prompt

    def test_includes_requirements(self):
        """Prompt includes generation requirements."""
        prompt = build_title_prompt("Title", "Content")
        assert "max 80 characters" in prompt.lower()
        assert "remove date prefixes" in prompt.lower()
        assert "seo-friendly" in prompt.lower()

    def test_is_deterministic(self):
        """Same inputs produce same prompt."""
        prompt1 = build_title_prompt("Test", "Summary")
        prompt2 = build_title_prompt("Test", "Summary")
        assert prompt1 == prompt2


class TestGenerateCleanTitle:
    """Test AI title generation (async with mocks)."""

    @pytest.mark.asyncio
    async def test_no_ai_for_clean_short_title(self):
        """Clean short title returned as-is, no AI used."""
        title = "Windows Security Update"
        mock_client = AsyncMock()

        result, cost = await generate_clean_title(title, "summary", mock_client)

        assert result == title
        assert cost == 0.0
        mock_client.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_removes_date_prefix_no_ai(self):
        """Date prefix removed without AI if rest is clean."""
        title = "(15 Oct) Windows Zero-Day Vulnerabilities"
        mock_client = AsyncMock()

        result, cost = await generate_clean_title(title, "summary", mock_client)

        assert result == "Windows Zero-Day Vulnerabilities"
        assert cost == 0.0
        mock_client.chat.completions.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_ai_for_long_title(self):
        """Long titles use AI to generate concise version."""
        long_title = (
            "This is an extremely long title that goes on and on with "
            "too much detail and needs to be shortened significantly to meet "
            "the maximum length requirements..."
        )

        # Mock Azure OpenAI response
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Concise Article Title"))]
        mock_response.usage = Mock(prompt_tokens=170, completion_tokens=15)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result, cost = await generate_clean_title(
            long_title, "Article summary here", mock_client
        )

        assert result == "Concise Article Title"
        assert cost > 0  # AI was used
        assert cost < 0.001  # But very cheap (gpt-4o-mini)

        # Verify correct model was used
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "gpt-4o-mini"
        assert call_args.kwargs["max_tokens"] == 25

    @pytest.mark.asyncio
    async def test_uses_ai_for_truncated_title(self):
        """Truncated titles use AI to generate complete version."""
        truncated = "Two New Windows Zero-Days Exploited in the Wild One Affects Every Version Ever Shipped ht..."

        # Mock response
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="Windows Zero-Days Exploited"))
        ]
        mock_response.usage = Mock(prompt_tokens=180, completion_tokens=10)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result, cost = await generate_clean_title(
            truncated, "Article about Windows vulnerabilities", mock_client
        )

        assert result == "Windows Zero-Days Exploited"
        assert not result.endswith("...")
        assert len(result) <= 80
        assert cost > 0

    @pytest.mark.asyncio
    async def test_cost_tracking_accuracy(self):
        """Cost calculation is accurate for gpt-4o-mini."""
        # Mock with realistic token usage
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Clean Title"))]
        mock_response.usage = Mock(prompt_tokens=170, completion_tokens=15)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        _, cost = await generate_clean_title(
            "Long title that needs AI...", "Summary", mock_client
        )

        # gpt-4o-mini: 170 * $0.00015/1k + 15 * $0.0006/1k ≈ $0.000035
        assert 0.00003 < cost < 0.00005

    @pytest.mark.asyncio
    async def test_removes_ai_added_quotes(self):
        """AI-added quotes are removed from title."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='"Quoted Title"'))]
        mock_response.usage = Mock(prompt_tokens=170, completion_tokens=15)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result, _ = await generate_clean_title("Long title...", "Summary", mock_client)

        assert result == "Quoted Title"
        assert not result.startswith('"')
        assert not result.endswith('"')

    @pytest.mark.asyncio
    async def test_enforces_max_length_on_ai_output(self):
        """AI output is truncated if exceeds max length."""
        # AI returns too-long title
        mock_client = AsyncMock()
        mock_response = Mock()
        too_long = "A" * 100  # 100 chars
        mock_response.choices = [Mock(message=Mock(content=too_long))]
        mock_response.usage = Mock(prompt_tokens=170, completion_tokens=30)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result, _ = await generate_clean_title("Original", "Summary", mock_client)

        assert len(result) <= 80
        assert not result.endswith(" ")  # Clean truncation at word boundary

    @pytest.mark.asyncio
    async def test_fallback_on_api_error(self):
        """Falls back to cleaned original on API error."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        result, cost = await generate_clean_title(
            "(15 Oct) Windows Security Update That Is Too Long...",
            "Summary",
            mock_client,
        )

        # Should return cleaned version without crashing
        assert "Windows Security Update" in result
        assert not result.startswith("(")
        assert len(result) <= 80
        assert cost == 0.0  # No cost on error

    @pytest.mark.asyncio
    async def test_prompt_includes_content_context(self):
        """Generated prompt includes content context."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Title"))]
        mock_response.usage = Mock(prompt_tokens=170, completion_tokens=10)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        content_summary = "Important content about AI safety research"
        await generate_clean_title("Long title...", content_summary, mock_client)

        # Verify prompt included content
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        user_message = messages[1]["content"]
        assert "AI safety research" in user_message

    @pytest.mark.asyncio
    async def test_temperature_set_for_creativity(self):
        """Temperature is set for balanced creativity."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Title"))]
        mock_response.usage = Mock(prompt_tokens=170, completion_tokens=10)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        await generate_clean_title("Long title...", "Summary", mock_client)

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["temperature"] == 0.7


class TestIntegrationScenarios:
    """Test realistic end-to-end scenarios."""

    @pytest.mark.asyncio
    async def test_real_world_reddit_title(self):
        """Real-world Reddit title scenario."""
        reddit_title = (
            "(15 Oct) Two New Windows Zero-Days Exploited in the Wild "
            "One Affects Every Version Ever Shipped ht..."
        )

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="Two Windows Zero-Days Exploit Every Version"))
        ]
        mock_response.usage = Mock(prompt_tokens=185, completion_tokens=12)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result, cost = await generate_clean_title(
            reddit_title,
            "Microsoft has disclosed two critical zero-day vulnerabilities...",
            mock_client,
        )

        assert not result.startswith("(")
        assert not result.endswith("...")
        assert len(result) <= 80
        assert "Windows" in result
        assert cost > 0
        assert cost < 0.0001  # Very cheap

    @pytest.mark.asyncio
    async def test_real_world_mastodon_title(self):
        """Real-world Mastodon title scenario."""
        mastodon_title = "AI"  # Very short, needs AI

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="Artificial Intelligence Breakthroughs"))
        ]
        mock_response.usage = Mock(prompt_tokens=165, completion_tokens=15)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result, cost = await generate_clean_title(
            mastodon_title,
            "Recent developments in artificial intelligence research show significant progress in natural language understanding...",
            mock_client,
        )

        assert len(result) > 20  # Not suspiciously short anymore
        assert len(result) <= 80
        assert cost > 0

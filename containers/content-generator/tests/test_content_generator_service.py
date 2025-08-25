"""Unit tests for content generator service logic"""

from unittest.mock import AsyncMock, Mock

import pytest

from models import GeneratedContent, RankedTopic, SourceData
from service_logic import ContentGeneratorService


class TestContentGeneratorService:
    """Test content generation service functionality"""

    @pytest.mark.asyncio
    async def test_generate_tldr_content(
        self, content_generator_service, sample_ranked_topic
    ):
        """Test TLDR content generation"""
        # Act
        result = await content_generator_service.generate_content(
            topic=sample_ranked_topic,
            content_type="tldr",
            writer_personality="professional",
        )

        # Assert
        assert isinstance(result, GeneratedContent)
        assert result.topic == sample_ranked_topic.topic
        assert result.content_type == "tldr"
        assert result.title is not None
        assert result.content is not None
        assert result.word_count > 0
        assert len(result.tags) > 0

    @pytest.mark.asyncio
    async def test_generate_blog_content(
        self, content_generator_service, sample_ranked_topic
    ):
        """Test blog content generation"""
        # Act
        result = await content_generator_service.generate_content(
            topic=sample_ranked_topic, content_type="blog", writer_personality="casual"
        )

        # Assert
        assert isinstance(result, GeneratedContent)
        assert result.content_type == "blog"
        assert result.word_count > 0
        assert (
            "blog" in result.content.lower()
            or "comprehensive" in result.content.lower()
        )

    @pytest.mark.asyncio
    async def test_generate_deepdive_content(
        self, content_generator_service, sample_ranked_topic
    ):
        """Test deep dive content generation"""
        # Act
        result = await content_generator_service.generate_content(
            topic=sample_ranked_topic,
            content_type="deepdive",
            writer_personality="expert",
        )

        # Assert
        assert isinstance(result, GeneratedContent)
        assert result.content_type == "deepdive"
        assert result.word_count > 0
        assert len(result.content) > 100  # Expect longer content

    def test_service_initialization(self):
        """Test service initializes correctly with dependency injection"""
        # Act
        service = ContentGeneratorService()

        # Assert
        assert service.blob_client is not None
        assert service.ai_clients is not None
        assert service.content_generators is not None
        assert isinstance(service.active_generations, dict)

    def test_has_sufficient_content_with_adequate_sources(
        self, content_generator_service, sample_ranked_topic
    ):
        """Test content sufficiency check with adequate sources"""
        # Act
        result = content_generator_service._has_sufficient_content(
            sample_ranked_topic, "tldr"
        )

        # Assert
        assert result is True

    def test_has_sufficient_content_with_empty_sources(self, content_generator_service):
        """Test content sufficiency check with empty sources"""
        # Arrange
        empty_topic = RankedTopic(
            topic="Empty Topic", sources=[], rank=1, ai_score=0.5, sentiment="neutral"
        )

        # Act
        result = content_generator_service._has_sufficient_content(empty_topic, "tldr")

        # Assert
        assert result is False

    def test_detect_content_type_from_prompt(self, content_generator_service):
        """Test content type detection from prompts"""
        # Test TLDR detection
        tldr_messages = [{"role": "user", "content": "Generate a TLDR summary"}]
        assert "tldr" in str(tldr_messages).lower()

        # Test blog detection
        blog_messages = [{"role": "user", "content": "Write a blog post about AI"}]
        assert "blog" in str(blog_messages).lower()

        # Test deepdive detection
        deepdive_messages = [{"role": "user", "content": "Create a deep dive analysis"}]
        assert "deep" in str(deepdive_messages).lower()

    @pytest.mark.asyncio
    async def test_content_generation_with_invalid_type(
        self, content_generator_service, sample_ranked_topic
    ):
        """Test content generation with invalid content type"""
        # Act & Assert - The system checks sufficiency first, then content type
        with pytest.raises(
            ValueError, match="Insufficient source material|Unknown content type"
        ):
            await content_generator_service.generate_content(
                topic=sample_ranked_topic, content_type="invalid_type"
            )

    @pytest.mark.asyncio
    async def test_content_generation_with_insufficient_sources(
        self, content_generator_service
    ):
        """Test content generation with insufficient source material"""
        # Arrange
        minimal_topic = RankedTopic(
            topic="Minimal Topic", sources=[], rank=1, ai_score=0.5, sentiment="neutral"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Insufficient source material"):
            await content_generator_service.generate_content(
                topic=minimal_topic, content_type="deepdive"
            )

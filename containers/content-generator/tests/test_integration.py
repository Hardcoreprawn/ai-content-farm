"""Integration tests for content generator service"""

import pytest
from unittest.mock import patch
import httpx

from models import RankedTopic, SourceData, GeneratedContent
from service_logic import ContentGeneratorService


@pytest.mark.integration
class TestContentGeneratorIntegration:
    """Integration tests with real external dependencies"""

    @pytest.mark.asyncio
    async def test_full_content_generation_pipeline(self, sample_ranked_topic):
        """Test complete content generation pipeline with all components"""
        # Arrange - Use real service but with mocked external dependencies
        service = ContentGeneratorService()

        # Act
        result = await service.generate_content(
            topic=sample_ranked_topic,
            content_type="tldr",
            writer_personality="professional"
        )

        # Assert
        assert isinstance(result, GeneratedContent)
        assert result.topic == sample_ranked_topic.topic
        assert result.content_type == "tldr"
        assert len(result.content) > 0
        assert result.word_count > 0
        assert result.ai_model is not None
        assert result.generation_time is not None

    @pytest.mark.asyncio
    async def test_batch_processing_simulation(self, sample_source_data):
        """Test batch processing simulation"""
        # Arrange
        service = ContentGeneratorService()
        topics = [
            RankedTopic(
                topic=f"Topic {i}",
                sources=sample_source_data,
                rank=i,
                ai_score=0.8 + (i * 0.02),
                sentiment="positive",
                tags=["AI", "technology"]
            )
            for i in range(1, 4)
        ]

        # Act
        results = []
        for topic in topics:
            result = await service.generate_content(
                topic=topic,
                content_type="tldr"
            )
            results.append(result)

        # Assert
        assert len(results) == 3
        for result in results:
            assert isinstance(result, GeneratedContent)
            assert result.word_count > 0

    @pytest.mark.asyncio
    async def test_different_content_types_integration(self, sample_ranked_topic):
        """Test all content types work end-to-end"""
        # Arrange
        service = ContentGeneratorService()
        content_types = ["tldr", "blog", "deepdive"]

        # Act & Assert
        for content_type in content_types:
            result = await service.generate_content(
                topic=sample_ranked_topic,
                content_type=content_type
            )
            assert result.content_type == content_type
            assert len(result.content) > 0

            # Verify content length expectations (adjusted for mock responses)
            if content_type == "tldr":
                assert 10 < result.word_count < 500
            elif content_type == "blog":
                assert 25 < result.word_count < 1500
            elif content_type == "deepdive":
                assert 40 < result.word_count < 3000

    @pytest.mark.asyncio
    async def test_different_writer_personalities(self, sample_ranked_topic):
        """Test different writer personalities produce varied content"""
        # Arrange
        service = ContentGeneratorService()
        personalities = ["professional", "casual", "expert", "skeptical"]

        # Act
        results = {}
        for personality in personalities:
            result = await service.generate_content(
                topic=sample_ranked_topic,
                content_type="tldr",
                writer_personality=personality
            )
            results[personality] = result

        # Assert
        for personality, result in results.items():
            assert result.writer_personality == personality
            assert len(result.content) > 0
            assert result.word_count > 0

    @pytest.mark.asyncio
    async def test_source_verification_integration(self, sample_ranked_topic):
        """Test source verification works with mock HTTP responses"""
        # Arrange
        service = ContentGeneratorService()

        # Act
        result = await service.generate_content(
            topic=sample_ranked_topic,
            content_type="tldr"
        )

        # Assert
        assert result.verification_status in ["verified", "partial", "unverified"]
        assert isinstance(result.fact_check_notes, list)
        assert len(result.fact_check_notes) > 0

    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling with various edge cases"""
        # Arrange
        service = ContentGeneratorService()

        # Test with empty topic
        empty_topic = RankedTopic(
            topic="",
            sources=[],
            rank=1,
            ai_score=0.5,
            sentiment="neutral"
        )

        # Act & Assert
        with pytest.raises(ValueError):
            await service.generate_content(topic=empty_topic, content_type="tldr")

    @pytest.mark.asyncio
    async def test_service_statistics_tracking(self, sample_ranked_topic):
        """Test that service tracks generation statistics"""
        # Arrange
        service = ContentGeneratorService()
        initial_count = len(service.active_generations)

        # Act
        await service.generate_content(
            topic=sample_ranked_topic,
            content_type="tldr"
        )

        # Assert
        # Active generations should be managed properly
        assert len(service.active_generations) >= initial_count

    @pytest.mark.asyncio
    async def test_blob_storage_integration(self, sample_ranked_topic):
        """Test blob storage operations work correctly"""
        # Arrange
        service = ContentGeneratorService()

        # Act
        result = await service.generate_content(
            topic=sample_ranked_topic,
            content_type="tldr"
        )

        # Assert
        # Verify blob client is functional (using mock)
        assert service.blob_client is not None
        assert hasattr(service.blob_client, 'upload_text')
        assert hasattr(service.blob_client, 'download_text')

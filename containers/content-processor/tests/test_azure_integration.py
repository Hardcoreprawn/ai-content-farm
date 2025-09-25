"""
Test Suite for Phase 2: Azure Integration

Tests Azure Blob Storage and OpenAI integration with proper mocking.
Follows functional patterns and prepares for real Azure deployment.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from models import ProcessingResult, TopicMetadata
from openai_client import OpenAIClient
from processor import ContentProcessor


class TestAzureIntegration:
    """Test Azure services integration with proper mocking."""

    @pytest.fixture
    def sample_topic(self):
        """Sample topic metadata for testing."""
        return TopicMetadata(
            topic_id="test-topic-001",
            title="How AI is Transforming Software Development",
            source="reddit",
            collected_at=datetime.now(timezone.utc),
            priority_score=0.85,
            subreddit="programming",
            upvotes=1250,
            comments=89,
        )

    @pytest.fixture
    def mock_blob_client(self):
        """Mock blob storage client."""
        with patch("processor.SimplifiedBlobClient") as mock:
            mock_instance = MagicMock()
            mock_instance.test_connection = MagicMock(
                return_value={"status": "healthy"}
            )
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client."""
        with patch("processor.OpenAIClient") as mock:
            mock_instance = MagicMock()
            mock_instance.test_connection = AsyncMock(return_value=True)
            mock_instance.generate_article = AsyncMock(
                return_value=(
                    "Test article content about AI in software development...",
                    0.25,  # cost
                    1500,  # tokens
                )
            )
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.mark.integration
    @patch("processor.SimplifiedBlobClient")
    @patch("processor.OpenAIClient")
    async def test_health_check_with_azure_services(
        self, mock_openai_class, mock_blob_class
    ):
        """Test health check validates Azure services."""
        # Setup mocks properly
        mock_blob = MagicMock()
        mock_blob.test_connection.return_value = {"status": "healthy"}
        mock_blob_class.return_value = mock_blob

        mock_openai = MagicMock()
        mock_openai.test_connection = AsyncMock(return_value=True)
        mock_openai_class.return_value = mock_openai

        processor = ContentProcessor()
        status = await processor.check_health()

        assert status.azure_openai_available is True
        assert status.blob_storage_available is True
        assert status.processor_id is not None
        assert status.last_health_check is not None

    @pytest.mark.integration
    async def test_process_available_work_integration(
        self, mock_blob_client, mock_openai_client, sample_topic
    ):
        """Test processing work with Azure integration."""
        processor = ContentProcessor()

        # Mock finding available topics
        with patch.object(
            processor.topic_discovery,
            "find_available_topics",
            return_value=[sample_topic],
        ):
            result = await processor.process_available_work(
                batch_size=5, priority_threshold=0.7
            )

        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert result.topics_processed >= 0
        assert result.total_cost >= 0.0

    @pytest.mark.integration
    async def test_topic_lease_coordination(self, mock_blob_client, mock_openai_client):
        """Test lease-based coordination for parallel processing."""
        processor = ContentProcessor()

        # Test lease acquisition via service
        lease_acquired = await processor.lease_coordinator.acquire_topic_lease(
            "test-topic"
        )
        assert lease_acquired is True

        # Test lease release via service
        lease_released = await processor.lease_coordinator.release_topic_lease(
            "test-topic"
        )
        assert lease_released is True

    @pytest.mark.integration
    async def test_openai_article_generation(self):
        """Test OpenAI article generation with cost tracking."""
        client = OpenAIClient()

        # Test without real credentials (should use mock)
        article, cost, tokens = await client.generate_article(
            topic_title="Test Topic",
            target_word_count=3000,
        )

        assert article is not None
        assert cost >= 0.0
        assert tokens >= 0

    @pytest.mark.integration
    async def test_error_handling_azure_failures(
        self, mock_blob_client, mock_openai_client
    ):
        """Test graceful handling of Azure service failures."""
        # Mock Azure failures
        mock_blob_client.test_connection = MagicMock(
            side_effect=Exception("Blob connection failed")
        )
        mock_openai_client.test_connection = AsyncMock(
            side_effect=Exception("OpenAI connection failed")
        )

        processor = ContentProcessor()
        status = await processor.check_health()

        # Should handle failures gracefully
        assert status.azure_openai_available is False
        assert status.blob_storage_available is False
        assert status.status == "error"

    @pytest.mark.integration
    async def test_cost_tracking_accuracy(
        self, mock_blob_client, mock_openai_client, sample_topic
    ):
        """Test accurate cost tracking across processing."""
        processor = ContentProcessor()

        # Mock processing with known costs
        mock_openai_client.generate_article = AsyncMock(
            return_value=("Test article", 0.30, 2000)
        )

        with patch.object(
            processor.topic_discovery,
            "find_available_topics",
            return_value=[sample_topic],
        ):
            result = await processor.process_available_work(batch_size=1)

        # Verify cost tracking
        assert result.total_cost > 0.0
        assert processor.session_cost >= result.total_cost

    @pytest.mark.integration
    async def test_functional_immutability_parallel_processing(
        self, mock_blob_client, mock_openai_client, sample_topic
    ):
        """Test that parallel processors don't interfere with each other."""
        # Create multiple processor instances
        processors = [ContentProcessor() for _ in range(3)]

        # Each should have unique ID
        processor_ids = [p.processor_id for p in processors]
        assert len(set(processor_ids)) == 3  # All unique

        # Parallel health checks should work independently
        health_results = []
        for processor in processors:
            status = await processor.check_health()
            health_results.append(status)

        # Each should have independent status
        for status in health_results:
            assert status.processor_id is not None
            assert status.last_health_check is not None


class TestOpenAIIntegration:
    """Focused tests for OpenAI integration."""

    @pytest.mark.integration
    def test_prompt_generation(self):
        """Test article prompt generation."""
        client = OpenAIClient()

        prompt = client._build_article_prompt(
            topic_title="AI in Healthcare",
            research_content="Research shows AI improves diagnostics...",
            target_word_count=3000,
            quality_requirements={"bias_check": True, "fact_check": True},
        )

        assert "AI in Healthcare" in prompt
        assert "3000 words" in prompt
        assert "Research shows AI improves diagnostics" in prompt
        assert "bias_check" in prompt

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cost_calculation(self):
        """Test OpenAI cost calculation accuracy."""
        client = OpenAIClient()

        # Test GPT-4 cost calculation
        client.model_name = "gpt-4"
        cost = await client._calculate_cost(total_tokens=2000, prompt_tokens=500)

        # Should calculate input (500 * $0.01/1k) + output (1500 * $0.03/1k)
        # Using current fallback pricing: input $0.01/1k, output $0.03/1k
        expected_cost = (500 * 0.01 / 1000) + (1500 * 0.03 / 1000)
        assert abs(cost - expected_cost) < 0.001

    @pytest.mark.integration
    def test_mock_article_generation(self):
        """Test mock article generation when OpenAI unavailable."""
        client = OpenAIClient()
        # Force mock mode by not setting credentials
        client.client = None

        mock_article = client._generate_mock_article("Test Topic")

        assert "Test Topic" in mock_article
        assert "mock article" in mock_article.lower()
        assert len(mock_article) > 100  # Reasonable length


class TestBlobStorageIntegration:
    """Tests for blob storage patterns."""

    @pytest.mark.integration
    @patch("libs.simplified_blob_client.SimplifiedBlobClient")
    async def test_topic_storage_patterns(self, mock_blob_class):
        """Test blob storage patterns for topic data."""
        mock_blob = MagicMock()
        mock_blob.test_connection = AsyncMock(return_value=True)
        mock_blob_class.return_value = mock_blob

        processor = ContentProcessor()

        # Test basic connectivity via storage service
        connection_ok = await processor.storage.test_storage_connectivity()
        assert connection_ok is True

    @pytest.mark.integration
    @patch("processor.SimplifiedBlobClient")
    async def test_blob_storage_error_handling(self, mock_blob_class):
        """Test blob storage error handling."""
        mock_blob = MagicMock()
        mock_blob.test_connection.side_effect = Exception("Storage error")
        mock_blob_class.return_value = mock_blob

        processor = ContentProcessor()

        # Should handle errors gracefully via storage service
        connection_ok = await processor.storage.test_storage_connectivity()
        assert connection_ok is False


# Integration test for complete workflow
class TestEndToEndWorkflow:
    """Test complete processing workflow."""

    @pytest.mark.integration
    @patch("processor.SimplifiedBlobClient")
    @patch("processor.OpenAIClient")
    async def test_complete_processing_workflow(
        self, mock_openai_class, mock_blob_class
    ):
        """Test complete topic → article workflow."""
        # Setup mocks
        mock_blob = MagicMock()
        mock_blob.test_connection = AsyncMock(return_value=True)
        mock_blob_class.return_value = mock_blob

        mock_openai = MagicMock()
        mock_openai.test_connection = AsyncMock(return_value=True)
        mock_openai.generate_article = AsyncMock(
            return_value=("Complete test article content", 0.45, 2800)
        )
        mock_openai_class.return_value = mock_openai

        # Create sample topic
        topic = TopicMetadata(
            topic_id="workflow-test",
            title="Complete Workflow Test",
            source="test",
            collected_at=datetime.now(timezone.utc),
            priority_score=0.9,
        )

        processor = ContentProcessor()

        # Test complete workflow
        with patch.object(
            processor.topic_discovery, "find_available_topics", return_value=[topic]
        ):
            result = await processor.process_available_work(batch_size=1)

        # Verify workflow completion
        assert result.success is True
        assert result.total_cost > 0.0
        assert result.processing_time > 0.0

        # Verify session tracking
        assert processor.session_topics_processed > 0
        assert processor.session_cost > 0.0

"""
Tests for ProcessorContext dataclass.

Tests immutability, dependency injection, and context creation.
"""

from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, Mock

import pytest
from core.processor_context import ProcessorContext


class TestProcessorContextImmutability:
    """Test that ProcessorContext is immutable."""

    def test_context_is_frozen(self):
        """Test that context fields cannot be modified."""
        # Arrange
        context = ProcessorContext(
            blob_client=Mock(),
            queue_client=Mock(),
            rate_limiter=Mock(),
            openai_client=Mock(),
            processor_id="test-processor",
            session_id="test-session",
        )

        # Act & Assert
        with pytest.raises(FrozenInstanceError):
            context.processor_id = "different-id"  # type: ignore[misc]

    def test_cannot_add_new_attributes(self):
        """Test that new attributes cannot be added to context."""
        # Arrange
        context = ProcessorContext(
            blob_client=Mock(),
            queue_client=Mock(),
            rate_limiter=Mock(),
            openai_client=Mock(),
            processor_id="test-processor",
            session_id="test-session",
        )

        # Act & Assert
        with pytest.raises(FrozenInstanceError):
            context.new_field = "value"  # type: ignore[misc]


class TestProcessorContextCreation:
    """Test ProcessorContext creation and initialization."""

    def test_creates_with_required_fields(self):
        """Test context creation with required fields."""
        # Arrange
        mock_blob = Mock()
        mock_queue = Mock()
        mock_limiter = Mock()
        mock_openai = Mock()

        # Act
        context = ProcessorContext(
            blob_client=mock_blob,
            queue_client=mock_queue,
            rate_limiter=mock_limiter,
            openai_client=mock_openai,
            processor_id="proc-123",
            session_id="sess-456",
        )

        # Assert
        assert context.blob_client is mock_blob
        assert context.queue_client is mock_queue
        assert context.rate_limiter is mock_limiter
        assert context.openai_client is mock_openai
        assert context.processor_id == "proc-123"
        assert context.session_id == "sess-456"

    def test_creates_with_default_values(self):
        """Test context creation with default container/queue names."""
        # Act
        context = ProcessorContext(
            blob_client=Mock(),
            queue_client=Mock(),
            rate_limiter=Mock(),
            openai_client=Mock(),
            processor_id="test",
            session_id="test",
        )

        # Assert - verify defaults
        assert context.input_container == "collected-content"
        assert context.output_container == "processed-content"
        assert context.markdown_queue == "markdown-generation"
        assert context.max_articles_per_run == 10
        assert context.min_articles_for_trigger == 5
        assert context.lease_timeout_seconds == 300

    def test_creates_with_custom_values(self):
        """Test context creation with custom configuration."""
        # Act
        context = ProcessorContext(
            blob_client=Mock(),
            queue_client=Mock(),
            rate_limiter=Mock(),
            openai_client=Mock(),
            processor_id="test",
            session_id="test",
            input_container="custom-input",
            output_container="custom-output",
            markdown_queue="custom-queue",
            max_articles_per_run=20,
            min_articles_for_trigger=10,
            lease_timeout_seconds=600,
        )

        # Assert
        assert context.input_container == "custom-input"
        assert context.output_container == "custom-output"
        assert context.markdown_queue == "custom-queue"
        assert context.max_articles_per_run == 20
        assert context.min_articles_for_trigger == 10
        assert context.lease_timeout_seconds == 600


class TestProcessorContextDependencyInjection:
    """Test that context properly holds dependencies."""

    def test_holds_blob_client_dependency(self):
        """Test that blob client is accessible."""
        # Arrange
        mock_blob_client = AsyncMock()
        mock_blob_client.test_method = AsyncMock(return_value="test")

        context = ProcessorContext(
            blob_client=mock_blob_client,
            queue_client=Mock(),
            rate_limiter=Mock(),
            openai_client=Mock(),
            processor_id="test",
            session_id="test",
        )

        # Act & Assert
        assert context.blob_client is mock_blob_client
        assert hasattr(context.blob_client, "test_method")

    def test_holds_queue_client_dependency(self):
        """Test that queue client is accessible."""
        # Arrange
        mock_queue_client = AsyncMock()
        mock_queue_client.send_message = AsyncMock()

        context = ProcessorContext(
            blob_client=Mock(),
            queue_client=mock_queue_client,
            rate_limiter=Mock(),
            openai_client=Mock(),
            processor_id="test",
            session_id="test",
        )

        # Act & Assert
        assert context.queue_client is mock_queue_client
        assert hasattr(context.queue_client, "send_message")

    def test_holds_rate_limiter_dependency(self):
        """Test that rate limiter is accessible."""
        # Arrange
        mock_rate_limiter = Mock()
        mock_rate_limiter.__aenter__ = AsyncMock()
        mock_rate_limiter.__aexit__ = AsyncMock()

        context = ProcessorContext(
            blob_client=Mock(),
            queue_client=Mock(),
            rate_limiter=mock_rate_limiter,
            openai_client=Mock(),
            processor_id="test",
            session_id="test",
        )

        # Act & Assert
        assert context.rate_limiter is mock_rate_limiter

    def test_holds_openai_client_dependency(self):
        """Test that OpenAI client is accessible."""
        # Arrange
        mock_openai_client = Mock()
        mock_openai_client.chat = Mock()

        context = ProcessorContext(
            blob_client=Mock(),
            queue_client=Mock(),
            rate_limiter=Mock(),
            openai_client=mock_openai_client,
            processor_id="test",
            session_id="test",
        )

        # Act & Assert
        assert context.openai_client is mock_openai_client
        assert hasattr(context.openai_client, "chat")


class TestProcessorContextIdentifiers:
    """Test processor and session identifiers."""

    def test_processor_id_is_set(self):
        """Test that processor_id is correctly set."""
        # Act
        context = ProcessorContext(
            blob_client=Mock(),
            queue_client=Mock(),
            rate_limiter=Mock(),
            openai_client=Mock(),
            processor_id="my-processor-id",
            session_id="test",
        )

        # Assert
        assert context.processor_id == "my-processor-id"

    def test_session_id_is_set(self):
        """Test that session_id is correctly set."""
        # Act
        context = ProcessorContext(
            blob_client=Mock(),
            queue_client=Mock(),
            rate_limiter=Mock(),
            openai_client=Mock(),
            processor_id="test",
            session_id="my-session-id",
        )

        # Assert
        assert context.session_id == "my-session-id"

    def test_different_instances_have_different_ids(self):
        """Test that different context instances can have different IDs."""
        # Act
        context1 = ProcessorContext(
            blob_client=Mock(),
            queue_client=Mock(),
            rate_limiter=Mock(),
            openai_client=Mock(),
            processor_id="processor-1",
            session_id="session-1",
        )

        context2 = ProcessorContext(
            blob_client=Mock(),
            queue_client=Mock(),
            rate_limiter=Mock(),
            openai_client=Mock(),
            processor_id="processor-2",
            session_id="session-2",
        )

        # Assert
        assert context1.processor_id != context2.processor_id
        assert context1.session_id != context2.session_id


class TestProcessorContextConfiguration:
    """Test configuration parameters in context."""

    def test_max_articles_per_run_default(self):
        """Test default max_articles_per_run value."""
        # Act
        context = ProcessorContext(
            blob_client=Mock(),
            queue_client=Mock(),
            rate_limiter=Mock(),
            openai_client=Mock(),
            processor_id="test",
            session_id="test",
        )

        # Assert
        assert context.max_articles_per_run == 10

    def test_max_articles_per_run_custom(self):
        """Test custom max_articles_per_run value."""
        # Act
        context = ProcessorContext(
            blob_client=Mock(),
            queue_client=Mock(),
            rate_limiter=Mock(),
            openai_client=Mock(),
            processor_id="test",
            session_id="test",
            max_articles_per_run=50,
        )

        # Assert
        assert context.max_articles_per_run == 50

    def test_container_names_are_accessible(self):
        """Test that container names are accessible."""
        # Act
        context = ProcessorContext(
            blob_client=Mock(),
            queue_client=Mock(),
            rate_limiter=Mock(),
            openai_client=Mock(),
            processor_id="test",
            session_id="test",
            input_container="input",
            output_container="output",
        )

        # Assert
        assert context.input_container == "input"
        assert context.output_container == "output"

    def test_queue_name_is_accessible(self):
        """Test that queue name is accessible."""
        # Act
        context = ProcessorContext(
            blob_client=Mock(),
            queue_client=Mock(),
            rate_limiter=Mock(),
            openai_client=Mock(),
            processor_id="test",
            session_id="test",
            markdown_queue="my-queue",
        )

        # Assert
        assert context.markdown_queue == "my-queue"

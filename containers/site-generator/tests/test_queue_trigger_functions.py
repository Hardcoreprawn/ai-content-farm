"""
Tests for Queue Trigger Functions

Tests queue message sending functions following contract-based testing principles.
Tests outcomes and data contracts, not implementation methods.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from queue_trigger_functions import (
    should_trigger_html_generation,
    trigger_batch_operation,
    trigger_html_generation,
)


class TestTriggerHTMLGeneration:
    """Test HTML generation trigger function contracts and outcomes."""

    @pytest.mark.asyncio
    async def test_successful_trigger_returns_success_contract(self):
        """
        Contract: Successful trigger returns dict with required fields.

        Outcome: status='success', message_id present, metadata correct
        """
        markdown_files = ["article1.md", "article2.md", "article3.md"]
        queue_name = "test-queue"
        generator_id = "test-gen-123"

        # Mock queue client
        mock_result = {"message_id": "msg-456", "status": "queued"}
        with patch("queue_trigger_functions.get_queue_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.send_message = AsyncMock(return_value=mock_result)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_client

            result = await trigger_html_generation(
                markdown_files=markdown_files,
                queue_name=queue_name,
                generator_id=generator_id,
            )

        # Verify contract: Required fields present
        assert result["status"] == "success"
        assert result["message_id"] == "msg-456"
        assert result["queue_name"] == queue_name
        assert result["markdown_files_count"] == 3
        assert "timestamp" in result
        assert "payload" in result

        # Verify outcome: Payload has correct structure
        payload = result["payload"]
        assert payload["content_type"] == "markdown"
        assert payload["markdown_files_count"] == 3
        assert payload["trigger"] == "markdown_completion"
        assert payload["generator_id"] == generator_id

    @pytest.mark.asyncio
    async def test_empty_files_list_returns_skipped_status(self):
        """
        Contract: Empty markdown files list results in skipped status.

        Outcome: No queue message sent, status='skipped'
        """
        result = await trigger_html_generation(
            markdown_files=[],
            queue_name="test-queue",
            generator_id="test-gen",
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "no_markdown_files"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_queue_failure_returns_error_without_raising(self):
        """
        Contract: Queue send failure returns error dict, doesn't raise exception.

        Outcome: status='error', error message present, calling code can continue
        """
        markdown_files = ["test.md"]

        # Mock queue client to raise exception
        with patch("queue_trigger_functions.get_queue_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.send_message = AsyncMock(
                side_effect=ConnectionError("Queue unavailable")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_client

            result = await trigger_html_generation(
                markdown_files=markdown_files,
                queue_name="test-queue",
                generator_id="test-gen",
            )

        # Verify contract: Error returned, not raised
        assert result["status"] == "error"
        assert "error" in result
        assert "Queue unavailable" in result["error"]
        assert result["error_type"] == "ConnectionError"

    @pytest.mark.asyncio
    async def test_correlation_id_propagation(self):
        """
        Contract: Correlation ID is propagated through queue message.

        Outcome: correlation_id in payload matches input
        """
        correlation_id = "correlation-xyz-789"

        mock_result = {"message_id": "msg-123"}
        with patch("queue_trigger_functions.get_queue_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.send_message = AsyncMock(return_value=mock_result)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_client

            result = await trigger_html_generation(
                markdown_files=["test.md"],
                queue_name="test-queue",
                generator_id="gen-123",
                correlation_id=correlation_id,
            )

        assert result["payload"]["correlation_id"] == correlation_id

    @pytest.mark.asyncio
    async def test_additional_metadata_merged_into_payload(self):
        """
        Contract: Additional metadata is merged into queue message payload.

        Outcome: Custom metadata fields appear in payload
        """
        additional_metadata = {
            "custom_field": "custom_value",
            "batch_size": 10,
        }

        mock_result = {"message_id": "msg-123"}
        with patch("queue_trigger_functions.get_queue_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.send_message = AsyncMock(return_value=mock_result)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_client

            result = await trigger_html_generation(
                markdown_files=["test.md"],
                queue_name="test-queue",
                generator_id="gen-123",
                additional_metadata=additional_metadata,
            )

        payload = result["payload"]
        assert payload["custom_field"] == "custom_value"
        assert payload["batch_size"] == 10


class TestTriggerBatchOperation:
    """Test generic batch operation trigger function."""

    @pytest.mark.asyncio
    async def test_batch_operation_sends_correct_message_structure(self):
        """
        Contract: Batch operation creates proper QueueMessageModel.

        Outcome: operation_type, service_name, and payload correct
        """
        payload = {"test_data": "test_value"}

        mock_result = {"message_id": "msg-789"}
        with patch("queue_trigger_functions.get_queue_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.send_message = AsyncMock(return_value=mock_result)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_client

            result = await trigger_batch_operation(
                operation_type="test_operation",
                queue_name="test-queue",
                service_name="test-service",
                payload=payload,
                correlation_id="corr-123",
            )

        assert result["status"] == "success"
        assert result["operation_type"] == "test_operation"
        assert result["payload"]["test_data"] == "test_value"
        assert result["payload"]["correlation_id"] == "corr-123"


class TestShouldTriggerHTMLGeneration:
    """Test HTML generation trigger decision logic."""

    def test_returns_true_when_files_present(self):
        """
        Contract: Returns True when markdown files exist.

        Outcome: Boolean True for valid file list
        """
        result = should_trigger_html_generation(
            markdown_files=["file1.md", "file2.md"],
            config={},
            force_trigger=False,
        )
        assert result is True

    def test_returns_false_when_no_files(self):
        """
        Contract: Returns False when no markdown files.

        Outcome: Boolean False for empty file list
        """
        result = should_trigger_html_generation(
            markdown_files=[],
            config={},
            force_trigger=False,
        )
        assert result is False

    def test_force_trigger_overrides_empty_files(self):
        """
        Contract: force_trigger=True returns True regardless of files.

        Outcome: Boolean True even with empty file list
        """
        result = should_trigger_html_generation(
            markdown_files=[],
            config={},
            force_trigger=True,
        )
        assert result is True

    def test_respects_minimum_files_threshold(self):
        """
        Contract: Respects html_trigger_min_files config setting.

        Outcome: Returns False if below threshold
        """
        result = should_trigger_html_generation(
            markdown_files=["file1.md"],
            config={"html_trigger_min_files": 3},
            force_trigger=False,
        )
        assert result is False

    def test_meets_minimum_files_threshold(self):
        """
        Contract: Returns True when meeting or exceeding threshold.

        Outcome: Boolean True when files >= threshold
        """
        result = should_trigger_html_generation(
            markdown_files=["file1.md", "file2.md", "file3.md"],
            config={"html_trigger_min_files": 3},
            force_trigger=False,
        )
        assert result is True


class TestQueueTriggerIntegration:
    """Integration tests for queue trigger workflow."""

    @pytest.mark.asyncio
    async def test_complete_trigger_workflow(self):
        """
        Integration: Complete workflow from markdown to HTML trigger.

        Outcome: Message sent with all required metadata
        """
        markdown_files = ["article-1.md", "article-2.md"]

        mock_queue_result = {
            "message_id": "msg-integration-test",
            "status": "queued",
        }

        with patch("queue_trigger_functions.get_queue_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.send_message = AsyncMock(return_value=mock_queue_result)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_get_client.return_value = mock_client

            # Simulate complete workflow
            should_trigger = should_trigger_html_generation(
                markdown_files=markdown_files,
                config={"html_trigger_min_files": 1},
                force_trigger=False,
            )

            assert should_trigger is True

            result = await trigger_html_generation(
                markdown_files=markdown_files,
                queue_name="site-generation-requests",
                generator_id="integration-test-gen",
                additional_metadata={"source": "integration-test"},
            )

            # Verify complete workflow outcome
            assert result["status"] == "success"
            assert result["markdown_files_count"] == 2
            assert result["payload"]["content_type"] == "markdown"
            assert result["payload"]["source"] == "integration-test"

            # Verify queue client was called correctly
            mock_client.send_message.assert_called_once()
            call_args = mock_client.send_message.call_args
            message = call_args[0][0]
            assert message.service_name == "site-generator"
            assert message.operation == "wake_up"

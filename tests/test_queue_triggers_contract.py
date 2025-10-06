"""
Test Queue Trigger Data Contracts

Verifies that queue trigger functions send correct message formats
for downstream consumers.
"""

from unittest.mock import AsyncMock, patch

import pytest

from libs.queue_triggers import (
    trigger_html_generation,
    trigger_markdown_generation,
    trigger_processing,
)


@pytest.mark.asyncio
async def test_trigger_markdown_generation_sends_json_content_type():
    """
    Verify that trigger_markdown_generation sends content_type='json'
    for site-generator to process correctly.

    Bug fix: Was sending 'processed' which caused site-generator to use
    backward-compatible fallback instead of explicit 'json' path.
    """
    with patch("libs.queue_triggers.get_queue_client") as mock_queue:
        # Setup mock
        mock_client = AsyncMock()
        mock_client.send_message = AsyncMock(return_value={"message_id": "test-123"})
        mock_queue.return_value.__aenter__.return_value = mock_client

        # Call function
        result = await trigger_markdown_generation(
            processed_files=["processed-content/articles/2025/10/06/test.json"],
            correlation_id="test-correlation-id",
        )

        # Verify success
        assert result["status"] == "success"
        assert result["queue_name"] == "site-generation-requests"

        # Verify message was sent
        assert mock_client.send_message.called

        # Extract the message that was sent
        sent_message = mock_client.send_message.call_args[0][0]

        # Verify critical fields
        assert sent_message.service_name == "content-processor"
        assert sent_message.operation == "wake_up"

        # CRITICAL: Verify content_type is "json" not "processed"
        assert (
            sent_message.payload["content_type"] == "json"
        ), "content_type must be 'json' for site-generator to process correctly"

        # Verify files are included
        assert sent_message.payload["files"] == [
            "processed-content/articles/2025/10/06/test.json"
        ]
        assert sent_message.payload["files_count"] == 1


@pytest.mark.asyncio
async def test_trigger_processing_sends_json_content_type():
    """Verify trigger_processing sends correct content_type."""
    with patch("libs.queue_triggers.get_queue_client") as mock_queue:
        mock_client = AsyncMock()
        mock_client.send_message = AsyncMock(return_value={"message_id": "test-456"})
        mock_queue.return_value.__aenter__.return_value = mock_client

        result = await trigger_processing(
            collected_files=["collections/2025/10/06/tech.json"]
        )

        assert result["status"] == "success"
        sent_message = mock_client.send_message.call_args[0][0]
        assert sent_message.payload["content_type"] == "json"


@pytest.mark.asyncio
async def test_trigger_html_generation_sends_markdown_content_type():
    """Verify trigger_html_generation sends correct content_type."""
    with patch("libs.queue_triggers.get_queue_client") as mock_queue:
        mock_client = AsyncMock()
        mock_client.send_message = AsyncMock(return_value={"message_id": "test-789"})
        mock_queue.return_value.__aenter__.return_value = mock_client

        result = await trigger_html_generation(
            markdown_files=["markdown-content/articles/test.md"]
        )

        assert result["status"] == "success"
        sent_message = mock_client.send_message.call_args[0][0]

        # HTML generation should send 'markdown' content_type
        assert sent_message.payload["content_type"] == "markdown"


@pytest.mark.asyncio
async def test_payload_type_hints_allow_mixed_types():
    """
    Verify payload can contain mixed types (str, list, int) without
    type errors.

    Bug fix: Added explicit Dict[str, Any] type hint to prevent
    Pyright from inferring Dict[str, str].
    """
    with patch("libs.queue_triggers.get_queue_client") as mock_queue:
        mock_client = AsyncMock()
        mock_client.send_message = AsyncMock(return_value={"message_id": "test-mixed"})
        mock_queue.return_value.__aenter__.return_value = mock_client

        result = await trigger_markdown_generation(
            processed_files=["file1.json", "file2.json", "file3.json"],
            correlation_id="test-123",
        )

        assert result["status"] == "success"
        sent_message = mock_client.send_message.call_args[0][0]

        # Verify mixed types in payload
        assert isinstance(sent_message.payload["content_type"], str)
        assert isinstance(sent_message.payload["files"], list)
        assert isinstance(sent_message.payload["files_count"], int)
        assert sent_message.payload["files_count"] == 3

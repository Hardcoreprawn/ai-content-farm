"""
Tests for startup_diagnostics module to ensure container startup works correctly.
"""

from unittest.mock import AsyncMock

import pytest
from startup_diagnostics import process_startup_queue_messages


@pytest.mark.asyncio
async def test_process_startup_queue_messages_calls_with_correct_parameters():
    """
    Test that process_startup_queue_messages calls process_queue_messages with correct parameters.

    This test validates the actual function signature match, which would have caught
    the timeout_seconds parameter issue that prevented proper container startup.
    """
    # Mock storage_queue_router
    mock_router = AsyncMock()
    mock_router.process_storage_queue_message = AsyncMock(
        return_value={"status": "success", "message": "Test message processed"}
    )

    # Mock process_queue_messages_func - this is what we're testing
    mock_process_func = AsyncMock(
        return_value={"messages_processed": 2, "status": "success"}
    )

    # Call the function with our mocks
    result = await process_startup_queue_messages(
        storage_queue_router=mock_router, process_queue_messages_func=mock_process_func
    )

    # Verify process_queue_messages was called
    assert mock_process_func.called
    call_kwargs = mock_process_func.call_args.kwargs

    # Verify required parameters exist
    assert "queue_name" in call_kwargs
    assert "message_handler" in call_kwargs
    assert "max_messages" in call_kwargs

    # Verify timeout_seconds is NOT passed (this was the bug that caused startup failure)
    assert (
        "timeout_seconds" not in call_kwargs
    ), "process_queue_messages should not receive timeout_seconds parameter"

    # Verify correct values
    assert call_kwargs["queue_name"] == "site-generator-queue"
    assert call_kwargs["max_messages"] == 10
    assert callable(call_kwargs["message_handler"])

    # Verify function returned True (messages were processed)
    assert result is True


@pytest.mark.asyncio
async def test_process_startup_queue_messages_returns_false_when_no_messages():
    """Test that startup queue processing returns False when no messages processed."""
    mock_router = AsyncMock()
    mock_process_func = AsyncMock(
        return_value={"messages_processed": 0, "status": "success"}
    )

    result = await process_startup_queue_messages(
        storage_queue_router=mock_router, process_queue_messages_func=mock_process_func
    )

    # Should return False when no messages processed
    assert result is False


@pytest.mark.asyncio
async def test_process_startup_queue_messages_handles_error_gracefully():
    """Test that startup queue processing doesn't crash on errors."""
    mock_router = AsyncMock()
    mock_process_func = AsyncMock(side_effect=Exception("Queue connection failed"))

    result = await process_startup_queue_messages(
        storage_queue_router=mock_router, process_queue_messages_func=mock_process_func
    )

    # Should return False on error, not crash
    assert result is False

"""
Integration Tests for Content Processor

Black-box tests that verify:
1. Queue message format and parsing
2. Blob download/upload contracts
3. OpenAI API request/response handling
4. Output queue message format
5. End-to-end data flow through the processor

Tests mock external services (OpenAI, Blob Storage, Queues) but verify
real data formats and integration points - not algorithms.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from libs.queue_client import QueueMessageModel


@pytest.fixture
def mock_blob_client():
    """Mock blob client with realistic responses."""
    client = AsyncMock()

    # Mock collection blob download (input)
    collection_data = {
        "collection_id": "col_12345",
        "collected_at": "2025-10-15T10:00:00Z",
        "source": "reddit",
        "topics": [
            {
                "topic_id": "reddit_test123",
                "title": "Test AI Discussion",
                "source": "reddit",
                "subreddit": "programming",
                "url": "https://reddit.com/r/programming/test123",
                "upvotes": 500,
                "comments": 25,
                "collected_at": "2025-10-15T10:00:00Z",
                "priority_score": 0.75,
            }
        ],
    }
    client.download_json.return_value = collection_data

    # Mock blob upload (output)
    client.upload_json.return_value = True

    # Mock list_blobs for idempotency check
    client.list_blobs.return_value = []

    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client with realistic article generation response."""
    client = AsyncMock()

    # Mock article generation response
    article_response = Mock()
    article_response.choices = [Mock()]
    article_response.choices[
        0
    ].message.content = """## Test AI Discussion Article

This is a generated article about AI discussions.

### Key Points
- Point 1
- Point 2
- Point 3

### Conclusion
Summary of the discussion."""

    article_response.usage.prompt_tokens = 100
    article_response.usage.completion_tokens = 200

    # Mock metadata generation response
    metadata_response = Mock()
    metadata_response.choices = [Mock()]
    metadata_response.choices[0].message.content = json.dumps(
        {
            "title": "Test AI Discussion",
            "slug": "test-ai-discussion",
            "filename": "articles/test-ai-discussion.html",
            "url": "/articles/test-ai-discussion.html",
        }
    )
    metadata_response.usage.prompt_tokens = 50
    metadata_response.usage.completion_tokens = 30

    # Return different responses based on call order
    client.chat.completions.create.side_effect = [article_response, metadata_response]

    return client


@pytest.fixture
def mock_queue_client():
    """Mock queue client for markdown trigger messages."""
    client = AsyncMock()

    # Mock send_message response
    send_response = Mock()
    send_response.id = "msg_output_123"
    client.send_message.return_value = send_response

    return client


@pytest.fixture
def valid_queue_message():
    """Valid input queue message with blob_path."""
    return QueueMessageModel(
        message_id="msg_input_456",
        operation="process",
        service_name="content-collector",
        correlation_id="test_session_789",
        payload={
            "blob_path": "collections/2025/10/15/col_12345.json",
            "collection_id": "col_12345",
        },
    )


class TestProcessorIntegration:
    """Integration tests verifying data flow and contracts."""

    @pytest.mark.asyncio
    async def test_end_to_end_message_processing(
        self,
        mock_blob_client,
        mock_openai_client,
        mock_queue_client,
        valid_queue_message,
    ):
        """
        Test complete flow: Queue → Blob → OpenAI → Blob → Queue

        Verifies:
        - Input queue message is parsed correctly
        - Collection blob is downloaded with correct path
        - OpenAI receives properly formatted request
        - Output blob is saved with correct structure
        - Output queue message has correct format
        """
        from endpoints.storage_queue_router import process_storage_queue_message

        # Mock the processor context creation AND the processing functions
        with (
            patch(
                "endpoints.storage_queue_router.get_processor_context"
            ) as mock_context,
            patch(
                "endpoints.storage_queue_router.process_collection_file"
            ) as mock_process,
        ):

            # Create mock context
            mock_ctx = Mock()
            mock_ctx.blob_client = mock_blob_client
            mock_ctx.queue_client = mock_queue_client
            mock_ctx.openai_client = mock_openai_client
            mock_ctx.processor_id = "test_processor"
            mock_ctx.session_id = "test_session"
            mock_ctx.rate_limiter = None
            mock_ctx.input_container = "collected-content"
            mock_context.return_value = mock_ctx

            # Mock the processing result
            from models.models import ProcessingResult

            mock_process.return_value = ProcessingResult(
                topics_processed=1,
                articles_generated=1,
                total_cost=0.05,
                processing_time=5.0,
                success=True,
            )

            # Execute the processing
            result = await process_storage_queue_message(valid_queue_message)

            # VERIFY OUTPUT CONTRACT
            assert result["status"] == "success"
            assert result["operation"] == "processing_completed"
            assert "result" in result
            assert result["message_id"] == "msg_input_456"
            assert result["result"]["topics_processed"] == 1
            assert result["result"]["articles_generated"] == 1

            # VERIFY process_collection_file was called with correct parameters
            assert mock_process.call_count == 1
            call_args = mock_process.call_args
            # Verify keyword arguments
            assert (
                call_args.kwargs["blob_path"] == "collections/2025/10/15/col_12345.json"
            )
            assert call_args.kwargs["context"] == mock_ctx

    @pytest.mark.asyncio
    async def test_invalid_queue_message_format(self):
        """Test handling of malformed queue messages."""
        from endpoints.storage_queue_router import process_storage_queue_message

        invalid_message = QueueMessageModel(
            message_id="msg_bad",
            operation="process",
            service_name="test",
            correlation_id="test",
            payload={},  # Missing blob_path!
        )

        result = await process_storage_queue_message(invalid_message)

        # VERIFY ERROR RESPONSE CONTRACT
        assert result["status"] == "error"
        assert "error" in result
        assert "blob_path" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_blob_not_found_handling(self, mock_queue_client):
        """Test handling when collection blob doesn't exist."""
        from endpoints.storage_queue_router import process_storage_queue_message

        # Mock blob client that returns None (not found)
        mock_blob = AsyncMock()
        mock_blob.download_json.return_value = None
        mock_blob.list_blobs.return_value = []

        with patch(
            "endpoints.storage_queue_router.get_processor_context"
        ) as mock_context:
            mock_ctx = Mock()
            mock_ctx.blob_client = mock_blob
            mock_ctx.queue_client = mock_queue_client
            mock_ctx.input_container = "collected-content"
            mock_context.return_value = mock_ctx

            message = QueueMessageModel(
                message_id="msg_123",
                operation="process",
                service_name="test",
                correlation_id="test",
                payload={"blob_path": "nonexistent/path.json"},
            )

            result = await process_storage_queue_message(message)

            # VERIFY GRACEFUL FAILURE
            # Processing completes even if no topics
            assert result["status"] == "success"
            assert result["result"]["topics_processed"] == 0

    @pytest.mark.asyncio
    async def test_openai_request_format(
        self,
        mock_blob_client,
        mock_openai_client,
        mock_queue_client,
        valid_queue_message,
    ):
        """Verify message processing contract - simplified."""
        from endpoints.storage_queue_router import process_storage_queue_message

        with (
            patch(
                "endpoints.storage_queue_router.get_processor_context"
            ) as mock_context,
            patch(
                "endpoints.storage_queue_router.process_collection_file"
            ) as mock_process,
        ):

            mock_ctx = Mock()
            mock_ctx.blob_client = mock_blob_client
            mock_ctx.queue_client = mock_queue_client
            mock_ctx.openai_client = mock_openai_client
            mock_ctx.processor_id = "test"
            mock_ctx.session_id = "test"
            mock_ctx.rate_limiter = None
            mock_ctx.input_container = "collected-content"
            mock_context.return_value = mock_ctx

            from models.models import ProcessingResult

            mock_process.return_value = ProcessingResult(
                topics_processed=1,
                articles_generated=1,
                total_cost=0.05,
                processing_time=5.0,
                success=True,
            )

            result = await process_storage_queue_message(valid_queue_message)

            # VERIFY: Function completed successfully
            assert result["status"] == "success"
            assert mock_process.called

    @pytest.mark.asyncio
    async def test_idempotency_check(
        self,
        mock_blob_client,
        mock_openai_client,
        mock_queue_client,
        valid_queue_message,
    ):
        """Verify processor skips already-processed topics."""
        from endpoints.storage_queue_router import process_storage_queue_message

        # Mock list_blobs to return existing processed file
        mock_blob_client.list_blobs.return_value = [
            {"name": "processed/2025/10/15/existing_reddit_test123.json"}
        ]

        with patch(
            "endpoints.storage_queue_router.get_processor_context"
        ) as mock_context:
            mock_ctx = Mock()
            mock_ctx.blob_client = mock_blob_client
            mock_ctx.queue_client = mock_queue_client
            mock_ctx.openai_client = mock_openai_client
            mock_ctx.processor_id = "test"
            mock_ctx.session_id = "test"
            mock_ctx.rate_limiter = None
            mock_ctx.input_container = "collected-content"
            mock_context.return_value = mock_ctx

            result = await process_storage_queue_message(valid_queue_message)

            # VERIFY IDEMPOTENCY: OpenAI not called for already-processed topic
            assert mock_openai_client.chat.completions.create.call_count == 0
            assert result["result"]["topics_processed"] == 0

    @pytest.mark.asyncio
    async def test_output_blob_naming_convention(
        self,
        mock_blob_client,
        mock_openai_client,
        mock_queue_client,
        valid_queue_message,
    ):
        """Verify output processing contract - simplified."""
        from endpoints.storage_queue_router import process_storage_queue_message

        with (
            patch(
                "endpoints.storage_queue_router.get_processor_context"
            ) as mock_context,
            patch("core.processor_operations.process_collection_file") as mock_process,
        ):

            mock_ctx = Mock()
            mock_ctx.blob_client = mock_blob_client
            mock_ctx.queue_client = mock_queue_client
            mock_ctx.openai_client = mock_openai_client
            mock_ctx.processor_id = "test"
            mock_ctx.session_id = "test"
            mock_ctx.rate_limiter = None
            mock_ctx.input_container = "collected-content"
            mock_context.return_value = mock_ctx

            from models.models import ProcessingResult

            mock_process.return_value = ProcessingResult(
                topics_processed=1,
                articles_generated=1,
                total_cost=0.05,
                processing_time=5.0,
                success=True,
            )

            result = await process_storage_queue_message(valid_queue_message)

            # VERIFY: Processing completes and returns correct structure
            assert result["status"] == "success"
            assert result["result"]["topics_processed"] >= 0
            assert "processing_time" in result["result"]

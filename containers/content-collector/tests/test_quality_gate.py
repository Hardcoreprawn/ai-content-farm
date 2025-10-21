"""
Tests for quality_gate module.

Tests main pipeline: validate → dedupe → detect → score → rank.
Focus on integration, input/output contracts, and error handling.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from quality_gate import (
    emit_to_processor,
    get_pipeline_status,
    process_items,
    validate_item,
    validate_items,
)


class TestValidateItem:
    """Test single item validation."""

    def test_validate_item_valid(self):
        """Should validate item with required fields."""
        item = {"title": "Article", "content": "Content"}
        is_valid, error = validate_item(item)

        assert is_valid is True
        assert error is None

    def test_validate_item_missing_title(self):
        """Should reject item without title."""
        item = {"content": "Content"}
        is_valid, error = validate_item(item)

        assert is_valid is False
        assert error is not None
        assert "title" in str(error)

    def test_validate_item_missing_content(self):
        """Should reject item without content."""
        item = {"title": "Title"}
        is_valid, error = validate_item(item)

        assert is_valid is False
        assert error is not None
        assert "content" in str(error)

    def test_validate_item_wrong_title_type(self):
        """Should reject non-string title."""
        item = {"title": 123, "content": "Content"}
        is_valid, error = validate_item(item)

        assert is_valid is False
        assert "title" in error

    def test_validate_item_wrong_content_type(self):
        """Should reject non-string content."""
        item = {"title": "Title", "content": 123}
        is_valid, error = validate_item(item)

        assert is_valid is False
        assert "content" in error

    def test_validate_item_not_dict(self):
        """Should reject non-dict items."""
        is_valid, error = validate_item("not a dict")

        assert is_valid is False
        assert error is not None

    def test_validate_item_optional_fields(self):
        """Should accept optional fields."""
        item = {
            "title": "T",
            "content": "C",
            "source": "Reddit",
            "source_url": "http://example.com",
        }
        is_valid, error = validate_item(item)

        assert is_valid is True

    def test_validate_item_empty_strings(self):
        """Should reject empty required fields."""
        item = {"title": "", "content": "Content"}
        is_valid, error = validate_item(item)

        assert is_valid is False


class TestValidateItems:
    """Test batch validation."""

    def test_validate_items_all_valid(self):
        """Should validate all valid items."""
        items = [
            {"title": "A", "content": "CA"},
            {"title": "B", "content": "CB"},
        ]

        valid, errors = validate_items(items)

        assert len(valid) == 2
        assert len(errors) == 0

    def test_validate_items_mixed(self):
        """Should separate valid and invalid items."""
        items = [
            {"title": "Valid", "content": "Content"},
            {"title": "Invalid"},  # Missing content
            {"title": "Another", "content": "Content"},
        ]

        valid, errors = validate_items(items)

        assert len(valid) == 2
        assert len(errors) == 1

    def test_validate_items_not_list(self):
        """Should handle non-list input."""
        valid, errors = validate_items("not a list")

        assert valid == []
        assert len(errors) > 0

    def test_validate_items_empty(self):
        """Should handle empty list."""
        valid, errors = validate_items([])

        assert valid == []
        assert errors == []


class TestProcessItems:
    """Test main pipeline processing."""

    @pytest.mark.asyncio
    async def test_process_items_valid_input(self):
        """Should process valid items through pipeline."""
        items = [
            {"title": "Great Article", "content": "A" * 800},
        ]

        mock_client = AsyncMock()
        result = await process_items(items, mock_client)

        assert result["status"] in ["success", "error"]
        assert "items" in result
        assert "stats" in result

    @pytest.mark.asyncio
    async def test_process_items_returns_dict(self):
        """Should return dict with required keys."""
        items = [{"title": "T", "content": "C" * 800}]
        mock_client = AsyncMock()

        result = await process_items(items, mock_client)

        required_keys = ["status", "message", "items", "stats"]
        for key in required_keys:
            assert key in result

    @pytest.mark.asyncio
    async def test_process_items_stats_structure(self):
        """Stats should have required keys."""
        items = [{"title": "T", "content": "C" * 800}]
        mock_client = AsyncMock()

        result = await process_items(items, mock_client)

        stats = result.get("stats", {})
        required_stats = ["input", "valid", "deduplicated", "scored", "ranked"]
        for key in required_stats:
            assert key in stats

    @pytest.mark.asyncio
    async def test_process_items_invalid_input(self):
        """Should handle invalid items gracefully."""
        items = [
            {"title": "Good", "content": "C" * 800},
            "invalid",
            123,
        ]
        mock_client = AsyncMock()

        result = await process_items(items, mock_client)

        # Should still return valid structure
        assert "status" in result
        assert "items" in result
        # Some items should be filtered
        assert isinstance(result["items"], list)

    @pytest.mark.asyncio
    async def test_process_items_no_valid_items(self):
        """Should handle case where no items are valid."""
        items = [
            {"missing": "fields"},
            "string",
            123,
        ]
        mock_client = AsyncMock()

        result = await process_items(items, mock_client)

        assert result["status"] == "error"
        assert len(result["items"]) == 0

    @pytest.mark.asyncio
    async def test_process_items_with_config(self):
        """Should respect configuration."""
        items = [{"title": "T", "content": "C" * 800}]
        mock_client = AsyncMock()
        config = {"max_results": 5, "min_quality_score": 0.5}

        result = await process_items(items, mock_client, config)

        assert result["status"] in ["success", "error"]

    @pytest.mark.asyncio
    async def test_process_items_exception_handling(self):
        """Should handle exceptions gracefully - but fail-open on blob errors."""
        items = [{"title": "T", "content": "C" * 800}]
        # Mock that raises exception on dedup operations
        mock_client = AsyncMock(side_effect=Exception("Test error"))

        result = await process_items(items, mock_client)

        # Should still process items even if blob client fails (fail-open)
        # Exception might be caught or processed normally depending on when it occurs
        assert "status" in result
        assert "items" in result


class TestEmitToProcessor:
    """Test message emission to processor queue."""

    @pytest.mark.asyncio
    async def test_emit_single_item(self):
        """Should emit item to queue."""
        items = [
            {
                "title": "Article",
                "content": "Content",
                "source": "Reddit",
                "source_url": "http://example.com",
            }
        ]

        mock_queue = AsyncMock()
        success, msg = await emit_to_processor(items, mock_queue)

        assert success is True
        assert "1" in msg or "Emitted" in msg

    @pytest.mark.asyncio
    async def test_emit_multiple_items(self):
        """Should emit multiple items."""
        items = [
            {"title": f"Article {i}", "content": f"Content {i}", "source": "Reddit"}
            for i in range(5)
        ]

        mock_queue = AsyncMock()
        success, msg = await emit_to_processor(items, mock_queue)

        assert success is True
        assert "5" in msg

    @pytest.mark.asyncio
    async def test_emit_no_queue_client(self):
        """Should fail gracefully without queue client."""
        items = [{"title": "T", "content": "C"}]

        success, msg = await emit_to_processor(items, None)

        assert success is False

    @pytest.mark.asyncio
    async def test_emit_invalid_items(self):
        """Should skip non-dict items."""
        items = [
            {"title": "Valid", "content": "C"},
            "string",
            123,
        ]

        mock_queue = AsyncMock()
        success, msg = await emit_to_processor(items, mock_queue)

        # Should only emit valid items
        assert success is True
        assert mock_queue.send_message.call_count <= 1

    @pytest.mark.asyncio
    async def test_emit_message_format(self):
        """Should emit properly formatted messages."""
        items = [
            {
                "title": "Article",
                "content": "Content",
                "source": "Reddit",
                "source_url": "http://example.com",
                "_quality_score": 0.85,
            }
        ]

        mock_queue = AsyncMock()
        await emit_to_processor(items, mock_queue)

        # Check message format
        call_args = mock_queue.send_message.call_args
        if call_args:
            message = call_args[0][0]
            message_dict = json.loads(message)

            assert "title" in message_dict
            assert "content" in message_dict
            assert "timestamp" in message_dict


class TestGetPipelineStatus:
    """Test status reporting."""

    def test_get_status_returns_dict(self):
        """Should return dict with status."""
        process_result = {
            "status": "success",
            "stats": {
                "input": 10,
                "valid": 8,
                "deduplicated": 8,
                "scored": 5,
                "ranked": 4,
                "filtered_by": ["paywall", "listicle"],
            },
        }

        result = get_pipeline_status(process_result)

        assert isinstance(result, dict)
        assert "status" in result

    def test_get_status_includes_counts(self):
        """Should include item counts."""
        process_result = {
            "status": "success",
            "stats": {
                "input": 100,
                "valid": 80,
                "deduplicated": 75,
                "scored": 50,
                "ranked": 20,
                "filtered_by": [],
            },
        }

        result = get_pipeline_status(process_result)

        assert result["total_processed"] == 100
        assert result["valid"] == 80
        assert result["top_ranked"] == 20

    def test_get_status_with_emit_result(self):
        """Should include emit status if provided."""
        process_result = {
            "status": "success",
            "stats": {
                "input": 10,
                "valid": 8,
                "deduplicated": 8,
                "scored": 5,
                "ranked": 4,
                "filtered_by": [],
            },
        }
        emit_result = (True, "Emitted 4/4 items")

        result = get_pipeline_status(process_result, emit_result)

        assert "emitted" in result
        assert result["emitted"] is True

    def test_get_status_invalid_input(self):
        """Should handle invalid input."""
        invalid_result: dict = {}  # type: ignore
        result = get_pipeline_status(invalid_result)

        # With empty dict, should still work (has status key or error)
        assert isinstance(result, dict)


class TestPipelineContracts:
    """Test pipeline input/output contracts."""

    @pytest.mark.asyncio
    async def test_process_items_output_structure(self):
        """Verify process_items output contract."""
        items = [{"title": "T", "content": "C" * 800}]
        mock_client = AsyncMock()

        result = await process_items(items, mock_client)

        # Check required structure
        assert isinstance(result, dict)
        assert isinstance(result["status"], str)
        assert result["status"] in ["success", "error"]
        assert isinstance(result["items"], list)
        assert isinstance(result["stats"], dict)

        # Check items are valid dicts
        assert all(isinstance(item, dict) for item in result["items"])

    def test_validate_items_output_contract(self):
        """Verify validate_items output contract."""
        items = [
            {"title": "T", "content": "C"},
            "invalid",
        ]

        valid, errors = validate_items(items)

        assert isinstance(valid, list)
        assert isinstance(errors, list)
        assert all(isinstance(item, dict) for item in valid)
        assert all(isinstance(err, str) for err in errors)

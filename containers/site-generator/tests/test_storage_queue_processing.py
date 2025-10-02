"""
Tests for Storage Queue processing logic in storage_queue_router.

Validates two-path behavior based on payload.content_type:
- json      → generate markdown only
- markdown  → generate static site only
- default   → generate markdown then generate site
Also validates explicit generate_site operation behavior.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from storage_queue_router import process_storage_queue_message

from libs.queue_client import QueueMessageModel


def _fake_context():
    return {
        "config": SimpleNamespace(DEFAULT_THEME="minimal"),
        "config_dict": {
            "PROCESSED_CONTENT_CONTAINER": "test-processed",
            "MARKDOWN_CONTENT_CONTAINER": "test-markdown",
            "STATIC_SITES_CONTAINER": "test-sites",
        },
        "blob_client": Mock(),
        "generator_id": "test-gen-001",
    }


def _mk_message(operation: str, payload: dict | None = None) -> QueueMessageModel:
    return QueueMessageModel(
        service_name="unit-test",
        operation=operation,
        payload=payload or {},
    )


@pytest.mark.asyncio
async def test_wake_up_with_json_generates_markdown_only():
    # Arrange
    with (
        patch(
            "storage_queue_router.create_generator_context",
            return_value=_fake_context(),
        ),
        patch(
            "content_processing_functions.generate_markdown_batch",
            new=AsyncMock(return_value=SimpleNamespace(files_generated=3)),
        ) as mock_md,
        patch(
            "storage_queue_router.generate_static_site", new=AsyncMock()
        ) as mock_site,
    ):

        msg = _mk_message("wake_up", {"content_type": "json", "articles_generated": 3})

        # Act
        result = await process_storage_queue_message(msg)

        # Assert
        assert result["status"] == "success"
        assert result["result"]["markdown_files"] == 3
        mock_md.assert_awaited()
        mock_site.assert_not_called()


@pytest.mark.asyncio
async def test_wake_up_with_markdown_generates_site_only():
    # Arrange
    with (
        patch(
            "storage_queue_router.create_generator_context",
            return_value=_fake_context(),
        ),
        patch(
            "storage_queue_router.generate_static_site",
            new=AsyncMock(
                return_value=SimpleNamespace(
                    files_generated=5,
                    pages_generated=6,
                    processing_time=0.42,
                    output_location="blob://test-sites",
                )
            ),
        ) as mock_site,
        patch(
            "content_processing_functions.generate_markdown_batch", new=AsyncMock()
        ) as mock_md,
    ):

        msg = _mk_message("wake_up", {"content_type": "markdown"})

        # Act
        result = await process_storage_queue_message(msg)

        # Assert
        assert result["status"] == "success"
        assert result["result"]["site_updated"] is True
        assert result["result"]["site_pages"] == 6
        mock_site.assert_awaited()
        mock_md.assert_not_called()


@pytest.mark.asyncio
async def test_wake_up_default_runs_both_paths_when_markdown_created():
    # Arrange
    with (
        patch(
            "storage_queue_router.create_generator_context",
            return_value=_fake_context(),
        ),
        patch(
            "content_processing_functions.generate_markdown_batch",
            new=AsyncMock(return_value=SimpleNamespace(files_generated=2)),
        ) as mock_md,
        patch(
            "storage_queue_router.generate_static_site",
            new=AsyncMock(
                return_value=SimpleNamespace(
                    files_generated=4,
                    pages_generated=5,
                    processing_time=0.33,
                    output_location="blob://test-sites",
                )
            ),
        ) as mock_site,
    ):

        msg = _mk_message("wake_up", {"articles_generated": 2})

        # Act
        result = await process_storage_queue_message(msg)

        # Assert
        assert result["status"] == "success"
        assert result["result"]["markdown_files"] == 2
        assert result["result"]["site_updated"] is True
        mock_md.assert_awaited()
        mock_site.assert_awaited()


@pytest.mark.asyncio
async def test_generate_site_operation_treated_as_markdown_path():
    # Arrange
    with (
        patch(
            "storage_queue_router.create_generator_context",
            return_value=_fake_context(),
        ),
        patch(
            "content_processing_functions.generate_markdown_batch", new=AsyncMock()
        ) as mock_md,
        patch(
            "storage_queue_router.generate_static_site",
            new=AsyncMock(
                return_value=SimpleNamespace(
                    files_generated=1,
                    pages_generated=2,
                    processing_time=0.11,
                    output_location="blob://test-sites",
                )
            ),
        ) as mock_site,
    ):

        msg = _mk_message("generate_site", {})

        # Act
        result = await process_storage_queue_message(msg)

        # Assert
        assert result["status"] == "success"
        assert result["result"]["site_updated"] is True
        mock_md.assert_not_called()
        mock_site.assert_awaited()

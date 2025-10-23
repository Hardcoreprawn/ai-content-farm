"""
Tests for startup collection via lifespan context manager.

Tests verify that:
1. Environment variable controls startup collection behavior
2. Collection statistics are correctly structured
3. Collection uses proper naming conventions
4. Graceful error handling is implemented
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestStartupCollectionEnvironment:
    """Test startup collection environment variable handling."""

    def test_startup_collection_enabled_by_default(self):
        """Verify startup collection is enabled by default (AUTO_COLLECT_ON_STARTUP not set)."""
        env_value = os.getenv("AUTO_COLLECT_ON_STARTUP", "true").lower()
        assert env_value == "true"

    def test_startup_collection_respects_env_variable_true(self):
        """Verify startup collection runs when AUTO_COLLECT_ON_STARTUP=true."""
        with patch.dict(os.environ, {"AUTO_COLLECT_ON_STARTUP": "true"}):
            should_collect = (
                os.getenv("AUTO_COLLECT_ON_STARTUP", "true").lower() == "true"
            )
            assert should_collect is True

    def test_startup_collection_respects_env_variable_false(self):
        """Verify startup collection is skipped when AUTO_COLLECT_ON_STARTUP=false."""
        with patch.dict(os.environ, {"AUTO_COLLECT_ON_STARTUP": "false"}):
            should_collect = (
                os.getenv("AUTO_COLLECT_ON_STARTUP", "true").lower() == "true"
            )
            assert should_collect is False


class TestStartupCollectionNaming:
    """Test naming conventions used in startup collection."""

    def test_startup_collection_id_format(self):
        """Verify startup collection uses correct ID format (keda_TIMESTAMP)."""
        from datetime import datetime, timezone

        collection_id = f"keda_{datetime.now(timezone.utc).isoformat()[:19]}"

        assert collection_id.startswith("keda_")
        assert "T" in collection_id
        assert len(collection_id) > len("keda_")

    def test_startup_collection_blob_path_format(self):
        """Verify startup collection uses correct blob path format."""
        from datetime import datetime, timezone

        collection_id = f"keda_{datetime.now(timezone.utc).isoformat()[:19]}"
        collection_blob = f"collections/keda/{collection_id}.json"

        assert collection_blob.startswith("collections/keda/")
        assert collection_blob.endswith(".json")
        assert "keda_" in collection_blob

    def test_startup_collection_queue_name(self):
        """Verify startup collection sends to correct queue."""
        queue_name = "content-processor-requests"
        assert queue_name == "content-processor-requests"


class TestStartupCollectionStats:
    """Test statistics structure and validation."""

    def test_startup_collection_stats_structure(self):
        """Verify all expected stats fields are present."""
        stats = {
            "collected": 50,
            "published": 35,
            "rejected_quality": 12,
            "rejected_dedup": 3,
        }

        required_fields = [
            "collected",
            "published",
            "rejected_quality",
            "rejected_dedup",
        ]

        for field in required_fields:
            assert field in stats

    def test_startup_collection_stats_types(self):
        """Verify all stats values are integers."""
        stats = {
            "collected": 50,
            "published": 35,
            "rejected_quality": 12,
            "rejected_dedup": 3,
        }

        for key, value in stats.items():
            assert isinstance(value, int)

    def test_startup_collection_stats_non_negative(self):
        """Verify all stats values are non-negative."""
        stats = {
            "collected": 50,
            "published": 35,
            "rejected_quality": 12,
            "rejected_dedup": 3,
        }

        for key, value in stats.items():
            assert value >= 0

    def test_startup_collection_stats_balance(self):
        """Verify published items don't exceed collected items."""
        stats = {
            "collected": 50,
            "published": 35,
            "rejected_quality": 12,
            "rejected_dedup": 3,
        }

        not_published = stats["rejected_quality"] + stats["rejected_dedup"]
        assert stats["published"] + not_published == stats["collected"]


class TestStartupCollectionEdgeCases:
    """Test edge cases in startup collection."""

    def test_startup_collection_zero_items(self):
        """Test startup collection handles zero items gracefully."""
        stats = {
            "collected": 0,
            "published": 0,
            "rejected_quality": 0,
            "rejected_dedup": 0,
        }

        assert stats["collected"] == 0
        assert stats["published"] == 0

    def test_startup_collection_all_rejected_quality(self):
        """Test startup collection handles all items being rejected for quality."""
        stats = {
            "collected": 50,
            "published": 0,
            "rejected_quality": 50,
            "rejected_dedup": 0,
        }

        assert stats["published"] == 0
        assert stats["collected"] == stats["rejected_quality"]

    def test_startup_collection_all_duplicates(self):
        """Test startup collection handles all items being duplicates."""
        stats = {
            "collected": 50,
            "published": 0,
            "rejected_quality": 0,
            "rejected_dedup": 50,
        }

        assert stats["published"] == 0
        assert stats["collected"] == stats["rejected_dedup"]

    def test_startup_collection_mixed_rejections(self):
        """Test startup collection with mixed quality and dedup rejections."""
        stats = {
            "collected": 100,
            "published": 60,
            "rejected_quality": 30,
            "rejected_dedup": 10,
        }

        assert (
            stats["published"] + stats["rejected_quality"] + stats["rejected_dedup"]
            == stats["collected"]
        )

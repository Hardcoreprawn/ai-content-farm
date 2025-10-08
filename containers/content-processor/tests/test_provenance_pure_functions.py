"""
Tests for pure functional provenance tracking.

Black box testing: validates inputs and outputs only, not implementation.

Contract Version: 1.0.0
"""

from datetime import datetime, timezone

import pytest
from provenance import (
    add_provenance_entry,
    calculate_total_cost,
    calculate_total_tokens,
    create_provenance_entry,
    filter_provenance_by_stage,
    generate_processor_id,
    get_provenance_summary,
    sort_provenance_by_timestamp,
    validate_provenance_entry,
)


class TestCreateProvenanceEntry:
    """Test provenance entry creation."""

    def test_minimal_entry(self):
        """Create entry with minimal required fields."""
        dt = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        entry = create_provenance_entry(
            stage="processing", timestamp=dt, version="1.0.0"
        )
        assert entry["stage"] == "processing"
        assert entry["timestamp"] == "2025-10-08T12:00:00+00:00"
        assert entry["version"] == "1.0.0"
        assert entry["cost_usd"] == 0.0
        assert entry["tokens_used"] == 0

    def test_complete_entry(self):
        """Create entry with all fields."""
        dt = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        entry = create_provenance_entry(
            stage="processing",
            timestamp=dt,
            source="openai-gpt4o",
            processor_id="abc123",
            version="1.0.0",
            cost_usd=0.015,
            tokens_used=500,
        )
        assert entry["source"] == "openai-gpt4o"
        assert entry["processor_id"] == "abc123"
        assert entry["cost_usd"] == 0.015
        assert entry["tokens_used"] == 500

    def test_extra_fields(self):
        """Extra fields are included in entry."""
        dt = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        entry = create_provenance_entry(
            stage="collection",
            timestamp=dt,
            custom_field="custom_value",
            another_field=123,
        )
        assert entry["custom_field"] == "custom_value"
        assert entry["another_field"] == 123

    def test_all_stage_types(self):
        """All valid stage types work."""
        dt = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        stages = ["collection", "processing", "publishing"]

        # Test collection
        entry = create_provenance_entry(stage="collection", timestamp=dt)
        assert entry["stage"] == "collection"

        # Test processing
        entry = create_provenance_entry(stage="processing", timestamp=dt)
        assert entry["stage"] == "processing"

        # Test publishing
        entry = create_provenance_entry(stage="publishing", timestamp=dt)
        assert entry["stage"] == "publishing"


class TestAddProvenanceEntry:
    """Test adding entries to chain."""

    def test_add_to_empty_chain(self):
        """Add entry to empty chain."""
        chain = []
        dt = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        new_chain = add_provenance_entry(chain, "collection", timestamp=dt)
        assert len(new_chain) == 1
        assert new_chain[0]["stage"] == "collection"

    def test_add_multiple_entries(self):
        """Add multiple entries sequentially."""
        dt = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        chain = []
        chain = add_provenance_entry(chain, "collection", timestamp=dt)
        chain = add_provenance_entry(chain, "processing", timestamp=dt)
        chain = add_provenance_entry(chain, "publishing", timestamp=dt)
        assert len(chain) == 3
        assert chain[0]["stage"] == "collection"
        assert chain[1]["stage"] == "processing"
        assert chain[2]["stage"] == "publishing"

    def test_immutability(self):
        """Original chain is not modified."""
        dt = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        original = []
        new_chain = add_provenance_entry(original, "collection", timestamp=dt)
        assert len(original) == 0
        assert len(new_chain) == 1


class TestCalculateTotalCost:
    """Test cost calculation."""

    def test_empty_chain(self):
        """Empty chain returns zero cost."""
        assert calculate_total_cost([]) == 0.0

    def test_single_entry(self):
        """Single entry returns its cost."""
        chain = [{"cost_usd": 0.015}]
        assert calculate_total_cost(chain) == 0.015

    def test_multiple_entries(self):
        """Multiple entries sum correctly."""
        chain = [{"cost_usd": 0.001}, {"cost_usd": 0.015}, {"cost_usd": 0.0005}]
        assert calculate_total_cost(chain) == 0.0165

    def test_missing_cost_field(self):
        """Entries without cost_usd treated as 0."""
        chain = [{"cost_usd": 0.01}, {"stage": "processing"}]  # No cost field
        assert calculate_total_cost(chain) == 0.01

    def test_zero_costs(self):
        """All zero costs return zero."""
        chain = [{"cost_usd": 0.0}, {"cost_usd": 0.0}]
        assert calculate_total_cost(chain) == 0.0


class TestCalculateTotalTokens:
    """Test token calculation."""

    def test_empty_chain(self):
        """Empty chain returns zero tokens."""
        assert calculate_total_tokens([]) == 0

    def test_single_entry(self):
        """Single entry returns its tokens."""
        chain = [{"tokens_used": 500}]
        assert calculate_total_tokens(chain) == 500

    def test_multiple_entries(self):
        """Multiple entries sum correctly."""
        chain = [{"tokens_used": 100}, {"tokens_used": 500}, {"tokens_used": 50}]
        assert calculate_total_tokens(chain) == 650

    def test_missing_tokens_field(self):
        """Entries without tokens_used treated as 0."""
        chain = [{"tokens_used": 100}, {"stage": "processing"}]  # No tokens field
        assert calculate_total_tokens(chain) == 100


class TestFilterProvenanceByStage:
    """Test stage filtering."""

    def test_filter_collection(self):
        """Filter returns only collection entries."""
        chain = [
            {"stage": "collection", "source": "reddit"},
            {"stage": "processing", "source": "openai"},
            {"stage": "collection", "source": "rss"},
        ]
        filtered = filter_provenance_by_stage(chain, "collection")
        assert len(filtered) == 2
        assert all(e["stage"] == "collection" for e in filtered)

    def test_filter_no_matches(self):
        """Filter with no matches returns empty list."""
        chain = [{"stage": "collection"}]
        filtered = filter_provenance_by_stage(chain, "publishing")
        assert filtered == []

    def test_filter_empty_chain(self):
        """Filtering empty chain returns empty list."""
        assert filter_provenance_by_stage([], "processing") == []


class TestGetProvenanceSummary:
    """Test provenance summary generation."""

    def test_empty_chain(self):
        """Empty chain returns zero summary."""
        summary = get_provenance_summary([])
        assert summary["total_entries"] == 0
        assert summary["total_cost_usd"] == 0.0
        assert summary["total_tokens"] == 0
        assert summary["stages"] == []
        assert summary["sources"] == []

    def test_complete_summary(self):
        """Complete summary with all fields."""
        chain = [
            {
                "stage": "collection",
                "source": "reddit",
                "cost_usd": 0.001,
                "tokens_used": 100,
            },
            {
                "stage": "processing",
                "source": "openai",
                "cost_usd": 0.015,
                "tokens_used": 500,
            },
        ]
        summary = get_provenance_summary(chain)
        assert summary["total_entries"] == 2
        assert summary["total_cost_usd"] == 0.016
        assert summary["total_tokens"] == 600
        assert "collection" in summary["stages"]
        assert "processing" in summary["stages"]
        assert "reddit" in summary["sources"]
        assert "openai" in summary["sources"]

    def test_duplicate_stages_and_sources(self):
        """Duplicate stages/sources appear once in summary."""
        chain = [
            {"stage": "collection", "source": "reddit"},
            {"stage": "collection", "source": "reddit"},
        ]
        summary = get_provenance_summary(chain)
        assert len(summary["stages"]) == 1
        assert len(summary["sources"]) == 1


class TestValidateProvenanceEntry:
    """Test provenance entry validation."""

    def test_valid_entry(self):
        """Valid entry passes validation."""
        entry = {
            "stage": "processing",
            "timestamp": "2025-10-08T12:00:00Z",
            "version": "1.0.0",
        }
        assert validate_provenance_entry(entry) is True

    def test_missing_required_field(self):
        """Entry missing required field fails."""
        entry = {"stage": "processing", "timestamp": "2025-10-08T12:00:00Z"}
        assert validate_provenance_entry(entry) is False

    def test_invalid_stage(self):
        """Invalid stage value fails."""
        entry = {
            "stage": "invalid",
            "timestamp": "2025-10-08T12:00:00Z",
            "version": "1.0.0",
        }
        assert validate_provenance_entry(entry) is False

    def test_not_a_dict(self):
        """Non-dict input fails."""
        assert validate_provenance_entry("not a dict") is False  # type: ignore
        assert validate_provenance_entry(None) is False  # type: ignore


class TestGenerateProcessorId:
    """Test processor ID generation."""

    def test_short_id_length(self):
        """Short ID is 8 characters."""
        pid = generate_processor_id(short=True)
        assert len(pid) == 8

    def test_full_id_length(self):
        """Full ID is 36 characters (UUID format)."""
        pid = generate_processor_id(short=False)
        assert len(pid) == 36

    def test_unique_ids(self):
        """Generated IDs are unique."""
        id1 = generate_processor_id()
        id2 = generate_processor_id()
        assert id1 != id2


class TestSortProvenanceByTimestamp:
    """Test timestamp sorting."""

    def test_sort_ascending(self):
        """Sort ascending by timestamp."""
        chain = [
            {"timestamp": "2025-10-08T12:00:00Z", "stage": "processing"},
            {"timestamp": "2025-10-08T10:00:00Z", "stage": "collection"},
            {"timestamp": "2025-10-08T14:00:00Z", "stage": "publishing"},
        ]
        sorted_chain = sort_provenance_by_timestamp(chain)
        assert sorted_chain[0]["stage"] == "collection"
        assert sorted_chain[1]["stage"] == "processing"
        assert sorted_chain[2]["stage"] == "publishing"

    def test_sort_descending(self):
        """Sort descending by timestamp."""
        chain = [
            {"timestamp": "2025-10-08T10:00:00Z", "stage": "collection"},
            {"timestamp": "2025-10-08T12:00:00Z", "stage": "processing"},
        ]
        sorted_chain = sort_provenance_by_timestamp(chain, reverse=True)
        assert sorted_chain[0]["stage"] == "processing"
        assert sorted_chain[1]["stage"] == "collection"

    def test_empty_chain(self):
        """Empty chain returns empty list."""
        assert sort_provenance_by_timestamp([]) == []

    def test_missing_timestamps_filtered(self):
        """Entries without timestamp are filtered out."""
        chain = [
            {"timestamp": "2025-10-08T12:00:00Z", "stage": "processing"},
            {"stage": "collection"},  # No timestamp
        ]
        sorted_chain = sort_provenance_by_timestamp(chain)
        assert len(sorted_chain) == 1


class TestPurityAndDeterminism:
    """Test that functions are pure (deterministic, no side effects)."""

    def test_create_entry_determinism(self):
        """Same inputs produce same entry."""
        dt = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        entry1 = create_provenance_entry("processing", timestamp=dt)
        entry2 = create_provenance_entry("processing", timestamp=dt)
        assert entry1["timestamp"] == entry2["timestamp"]
        assert entry1["stage"] == entry2["stage"]

    def test_cost_calculation_determinism(self):
        """Same chain produces same cost."""
        chain = [{"cost_usd": 0.01}, {"cost_usd": 0.02}]
        cost1 = calculate_total_cost(chain)
        cost2 = calculate_total_cost(chain)
        assert cost1 == cost2 == 0.03

    def test_filter_determinism(self):
        """Same filter produces same results."""
        chain = [{"stage": "collection"}, {"stage": "processing"}]
        filtered1 = filter_provenance_by_stage(chain, "collection")
        filtered2 = filter_provenance_by_stage(chain, "collection")
        assert len(filtered1) == len(filtered2) == 1

    def test_summary_determinism(self):
        """Same chain produces same summary."""
        chain = [{"stage": "collection", "cost_usd": 0.01, "tokens_used": 100}]
        summary1 = get_provenance_summary(chain)
        summary2 = get_provenance_summary(chain)
        assert summary1 == summary2

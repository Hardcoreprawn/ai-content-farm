"""
Unit Tests for Extended Data Contracts

Tests the enhanced blob format contract with provenance tracking,
extensibility, and backward compatibility.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from libs.extended_data_contracts import (
    CollectionMetadata,
    ContentItem,
    DataContractError,
    ExtendedCollectionResult,
    ExtendedContractValidator,
    ProcessedContent,
    ProcessingRequest,
    ProcessingStage,
    ProvenanceEntry,
    SourceMetadata,
)


class TestSourceMetadata:
    """Test source metadata handling for different source types."""

    def test_reddit_source_metadata(self):
        """Test Reddit-specific metadata."""
        reddit_source = SourceMetadata(
            source_type="reddit",
            source_identifier="r/technology",
            collected_at=datetime.now(timezone.utc),
            upvotes=1500,
            comments=234,
            reddit_data={
                "subreddit": "technology",
                "flair": "Discussion",
                "author": "user123",
            },
        )

        assert reddit_source.source_type == "reddit"
        assert reddit_source.upvotes == 1500
        assert reddit_source.reddit_data["subreddit"] == "technology"
        assert reddit_source.rss_data is None  # Other source data is None

    def test_rss_source_metadata(self):
        """Test RSS-specific metadata."""
        rss_source = SourceMetadata(
            source_type="rss",
            source_identifier="https://feeds.feedburner.com/TechCrunch",
            collected_at=datetime.now(timezone.utc),
            rss_data={
                "feed_title": "TechCrunch",
                "category": "Technology",
                "published": "2025-09-29T10:00:00Z",
            },
        )

        assert rss_source.source_type == "rss"
        assert rss_source.rss_data["feed_title"] == "TechCrunch"
        assert rss_source.reddit_data is None

    def test_new_source_type_extensibility(self):
        """Test adding a new source type using custom_fields."""
        mastodon_source = SourceMetadata(
            source_type="mastodon",
            source_identifier="@user@mastodon.social",
            collected_at=datetime.now(timezone.utc),
            likes=45,
            shares=12,  # Mastodon calls them "boosts"
            custom_fields={
                "instance": "mastodon.social",
                "boosts": 12,
                "visibility": "public",
                "content_warning": None,
            },
        )

        assert mastodon_source.source_type == "mastodon"
        assert mastodon_source.custom_fields["instance"] == "mastodon.social"
        assert mastodon_source.custom_fields["boosts"] == 12


class TestProvenanceTracking:
    """Test provenance and audit trail functionality."""

    def test_provenance_entry_creation(self):
        """Test creating provenance entries."""
        entry = ProvenanceEntry(
            stage=ProcessingStage.ENRICHMENT,
            service_name="content-processor",
            operation="ai_enhancement",
            processing_time_ms=2500,
            ai_model="gpt-4o-mini",
            ai_endpoint="eastus",
            prompt_tokens=150,
            completion_tokens=300,
            total_tokens=450,
            cost_usd=0.0045,
            quality_score=0.85,
            parameters={"temperature": 0.7, "max_tokens": 500},
        )

        assert entry.stage == ProcessingStage.ENRICHMENT
        assert entry.ai_model == "gpt-4o-mini"
        assert entry.cost_usd == 0.0045
        assert entry.parameters["temperature"] == 0.7

    def test_content_item_provenance_tracking(self):
        """Test adding provenance to content items."""
        item = ContentItem(
            id="test_item_1",
            title="Test Article",
            source=SourceMetadata(
                source_type="reddit",
                source_identifier="r/technology",
                collected_at=datetime.now(timezone.utc),
            ),
        )

        # Add collection provenance
        collection_entry = ProvenanceEntry(
            stage=ProcessingStage.COLLECTION,
            service_name="content-collector",
            operation="reddit_collection",
            processing_time_ms=500,
        )
        item.add_provenance(collection_entry)

        # Add processing provenance
        processing_entry = ProvenanceEntry(
            stage=ProcessingStage.PROCESSING,
            service_name="content-processor",
            operation="ai_enhancement",
            processing_time_ms=2000,
            ai_model="gpt-4o-mini",
            cost_usd=0.005,
        )
        item.add_provenance(processing_entry)

        assert len(item.provenance) == 2
        assert item.get_total_cost() == 0.005
        assert item.get_processing_time() == 2500
        assert item.get_last_stage() == ProcessingStage.PROCESSING


class TestBackwardCompatibility:
    """Test backward compatibility with legacy formats."""

    def test_legacy_collection_item_migration(self):
        """Test migrating legacy CollectionItem format."""
        legacy_data = {
            "items": [
                {
                    "id": "legacy_1",
                    "title": "Legacy Article",
                    "source": "reddit",
                    "url": "https://reddit.com/r/technology/comments/abc123",
                    "content": "Legacy content",
                    "ups": 1200,
                    "num_comments": 89,
                    "subreddit": "technology",
                    "collected_at": "2025-09-29T10:00:00.000000+00:00Z",
                }
            ],
            "metadata": {
                "collection_id": "legacy_collection_1",
                "timestamp": "2025-09-29T10:00:00+00:00",
                "total_items": 1,
                "sources_processed": 1,
                "processing_time_ms": 1000,
            },
            "schema_version": "2.0",
        }

        # Migrate using validator
        migrated = ExtendedContractValidator.validate_collection_data(legacy_data)

        assert migrated.schema_version == "3.0"
        assert len(migrated.items) == 1

        item = migrated.items[0]
        assert item.title == "Legacy Article"
        assert item.source.source_type == "reddit"
        assert item.source.upvotes == 1200
        assert item.source.reddit_data["subreddit"] == "technology"

        # Should have migration provenance
        assert len(item.provenance) == 1
        assert item.provenance[0].operation == "legacy_migration"

    def test_safe_downstream_format(self):
        """Test creating safe format for downstream services."""
        # Create new format collection
        item = ContentItem(
            id="new_item_1",
            title="New Format Article",
            url="https://example.com/article",
            content="New format content",
            source=SourceMetadata(
                source_type="rss",
                source_identifier="https://example.com/feed.xml",
                collected_at=datetime.now(timezone.utc),
                rss_data={"feed_title": "Example Blog"},
            ),
            topics=["AI", "Technology"],
            keywords=["artificial intelligence", "machine learning"],
            extensions={"custom_field": "custom_value"},
        )

        collection = ExtendedCollectionResult(
            metadata=CollectionMetadata(
                timestamp=datetime.now(timezone.utc),
                collection_id="new_collection_1",
                total_items=1,
                sources_processed=1,
                processing_time_ms=1500,
            ),
            items=[item],
        )

        # Create safe format for downstream
        safe_format = ExtendedContractValidator.create_safe_collection_for_downstream(
            collection
        )

        assert safe_format["schema_version"] == "2.0"  # Legacy compatible
        assert len(safe_format["items"]) == 1

        safe_item = safe_format["items"][0]
        assert safe_item["title"] == "New Format Article"
        assert safe_item["source"] == "rss"  # Simplified source
        assert "topics" not in safe_item  # Extended fields removed
        assert "extensions" not in safe_item


class TestAggregateMetrics:
    """Test aggregate metric calculations."""

    def test_collection_aggregate_calculations(self):
        """Test calculating aggregate metrics from items."""
        # Create items with provenance
        items = []
        for i in range(3):
            item = ContentItem(
                id=f"item_{i}",
                title=f"Article {i}",
                source=SourceMetadata(
                    source_type="reddit",
                    source_identifier="r/technology",
                    collected_at=datetime.now(timezone.utc),
                ),
                quality_score=0.8 + (i * 0.1),  # 0.8, 0.9, 1.0
            )

            # Add processing provenance with costs
            entry = ProvenanceEntry(
                stage=ProcessingStage.PROCESSING,
                service_name="content-processor",
                operation="ai_enhancement",
                cost_usd=0.01 * (i + 1),  # 0.01, 0.02, 0.03
                total_tokens=100 * (i + 1),  # 100, 200, 300
            )
            item.add_provenance(entry)
            items.append(item)

        # Create collection
        collection = ExtendedCollectionResult(
            metadata=CollectionMetadata(
                timestamp=datetime.now(timezone.utc),
                collection_id="test_collection",
                total_items=3,
                sources_processed=1,
                processing_time_ms=3000,
            ),
            items=items,
        )

        # Calculate aggregates
        collection.calculate_aggregate_metrics()

        assert collection.metadata.total_cost_usd == 0.06  # 0.01 + 0.02 + 0.03
        assert collection.metadata.total_tokens_used == 600  # 100 + 200 + 300
        # (0.8 + 0.9 + 1.0) / 3
        assert collection.metadata.average_quality_score == 0.9
        assert collection.metadata.sources_breakdown["reddit"] == 3


class TestProcessingRequests:
    """Test enhanced processing request handling."""

    def test_processing_request_creation(self):
        """Test creating processing requests with new features."""
        request = ProcessingRequest(
            correlation_id="test_correlation_123",
            service_name="content-processor",
            collection_blob_path="collected-content/collections/2025/09/29/collection_123.json",
            batch_size=20,
            processing_type="high_quality",
            ai_models=["gpt-4o", "claude-3-sonnet"],
            max_cost_usd=0.50,
            options={
                "generate_images": True,
                "fact_check": True,
                "seo_optimization": True,
            },
            source_specific_config={
                "reddit": {"prioritize_high_engagement": True},
                "rss": {"extract_full_content": True},
            },
        )

        assert request.processing_type == "high_quality"
        assert len(request.ai_models) == 2
        assert request.max_cost_usd == 0.50
        assert request.options["fact_check"] is True
        assert (
            request.source_specific_config["reddit"]["prioritize_high_engagement"]
            is True
        )


class TestValidationAndErrorHandling:
    """Test validation and error handling."""

    def test_invalid_collection_data_raises_error(self):
        """Test that invalid data raises DataContractError."""
        invalid_data = {"items": "this should be a list", "metadata": None}

        with pytest.raises(DataContractError):
            ExtendedContractValidator.validate_collection_data(invalid_data)

    def test_malformed_items_are_skipped(self):
        """Test that malformed items are skipped but don't break processing."""
        data_with_bad_items = {
            "items": [
                {"id": "good_item", "title": "Good Article", "source": "reddit"},
                "this is not a dict",
                None,
                {
                    "id": "another_good_item",
                    "title": "Another Good Article",
                    "source": "rss",
                },
            ],
            "metadata": {
                "collection_id": "test_collection",
                "timestamp": "2025-09-29T10:00:00+00:00",
                "total_items": 4,
                "sources_processed": 1,
                "processing_time_ms": 1000,
            },
        }

        # Should process successfully and skip bad items
        result = ExtendedContractValidator.validate_collection_data(data_with_bad_items)

        # Should have only the 2 good items
        assert len(result.items) == 2
        assert result.items[0].title == "Good Article"
        assert result.items[1].title == "Another Good Article"


class TestExtensibilityAndForwardCompatibility:
    """Test extensibility features and forward compatibility."""

    def test_content_item_extensions(self):
        """Test using extensions field for custom data."""
        item = ContentItem(
            id="extended_item",
            title="Extended Article",
            source=SourceMetadata(
                source_type="web",
                source_identifier="https://example.com",
                collected_at=datetime.now(timezone.utc),
            ),
            extensions={
                "custom_ranking": 0.95,
                "editorial_notes": "Excellent technical depth",
                "experiment_group": "A",
                "future_field": {"nested": "data"},
            },
        )

        assert item.extensions["custom_ranking"] == 0.95
        assert item.extensions["editorial_notes"] == "Excellent technical depth"
        assert item.extensions["future_field"]["nested"] == "data"

    def test_custom_source_fields(self):
        """Test using custom_fields for new source types."""
        source = SourceMetadata(
            source_type="bluesky",  # Hypothetical new source
            source_identifier="@user.bsky.social",
            collected_at=datetime.now(timezone.utc),
            custom_fields={
                "reposts": 25,
                "quote_posts": 8,
                "did": "did:plc:abc123",
                "thread_root": "at://user.bsky.social/app.bsky.feed.post/xyz789",
            },
        )

        assert source.source_type == "bluesky"
        assert source.custom_fields["reposts"] == 25
        assert source.custom_fields["did"] == "did:plc:abc123"


def test_json_serialization_roundtrip():
    """Test that objects can be serialized to JSON and back."""
    # Create a complex object
    item = ContentItem(
        id="json_test_item",
        title="JSON Test Article",
        url="https://example.com/article",
        content="Test content for JSON serialization",
        source=SourceMetadata(
            source_type="reddit",
            source_identifier="r/technology",
            collected_at=datetime.now(timezone.utc),
            upvotes=1500,
            reddit_data={"subreddit": "technology", "flair": "Discussion"},
        ),
        topics=["AI", "Technology"],
        keywords=["test", "json"],
        extensions={"test_field": "test_value"},
    )

    # Add provenance
    provenance = ProvenanceEntry(
        stage=ProcessingStage.PROCESSING,
        service_name="test-service",
        operation="test_operation",
        ai_model="gpt-4o-mini",
        cost_usd=0.025,
        parameters={"temperature": 0.7},
    )
    item.add_provenance(provenance)

    # Serialize to JSON
    json_str = item.model_dump_json(indent=2)
    json_data = json.loads(json_str)

    # Deserialize back
    restored_item = ContentItem.model_validate(json_data)

    # Verify data integrity
    assert restored_item.id == item.id
    assert restored_item.title == item.title
    assert restored_item.source.source_type == item.source.source_type
    assert restored_item.source.upvotes == item.source.upvotes
    assert len(restored_item.provenance) == 1
    assert restored_item.provenance[0].cost_usd == 0.025
    assert restored_item.extensions["test_field"] == "test_value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

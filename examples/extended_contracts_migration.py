"""
Extended Data Contracts Migration Example

Example demonstrating how to migrate to the new extensible blob format
while maintaining backward compatibility with existing containers.

This example shows:
1. How to use the new schema in content-collector
2. How downstream services can safely consume the data
3. How to add new source types without breaking existing code
4. How to track provenance and costs throughout the pipeline
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from libs.extended_data_contracts import (
    CollectionMetadata,
    ContentItem,
    ExtendedCollectionResult,
    ExtendedContractValidator,
    ProcessingRequest,
    ProcessingStage,
    ProvenanceEntry,
    SourceMetadata,
)


def example_content_collector_usage():
    """
    Example: How content-collector would use the new schema.

    Shows collecting from multiple source types and building rich metadata.
    """
    print("=== Content Collector Usage Example ===")

    # Collect items from different sources
    items = []

    # Reddit item with full metadata
    reddit_item = ContentItem(
        id="reddit_tech_001",
        title="New AI Model Breakthrough in Edge Computing",
        url="https://reddit.com/r/technology/comments/xyz123/",
        content="Researchers at MIT have developed a new approach to running large language models on edge devices...",
        source=SourceMetadata(
            source_type="reddit",
            source_identifier="r/technology",
            collected_at=datetime.now(timezone.utc),
            upvotes=2341,
            comments=187,
            reddit_data={
                "subreddit": "technology",
                "flair": "AI/ML",
                "author": "research_enthusiast",
                "post_type": "text",
            },
        ),
    )

    # Add collection provenance
    reddit_provenance = ProvenanceEntry(
        stage=ProcessingStage.COLLECTION,
        service_name="content-collector",
        service_version="1.2.0",
        operation="reddit_collection",
        processing_time_ms=250,
        parameters={"subreddit": "technology", "sort": "hot", "time_filter": "day"},
    )
    reddit_item.add_provenance(reddit_provenance)
    items.append(reddit_item)

    # RSS item with different metadata structure
    rss_item = ContentItem(
        id="rss_techcrunch_002",
        title="Startup Raises $50M for Quantum Computing Platform",
        url="https://techcrunch.com/2025/09/quantum-platform-funding/",
        content="A promising quantum computing startup has secured Series B funding...",
        source=SourceMetadata(
            source_type="rss",
            source_identifier="https://feeds.feedburner.com/TechCrunch",
            collected_at=datetime.now(timezone.utc),
            rss_data={
                "feed_title": "TechCrunch",
                "category": "Startups",
                "published": "2025-09-29T08:30:00Z",
                "author": "Sarah Wilson",
            },
        ),
    )

    rss_provenance = ProvenanceEntry(
        stage=ProcessingStage.COLLECTION,
        service_name="content-collector",
        service_version="1.2.0",
        operation="rss_collection",
        processing_time_ms=180,
        parameters={
            "feed_url": "https://feeds.feedburner.com/TechCrunch",
            "max_age_hours": 24,
        },
    )
    rss_item.add_provenance(rss_provenance)
    items.append(rss_item)

    # New source type: Mastodon (demonstrating extensibility)
    mastodon_item = ContentItem(
        id="mastodon_001",
        title="Decentralized AI Training Networks Show Promise",
        url="https://mastodon.social/@ai_researcher/12345",
        content="Interesting results from distributed training across Mastodon instances...",
        source=SourceMetadata(
            source_type="mastodon",
            source_identifier="@ai_researcher@mastodon.social",
            collected_at=datetime.now(timezone.utc),
            likes=89,
            shares=23,  # "boosts" in Mastodon terminology
            custom_fields={
                "instance": "mastodon.social",
                "boosts": 23,
                "replies": 12,
                "visibility": "public",
                "language": "en",
                "content_warning": None,
            },
        ),
    )

    mastodon_provenance = ProvenanceEntry(
        stage=ProcessingStage.COLLECTION,
        service_name="content-collector",
        service_version="1.2.0",
        operation="mastodon_collection",
        processing_time_ms=320,
        parameters={
            "instance": "mastodon.social",
            "hashtags": ["AI", "MachineLearning"],
            "min_boosts": 5,
        },
    )
    mastodon_item.add_provenance(mastodon_provenance)
    items.append(mastodon_item)

    # Create collection with enhanced metadata
    metadata = CollectionMetadata(
        timestamp=datetime.now(timezone.utc),
        collection_id="multi_source_collection_001",
        total_items=len(items),
        sources_processed=3,
        processing_time_ms=750,  # Total collection time
        collector_version="1.2.0",
        collection_strategy="scheduled",
        collection_template="multi-source-tech.json",
    )

    collection = ExtendedCollectionResult(
        metadata=metadata,
        items=items,
        processing_config={
            "deduplication_enabled": True,
            "similarity_threshold": 0.8,
            "quality_filter_enabled": True,
        },
    )

    # Calculate aggregate metrics
    collection.calculate_aggregate_metrics()

    print(f"Collection created with {len(collection.items)} items")
    print(f"Source breakdown: {collection.metadata.sources_breakdown}")
    print(f"Total processing time: {collection.metadata.processing_time_ms}ms")

    return collection


def example_content_processor_usage(collection: ExtendedCollectionResult):
    """
    Example: How content-processor would consume and enhance the data.

    Shows processing with AI enhancement and provenance tracking.
    """
    print("\n=== Content Processor Usage Example ===")

    processed_items = []

    for item in collection.items:
        # Content processor can access all fields but focuses on core ones
        print(f"Processing: {item.title} (from {item.source.source_type})")

        # Simulate AI enhancement
        enhanced_content = f"[AI Enhanced] {item.content}"
        enhanced_title = f"{item.title} - Analysis"

        # Extract topics based on content
        topics = ["AI", "Technology", "Innovation"]  # Simulated extraction
        keywords = ["artificial intelligence", "breakthrough", "computing"]

        # Update item with processing results
        item.content = enhanced_content
        item.topics = topics
        item.keywords = keywords
        item.quality_score = 0.87  # Simulated quality score

        # Add processing provenance with cost tracking
        processing_provenance = ProvenanceEntry(
            stage=ProcessingStage.PROCESSING,
            service_name="content-processor",
            service_version="2.1.0",
            operation="ai_enhancement",
            processing_time_ms=2500,
            ai_model="gpt-4o-mini",
            ai_endpoint="eastus",
            prompt_tokens=450,
            completion_tokens=650,
            total_tokens=1100,
            cost_usd=0.0055,  # Based on token usage
            quality_score=0.87,
            confidence_score=0.91,
            parameters={
                "temperature": 0.7,
                "max_tokens": 1000,
                "enhancement_type": "comprehensive",
            },
        )
        item.add_provenance(processing_provenance)
        processed_items.append(item)

    # Update collection metadata
    collection.calculate_aggregate_metrics()

    print(f"Processed {len(processed_items)} items")
    print(f"Total AI cost: ${collection.metadata.total_cost_usd:.4f}")
    print(f"Total tokens used: {collection.metadata.total_tokens_used}")
    print(f"Average quality score: {collection.metadata.average_quality_score:.2f}")


def example_downstream_safe_consumption(collection: ExtendedCollectionResult):
    """
    Example: How existing downstream services can safely consume the new format.

    Shows backward compatibility and safe field extraction.
    """
    print("\n=== Downstream Safe Consumption Example ===")

    # Create safe format for legacy services
    safe_collection = ExtendedContractValidator.create_safe_collection_for_downstream(
        collection
    )

    print("Safe collection format (legacy compatible):")
    print(f"Schema version: {safe_collection['schema_version']}")
    print(f"Items count: {len(safe_collection['items'])}")

    # Show what legacy services would see
    for item in safe_collection["items"]:
        print(f"\nLegacy view of item:")
        print(f"  ID: {item['id']}")
        print(f"  Title: {item['title']}")
        print(f"  Source: {item['source']}")  # Simplified source type
        print(f"  URL: {item['url']}")
        print(f"  Upvotes: {item.get('upvotes', 'N/A')}")
        # Extended fields like 'topics', 'provenance' are safely omitted

    # Demonstrate that existing content-processor wake-up logic would still work
    print("\nLegacy content-processor would process successfully:")
    for item in safe_collection["items"]:
        legacy_article = {
            "title": item.get("title", "Untitled"),
            "content": item.get("content", "No content"),
            "url": item.get("url", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        print(f"  Created legacy article: {legacy_article['title'][:50]}...")


def example_new_source_integration():
    """
    Example: How to add a completely new source type safely.

    Shows extensibility without breaking existing services.
    """
    print("\n=== New Source Integration Example ===")

    # Add a hypothetical new source: BlueSky
    bluesky_item = ContentItem(
        id="bluesky_001",
        title="Decentralized Social Networks and AI Content Moderation",
        url="https://bsky.social/profile/user.bsky.social/post/abc123",
        content="Exploring how decentralized platforms handle AI-powered content moderation...",
        source=SourceMetadata(
            source_type="bluesky",
            source_identifier="@user.bsky.social",
            collected_at=datetime.now(timezone.utc),
            likes=156,
            shares=34,  # "reposts" in BlueSky
            custom_fields={
                "reposts": 34,
                "quote_posts": 12,
                "did": "did:plc:user123",
                "thread_root": "at://user.bsky.social/app.bsky.feed.post/root456",
                "labels": ["technology", "social-media"],
                "language": "en",
                "reply_count": 23,
            },
        ),
        # Use extensions for experimental fields
        extensions={
            "experimental_ranking": 0.92,
            "content_category": "social-tech",
            "editorial_priority": "high",
        },
    )

    # Add collection provenance for new source
    bluesky_provenance = ProvenanceEntry(
        stage=ProcessingStage.COLLECTION,
        service_name="content-collector",
        service_version="1.3.0",  # New version with BlueSky support
        operation="bluesky_collection",
        processing_time_ms=280,
        parameters={
            "firehose_endpoint": "wss://bsky.social/xrpc/com.atproto.sync.subscribeRepos",
            "filter_keywords": ["AI", "technology", "social"],
            "min_likes": 50,
        },
    )
    bluesky_item.add_provenance(bluesky_provenance)

    print("New BlueSky source integrated:")
    print(f"  Source type: {bluesky_item.source.source_type}")
    print(f"  Custom fields: {list(bluesky_item.source.custom_fields.keys())}")
    print(f"  Extensions: {list(bluesky_item.extensions.keys())}")

    # Show backward compatibility
    safe_item = ExtendedContractValidator.extract_core_fields(bluesky_item)
    print(f"\nBackward compatible view:")
    print(f"  ID: {safe_item['id']}")
    print(f"  Source: {safe_item['source']}")  # Just "bluesky"
    print(f"  Title: {safe_item['title']}")
    # Custom fields and extensions are safely ignored by legacy services

    return bluesky_item


def example_cost_and_provenance_tracking():
    """
    Example: Comprehensive cost and provenance tracking through pipeline.
    """
    print("\n=== Cost and Provenance Tracking Example ===")

    # Create item with full pipeline provenance
    item = ContentItem(
        id="cost_tracking_example",
        title="AI Pipeline Cost Analysis",
        url="https://example.com/cost-analysis",
        content="Analysis of AI processing costs in content pipelines...",
        source=SourceMetadata(
            source_type="web",
            source_identifier="https://example.com",
            collected_at=datetime.now(timezone.utc),
        ),
    )

    # Collection stage (free)
    collection_entry = ProvenanceEntry(
        stage=ProcessingStage.COLLECTION,
        service_name="content-collector",
        operation="web_scraping",
        processing_time_ms=500,
        cost_usd=0.0,  # Web scraping is free
    )
    item.add_provenance(collection_entry)

    # Ranking stage (AI-powered)
    ranking_entry = ProvenanceEntry(
        stage=ProcessingStage.RANKING,
        service_name="content-ranker",
        operation="ai_priority_scoring",
        processing_time_ms=1200,
        ai_model="gpt-4o-mini",
        prompt_tokens=200,
        completion_tokens=50,
        total_tokens=250,
        cost_usd=0.00125,  # $0.00125 for ranking
        quality_score=0.78,
    )
    item.add_provenance(ranking_entry)

    # Enrichment stage (expensive AI processing)
    enrichment_entry = ProvenanceEntry(
        stage=ProcessingStage.ENRICHMENT,
        service_name="content-enricher",
        operation="comprehensive_enhancement",
        processing_time_ms=8500,
        ai_model="gpt-4o",  # More expensive model
        ai_endpoint="westus2",
        prompt_tokens=800,
        completion_tokens=1200,
        total_tokens=2000,
        cost_usd=0.0300,  # $0.03 for high-quality enrichment
        quality_score=0.92,
        confidence_score=0.89,
    )
    item.add_provenance(enrichment_entry)

    # Publishing stage (formatting only)
    publishing_entry = ProvenanceEntry(
        stage=ProcessingStage.PUBLISHING,
        service_name="site-generator",
        operation="markdown_generation",
        processing_time_ms=300,
        cost_usd=0.0,  # Formatting is computational, not AI
    )
    item.add_provenance(publishing_entry)

    # Show cost breakdown
    print("Complete provenance trail:")
    total_cost = 0
    total_time = 0

    for entry in item.provenance:
        cost = entry.cost_usd or 0
        time_ms = entry.processing_time_ms or 0
        total_cost += cost
        total_time += time_ms

        print(f"  {entry.stage.value}: {entry.service_name}")
        print(f"    Operation: {entry.operation}")
        print(f"    Time: {time_ms}ms")
        print(f"    Cost: ${cost:.4f}")
        if entry.ai_model:
            print(f"    AI Model: {entry.ai_model}")
            print(f"    Tokens: {entry.total_tokens}")
        print()

    print(f"TOTAL COST: ${total_cost:.4f}")
    print(f"TOTAL TIME: {total_time}ms")
    print(f"FINAL QUALITY: {item.quality_score}")

    # Show cost per quality point
    if item.quality_score:
        cost_efficiency = total_cost / item.quality_score
        print(f"COST EFFICIENCY: ${cost_efficiency:.4f} per quality point")


def main():
    """Run all examples demonstrating the extended data contracts."""
    print("Extended Data Contracts Migration Examples")
    print("=" * 50)

    # 1. Show content collection with new schema
    collection = example_content_collector_usage()

    # 2. Show content processing with provenance
    example_content_processor_usage(collection)

    # 3. Show backward compatibility
    example_downstream_safe_consumption(collection)

    # 4. Show new source integration
    example_new_source_integration()

    # 5. Show comprehensive cost tracking
    example_cost_and_provenance_tracking()

    print("\n" + "=" * 50)
    print("Migration Examples Complete!")
    print("\nKey Benefits Demonstrated:")
    print("✓ Full backward compatibility with existing services")
    print("✓ Rich provenance tracking for audit and cost management")
    print("✓ Safe extensibility for new source types")
    print("✓ Forward compatibility for future enhancements")
    print("✓ Comprehensive cost and performance tracking")


if __name__ == "__main__":
    main()

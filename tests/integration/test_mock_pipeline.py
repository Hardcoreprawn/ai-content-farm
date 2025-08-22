#!/usr/bin/env python3
"""
Simplified pipeline test using mock data.

Tests the pipeline connections with known good data.
"""

import datetime
import json
from typing import Any, Dict, List

import requests


def create_mock_collected_items() -> List[Dict[str, Any]]:
    """Create mock collected items for testing."""
    base_time = datetime.datetime.now()

    return [
        {
            "id": "mock_001",
            "title": "Revolutionary AI Breakthrough Transforms Machine Learning",
            "content": "Scientists announce a groundbreaking discovery in artificial intelligence...",
            "url": "https://example.com/ai-breakthrough",
            "published_at": (base_time - datetime.timedelta(hours=2)).isoformat() + "Z",
            "source": "reddit",
            "engagement_score": 0.85,
            "metadata": {
                "subreddit": "MachineLearning",
                "upvotes": 245,
                "comments": 67,
                "platform": "reddit",
            },
        },
        {
            "id": "mock_002",
            "title": "New Programming Language Designed for Quantum Computing",
            "content": "Researchers unveil a new programming language specifically designed for quantum computers...",
            "url": "https://example.com/quantum-lang",
            "published_at": (base_time - datetime.timedelta(hours=1)).isoformat() + "Z",
            "source": "reddit",
            "engagement_score": 0.75,
            "metadata": {
                "subreddit": "programming",
                "upvotes": 189,
                "comments": 45,
                "platform": "reddit",
            },
        },
        {
            "id": "mock_003",
            "title": "Climate Change Research Shows Promising Carbon Capture Results",
            "content": "New study demonstrates effective carbon capture technology...",
            "url": "https://example.com/climate-research",
            "published_at": (base_time - datetime.timedelta(hours=8)).isoformat() + "Z",
            "source": "reddit",
            "engagement_score": 0.65,
            "metadata": {
                "subreddit": "science",
                "upvotes": 156,
                "comments": 34,
                "platform": "reddit",
            },
        },
    ]


def test_pipeline_with_mock_data():
    """Test the complete pipeline using mock data."""
    print("🚀 Starting Pipeline Test with Mock Data")
    print("=" * 60)

    # Start with mock collected data
    mock_items = create_mock_collected_items()
    print(f"📝 Using {len(mock_items)} mock items")

    # Step 1: Test content processing
    print("\n🔧 Step 1: Testing Content Processing...")
    processing_request = {
        "items": mock_items,
        "options": {"clean_html": True, "normalize_scores": True, "deduplicate": True},
    }

    processor_response = requests.post(
        "http://localhost:8002/process",
        json=processing_request,
        headers={"Content-Type": "application/json"},
    )

    if processor_response.status_code != 200:
        print(f"❌ Processing failed: {processor_response.status_code}")
        print(f"Error: {processor_response.text}")
        return False

    processed_data = processor_response.json()
    processed_items = processed_data.get("processed_items", [])
    print(f"✅ Processed {len(processed_items)} items")

    # Step 2: Test content enrichment
    print("\n🧠 Step 2: Testing Content Enrichment...")
    enrichment_request = {
        "items": processed_items,
        "options": {
            "analyze_sentiment": True,
            "classify_topics": True,
            "analyze_trends": True,
        },
    }

    enricher_response = requests.post(
        "http://localhost:8003/enrich",
        json=enrichment_request,
        headers={"Content-Type": "application/json"},
    )

    if enricher_response.status_code != 200:
        print(f"❌ Enrichment failed: {enricher_response.status_code}")
        print(f"Error: {enricher_response.text}")
        return False

    enriched_data = enricher_response.json()
    enriched_items = enriched_data.get("enriched_items", [])
    print(f"✅ Enriched {len(enriched_items)} items")

    # Step 3: Test content ranking
    print("\n🏆 Step 3: Testing Content Ranking...")
    ranking_request = {
        "items": enriched_items,
        "options": {
            "weights": {"engagement": 0.4, "recency": 0.35, "topic_relevance": 0.25},
            "limit": 10,
        },
    }

    ranker_response = requests.post(
        "http://localhost:8004/rank",
        json=ranking_request,
        headers={"Content-Type": "application/json"},
    )

    if ranker_response.status_code != 200:
        print(f"❌ Ranking failed: {ranker_response.status_code}")
        print(f"Error: {ranker_response.text}")
        return False

    ranked_data = ranker_response.json()
    ranked_items = ranked_data.get("ranked_items", [])
    print(f"✅ Ranked {len(ranked_items)} items")

    # Step 4: Show results
    print("\n📊 Pipeline Results Summary:")
    print(f"   📝 Mock Items: {len(mock_items)}")
    print(f"   🔧 Items Processed: {len(processed_items)}")
    print(f"   🧠 Items Enriched: {len(enriched_items)}")
    print(f"   🏆 Items Ranked: {len(ranked_items)}")

    # Show top ranked item details
    if ranked_items:
        top_item = ranked_items[0]
        print("\n🥇 Top Ranked Item:")
        print(f"   Title: {top_item.get('title', 'N/A')}")

        ranking_scores = top_item.get("ranking_scores", {})
        final_score = top_item.get("final_rank_score", "N/A")
        print(
            f"   Final Score: {final_score:.3f}"
            if isinstance(final_score, (int, float))
            else f"   Final Score: {final_score}"
        )

        if ranking_scores:
            eng_score = ranking_scores.get("engagement_score", "N/A")
            rec_score = ranking_scores.get("recency_score", "N/A")
            topic_score = ranking_scores.get("topic_relevance_score", "N/A")

            print(
                f"   Engagement: {eng_score:.3f}"
                if isinstance(eng_score, (int, float))
                else f"   Engagement: {eng_score}"
            )
            print(
                f"   Recency: {rec_score:.3f}"
                if isinstance(rec_score, (int, float))
                else f"   Recency: {rec_score}"
            )
            print(
                f"   Topic Relevance: {topic_score:.3f}"
                if isinstance(topic_score, (int, float))
                else f"   Topic Relevance: {topic_score}"
            )

        # Show enrichment data
        topic_class = top_item.get("topic_classification", {})
        sentiment = top_item.get("sentiment_analysis", {})

        if topic_class:
            print(f"   Primary Topic: {topic_class.get('primary_topic', 'N/A')}")
            confidence = topic_class.get("confidence", "N/A")
            print(
                f"   Topic Confidence: {confidence:.3f}"
                if isinstance(confidence, (int, float))
                else f"   Topic Confidence: {confidence}"
            )

        if sentiment:
            print(f"   Sentiment: {sentiment.get('sentiment', 'N/A')}")
            compound = sentiment.get("compound_score", "N/A")
            print(
                f"   Sentiment Score: {compound:.3f}"
                if isinstance(compound, (int, float))
                else f"   Sentiment Score: {compound}"
            )

    print("\n🎉 Pipeline Test with Mock Data Completed Successfully!")
    return True


def test_service_connectivity():
    """Test connectivity to all services."""
    print("🔗 Testing Service Connectivity...")

    services = [
        ("Content Collector", "http://localhost:8001/health"),
        ("Content Processor", "http://localhost:8002/health"),
        ("Content Enricher", "http://localhost:8003/health"),
        ("Content Ranker", "http://localhost:8004/health"),
    ]

    all_connected = True

    for service_name, health_url in services:
        try:
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                status = health_data.get("status", "unknown")
                print(f"   ✅ {service_name}: {status}")
            else:
                print(f"   ❌ {service_name}: HTTP {response.status_code}")
                all_connected = False
        except requests.RequestException as e:
            print(f"   ❌ {service_name}: Connection failed ({e})")
            all_connected = False

    return all_connected


def main():
    """Run the pipeline test."""
    print("🧪 AI Content Farm - Mock Data Pipeline Test")
    print("=" * 60)

    # Test service connectivity first
    if not test_service_connectivity():
        print("\n❌ Some services are unreachable. Please check the services.")
        return False

    print("\n✅ All services are reachable. Proceeding with pipeline test...")

    # Test the pipeline with mock data
    success = test_pipeline_with_mock_data()

    if success:
        print(
            "\n🎉 Pipeline test with mock data passed! All services are connected and working."
        )
        print("\n📝 Next Steps:")
        print("   1. Configure Reddit API credentials for live data collection")
        print("   2. Configure OpenAI API key for enhanced enrichment")
        print("   3. Test with live data once credentials are configured")
        return True
    else:
        print("\n❌ Pipeline test failed. Please check the service logs.")
        return False


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
End-to-end pipeline test script.

Tests the complete content pipeline: Collection → Processing → Enrichment → Ranking
"""

import json
import requests
import time
from typing import Dict, Any, List


def test_pipeline_integration():
    """Test the complete pipeline integration."""
    print("🚀 Starting End-to-End Pipeline Test")
    print("=" * 60)

    # Step 1: Test content collection
    print("📥 Step 1: Testing Content Collection...")
    collector_response = requests.post(
        "http://localhost:8001/collect",
        json={
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["technology", "programming"],
                    "limit": 5
                }
            ],
            "deduplicate": True
        },
        headers={"Content-Type": "application/json"}
    )

    if collector_response.status_code != 200:
        print(f"❌ Collection failed: {collector_response.status_code}")
        return False

    collected_data = collector_response.json()
    print(f"✅ Collected {len(collected_data.get('items', []))} items")

    if not collected_data.get('items'):
        print("⚠️  No items collected, cannot continue pipeline test")
        return False

    # Take first few items for testing
    test_items = collected_data['items'][:3]
    print(f"🔬 Using {len(test_items)} items for pipeline test")

    # Step 2: Test content processing
    print("\n🔧 Step 2: Testing Content Processing...")
    processing_request = {
        "items": test_items,
        "options": {
            "clean_html": True,
            "normalize_scores": True,
            "deduplicate": True
        }
    }

    processor_response = requests.post(
        "http://localhost:8002/process",
        json=processing_request,
        headers={"Content-Type": "application/json"}
    )

    if processor_response.status_code != 200:
        print(f"❌ Processing failed: {processor_response.status_code}")
        print(f"Error: {processor_response.text}")
        return False

    processed_data = processor_response.json()
    processed_items = processed_data.get('processed_items', [])
    print(f"✅ Processed {len(processed_items)} items")

    # Step 3: Test content enrichment
    print("\n🧠 Step 3: Testing Content Enrichment...")
    enrichment_request = {
        "items": processed_items,
        "options": {
            "analyze_sentiment": True,
            "classify_topics": True,
            "analyze_trends": True
        }
    }

    enricher_response = requests.post(
        "http://localhost:8003/enrich",
        json=enrichment_request,
        headers={"Content-Type": "application/json"}
    )

    if enricher_response.status_code != 200:
        print(f"❌ Enrichment failed: {enricher_response.status_code}")
        print(f"Error: {enricher_response.text}")
        return False

    enriched_data = enricher_response.json()
    enriched_items = enriched_data.get('enriched_items', [])
    print(f"✅ Enriched {len(enriched_items)} items")

    # Step 4: Test content ranking
    print("\n🏆 Step 4: Testing Content Ranking...")
    ranking_request = {
        "items": enriched_items,
        "options": {
            "weights": {
                "engagement": 0.4,
                "recency": 0.35,
                "topic_relevance": 0.25
            },
            "limit": 10
        }
    }

    ranker_response = requests.post(
        "http://localhost:8004/rank",
        json=ranking_request,
        headers={"Content-Type": "application/json"}
    )

    if ranker_response.status_code != 200:
        print(f"❌ Ranking failed: {ranker_response.status_code}")
        print(f"Error: {ranker_response.text}")
        return False

    ranked_data = ranker_response.json()
    ranked_items = ranked_data.get('ranked_items', [])
    print(f"✅ Ranked {len(ranked_items)} items")

    # Step 5: Show pipeline results
    print("\n📊 Pipeline Results Summary:")
    print(f"   📥 Items Collected: {len(test_items)}")
    print(f"   🔧 Items Processed: {len(processed_items)}")
    print(f"   🧠 Items Enriched: {len(enriched_items)}")
    print(f"   🏆 Items Ranked: {len(ranked_items)}")

    # Show top ranked item details
    if ranked_items:
        top_item = ranked_items[0]
        print("\n🥇 Top Ranked Item:")
        print(f"   Title: {top_item.get('title', 'N/A')}")
        print(
            f"   Source: {top_item.get('source_metadata', {}).get('platform', 'N/A')}")

        ranking_scores = top_item.get('ranking_scores', {})
        final_score = top_item.get('final_rank_score', 'N/A')
        print(f"   Final Score: {final_score}")

        if ranking_scores:
            print(
                f"   Engagement: {ranking_scores.get('engagement_score', 'N/A')}")
            print(f"   Recency: {ranking_scores.get('recency_score', 'N/A')}")
            print(
                f"   Topic Relevance: {ranking_scores.get('topic_relevance_score', 'N/A')}")

        # Show enrichment data
        topic_class = top_item.get('topic_classification', {})
        sentiment = top_item.get('sentiment_analysis', {})

        if topic_class:
            print(
                f"   Primary Topic: {topic_class.get('primary_topic', 'N/A')}")
            print(
                f"   Topic Confidence: {topic_class.get('confidence', 'N/A')}")

        if sentiment:
            print(f"   Sentiment: {sentiment.get('sentiment', 'N/A')}")
            print(
                f"   Sentiment Score: {sentiment.get('compound_score', 'N/A')}")

    print("\n🎉 End-to-End Pipeline Test Completed Successfully!")
    return True


def test_service_health():
    """Test all service health endpoints."""
    print("\n🏥 Testing Service Health...")

    services = [
        ("Content Collector", "http://localhost:8001/health"),
        ("Content Processor", "http://localhost:8002/health"),
        ("Content Enricher", "http://localhost:8003/health"),
        ("Content Ranker", "http://localhost:8004/health")
    ]

    all_healthy = True

    for service_name, health_url in services:
        try:
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                status = health_data.get('status', 'unknown')
                print(f"   ✅ {service_name}: {status}")
            else:
                print(f"   ❌ {service_name}: HTTP {response.status_code}")
                all_healthy = False
        except requests.RequestException as e:
            print(f"   ❌ {service_name}: Connection failed ({e})")
            all_healthy = False

    return all_healthy


def main():
    """Run the complete test suite."""
    print("🌟 AI Content Farm - Pipeline Integration Test")
    print("=" * 60)

    # Test service health first
    if not test_service_health():
        print("\n❌ Some services are unhealthy. Please check the services.")
        return False

    print("\n✅ All services are healthy. Proceeding with pipeline test...")

    # Test the complete pipeline
    success = test_pipeline_integration()

    if success:
        print("\n🎉 All pipeline tests passed! The content farm is working correctly.")
        return True
    else:
        print("\n❌ Pipeline test failed. Please check the logs.")
        return False


if __name__ == "__main__":
    main()

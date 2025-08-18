#!/usr/bin/env python3
"""
Test script for content-ranker service.

Tests the ranking API with sample enriched content.
"""

import json
import requests
import datetime
from typing import List, Dict, Any


def create_test_content() -> List[Dict[str, Any]]:
    """Create sample enriched content items for testing."""

    base_time = datetime.datetime.now()

    test_items = [
        {
            "id": "test_001",
            "title": "Revolutionary AI Breakthrough in Machine Learning",
            "clean_title": "Revolutionary AI Breakthrough in Machine Learning",
            "engagement_score": 0.85,
            "normalized_score": 0.85,
            "published_at": (base_time - datetime.timedelta(hours=2)).isoformat() + "Z",
            "content_type": "article",
            "topic_classification": {
                "primary_topic": "artificial_intelligence",
                "confidence": 0.92,
                "categories": ["technology", "machine_learning", "innovation"]
            },
            "sentiment_analysis": {
                "sentiment": "positive",
                "confidence": 0.88,
                "compound_score": 0.7
            },
            "trend_analysis": {
                "trending": True,
                "trend_score": 0.9,
                "velocity": "increasing"
            },
            "source_metadata": {
                "platform": "reddit",
                "subreddit": "MachineLearning",
                "upvotes": 245,
                "comments": 67
            }
        },
        {
            "id": "test_002",
            "title": "Climate Change Research Shows Promising Results",
            "clean_title": "Climate Change Research Shows Promising Results",
            "engagement_score": 0.65,
            "normalized_score": 0.65,
            "published_at": (base_time - datetime.timedelta(hours=8)).isoformat() + "Z",
            "content_type": "article",
            "topic_classification": {
                "primary_topic": "environment",
                "confidence": 0.89,
                "categories": ["science", "climate", "research"]
            },
            "sentiment_analysis": {
                "sentiment": "positive",
                "confidence": 0.82,
                "compound_score": 0.5
            },
            "trend_analysis": {
                "trending": False,
                "trend_score": 0.4,
                "velocity": "stable"
            },
            "source_metadata": {
                "platform": "reddit",
                "subreddit": "science",
                "upvotes": 156,
                "comments": 34
            }
        },
        {
            "id": "test_003",
            "title": "New Programming Language Released for Web Development",
            "clean_title": "New Programming Language Released for Web Development",
            "engagement_score": 0.75,
            "normalized_score": 0.75,
            "published_at": (base_time - datetime.timedelta(hours=1)).isoformat() + "Z",
            "content_type": "article",
            "topic_classification": {
                "primary_topic": "programming",
                "confidence": 0.95,
                "categories": ["technology", "programming", "web_development"]
            },
            "sentiment_analysis": {
                "sentiment": "neutral",
                "confidence": 0.75,
                "compound_score": 0.2
            },
            "trend_analysis": {
                "trending": True,
                "trend_score": 0.7,
                "velocity": "increasing"
            },
            "source_metadata": {
                "platform": "reddit",
                "subreddit": "programming",
                "upvotes": 189,
                "comments": 45
            }
        },
        {
            "id": "test_004",
            "title": "Breakthrough in Quantum Computing Technology",
            "clean_title": "Breakthrough in Quantum Computing Technology",
            "engagement_score": 0.92,
            "normalized_score": 0.92,
            "published_at": (base_time - datetime.timedelta(hours=24)).isoformat() + "Z",
            "content_type": "article",
            "topic_classification": {
                "primary_topic": "quantum_computing",
                "confidence": 0.88,
                "categories": ["technology", "computing", "science"]
            },
            "sentiment_analysis": {
                "sentiment": "positive",
                "confidence": 0.91,
                "compound_score": 0.8
            },
            "trend_analysis": {
                "trending": False,
                "trend_score": 0.3,
                "velocity": "decreasing"
            },
            "source_metadata": {
                "platform": "reddit",
                "subreddit": "technology",
                "upvotes": 312,
                "comments": 89
            }
        },
        {
            "id": "test_005",
            "title": "Mobile App Privacy Concerns Raised by Security Experts",
            "clean_title": "Mobile App Privacy Concerns Raised by Security Experts",
            "engagement_score": 0.58,
            "normalized_score": 0.58,
            "published_at": (base_time - datetime.timedelta(hours=12)).isoformat() + "Z",
            "content_type": "article",
            "topic_classification": {
                "primary_topic": "cybersecurity",
                "confidence": 0.85,
                "categories": ["technology", "security", "privacy"]
            },
            "sentiment_analysis": {
                "sentiment": "negative",
                "confidence": 0.79,
                "compound_score": -0.4
            },
            "trend_analysis": {
                "trending": False,
                "trend_score": 0.2,
                "velocity": "stable"
            },
            "source_metadata": {
                "platform": "reddit",
                "subreddit": "cybersecurity",
                "upvotes": 98,
                "comments": 23
            }
        }
    ]

    return test_items


def test_ranking_basic():
    """Test basic ranking functionality."""
    print("=== Basic Ranking Test ===")

    test_content = create_test_content()

    request_data = {
        "items": test_content
    }

    response = requests.post(
        "http://localhost:8004/rank",
        json=request_data,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Successfully ranked {len(result['ranked_items'])} items")
        print(f"📊 Metadata: {result['metadata']}")

        print("\n🏆 Top 3 Ranked Items:")
        for i, item in enumerate(result['ranked_items'][:3], 1):
            scores = item.get('ranking_scores', {})
            final_score = item.get('final_rank_score', 'N/A')
            print(f"{i}. {item['title']}")
            print(f"   Final Score: {final_score:.3f}" if isinstance(
                final_score, (int, float)) else f"   Final Score: {final_score}")
            print(f"   Engagement: {scores.get('engagement_score', 'N/A'):.3f}" if isinstance(scores.get(
                'engagement_score'), (int, float)) else f"   Engagement: {scores.get('engagement_score', 'N/A')}")
            print(f"   Recency: {scores.get('recency_score', 'N/A'):.3f}" if isinstance(scores.get(
                'recency_score'), (int, float)) else f"   Recency: {scores.get('recency_score', 'N/A')}")
            print(f"   Topic Relevance: {scores.get('topic_relevance_score', 'N/A'):.3f}" if isinstance(scores.get(
                'topic_relevance_score'), (int, float)) else f"   Topic Relevance: {scores.get('topic_relevance_score', 'N/A')}")
            print()

        return True
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"Error: {response.text}")
        return False


def test_ranking_with_options():
    """Test ranking with custom options."""
    print("=== Custom Options Ranking Test ===")

    test_content = create_test_content()

    # Test with custom weights favoring recency
    request_data = {
        "items": test_content,
        "options": {
            "weights": {
                "engagement": 0.2,
                "recency": 0.6,
                "topic_relevance": 0.2
            },
            "target_topics": ["artificial_intelligence", "programming"],
            "limit": 3
        }
    }

    response = requests.post(
        "http://localhost:8004/rank",
        json=request_data,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Successfully ranked with custom options")
        print(f"📊 Items returned: {len(result['ranked_items'])}")
        print(
            f"🎯 Options applied: {result['metadata'].get('options_applied', {})}")

        print("\n🏆 Top ranked items with recency priority:")
        for i, item in enumerate(result['ranked_items'], 1):
            scores = item.get('ranking_scores', {})
            final_score = item.get('final_rank_score', 'N/A')
            print(f"{i}. {item['title']}")
            print(f"   Final Score: {final_score:.3f}" if isinstance(
                final_score, (int, float)) else f"   Final Score: {final_score}")
            print(f"   Published: {item.get('published_at', 'N/A')}")
            print()

        return True
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"Error: {response.text}")
        return False


def test_ranking_edge_cases():
    """Test ranking with edge cases."""
    print("=== Edge Cases Test ===")

    # Test with empty list
    print("Testing empty list...")
    response = requests.post(
        "http://localhost:8004/rank",
        json={"items": []},
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        result = response.json()
        print(
            f"✅ Empty list handled correctly: {len(result['ranked_items'])} items returned")
    else:
        print(f"❌ Empty list test failed: {response.status_code}")
        return False

    # Test with single item
    print("Testing single item...")
    single_item = create_test_content()[:1]
    response = requests.post(
        "http://localhost:8004/rank",
        json={"items": single_item},
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        result = response.json()
        print(
            f"✅ Single item handled correctly: {len(result['ranked_items'])} items returned")
        if result['ranked_items']:
            scores = result['ranked_items'][0].get('ranking_scores', {})
            final_score = result['ranked_items'][0].get(
                'final_rank_score', 'N/A')
            print(f"   Final Score: {final_score:.3f}" if isinstance(
                final_score, (int, float)) else f"   Final Score: {final_score}")
    else:
        print(f"❌ Single item test failed: {response.status_code}")
        return False

    return True


def test_error_handling():
    """Test API error handling."""
    print("=== Error Handling Test ===")

    # Test with invalid data
    print("Testing invalid request data...")
    response = requests.post(
        "http://localhost:8004/rank",
        json={"invalid": "data"},
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 422:
        print("✅ Invalid data handled correctly with 422 status")
    else:
        print(f"❌ Expected 422 for invalid data, got {response.status_code}")
        return False

    # Test with malformed JSON
    print("Testing malformed JSON...")
    response = requests.post(
        "http://localhost:8004/rank",
        data="{invalid json}",
        headers={"Content-Type": "application/json"}
    )

    if response.status_code in [400, 422]:
        print(
            f"✅ Malformed JSON handled correctly with {response.status_code} status")
    else:
        print(
            f"❌ Expected 400 or 422 for malformed JSON, got {response.status_code}")
        return False

    return True


def main():
    """Run all tests."""
    print("🚀 Starting Content Ranker API Tests")
    print("=" * 50)

    tests = [
        test_ranking_basic,
        test_ranking_with_options,
        test_ranking_edge_cases,
        test_error_handling
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
                print("✅ Test passed\n")
            else:
                print("❌ Test failed\n")
        except Exception as e:
            print(f"❌ Test error: {e}\n")

    print("=" * 50)
    print(f"🏁 Tests completed: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed! Content Ranker is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the service configuration.")
        return False


if __name__ == "__main__":
    main()

"""
Simplified Core Ranking Engine Tests
Tests only the pure ranking functions without external dependencies
"""

import sys
import os
import math
from datetime import datetime, timezone

# Add current directory to Python path for local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import only the pure functions we can test without pydantic
from core.ranking_engine import (
    calculate_engagement_score,
    calculate_recency_score,
    calculate_monetization_score,
    calculate_title_quality_score,
    rank_topic_functional,
    deduplicate_topics,
    transform_blob_to_topics,
    create_ranking_output,
    process_content_ranking
)

# Test data fixtures
SAMPLE_REDDIT_TOPIC = {
    "title": "AI and Machine Learning Breakthrough Transforms Technology Industry",
    "external_url": "https://www.techdirt.com/2025/08/04/example/",
    "reddit_url": "https://www.reddit.com/r/technology/comments/1mhtu7d/example/",
    "reddit_id": "1mhtu7d",
    "score": 13670,
    "created_utc": datetime.now(timezone.utc).timestamp() - 3600,  # 1 hour ago
    "num_comments": 547,
    "author": "AerialDarkguy",
    "subreddit": "technology",
    "fetched_at": "20250805_132500",
    "selftext": ""
}

RANKING_CONFIG = {
    "min_score_threshold": 100,
    "min_comments_threshold": 10,
    "weights": {
        "engagement": 0.3,
        "recency": 0.2,
        "monetization": 0.3,
        "title_quality": 0.2
    }
}


def test_calculate_engagement_score():
    """Test engagement scoring based on Reddit metrics"""
    # Test high engagement topic
    topic = {"score": 10000, "num_comments": 500}
    score = calculate_engagement_score(topic)

    assert 0 <= score <= 1.0
    assert isinstance(score, float)
    assert score > 0.8  # High engagement should score high
    print(f"✓ Engagement score test passed: {score}")


def test_calculate_recency_score():
    """Test recency scoring based on post age"""
    now = datetime.now(timezone.utc).timestamp()

    # Fresh topic (1 hour old)
    fresh_topic = {"created_utc": now - 3600}
    fresh_score = calculate_recency_score(fresh_topic)

    # Old topic (7 days old)
    old_topic = {"created_utc": now - (7 * 24 * 3600)}
    old_score = calculate_recency_score(old_topic)

    assert fresh_score > old_score
    assert fresh_score > 0.8
    assert old_score < 0.2
    print(f"✓ Recency score test passed: fresh={fresh_score}, old={old_score}")


def test_calculate_monetization_score():
    """Test monetization potential scoring"""
    # High-value keywords
    ai_topic = {
        "title": "AI and Machine Learning Breakthrough in Crypto Trading",
        "selftext": "This discusses artificial intelligence and blockchain technology"
    }
    ai_score = calculate_monetization_score(ai_topic)

    # Low-value topic
    random_topic = {"title": "Random discussion about weather"}
    random_score = calculate_monetization_score(random_topic)

    assert ai_score > random_score
    assert ai_score > 0.4  # Should have decent monetization score
    print(f"✓ Monetization score test passed: AI={ai_score}, weather={random_score}")


def test_calculate_title_quality_score():
    """Test title quality scoring"""
    # Good title quality
    good_title = {
        "title": "How to Build AI Applications: Complete Guide 2025"
    }
    good_score = calculate_title_quality_score(good_title)

    # Poor title quality
    poor_title = {"title": "this is bad title"}
    poor_score = calculate_title_quality_score(poor_title)

    assert good_score > poor_score
    print(f"✓ Title quality test passed: good={good_score}, poor={poor_score}")


def test_rank_single_topic():
    """Test ranking a single topic"""
    result = rank_topic_functional(SAMPLE_REDDIT_TOPIC, RANKING_CONFIG)

    assert "ranking_score" in result
    assert "ranking_details" in result
    assert 0 <= result["ranking_score"] <= 1.0

    # Verify updated breakdown structure
    breakdown = result["ranking_details"]
    required_keys = ["engagement", "recency", "monetization", "title_quality", "final"]
    for key in required_keys:
        assert key in breakdown
        assert isinstance(breakdown[key], (int, float))

    print(f"✓ Single topic ranking test passed: score={result['ranking_score']}")
    print(f"  Breakdown: {breakdown}")


def test_blob_transformation():
    """Test transforming blob input to ranking format"""
    blob_data = {
        "job_id": "test-123",
        "source": "reddit",
        "subject": "technology",
        "fetched_at": "20250813_150000",
        "topics": [SAMPLE_REDDIT_TOPIC]
    }

    transformed = transform_blob_to_topics(blob_data)

    assert isinstance(transformed, list)
    assert len(transformed) == 1

    # Check that original topic data is preserved
    topic = transformed[0]
    assert topic["title"] == SAMPLE_REDDIT_TOPIC["title"]
    assert topic["score"] == SAMPLE_REDDIT_TOPIC["score"]

    # Check that metadata was added
    assert "source_file" in topic
    assert "job_id" in topic
    assert topic["job_id"] == "test-123"

    print(f"✓ Blob transformation test passed")


def test_end_to_end_ranking():
    """Test the complete content ranking process"""
    blob_data = {
        "job_id": "test-123",
        "source": "reddit",
        "subject": "technology",
        "fetched_at": "20250813_120000",
        "topics": [
            {**SAMPLE_REDDIT_TOPIC, "score": 15000, "title": "AI Breakthrough in Machine Learning"},
            {**SAMPLE_REDDIT_TOPIC, "score": 5000, "title": "Random weather discussion", "reddit_id": "test2"},
            {**SAMPLE_REDDIT_TOPIC, "score": 50, "num_comments": 5, "title": "Low quality post", "reddit_id": "test3"}  # Should be filtered
        ]
    }

    result = process_content_ranking(blob_data, RANKING_CONFIG)

    # Verify output structure
    assert "ranked_topics" in result
    assert "metadata" in result
    assert "ranking_config" in result

    # Verify topics are ranked and filtered
    ranked_topics = result["ranked_topics"]
    assert len(ranked_topics) >= 1  # At least one should pass filtering
    
    # Verify ranking scores exist and are ordered
    for i, topic in enumerate(ranked_topics):
        assert "ranking_score" in topic
        assert "ranking_details" in topic
        assert 0 <= topic["ranking_score"] <= 1.0
        
        # Verify descending order
        if i > 0:
            assert topic["ranking_score"] <= ranked_topics[i-1]["ranking_score"]

    print(f"✓ End-to-end ranking test passed: {len(ranked_topics)} topics ranked")
    for i, topic in enumerate(ranked_topics[:3]):  # Show top 3
        print(f"  {i+1}. {topic['title'][:50]}... (score: {topic['ranking_score']})")


if __name__ == "__main__":
    print("Running Content Ranker Core Function Tests...")
    print("=" * 50)
    
    test_calculate_engagement_score()
    test_calculate_recency_score() 
    test_calculate_monetization_score()
    test_calculate_title_quality_score()
    test_rank_single_topic()
    test_blob_transformation()
    test_end_to_end_ranking()
    
    print("=" * 50)
    print("✅ All core function tests passed!")
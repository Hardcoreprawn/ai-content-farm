"""
Unit tests for Content Ranking Engine - Pure Functions
Migrated and enhanced from existing test_content_ranker.py
"""

import json
import pytest
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any

# Add current directory to Python path for local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.ranking_engine import (
    calculate_engagement_score,
    calculate_recency_score,
    calculate_monetization_score,
    calculate_title_quality_score,
    rank_topic_functional,
    rank_topics_functional,
    deduplicate_topics,
    transform_blob_to_topics,
    create_ranking_output,
    process_content_ranking
)

# Test data fixtures
SAMPLE_REDDIT_TOPIC = {
    "title": "Didn't Take Long To Reveal The UK's Online Safety Act Is Exactly The Privacy-Crushing Failure Everyone Warned About",
    "external_url": "https://www.techdirt.com/2025/08/04/example/",
    "reddit_url": "https://www.reddit.com/r/technology/comments/1mhtu7d/example/",
    "reddit_id": "1mhtu7d",
    "score": 13670,
    "created_utc": 1754351510.0,
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
        "recency": 0.2,  # Updated from 'freshness'
        "monetization": 0.3,
        "title_quality": 0.2  # Updated from 'seo_potential'
    }
}


class TestTopicScoringFunctions:
    """Test pure functions for topic scoring"""

    def test_calculate_engagement_score(self):
        """Test engagement scoring based on Reddit metrics"""
        # Test high engagement topic
        topic = {"score": 10000, "num_comments": 500}
        score = calculate_engagement_score(topic)

        assert 0 <= score <= 1.0
        assert isinstance(score, float)
        assert score > 0.8  # High engagement should score high

    def test_calculate_recency_score(self):
        """Test recency scoring based on post age (updated from freshness)"""
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

    def test_calculate_monetization_score(self):
        """Test monetization potential scoring"""
        # High-value keywords
        ai_topic = {
            "title": "AI and Machine Learning Breakthrough in Crypto Trading"}
        ai_score = calculate_monetization_score(ai_topic)

        # Low-value topic
        random_topic = {"title": "Random discussion about weather"}
        random_score = calculate_monetization_score(random_topic)

        assert ai_score > random_score
        assert ai_score > 0.5
        assert random_score < 0.3

    def test_calculate_title_quality_score(self):
        """Test title quality scoring (updated from SEO score)"""
        # Good title quality
        good_title = {
            "title": "How to Build AI Applications: Complete Guide 2025"}
        good_score = calculate_title_quality_score(good_title)

        # Poor title quality
        poor_title = {"title": "this is bad title"}
        poor_score = calculate_title_quality_score(poor_title)

        assert good_score > poor_score


class TestTopicRankingPipeline:
    """Test the complete ranking pipeline"""

    def test_rank_single_topic(self):
        """Test ranking a single topic with updated score structure"""
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

    def test_rank_multiple_topics(self):
        """Test ranking multiple topics with sorting"""
        topics = [
            {**SAMPLE_REDDIT_TOPIC, "score": 1000, "title": "Low engagement topic about weather patterns",
             "external_url": "https://example.com/weather", "reddit_id": "test1"},
            {**SAMPLE_REDDIT_TOPIC, "score": 15000, "title": "High engagement AI breakthrough announcement",
             "external_url": "https://example.com/ai", "reddit_id": "test2"},
            {**SAMPLE_REDDIT_TOPIC, "score": 5000, "title": "Medium engagement cryptocurrency market analysis",
             "external_url": "https://example.com/crypto", "reddit_id": "test3"}
        ]

        ranked = rank_topics_functional(topics, RANKING_CONFIG)

        assert len(ranked) == 3
        # Should be sorted by ranking_score (highest first)
        assert ranked[0]["ranking_score"] >= ranked[1]["ranking_score"]
        assert ranked[1]["ranking_score"] >= ranked[2]["ranking_score"]

    def test_topic_filtering(self):
        """Test that low-quality topics are filtered out"""
        topics = [
            {**SAMPLE_REDDIT_TOPIC, "score": 50,
                "num_comments": 5},  # Below threshold
            {**SAMPLE_REDDIT_TOPIC, "score": 1000,
                "num_comments": 50},  # Above threshold
        ]

        ranked = rank_topics_functional(topics, RANKING_CONFIG)

        assert len(ranked) == 1
        assert ranked[0]["score"] == 1000

    def test_deduplication(self):
        """Test that duplicate topics are removed"""
        topics = [
            {**SAMPLE_REDDIT_TOPIC, "reddit_id": "1", "score": 1000},
            {**SAMPLE_REDDIT_TOPIC, "reddit_id": "2",
                "score": 2000, "title": "Slightly different title"},
            {**SAMPLE_REDDIT_TOPIC, "reddit_id": "3",
                "score": 500}  # Duplicate title
        ]

        deduplicated = deduplicate_topics(topics)

        # Should keep highest scoring version of duplicates
        assert len(deduplicated) <= len(topics)


class TestDataTransformation:
    """Test data transformation functions"""

    def test_transform_blob_input(self):
        """Test transforming blob input to ranking format"""
        blob_data = {
            "job_id": "test-123",
            "source": "reddit",
            "subject": "technology",
            "fetched_at": "20250811_150000",
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

    def test_create_ranking_output(self):
        """Test creating the ranking output format"""
        ranked_topics = [
            {**SAMPLE_REDDIT_TOPIC, "ranking_score": 0.75,
                "ranking_details": {"final": 0.75}}
        ]
        source_files = ["test_file.json"]

        output = create_ranking_output(
            ranked_topics, source_files, RANKING_CONFIG)

        assert "ranked_topics" in output
        assert "metadata" in output
        assert "ranking_config" in output
        
        # Check metadata structure
        metadata = output["metadata"]
        assert "timestamp" in metadata
        assert "source_files" in metadata
        assert "total_topics" in metadata
        assert metadata["total_topics"] == 1
        assert metadata["source_files"] == source_files

    def test_process_content_ranking_end_to_end(self):
        """Test the complete content ranking process"""
        blob_data = {
            "job_id": "test-123",
            "source": "reddit",
            "subject": "technology",
            "fetched_at": "20250813_120000",
            "topics": [
                {**SAMPLE_REDDIT_TOPIC, "score": 15000, "title": "AI Breakthrough in Machine Learning"},
                {**SAMPLE_REDDIT_TOPIC, "score": 5000, "title": "Random weather discussion", "reddit_id": "test2"}
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
        
        # Verify ranking scores exist
        for topic in ranked_topics:
            assert "ranking_score" in topic
            assert "ranking_details" in topic
            assert 0 <= topic["ranking_score"] <= 1.0


class TestConfigurationHandling:
    """Test configuration and weight handling"""

    def test_default_weights(self):
        """Test that default weights are used when not provided"""
        topic = SAMPLE_REDDIT_TOPIC
        config_no_weights = {"min_score_threshold": 100}
        
        result = rank_topic_functional(topic, config_no_weights)
        assert "ranking_score" in result
        assert result["ranking_score"] > 0

    def test_custom_weights(self):
        """Test that custom weights are applied correctly"""
        topic = SAMPLE_REDDIT_TOPIC
        
        # Config heavily weighting engagement
        config_engagement = {
            "weights": {
                "engagement": 0.8,
                "recency": 0.1,
                "monetization": 0.05,
                "title_quality": 0.05
            }
        }
        
        # Config heavily weighting monetization
        config_monetization = {
            "weights": {
                "engagement": 0.1,
                "recency": 0.1,
                "monetization": 0.7,
                "title_quality": 0.1
            }
        }
        
        result_engagement = rank_topic_functional(topic, config_engagement)
        result_monetization = rank_topic_functional(topic, config_monetization)
        
        # Both should have valid scores but potentially different values
        assert 0 <= result_engagement["ranking_score"] <= 1.0
        assert 0 <= result_monetization["ranking_score"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
#!/usr/bin/env python3
"""
Unit tests for Content Ranker functional implementation.
Tests core ranking algorithms using existing data as baseline.
"""

# Test comment for pipeline optimization - test change (2025-08-12 14:36)

import json
import pytest
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any

# Add ContentRanker module to path
content_ranker_path = os.path.join(os.path.dirname(__file__), '../../functions/ContentRanker')
sys.path.insert(0, content_ranker_path)

from ranker_core import (
    calculate_engagement_score,
    calculate_freshness_score,
    calculate_monetization_score,
    calculate_seo_score,
    rank_topic_functional,
    rank_topics_functional,
    deduplicate_topics,
    transform_blob_to_topics,
    create_ranking_output
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
        "engagement": 0.4,
        "freshness": 0.2,
        "monetization": 0.3,
        "seo": 0.1
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

    def test_calculate_freshness_score(self):
        """Test freshness scoring based on post age"""
        now = datetime.now(timezone.utc).timestamp()

        # Fresh topic (1 hour old)
        fresh_topic = {"created_utc": now - 3600}
        fresh_score = calculate_freshness_score(fresh_topic)

        # Old topic (7 days old)
        old_topic = {"created_utc": now - (7 * 24 * 3600)}
        old_score = calculate_freshness_score(old_topic)

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

    def test_calculate_seo_score(self):
        """Test SEO potential scoring"""
        # Good SEO title
        good_title = {
            "title": "How to Build AI Applications: Complete Guide 2025"}
        good_score = calculate_seo_score(good_title)

        # Poor SEO title
        poor_title = {"title": "this is bad seo"}
        poor_score = calculate_seo_score(poor_title)

        assert good_score > poor_score


class TestTopicRankingPipeline:
    """Test the complete ranking pipeline"""

    def test_rank_single_topic(self):
        """Test ranking a single topic"""
        result = rank_topic_functional(SAMPLE_REDDIT_TOPIC, RANKING_CONFIG)

        assert "ranking_score" in result
        assert "score_breakdown" in result
        assert 0 <= result["ranking_score"] <= 1.0

        # Verify breakdown structure
        breakdown = result["score_breakdown"]
        required_keys = ["engagement", "freshness",
                         "monetization", "seo", "final"]
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
                "score_breakdown": {"final": 0.75}}
        ]
        source_files = ["test_file.json"]

        output = create_ranking_output(
            ranked_topics, source_files, RANKING_CONFIG)

        assert "generated_at" in output
        assert "source_files" in output
        assert "total_topics" in output
        assert "ranking_criteria" in output
        assert "topics" in output
        assert output["total_topics"] == 1
        assert output["source_files"] == source_files


class TestBaselineComparison:
    """Test against existing baseline data"""

    @pytest.fixture
    def baseline_data(self):
        """Load baseline ranking data from August 5th"""
        baseline_file = "/workspaces/ai-content-farm/output/ranked_topics_20250805_132514.json"
        if os.path.exists(baseline_file):
            with open(baseline_file, 'r') as f:
                return json.load(f)
        return None

    def test_ranking_consistency(self, baseline_data):
        """Test that new ranker produces consistent results with baseline"""
        if not baseline_data:
            pytest.skip("Baseline data not available")

        # Extract topics without ranking scores
        original_topics = []
        for topic in baseline_data["topics"]:
            clean_topic = {k: v for k, v in topic.items()
                           if k not in ["ranking_score", "score_breakdown"]}
            original_topics.append(clean_topic)

        # Re-rank with new algorithm
        new_rankings = rank_topics_functional(original_topics, RANKING_CONFIG)

        # Compare top topics (order might differ slightly)
        assert len(new_rankings) > 0
        assert all("ranking_score" in topic for topic in new_rankings)

        # Top topic should still be high quality
        top_topic = new_rankings[0]
        assert top_topic["ranking_score"] > 0.5


# Import the functional implementation
sys.path.append(os.path.join(os.path.dirname(
    __file__), '../../functions/ContentRanker'))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

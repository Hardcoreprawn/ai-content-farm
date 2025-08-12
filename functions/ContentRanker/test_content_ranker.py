#!/usr/bin/env python3
"""
Unit tests for ContentRanker function.

Tests the core ranking logic alongside the function implementation.
These tests focus on the pure functional components that can be
tested without Azure infrastructure dependencies.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime, timezone

# Add current directory to path for local imports
sys.path.insert(0, os.path.dirname(__file__))

try:
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
except ImportError as e:
    pytest.skip(f"Cannot import ranker_core: {e}", allow_module_level=True)


class TestContentRankerCore:
    """Test the core ranking algorithms"""
    
    @pytest.mark.unit
    def test_calculate_engagement_score(self, sample_reddit_topic, ranking_config):
        """Test engagement score calculation"""
        score = calculate_engagement_score(sample_reddit_topic)
        
        assert isinstance(score, (int, float))
        assert 0 <= score <= 1
        
        # High engagement topic should score well
        high_engagement = sample_reddit_topic.copy()
        high_engagement['score'] = 5000
        high_engagement['num_comments'] = 200
        
        high_score = calculate_engagement_score(high_engagement)
        
        assert high_score > score
    
    @pytest.mark.unit
    def test_calculate_freshness_score(self, sample_reddit_topic, ranking_config):
        """Test freshness score calculation"""
        # Test with current timestamp (should be very fresh)
        fresh_topic = sample_reddit_topic.copy()
        fresh_topic['created_utc'] = datetime.now(timezone.utc).timestamp()
        
        score = calculate_freshness_score(fresh_topic)
        
        assert isinstance(score, (int, float))
        assert 0 <= score <= 1
        assert score > 0.8  # Should be very fresh
    
    @pytest.mark.unit
    def test_calculate_seo_score(self, sample_reddit_topic):
        """Test SEO potential scoring"""
        score = calculate_seo_score(sample_reddit_topic)
        
        assert isinstance(score, (int, float))
        assert 0 <= score <= 1
        
        # Test with high-value keywords
        seo_topic = sample_reddit_topic.copy()
        seo_topic['title'] = "How to make money with AI automation tips"
        
        seo_score = calculate_seo_score(seo_topic)
        assert seo_score > score
    
    @pytest.mark.unit
    def test_rank_topic_functional(self, sample_reddit_topic, ranking_config):
        """Test single topic ranking"""
        ranked_topic = rank_topic_functional(sample_reddit_topic, ranking_config)
        
        # Verify structure
        assert 'ranking_score' in ranked_topic
        assert 'ranking_details' in ranked_topic
        assert isinstance(ranked_topic['ranking_score'], (int, float))
        
        # Verify score components
        details = ranked_topic['ranking_details']
        required_components = ['engagement', 'freshness', 'monetization', 'seo_potential']
        for component in required_components:
            assert component in details
            assert isinstance(details[component], (int, float))
    
    @pytest.mark.unit
    def test_rank_topics_functional(self, sample_reddit_topics, ranking_config):
        """Test batch topic ranking"""
        ranked_topics = rank_topics_functional(sample_reddit_topics, ranking_config)
        
        assert len(ranked_topics) <= len(sample_reddit_topics)
        
        # Verify sorting (highest score first)
        scores = [topic['ranking_score'] for topic in ranked_topics]
        assert scores == sorted(scores, reverse=True)
        
        # Verify all topics have required fields
        for topic in ranked_topics:
            assert 'ranking_score' in topic
            assert 'ranking_details' in topic
    
    @pytest.mark.unit
    def test_deduplicate_topics(self, sample_reddit_topics):
        """Test topic deduplication"""
        # Create duplicates with same title
        topics_with_dupes = sample_reddit_topics.copy()
        duplicate = sample_reddit_topics[0].copy()
        duplicate['reddit_id'] = 'duplicate_id'
        topics_with_dupes.append(duplicate)
        
        deduplicated = deduplicate_topics(topics_with_dupes)
        
        # Should remove duplicate
        assert len(deduplicated) == len(sample_reddit_topics)
        
        # Should keep higher scoring duplicate
        titles = [topic['title'] for topic in deduplicated]
        assert len(titles) == len(set(titles))  # All unique titles
    
    @pytest.mark.unit
    def test_threshold_filtering(self, ranking_config):
        """Test that low-quality topics are filtered out"""
        low_quality_topic = {
            "title": "Low quality topic",
            "reddit_id": "low_quality",
            "score": 50,  # Below threshold
            "num_comments": 5,  # Below threshold
            "subreddit": "test",
            "created_utc": datetime.now(timezone.utc).timestamp(),
            "fetched_at": "20250812_120000"
        }
        
        ranked_topics = rank_topics_functional([low_quality_topic], ranking_config)
        
        # Should be filtered out due to low score/comments
        assert len(ranked_topics) == 0


class TestContentRankerIntegration:
    """Integration tests for ContentRanker function"""
    
    @pytest.mark.function
    @patch('azure.storage.blob.BlobServiceClient')
    def test_transform_blob_to_topics(self, mock_blob_client, sample_reddit_topics):
        """Test blob data transformation"""
        # Mock blob content
        blob_data = {
            "topics": sample_reddit_topics,
            "metadata": {"timestamp": "2025-08-12T12:00:00Z"}
        }
        
        topics = transform_blob_to_topics(blob_data)
        
        assert isinstance(topics, list)
        assert len(topics) == len(sample_reddit_topics)
        
        for topic in topics:
            assert 'title' in topic
            assert 'reddit_id' in topic
    
    @pytest.mark.function
    def test_create_ranking_output(self, sample_reddit_topics, ranking_config):
        """Test ranking output format"""
        ranked_topics = rank_topics_functional(sample_reddit_topics, ranking_config)
        output = create_ranking_output(ranked_topics, ["test_file.json"], ranking_config)
        
        # Verify output structure
        assert 'ranked_topics' in output
        assert 'metadata' in output
        assert 'ranking_config' in output
        
        # Verify metadata
        metadata = output['metadata']
        assert 'timestamp' in metadata
        assert 'total_topics' in metadata
        assert 'filtered_topics' in metadata
        
        # Verify topics are properly formatted
        for topic in output['ranked_topics']:
            assert 'ranking_score' in topic
            assert 'ranking_details' in topic


class TestContentRankerEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.unit
    def test_empty_topics_list(self, ranking_config):
        """Test handling of empty topics list"""
        result = rank_topics_functional([], ranking_config)
        assert result == []
    
    @pytest.mark.unit
    def test_invalid_topic_data(self, ranking_config):
        """Test handling of malformed topic data"""
        invalid_topic = {"title": "Missing required fields"}
        
        # Should not crash, should filter out invalid topics
        result = rank_topics_functional([invalid_topic], ranking_config)
        assert len(result) == 0
    
    @pytest.mark.unit
    def test_missing_config_values(self, sample_reddit_topic):
        """Test handling of incomplete configuration"""
        incomplete_config = {"weights": {"engagement": 1.0}}
        
        # Should use defaults or handle gracefully
        try:
            rank_topic_functional(sample_reddit_topic, incomplete_config)
        except KeyError:
            pytest.fail("Should handle missing config gracefully")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])

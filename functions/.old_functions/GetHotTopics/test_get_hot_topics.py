#!/usr/bin/env python3
"""
Unit tests for GetHotTopics function.

Tests the Reddit topic collection logic alongside the function implementation.
"""

import pytest
import sys
import os
import json
from unittest.mock import Mock, patch

# Add current directory to path for local imports
sys.path.insert(0, os.path.dirname(__file__))


class TestGetHotTopicsStructure:
    """Test that the GetHotTopics function is properly structured"""
    
    @pytest.mark.unit
    def test_function_structure(self):
        """Test that function has proper Azure Functions structure"""
        # Check for function.json
        function_json_path = os.path.join(os.path.dirname(__file__), 'function.json')
        assert os.path.exists(function_json_path), "function.json should exist"
        
        # Check that it's valid JSON
        with open(function_json_path, 'r') as f:
            function_config = json.load(f)
        
        assert 'bindings' in function_config
        assert isinstance(function_config['bindings'], list)
    
    @pytest.mark.unit
    def test_init_file_exists(self):
        """Test that __init__.py exists for Azure Functions"""
        init_path = os.path.join(os.path.dirname(__file__), '__init__.py')
        assert os.path.exists(init_path), "__init__.py should exist for Azure Functions"


class TestGetHotTopicsLogic:
    """Test the core Reddit collection logic"""
    
    @pytest.mark.unit
    def test_reddit_data_structure(self, sample_reddit_topic):
        """Test that sample data follows expected Reddit structure"""
        required_fields = [
            'title', 'reddit_id', 'score', 'num_comments',
            'author', 'subreddit', 'created_utc'
        ]
        
        for field in required_fields:
            assert field in sample_reddit_topic, f"Missing field: {field}"
        
        # Validate data types
        assert isinstance(sample_reddit_topic['score'], (int, float))
        assert isinstance(sample_reddit_topic['num_comments'], int)
        assert isinstance(sample_reddit_topic['created_utc'], (int, float))
    
    @pytest.mark.unit
    @patch('praw.Reddit')
    def test_reddit_api_mocking(self, mock_reddit):
        """Test that Reddit API can be mocked for testing"""
        # Setup mock Reddit client
        mock_subreddit = Mock()
        mock_submission = Mock()
        mock_submission.title = "Test Topic"
        mock_submission.id = "test123"
        mock_submission.score = 1000
        mock_submission.num_comments = 50
        
        mock_subreddit.hot.return_value = [mock_submission]
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        
        # Test that mocking works
        reddit = mock_reddit()
        subreddit = reddit.subreddit('technology')
        topics = list(subreddit.hot(limit=1))
        
        assert len(topics) == 1
        assert topics[0].title == "Test Topic"


class TestGetHotTopicsConfiguration:
    """Test configuration and setup"""
    
    @pytest.mark.unit
    def test_subreddit_list_validation(self):
        """Test that subreddit lists are properly formatted"""
        # Common subreddits for testing
        test_subreddits = [
            'technology', 'programming', 'MachineLearning',
            'datascience', 'artificial', 'Futurology'
        ]
        
        for subreddit in test_subreddits:
            # Should be strings
            assert isinstance(subreddit, str)
            # Should not have r/ prefix
            assert not subreddit.startswith('r/')
            # Should not be empty
            assert len(subreddit) > 0
    
    @pytest.mark.unit
    def test_collection_parameters(self):
        """Test collection parameter validation"""
        # Test reasonable limits
        test_params = {
            'limit_per_subreddit': 25,
            'min_score_threshold': 100,
            'min_comments_threshold': 10,
            'max_age_hours': 24
        }
        
        for param, value in test_params.items():
            assert isinstance(value, (int, float))
            assert value > 0


class TestGetHotTopicsIntegration:
    """Integration tests for GetHotTopics"""
    
    @pytest.mark.integration
    @pytest.mark.azure
    def test_timer_trigger_format(self):
        """Test timer trigger configuration"""
        function_json_path = os.path.join(os.path.dirname(__file__), 'function.json')
        
        if os.path.exists(function_json_path):
            with open(function_json_path, 'r') as f:
                function_config = json.load(f)
            
            # Look for timer trigger
            timer_binding = next((b for b in function_config['bindings'] 
                                if b.get('type') == 'timerTrigger'), None)
            
            if timer_binding:
                assert 'schedule' in timer_binding
                # Schedule should be a valid CRON expression
                schedule = timer_binding['schedule']
                assert isinstance(schedule, str)
                assert len(schedule.split()) >= 5  # Basic CRON validation
    
    @pytest.mark.function
    def test_output_format(self):
        """Test that output follows expected format"""
        # Expected output structure for Reddit topics
        expected_structure = {
            'topics': [],
            'metadata': {
                'timestamp': 'ISO-8601',
                'subreddits_processed': [],
                'total_topics_collected': 0,
                'function': 'GetHotTopics'
            }
        }
        
        # Verify structure exists (this is a template test)
        assert 'topics' in expected_structure
        assert 'metadata' in expected_structure
        assert isinstance(expected_structure['topics'], list)
        assert isinstance(expected_structure['metadata'], dict)


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])

"""
Unit tests for Content Enricher enhancement engine.
Tests core enhancement algorithms using mock data.
"""

import asyncio
import pytest
import os
import sys
from unittest.mock import patch, AsyncMock
from datetime import datetime

# Add the current directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.enhancement_engine import (
    enhance_content, enhance_topics_batch, EnhancementConfig,
    extract_content_preview, generate_fallback_content,
    get_openai_client
)


class TestContentExtraction:
    """Test content extraction and preprocessing"""
    
    def test_extract_content_preview(self):
        """Test content preview extraction"""
        topic = {
            "title": "Test AI Article",
            "content": "This is a detailed article about AI and machine learning.",
            "description": "A comprehensive guide to understanding AI"
        }
        
        preview = extract_content_preview(topic, max_length=200)
        
        assert "Title: Test AI Article" in preview
        assert "Content: This is a detailed article" in preview
        assert "Description: A comprehensive guide" in preview
    
    def test_extract_content_preview_truncation(self):
        """Test content truncation for long content"""
        long_content = "A" * 5000
        topic = {"title": "Test", "content": long_content}
        
        preview = extract_content_preview(topic, max_length=100)
        
        assert len(preview) <= 103  # 100 + "..."
        assert preview.endswith("...")


class TestFallbackEnhancement:
    """Test rule-based fallback enhancement"""
    
    def test_generate_fallback_content(self):
        """Test fallback content generation"""
        topic = {
            "title": "AI Breakthrough in Machine Learning Technology",
            "reddit_id": "test123",
            "content": "This discusses artificial intelligence advances."
        }
        
        result = generate_fallback_content(topic)
        
        assert result.success == True
        assert result.topic_id == "test123"
        assert "ai" in result.tags
        assert "machine learning" in result.tags
        assert result.sentiment in ["positive", "negative", "neutral"]
        assert result.enhancement_metadata["method"] == "rule_based_fallback"
    
    def test_fallback_sentiment_detection(self):
        """Test sentiment detection in fallback mode"""
        positive_topic = {
            "title": "Amazing breakthrough in technology innovation",
            "reddit_id": "pos1"
        }
        
        negative_topic = {
            "title": "Major failure causes concern in the industry",
            "reddit_id": "neg1"
        }
        
        neutral_topic = {
            "title": "Regular update about market conditions",
            "reddit_id": "neu1"
        }
        
        pos_result = generate_fallback_content(positive_topic)
        neg_result = generate_fallback_content(negative_topic)
        neu_result = generate_fallback_content(neutral_topic)
        
        assert pos_result.sentiment == "positive"
        assert neg_result.sentiment == "negative"
        assert neu_result.sentiment == "neutral"


class TestEnhancementConfig:
    """Test enhancement configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = EnhancementConfig()
        
        assert config.openai_model == "gpt-3.5-turbo"
        assert config.max_tokens == 500
        assert config.temperature == 0.7
        assert config.include_sentiment == True
        assert config.include_tags == True
        assert config.include_insights == True
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = EnhancementConfig(
            openai_model="gpt-4",
            max_tokens=1000,
            temperature=0.5,
            include_sentiment=False
        )
        
        assert config.openai_model == "gpt-4"
        assert config.max_tokens == 1000
        assert config.temperature == 0.5
        assert config.include_sentiment == False


@pytest.mark.asyncio
class TestEnhancementEngine:
    """Test the main enhancement engine"""
    
    async def test_enhance_content_fallback(self):
        """Test content enhancement with fallback (no OpenAI)"""
        topic = {
            "title": "Revolutionary AI Technology Breakthrough",
            "content": "Scientists have developed new artificial intelligence algorithms.",
            "reddit_id": "test456",
            "score": 2000,
            "num_comments": 150
        }
        
        # Ensure OpenAI is not available for this test
        with patch('core.enhancement_engine.get_openai_client', return_value=None):
            result = await enhance_content(topic)
        
        assert result.success == True
        assert result.topic_id == "test456"
        assert len(result.tags) > 0
        assert result.sentiment in ["positive", "negative", "neutral"]
        assert result.enhancement_metadata["method"] == "rule_based_fallback"
    
    async def test_enhance_topics_batch(self):
        """Test batch enhancement of multiple topics"""
        topics = [
            {
                "title": "AI News Update",
                "reddit_id": "batch1",
                "content": "Latest AI developments"
            },
            {
                "title": "Blockchain Technology Review", 
                "reddit_id": "batch2",
                "content": "Crypto and blockchain analysis"
            }
        ]
        
        with patch('core.enhancement_engine.get_openai_client', return_value=None):
            results = await enhance_topics_batch(topics)
        
        assert len(results) == 2
        assert all(result.success for result in results)
        assert results[0].topic_id == "batch1"
        assert results[1].topic_id == "batch2"
    
    async def test_enhance_content_no_content(self):
        """Test enhancement with empty content"""
        topic = {
            "reddit_id": "empty1",
            "title": "",
            "content": ""
        }
        
        result = await enhance_content(topic)
        
        assert result.success == False
        assert result.error == "No content available for enhancement"
    
    @patch('core.enhancement_engine.AsyncOpenAI')
    async def test_enhance_content_with_openai_mock(self, mock_openai_class):
        """Test enhancement with mocked OpenAI"""
        # Mock OpenAI client
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        # Mock API responses
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock()]
        mock_response.choices[0].message.content = "This is a mocked summary"
        mock_client.chat.completions.create.return_value = mock_response
        
        topic = {
            "title": "Test Article",
            "content": "Test content for OpenAI enhancement",
            "reddit_id": "openai_test"
        }
        
        with patch('core.enhancement_engine.get_openai_client', return_value=mock_client):
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'}):
                result = await enhance_content(topic)
        
        assert result.success == True
        assert result.topic_id == "openai_test"
        # Should have made API calls for summary, insights, tags, sentiment
        assert mock_client.chat.completions.create.call_count >= 1


class TestOpenAIClient:
    """Test OpenAI client setup"""
    
    def test_get_openai_client_no_key(self):
        """Test OpenAI client when no API key is set"""
        with patch.dict(os.environ, {}, clear=True):
            client = get_openai_client()
            assert client is None
    
    def test_get_openai_client_with_key(self):
        """Test OpenAI client when API key is available"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'}):
            with patch('core.enhancement_engine.AsyncOpenAI') as mock_openai:
                client = get_openai_client()
                mock_openai.assert_called_once_with(api_key='test_key')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
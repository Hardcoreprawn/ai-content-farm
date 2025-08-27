"""API tests for content generator FastAPI endpoints"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from main import app
from models import GeneratedContent, GenerationRequest, RankedTopic
from service_logic import ContentGeneratorService


@pytest.fixture
def test_client():
    """Create test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def mock_generated_content(sample_ranked_topic):
    """Create mock generated content"""
    return GeneratedContent(
        topic=sample_ranked_topic.topic,
        content_type="tldr",
        title="AI Healthcare Breakthrough: Quick Take",
        content="Revolutionary AI system transforms medical diagnosis...",
        word_count=150,
        tags=["AI", "healthcare", "innovation"],
        sources=sample_ranked_topic.sources,
        writer_personality="professional",
        generation_time=datetime.utcnow(),
        ai_model="azure-openai",
        metadata={"generation_time": 2.5, "model_used": "azure-openai"},
    )


class TestContentGeneratorAPI:
    """Test FastAPI endpoints for content generation"""

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns service information"""
        # Act
        response = test_client.get("/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Content Generator"
        assert "version" in data
        assert "endpoints" in data

    def test_health_endpoint(self, test_client):
        """Test health check endpoint"""
        # Act
        response = test_client.get("/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data

    def test_status_endpoint(self, test_client):
        """Test status endpoint returns service metrics"""
        # Act
        response = test_client.get("/status")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "uptime" in data
        assert "active_generations" in data
        assert "total_generated" in data

    @patch.object(ContentGeneratorService, "generate_content")
    def test_generate_tldr_endpoint(
        self, mock_generate, test_client, sample_ranked_topic, mock_generated_content
    ):
        """Test TLDR generation endpoint"""
        # Arrange
        mock_generate.return_value = mock_generated_content
        request_data = {
            "topic": sample_ranked_topic.topic,
            "sources": [source.model_dump() for source in sample_ranked_topic.sources],
            "rank": sample_ranked_topic.rank,
            "ai_score": sample_ranked_topic.ai_score,
            "sentiment": sample_ranked_topic.sentiment,
            "tags": sample_ranked_topic.tags,
        }

        # Act
        response = test_client.post("/generate/tldr", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["topic"] == sample_ranked_topic.topic
        assert data["content_type"] == "tldr"
        assert "content" in data
        assert "word_count" in data

    @patch.object(ContentGeneratorService, "generate_content")
    def test_generate_blog_endpoint(
        self, mock_generate, test_client, sample_ranked_topic, mock_generated_content
    ):
        """Test blog generation endpoint"""
        # Arrange
        blog_content = GeneratedContent(
            topic=sample_ranked_topic.topic,
            content_type="blog",
            title="Understanding AI in Healthcare",
            content="Comprehensive analysis of AI healthcare applications...",
            word_count=500,
            tags=["AI", "healthcare", "technology"],
            sources=sample_ranked_topic.sources,
            writer_personality="professional",
            generation_time=datetime.utcnow(),
            ai_model="azure-openai",
            metadata={"generation_time": 5.2, "model_used": "azure-openai"},
        )
        mock_generate.return_value = blog_content
        request_data = {
            "topic": sample_ranked_topic.topic,
            "sources": [source.model_dump() for source in sample_ranked_topic.sources],
            "rank": sample_ranked_topic.rank,
            "ai_score": sample_ranked_topic.ai_score,
            "sentiment": sample_ranked_topic.sentiment,
            "tags": sample_ranked_topic.tags,
        }

        # Act
        response = test_client.post("/generate/blog", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["content_type"] == "blog"
        assert data["word_count"] > 100

    @patch.object(ContentGeneratorService, "generate_content")
    def test_generate_deepdive_endpoint(
        self, mock_generate, test_client, sample_ranked_topic
    ):
        """Test deep dive generation endpoint"""
        # Arrange
        deepdive_content = GeneratedContent(
            topic=sample_ranked_topic.topic,
            content_type="deepdive",
            title="Deep Dive: AI Healthcare Revolution",
            content="Comprehensive analysis with extensive research...",
            word_count=1200,
            tags=["AI", "healthcare", "research"],
            sources=sample_ranked_topic.sources,
            writer_personality="professional",
            generation_time=datetime.utcnow(),
            ai_model="claude",
            metadata={"generation_time": 12.8, "model_used": "claude"},
        )
        mock_generate.return_value = deepdive_content
        request_data = {
            "topic": sample_ranked_topic.topic,
            "sources": [source.model_dump() for source in sample_ranked_topic.sources],
            "rank": sample_ranked_topic.rank,
            "ai_score": sample_ranked_topic.ai_score,
            "sentiment": sample_ranked_topic.sentiment,
            "tags": sample_ranked_topic.tags,
        }

        # Act
        response = test_client.post("/generate/deepdive", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["content_type"] == "deepdive"
        assert data["word_count"] > 500

    def test_generate_endpoint_with_invalid_data(self, test_client):
        """Test generation endpoints with invalid request data"""
        # Act
        response = test_client.post("/generate/tldr", json={})

        # Assert
        assert response.status_code == 422  # Validation error

    def test_generate_endpoint_with_missing_topic(self, test_client):
        """Test generation endpoints with missing required fields"""
        # Arrange
        incomplete_data = {
            "sources": [],
            "rank": 1,
            "ai_score": 0.8,
            "sentiment": "positive",
            # Missing 'topic'
        }

        # Act
        response = test_client.post("/generate/tldr", json=incomplete_data)

        # Assert
        assert response.status_code == 422

    @patch.object(ContentGeneratorService, "generate_content")
    def test_generation_error_handling(
        self, mock_generate, test_client, sample_ranked_topic
    ):
        """Test error handling when generation fails"""
        # Arrange
        mock_generate.side_effect = ValueError("Insufficient source material")
        request_data = {
            "topic": sample_ranked_topic.topic,
            "sources": [source.model_dump() for source in sample_ranked_topic.sources],
            "rank": sample_ranked_topic.rank,
            "ai_score": sample_ranked_topic.ai_score,
            "sentiment": sample_ranked_topic.sentiment,
            "tags": sample_ranked_topic.tags,
        }

        # Act
        response = test_client.post("/generate/tldr", json=request_data)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Invalid request parameters" in data["detail"]

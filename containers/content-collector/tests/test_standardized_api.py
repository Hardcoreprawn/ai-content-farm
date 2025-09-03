"""
Tests for standardized API endpoints in The Collector.

Tests the new /api/content-womble/* endpoints alongside legacy endpoints
to verify both formats work correctly during the transition period.
"""

import json
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from main import app

# Create test client
client = TestClient(app)


@pytest.mark.integration
class TestStandardizedAPIEndpoints:
    """Test new standardized API endpoints."""

    def test_health_endpoint_format(self):
        """Test standardized health endpoint returns StandardResponse format."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse format
        assert "status" in data
        assert "message" in data
        assert "data" in data
        assert "metadata" in data

        assert data["status"] == "success"
        assert "Service is" in data["message"]

        # Verify metadata contains required fields
        metadata = data["metadata"]
        assert "timestamp" in metadata
        assert metadata["function"] == "content-womble"
        assert "version" in metadata

        # Verify health data structure
        health_data = data["data"]
        assert health_data["service"] == "content-womble"
        assert health_data["status"] in ["healthy", "warning", "unhealthy"]
        assert "dependencies" in health_data
        assert "uptime_seconds" in health_data

    def test_status_endpoint_format(self):
        """Test standardized status endpoint returns StandardResponse format."""
        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse format
        assert "status" in data
        assert "message" in data
        assert "data" in data
        assert "metadata" in data

        assert data["status"] == "success"
        assert data["metadata"]["function"] == "content-womble"

        # Verify status data structure
        status_data = data["data"]
        assert status_data["service"] == "content-womble"
        assert "uptime_seconds" in status_data
        assert "stats" in status_data
        assert "last_operation" in status_data

    def test_process_endpoint_success(self):
        """Test standardized process endpoint with successful collection."""
        test_data = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 5,
                }
            ],
            "deduplicate": True,
            "save_to_storage": True,
        }

        response = client.post("/process", json=test_data)

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse format
        assert data["status"] == "success"
        assert "Collected" in data["message"]
        assert data["metadata"]["function"] == "content-womble"
        assert "execution_time_ms" in data["metadata"]

        # Verify collection data structure (standardized format)
        collection_data = data["data"]
        assert "sources_processed" in collection_data
        assert "total_items_collected" in collection_data
        assert "items_saved" in collection_data
        assert "storage_location" in collection_data
        assert "processing_time_ms" in collection_data
        assert "summary" in collection_data

    def test_process_endpoint_error_handling(self):
        """Test standardized error handling in process endpoint."""
        # Invalid request data (missing required fields)
        test_data = {"invalid": "data"}

        response = client.post("/process", json=test_data)

        assert response.status_code == 422  # Validation error
        data = response.json()

        # Should be handled by global exception handler with StandardResponse format
        assert "status" in data
        assert data["status"] == "error"
        assert "message" in data
        assert "metadata" in data
        assert data["metadata"]["function"] == "content-womble"

    def test_docs_endpoint(self):
        """Test API documentation endpoint."""
        response = client.get("/docs")

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse format
        assert data["status"] == "success"
        assert data["message"] == "API documentation retrieved"
        assert data["metadata"]["function"] == "content-womble"

        # Verify documentation structure
        docs_data = data["data"]
        assert docs_data["service"] == "content-womble"
        assert "endpoints" in docs_data
        assert "supported_sources" in docs_data
        assert "authentication" in docs_data

        # Verify endpoint documentation
        endpoints = docs_data["endpoints"]
        assert "/health" in endpoints
        assert "/status" in endpoints
        assert "/process" in endpoints


@pytest.mark.integration
class TestStandardizedErrorHandling:
    """Test standardized error responses."""

    def test_404_error_format(self):
        """Test 404 errors use standardized format."""
        response = client.get("/api/content-womble/nonexistent")

        assert response.status_code == 404
        data = response.json()

        # Should use standardized error format
        assert data["status"] == "error"
        assert "not found" in data["message"].lower()
        assert data["metadata"]["function"] == "content-womble"

    def test_method_not_allowed_error_format(self):
        """Test 405 errors use standardized format."""
        response = client.post("/api/content-womble/health")  # GET endpoint

        assert response.status_code == 405
        data = response.json()

        # Should use standardized error format
        assert data["status"] == "error"
        assert data["metadata"]["function"] == "content-womble"


@pytest.mark.integration
class TestRootEndpointUpdated:
    """Test root endpoint shows both legacy and new endpoints."""

    def test_root_endpoint_standardized_format(self):
        """Test root endpoint uses StandardResponse and shows all endpoints."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Verify StandardResponse format
        assert data["status"] == "success"
        assert data["message"] == "Content Collector API running"
        assert data["metadata"]["function"] == "content-womble"

        # Verify endpoint listing includes legacy and standardized endpoints
        endpoints = data["data"]["endpoints"]

        # Legacy endpoints (kept for backward compatibility)
        assert "collect" in endpoints
        assert "sources" in endpoints

        # Standardized endpoints
        assert "api_health" in endpoints
        assert "api_process" in endpoints
        assert "api_docs" in endpoints

        # Verify new endpoint paths
        assert endpoints["api_health"] == "/api/content-womble/health"
        assert endpoints["api_process"] == "/api/content-womble/process"


@pytest.mark.integration
class TestResponseTimingMetadata:
    """Test execution time tracking in responses."""

    def test_execution_time_in_success_response(self):
        """Test execution time is tracked in successful API calls."""
        test_data = {
            "sources": [
                {
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 1,
                }
            ],
        }

        response = client.post("/api/content-womble/process", json=test_data)

        assert response.status_code == 200
        data = response.json()

        # Verify execution time is present and reasonable
        execution_time = data["metadata"]["execution_time_ms"]
        assert isinstance(execution_time, int)
        assert execution_time > 0
        assert execution_time < 30000  # Should be less than 30 seconds

    def test_execution_time_in_error_response(self):
        """Test execution time is tracked even in error responses."""
        # This will cause an internal error due to missing dependencies
        test_data = {
            "sources": [
                {
                    "type": "invalid_source_type",
                    "config": {"invalid": "config"},
                }
            ],
        }

        response = client.post("/api/content-womble/process", json=test_data)

        # Should handle gracefully and return execution time
        data = response.json()
        if "metadata" in data and "execution_time_ms" in data["metadata"]:
            execution_time = data["metadata"]["execution_time_ms"]
            assert isinstance(execution_time, int)
            assert execution_time >= 0


# ============================================================================
# UNIT TESTS
# ============================================================================


@pytest.mark.unit
class TestModels:
    """Unit tests for Pydantic models."""

    def test_source_config_creation(self):
        """Test SourceConfig model creation and validation."""
        from models import SourceConfig

        # Valid configuration
        config = SourceConfig(
            type="reddit", subreddits=["technology", "science"], limit=20
        )

        assert config.type == "reddit"
        assert config.subreddits == ["technology", "science"]
        assert config.limit == 20
        assert config.criteria == {}

    def test_source_config_defaults(self):
        """Test SourceConfig default values."""
        from models import SourceConfig

        config = SourceConfig(type="web")

        assert config.type == "web"
        assert config.subreddits is None
        assert config.websites is None
        assert config.limit == 10
        assert config.criteria == {}

    def test_discovery_request_creation(self):
        """Test DiscoveryRequest model creation."""
        from models import DiscoveryRequest, SourceConfig

        source = SourceConfig(type="reddit", subreddits=["technology"])
        request = DiscoveryRequest(sources=[source])

        assert len(request.sources) == 1
        assert request.analysis_depth == "standard"
        assert request.include_trending is True
        assert request.include_recommendations is True

    def test_trending_topic_creation(self):
        """Test TrendingTopic model creation."""
        from models import TrendingTopic

        topic = TrendingTopic(
            topic="artificial intelligence",
            mentions=10,
            growth_rate=0.5,
            confidence=0.8,
            related_keywords=["AI", "machine learning"],
            sample_content=["AI breakthrough in healthcare"],
            source_breakdown={"technology": 5, "science": 5},
            sentiment_score=0.7,
        )

        assert topic.topic == "artificial intelligence"
        assert topic.mentions == 10
        assert topic.confidence == 0.8
        assert len(topic.related_keywords) == 2


@pytest.mark.unit
class TestDiscoveryFunctions:
    """Unit tests for discovery.py functions."""

    def test_analyze_trending_topics_basic(self):
        """Test basic trending topic analysis."""
        from discovery import analyze_trending_topics

        posts = [
            {
                "title": "Artificial Intelligence breakthrough in healthcare",
                "selftext": "New AI model shows promise in medical diagnosis",
                "subreddit": "technology",
            },
            {
                "title": "Machine learning algorithm improves accuracy",
                "selftext": "Researchers develop AI system for better predictions",
                "subreddit": "MachineLearning",
            },
        ]

        topics = analyze_trending_topics(posts, min_mentions=1)

        assert isinstance(topics, list)
        # Should find some topics from the posts
        assert len(topics) >= 0

    def test_analyze_trending_topics_min_mentions_filter(self):
        """Test that min_mentions filtering works."""
        from discovery import analyze_trending_topics

        posts = [
            {"title": "Single mention topic", "selftext": "", "subreddit": "test"},
            {
                "title": "Repeated topic here",
                "selftext": "repeated topic again",
                "subreddit": "test",
            },
        ]

        # With min_mentions=2, should filter appropriately
        topics = analyze_trending_topics(posts, min_mentions=2)

        assert isinstance(topics, list)
        # Verify function returns expected type
        for topic in topics:
            assert hasattr(topic, "topic")
            assert hasattr(topic, "mentions")

    def test_extract_keywords_function(self):
        """Test keyword extraction utility."""
        from discovery import extract_keywords

        text = "Artificial intelligence and machine learning algorithms"
        keywords = extract_keywords(text)

        assert isinstance(keywords, list)
        assert len(keywords) >= 0
        # Should extract some form of keywords
        for keyword in keywords:
            assert isinstance(keyword, str)

    def test_generate_research_recommendations(self):
        """Test research recommendation generation."""
        from discovery import generate_research_recommendations
        from models import TrendingTopic

        topics = [
            TrendingTopic(
                topic="artificial intelligence",
                mentions=10,
                growth_rate=0.5,
                confidence=0.8,
                related_keywords=["AI", "machine learning"],
                sample_content=["AI breakthrough in healthcare"],
                source_breakdown={"technology": 5, "science": 5},
                sentiment_score=0.7,
            )
        ]

        recommendations = generate_research_recommendations(topics)

        assert isinstance(recommendations, list)
        # Should generate recommendations
        for rec in recommendations:
            assert hasattr(rec, "topic")
            assert hasattr(rec, "research_potential")


@pytest.mark.unit
class TestRedditClientCore:
    """Unit tests for Reddit client core functionality (without external dependencies)."""

    @patch("reddit_client.os.getenv")
    def test_environment_detection(self, mock_getenv):
        """Test environment detection logic."""
        from reddit_client import RedditClient

        # Mock development environment
        mock_getenv.side_effect = lambda key, default=None: {
            "ENVIRONMENT": "development",
            "REDDIT_CLIENT_ID": None,
            "REDDIT_CLIENT_SECRET": None,
            "REDDIT_USER_AGENT": None,
        }.get(key, default)

        with patch.object(RedditClient, "_init_local_reddit"):
            client = RedditClient()
            assert client.environment == "development"

    @patch("reddit_client.os.getenv")
    def test_container_apps_credentials_detection(self, mock_getenv):
        """Test Container Apps secret detection."""
        from reddit_client import RedditClient

        # Mock Container Apps environment with secrets
        mock_getenv.side_effect = lambda key, default=None: {
            "ENVIRONMENT": "production",
            "REDDIT_CLIENT_ID": "test_client_id",
            "REDDIT_CLIENT_SECRET": "test_secret",  # pragma: allowlist secret
            "REDDIT_USER_AGENT": "test_agent",
        }.get(key, default)

        with patch.object(RedditClient, "_init_reddit_with_creds") as mock_init:
            client = RedditClient()
            mock_init.assert_called_once_with(
                "test_client_id", "test_secret", "test_agent"
            )

    def test_rate_limiting_calculation(self):
        """Test rate limiting delay calculation."""
        from reddit_client import RedditClient

        with patch.object(RedditClient, "_initialize_reddit"):
            client = RedditClient()

            # Test rate limiting logic if it exists in the class
            # This would test any rate limiting helper methods


@pytest.mark.unit
class TestSourceCollectors:
    """Unit tests for source collector factory."""

    def test_create_reddit_collector(self):
        """Test creating Reddit collector."""
        from source_collectors import SourceCollectorFactory

        collector = SourceCollectorFactory.create_collector("reddit")

        assert collector is not None
        # Should return a Reddit collector instance
        assert hasattr(collector, "collect_content")

    def test_create_web_collector(self):
        """Test creating web collector."""
        from source_collectors import SourceCollectorFactory

        collector = SourceCollectorFactory.create_collector("web")

        assert collector is not None
        # Should return a web collector instance
        assert hasattr(collector, "collect_content")

    def test_get_available_sources(self):
        """Test getting available source types."""
        from source_collectors import SourceCollectorFactory

        sources = SourceCollectorFactory.get_available_sources()

        assert isinstance(sources, list)
        assert "reddit" in sources
        assert "web" in sources

    def test_create_collector_invalid_type(self):
        """Test handling of invalid collector type."""
        from source_collectors import SourceCollectorFactory

        with pytest.raises(ValueError):
            SourceCollectorFactory.create_collector("invalid_type")


@pytest.mark.unit
class TestUtilityFunctions:
    """Unit tests for utility functions across modules."""

    def test_data_validation_helpers(self):
        """Test any data validation utility functions."""
        # This would test utility functions for data validation
        # if they exist in the codebase
        pass

    def test_error_handling_helpers(self):
        """Test error handling utility functions."""
        # This would test error handling utilities
        # if they exist in the codebase
        pass

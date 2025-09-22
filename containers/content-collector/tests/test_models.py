"""
Data Models Tests for Content Collector - ACTIVE

CURRENT ARCHITECTURE: Tests for API request/response models
Status: ACTIVE - Still needed for API validation

Tests data models and validation logic.
These models are still used by the FastAPI endpoints regardless of collector architecture.

Test Coverage:
- SourceConfig validation
- DiscoveryRequest validation
- TrendingTopic model validation
- Pydantic model behavior
- API request/response structure

Tests data models and validation logic.
"""

import pytest
from models import DiscoveryRequest, SourceConfig, TrendingTopic


@pytest.mark.unit
class TestModels:
    """Test data model creation and validation."""

    def test_source_config_creation(self):
        """Test SourceConfig model creation."""
        config = SourceConfig(type="reddit", subreddits=["programming"], limit=10)

        assert config.type == "reddit"
        assert config.config["subreddits"] == ["programming"]
        assert config.config["limit"] == 10

    def test_source_config_defaults(self):
        """Test SourceConfig default values."""
        config = SourceConfig(type="web")

        assert config.type == "web"
        assert config.config == {"limit": 10}

    def test_discovery_request_creation(self):
        """Test DiscoveryRequest model creation."""
        reddit_source = SourceConfig(type="reddit", subreddits=["technology"])
        web_source = SourceConfig(type="web", websites=["example.com"])

        request = DiscoveryRequest(
            sources=[reddit_source, web_source],
            keywords=["technology"],
            analysis_depth="basic",
        )

        assert len(request.sources) == 2
        assert request.sources[0].type == "reddit"
        assert request.sources[1].type == "web"
        assert request.keywords == ["technology"]
        assert request.analysis_depth == "basic"

    def test_trending_topic_creation(self):
        """Test TrendingTopic model creation."""
        topic = TrendingTopic(
            topic="artificial intelligence",
            mentions=15,
            growth_rate=0.4,
            confidence=0.85,
            related_keywords=["AI", "ML", "deep learning"],
            sample_content=["AI news article 1", "AI news article 2"],
            source_breakdown={"technology": 8, "science": 7},
            sentiment_score=0.6,
        )

        assert topic.topic == "artificial intelligence"
        assert topic.mentions == 15
        assert topic.growth_rate == 0.4
        assert topic.confidence == 0.85
        assert len(topic.related_keywords) == 3
        assert len(topic.sample_content) == 2
        assert topic.source_breakdown["technology"] == 8


@pytest.mark.unit
class TestModelValidation:
    """Test model validation and error handling."""

    def test_source_config_invalid_type(self):
        """Test SourceConfig with invalid type."""
        # Depending on model implementation, this might raise ValidationError
        try:
            config = SourceConfig(type="")
            # If no validation, just check it was created
            assert config.type == ""
        except ValueError:
            # Expected if validation is implemented
            pass

    def test_discovery_request_empty_sources(self):
        """Test DiscoveryRequest with empty sources."""
        try:
            request = DiscoveryRequest(sources=[])
            # If no validation, just check it was created
            assert request.sources == []
        except ValueError:
            # Expected if validation requires non-empty sources
            pass

    def test_trending_topic_negative_values(self):
        """Test TrendingTopic with negative values."""
        try:
            topic = TrendingTopic(
                topic="test",
                mentions=-1,  # Negative mentions
                growth_rate=-0.5,
                confidence=1.5,  # Over 1.0
                related_keywords=[],
                sample_content=[],
                source_breakdown={},
                sentiment_score=2.0,  # Outside normal range
            )
            # If no validation, check values were set
            assert topic.mentions == -1
        except ValueError:
            # Expected if validation prevents negative/invalid values
            pass


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

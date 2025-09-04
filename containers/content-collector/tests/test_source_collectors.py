"""
Source Collector Tests for Content Collector

Tests source collector factory and implementations.
"""

from unittest.mock import Mock, patch

import pytest
from source_collectors import SourceCollectorFactory


@pytest.mark.unit
class TestSourceCollectorFactory:
    """Unit tests for source collector factory."""

    @patch("source_collectors.RedditPRAWCollector")
    @patch("source_collectors.get_reddit_credentials_with_fallback")
    def test_create_reddit_collector(self, mock_get_creds, mock_reddit_collector):
        """Test creating Reddit collector."""
        # Mock credentials check to avoid network calls
        mock_get_creds.return_value = {
            "client_id": None,
            "client_secret": None,
            "user_agent": None,
        }

        # Mock the collector instance
        mock_collector_instance = Mock()
        mock_collector_instance.collect_content = Mock()
        mock_reddit_collector.return_value = mock_collector_instance

        collector = SourceCollectorFactory.create_collector("reddit")

        assert collector is not None
        # Should return a Reddit collector instance
        assert hasattr(collector, "collect_content")

    @patch("source_collectors.WebContentCollector")
    def test_create_web_collector(self, mock_web_collector):
        """Test creating web collector."""
        # Mock the collector instance
        mock_collector_instance = Mock()
        mock_collector_instance.collect_content = Mock()
        mock_web_collector.return_value = mock_collector_instance

        collector = SourceCollectorFactory.create_collector("web")

        assert collector is not None
        # Should return a web collector instance
        assert hasattr(collector, "collect_content")

    def test_get_available_sources(self):
        """Test getting available source types."""
        sources = SourceCollectorFactory.get_available_sources()

        assert isinstance(sources, list)
        assert "reddit" in sources
        assert "web" in sources

    def test_create_collector_invalid_type(self):
        """Test handling of invalid collector type."""
        with pytest.raises(ValueError):
            SourceCollectorFactory.create_collector("invalid_type")


@pytest.mark.unit
class TestSourceCollectorConfig:
    """Test source collector configuration handling."""

    @patch("source_collectors.RedditPRAWCollector")
    def test_reddit_collector_with_explicit_config(self, mock_reddit_collector):
        """Test Reddit collector creation with explicit configuration."""
        config = {
            "client_id": "test_client_id",
            "client_secret": "test_secret",  # pragma: allowlist secret
            "user_agent": "test_agent",
        }

        mock_collector_instance = Mock()
        mock_reddit_collector.return_value = mock_collector_instance

        collector = SourceCollectorFactory.create_collector("reddit", config)

        # Verify collector was created with provided config
        mock_reddit_collector.assert_called_once_with(config)
        assert collector is not None

    @patch("source_collectors.WebContentCollector")
    def test_web_collector_with_config(self, mock_web_collector):
        """Test web collector creation with configuration."""
        config = {"timeout": 30, "headers": {"User-Agent": "test"}}

        mock_collector_instance = Mock()
        mock_web_collector.return_value = mock_collector_instance

        collector = SourceCollectorFactory.create_collector("web", config)

        assert collector is not None

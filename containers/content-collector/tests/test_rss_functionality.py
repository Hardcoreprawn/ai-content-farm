"""
RSS Functionality Tests

Simple, resilient tests to ensure RSS parsing works correctly with lxml backend.
Focuses on core feedparser functionality without being overly comprehensive.
"""

from unittest.mock import Mock, patch

import feedparser
import pytest
from collectors.simple_rss import SimpleRSSCollector


class TestRSSFunctionality:
    """Test core RSS parsing functionality with lxml backend."""

    def test_feedparser_basic_parsing(self):
        """Test that feedparser can parse a simple RSS feed structure."""
        # Simple RSS content that should always parse correctly
        rss_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
                <description>A test RSS feed</description>
                <item>
                    <title>Test Article</title>
                    <description>Test content</description>
                    <link>https://example.com/article</link>
                    <pubDate>Tue, 24 Sep 2025 10:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>"""

        # Parse the RSS content
        feed = feedparser.parse(rss_content)

        # Basic assertions that should always work
        assert feed.feed.title == "Test Feed"
        assert len(feed.entries) == 1
        assert feed.entries[0].title == "Test Article"
        assert feed.entries[0].link == "https://example.com/article"

    def test_rss_collector_initialization(self):
        """Test that RSS collector can be initialized properly."""
        config = {"feed_urls": ["https://example.com/feed.rss"], "max_items": 10}

        collector = SimpleRSSCollector(config)

        assert collector.feed_urls == ["https://example.com/feed.rss"]
        assert collector.config.get("max_items") == 10

    def test_feedparser_with_response_text(self):
        """Test feedparser directly with RSS content (simulating HTTP response)."""
        # Simulate what would come from an HTTP response
        response_text = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Mock Feed</title>
                <item>
                    <title>Mock Article</title>
                    <description>Mock content</description>
                    <link>https://mock.com/article</link>
                </item>
            </channel>
        </rss>"""

        # This should not raise an exception with lxml backend
        try:
            feed = feedparser.parse(response_text)
            assert feed.feed.title == "Mock Feed"
            assert len(feed.entries) == 1
            assert feed.entries[0].title == "Mock Article"
        except Exception as e:
            pytest.fail(f"RSS parsing failed with lxml backend: {e}")

    def test_feedparser_handles_malformed_feed(self):
        """Test that feedparser gracefully handles malformed RSS."""
        # Intentionally malformed RSS
        bad_rss = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Bad Feed</title>
                <item>
                    <title>Unclosed title
                    <description>Missing closing tag</description>
                </item>
            </channel>"""  # Missing closing tags

        # Should not raise an exception, just parse what it can
        feed = feedparser.parse(bad_rss)

        # feedparser should handle this gracefully
        assert hasattr(feed, "feed")
        assert hasattr(feed, "entries")
        # Don't make strict assertions about malformed content

    def test_lxml_backend_available(self):
        """Test that lxml is available as a parser backend."""
        try:
            import lxml.etree

            # Basic lxml functionality test
            xml_content = "<root><item>test</item></root>"
            tree = lxml.etree.fromstring(xml_content)
            assert tree.find("item").text == "test"
        except ImportError:
            pytest.fail("lxml not available")
        except Exception as e:
            pytest.fail(f"lxml basic functionality failed: {e}")

    def test_beautifulsoup_with_lxml(self):
        """Test that BeautifulSoup works with lxml parser."""
        try:
            from bs4 import BeautifulSoup

            html_content = "<html><body><p>Test content</p></body></html>"

            # Test with lxml parser
            soup = BeautifulSoup(html_content, "lxml")
            assert soup.find("p").text == "Test content"

        except ImportError:
            pytest.skip("BeautifulSoup not available")
        except Exception as e:
            pytest.fail(f"BeautifulSoup with lxml parser failed: {e}")


class TestRSSCollectorIntegration:
    """Simple integration tests for RSS collector."""

    def test_collector_initialization_graceful(self):
        """Test that RSS collector initializes gracefully with various configs."""
        collector = SimpleRSSCollector({"feed_urls": ["https://example.com/feed.rss"]})

        # Should not crash on initialization
        assert collector.feed_urls == ["https://example.com/feed.rss"]
        assert hasattr(collector, "collect_batch")  # Check actual method name

    def test_empty_feed_urls_handling(self):
        """Test collector handles empty feed URLs."""
        collector = SimpleRSSCollector({"feed_urls": []})

        assert collector.feed_urls == []
        # Should initialize without error
        assert hasattr(collector, "collect_batch")  # Check actual method name

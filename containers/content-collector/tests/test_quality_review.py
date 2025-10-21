"""
Tests for quality review module.

Verify item-level filtering for readability, relevance, and validation.
"""

import pytest
from quality.review import (
    check_readability,
    check_technical_relevance,
    review_item,
    validate_item,
)


class TestValidateItem:
    """Verify item validation catches missing/invalid fields."""

    def test_valid_item_passes(self):
        """Valid item with all required fields passes validation."""
        item = {
            "id": "test_id",
            "title": "Test Article Title",
            "content": "This is test content with meaningful information",
            "source": "reddit",
        }

        is_valid, error = validate_item(item)
        assert is_valid is True
        assert error is None

    def test_missing_id_fails(self):
        """Item missing id field fails validation."""
        item = {
            "title": "Test",
            "content": "Content",
            "source": "reddit",
        }

        is_valid, error = validate_item(item)
        assert is_valid is False
        assert error is not None and "id" in error

    def test_missing_title_fails(self):
        """Item missing title field fails validation."""
        item = {
            "id": "test",
            "content": "Content",
            "source": "reddit",
        }

        is_valid, error = validate_item(item)
        assert is_valid is False
        assert error is not None and "title" in error

    def test_invalid_title_type_fails(self):
        """Item with non-string title fails validation."""
        item = {
            "id": "test",
            "title": 123,  # Should be string
            "content": "Content",
            "source": "reddit",
        }

        is_valid, error = validate_item(item)
        assert is_valid is False

    def test_not_dict_fails(self):
        """Non-dict object fails validation."""
        is_valid, error = validate_item("not a dict")
        assert is_valid is False


class TestReadabilityCheck:
    """Verify readability filters catch low-quality content."""

    def test_readable_content_passes(self):
        """Well-written content passes readability check."""
        item = {
            "title": "Understanding Python Async/Await Patterns",
            "content": "Python's async/await provides powerful concurrency primitives. "
            * 10,  # Ensure > 100 chars
        }

        passes, reason = check_readability(item)
        assert passes is True
        assert reason is None

    def test_title_too_short_fails(self):
        """Title shorter than 10 chars fails."""
        item = {
            "title": "Short",
            "content": "This is a long enough content" * 10,
        }

        passes, reason = check_readability(item)
        assert passes is False
        assert reason == "title_too_short"

    def test_content_too_short_fails(self):
        """Content shorter than 100 chars fails."""
        item = {
            "title": "Long Enough Title Here",
            "content": "Short content",
        }

        passes, reason = check_readability(item)
        assert passes is False
        assert reason == "content_too_short"

    def test_title_not_readable_fails(self):
        """Title with mostly symbols/numbers fails."""
        item = {
            "title": "!@#$%^&*() 123 456",
            "content": "This is a long enough content" * 10,
        }

        passes, reason = check_readability(item)
        assert passes is False
        assert reason == "title_not_readable"

    def test_content_mostly_markup_fails(self):
        """Content that is mostly HTML/JSON fails."""
        item = {
            "title": "Real Title Here For Sure",
            "content": "<html><body><div><span>" * 30,  # Even more HTML
        }

        passes, reason = check_readability(item)
        assert passes is False
        assert reason == "content_mostly_markup"


class TestTechnicalRelevanceCheck:
    """Verify technical relevance filter catches off-topic content."""

    def test_technical_content_passes(self):
        """Content with tech keywords passes relevance check."""
        item = {
            "title": "Building a Python API with FastAPI",
            "content": "FastAPI makes it easy to build APIs with Python. " * 5,
            "metadata": {"subreddit": "programming"},
        }

        passes, reason = check_technical_relevance(item)
        assert passes is True
        assert reason is None

    def test_no_technical_keywords_fails(self):
        """Content without tech keywords fails."""
        item = {
            "title": "My favorite vacation spots in Europe",
            "content": "I visited many beautiful places this summer " * 5,
            "metadata": {"subreddit": "worldnews"},
        }

        passes, reason = check_technical_relevance(item)
        assert passes is False
        assert reason == "no_technical_keywords"

    def test_off_topic_source_fails(self):
        """Content from off-topic subreddits fails."""
        item = {
            "title": "Machine Learning Algorithm Optimization",
            "content": "This paper discusses advanced optimization techniques " * 5,
            "metadata": {"subreddit": "funny"},  # Off-topic source
        }

        passes, reason = check_technical_relevance(item)
        assert passes is False
        assert reason == "off_topic_source"

    def test_multiple_keywords_passes(self):
        """Content with multiple tech keywords passes."""
        item = {
            "title": "Database Design for Cloud Applications",
            "content": "When building applications in the cloud, database design is critical. "
            "APIs and security are also important considerations. " * 3,
            "metadata": {"subreddit": "programming"},
        }

        passes, reason = check_technical_relevance(item)
        assert passes is True


class TestReviewItem:
    """Verify complete review pipeline."""

    def test_quality_item_passes_full_review(self):
        """High-quality item passes all review stages."""
        item = {
            "id": "reddit_abc123",
            "title": "Advanced Python Concurrency Patterns with Async/Await",
            "content": "Python's async/await provides powerful concurrency primitives. "
            "Understanding how event loops work is crucial for writing efficient code. "
            * 3,
            "source": "reddit",
            "metadata": {"subreddit": "programming"},
        }

        passes, reason = review_item(item)
        assert passes is True
        assert reason is None

    def test_short_title_fails_review(self):
        """Short title fails review."""
        item = {
            "id": "test",
            "title": "Short",
            "content": "This is meaningful content about programming " * 10,
            "source": "reddit",
            "metadata": {"subreddit": "programming"},
        }

        passes, reason = review_item(item)
        assert passes is False
        assert reason is not None and "title_too_short" in reason

    def test_no_keywords_fails_review(self):
        """Content without technical keywords fails review."""
        item = {
            "id": "test",
            "title": "My Family Vacation Was Amazing",
            "content": "We went to the beach and had so much fun. " * 10,
            "source": "reddit",
            "metadata": {"subreddit": "programming"},
        }

        passes, reason = review_item(item)
        assert passes is False
        assert reason is not None and "no_technical_keywords" in reason

    def test_skip_relevance_check_if_disabled(self):
        """When check_relevance=False, technical keywords not required."""
        item = {
            "id": "test",
            "title": "Very Long Title About Something Interesting",
            "content": "This is meaningful content " * 10,
            "source": "reddit",
            "metadata": {"subreddit": "random"},
        }

        passes, reason = review_item(item, check_relevance=False)
        assert passes is True
        assert reason is None

    def test_validation_error_includes_context(self):
        """Validation errors include context."""
        item = {
            "id": "test",
            "title": "Valid Title Here",
            "content": "This is valid content that should pass " * 10,
            "source": "reddit",
            # Missing metadata field is ok (optional)
        }

        passes, reason = review_item(item, check_relevance=False)
        assert passes is True


class TestReviewIntegration:
    """Integration tests for complete review workflow."""

    def test_mixed_items(self):
        """Test review on mix of good and bad items."""
        items = [
            {
                "id": "good_1",
                "title": "Python Best Practices for Async Code",
                "content": "When writing async Python code, following best practices is essential. "
                * 5,
                "source": "reddit",
                "metadata": {"subreddit": "programming"},
            },
            {
                "id": "bad_1",
                "title": "Hi",  # Too short
                "content": "Short",
                "source": "reddit",
            },
            {
                "id": "bad_2",
                "title": "Vacation Time is the Best",
                "content": "We had so much fun on vacation at the beach " * 5,
                "source": "reddit",
                "metadata": {"subreddit": "travel"},
            },
        ]

        results = []
        for item in items:
            passes, reason = review_item(item)
            results.append((item["id"], passes, reason))

        # First should pass
        assert results[0][1] is True

        # Second and third should fail
        assert results[1][1] is False
        assert results[2][1] is False

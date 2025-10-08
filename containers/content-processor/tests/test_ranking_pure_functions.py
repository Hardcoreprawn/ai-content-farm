"""
Tests for pure functional topic ranking logic.

Black box testing: validates inputs and outputs only, not implementation.

Contract Version: 1.0.0
"""

from datetime import datetime, timedelta, timezone

import pytest
from ranking import (
    calculate_engagement_score,
    calculate_freshness_score,
    calculate_priority_score,
    calculate_priority_score_from_dict,
    calculate_title_quality_score,
    calculate_url_quality_score,
)


class TestCalculateEngagementScore:
    """Test engagement score calculation."""

    def test_no_engagement(self):
        """Zero upvotes and comments returns 0.0."""
        assert calculate_engagement_score(0, 0) == 0.0

    def test_max_engagement(self):
        """100 upvotes and 50 comments returns 0.3 (with float tolerance)."""
        assert abs(calculate_engagement_score(100, 50) - 0.3) < 0.001

    def test_partial_engagement(self):
        """50 upvotes and 25 comments returns expected score."""
        score = calculate_engagement_score(50, 25)
        assert 0.0 < score < 0.31  # Allow for float precision

    def test_over_max_upvotes(self):
        """Over 100 upvotes capped at 0.2 contribution."""
        score1 = calculate_engagement_score(100, 0)
        score2 = calculate_engagement_score(200, 0)
        assert score1 == score2 == 0.2

    def test_over_max_comments(self):
        """Over 50 comments capped at 0.1 contribution."""
        score1 = calculate_engagement_score(0, 50)
        score2 = calculate_engagement_score(0, 100)
        assert score1 == score2 == 0.1

    def test_negative_upvotes_raises_error(self):
        """Negative upvotes raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_engagement_score(-1, 0)

    def test_negative_comments_raises_error(self):
        """Negative comments raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            calculate_engagement_score(0, -1)


class TestCalculateFreshnessScore:
    """Test freshness score calculation."""

    def test_very_fresh_content(self):
        """Content less than 1 hour old has high freshness score."""
        now = datetime.now(timezone.utc)
        recent = now - timedelta(hours=1)
        score = calculate_freshness_score(recent, now)
        assert 0.25 < score <= 0.3

    def test_half_day_old_content(self):
        """Content 12 hours old has medium freshness score."""
        now = datetime.now(timezone.utc)
        half_day = now - timedelta(hours=12)
        score = calculate_freshness_score(half_day, now)
        assert 0.1 < score < 0.2

    def test_old_content(self):
        """Content 24+ hours old has zero freshness score."""
        now = datetime.now(timezone.utc)
        old = now - timedelta(hours=25)
        score = calculate_freshness_score(old, now)
        assert score == 0.0

    def test_exactly_24_hours_old(self):
        """Content exactly 24 hours old has zero freshness score."""
        now = datetime.now(timezone.utc)
        exactly_24h = now - timedelta(hours=24)
        score = calculate_freshness_score(exactly_24h, now)
        assert score == 0.0

    def test_naive_datetime_raises_error(self):
        """Naive datetime (no timezone) raises ValueError."""
        naive = datetime.now()  # No timezone
        with pytest.raises(ValueError, match="timezone-aware"):
            calculate_freshness_score(naive)

    def test_future_datetime_raises_error(self):
        """Future timestamp raises ValueError."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=1)
        with pytest.raises(ValueError, match="future"):
            calculate_freshness_score(future, now)


class TestCalculateTitleQualityScore:
    """Test title quality score calculation."""

    def test_empty_title(self):
        """Empty title returns 0.0."""
        assert calculate_title_quality_score("") == 0.0

    def test_short_title(self):
        """Very short title (< 10 chars) returns 0.0."""
        assert calculate_title_quality_score("Post") == 0.0

    def test_long_title(self):
        """Very long title (> 200 chars) has reduced score."""
        long_title = "x" * 250
        score = calculate_title_quality_score(long_title)
        assert score < 0.2  # No length bonus

    def test_good_length_no_keywords(self):
        """Good length but no keywords gets partial score."""
        title = "Random article text here"
        score = calculate_title_quality_score(title)
        assert 0.0 < score <= 0.1

    def test_good_length_with_keywords(self):
        """Good length with engaging keywords gets max score."""
        title = "How AI is Changing Technology in 2025"
        score = calculate_title_quality_score(title)
        assert score == 0.2

    def test_keywords_only(self):
        """Keywords in short title gets keyword score only."""
        title = "AI"
        score = calculate_title_quality_score(title)
        assert score == 0.1  # Keyword bonus only, no length bonus

    def test_case_insensitive_keywords(self):
        """Keywords work regardless of case."""
        title1 = "how ai works in technology"
        title2 = "HOW AI WORKS IN TECHNOLOGY"
        assert calculate_title_quality_score(title1) == calculate_title_quality_score(
            title2
        )


class TestCalculateUrlQualityScore:
    """Test URL quality score calculation."""

    def test_empty_url(self):
        """Empty URL returns 0.0."""
        assert calculate_url_quality_score("") == 0.0

    def test_short_url(self):
        """Very short URL (< 10 chars) returns 0.0."""
        assert calculate_url_quality_score("http://x") == 0.0

    def test_valid_url(self):
        """Valid URL returns 0.05."""
        assert calculate_url_quality_score("https://example.com/article") == 0.05

    def test_long_url(self):
        """Long URL returns 0.05."""
        long_url = "https://example.com/" + "x" * 100
        assert calculate_url_quality_score(long_url) == 0.05


class TestCalculatePriorityScore:
    """Test comprehensive priority score calculation."""

    def test_minimal_input(self):
        """Minimal input returns base score (0.6)."""
        score = calculate_priority_score()
        assert score == 0.6

    def test_high_engagement_only(self):
        """High engagement alone increases score."""
        score = calculate_priority_score(upvotes=100, comments=50)
        assert 0.8 < score <= 1.0

    def test_freshness_only(self):
        """Recent content alone increases score."""
        now = datetime.now(timezone.utc)
        recent = now - timedelta(hours=1)
        score = calculate_priority_score(collected_at=recent, now=now)
        assert 0.8 < score <= 1.0

    def test_title_quality_only(self):
        """Good title alone increases score."""
        score = calculate_priority_score(title="How AI is Changing Technology in 2025")
        assert 0.7 < score <= 0.9

    def test_url_quality_only(self):
        """Valid URL alone slightly increases score."""
        score = calculate_priority_score(url="https://example.com/article")
        assert 0.6 < score <= 0.7

    def test_perfect_score(self):
        """All factors combined can reach 1.0."""
        now = datetime.now(timezone.utc)
        recent = now - timedelta(minutes=30)
        score = calculate_priority_score(
            upvotes=100,
            comments=50,
            title="How AI is Changing Technology in 2025",
            url="https://example.com/article",
            collected_at=recent,
            now=now,
        )
        assert score == 1.0

    def test_score_clamped_to_minimum(self):
        """Score never goes below 0.5."""
        score = calculate_priority_score(base_score=0.1)  # Try to force low score
        assert score >= 0.5

    def test_score_clamped_to_maximum(self):
        """Score never exceeds 1.0."""
        now = datetime.now(timezone.utc)
        score = calculate_priority_score(
            upvotes=1000,
            comments=500,
            title="How AI is Changing Technology in 2025",
            url="https://example.com/article",
            collected_at=now,
            now=now,
            base_score=0.9,
        )
        assert score == 1.0

    def test_custom_base_score(self):
        """Custom base score is respected."""
        score = calculate_priority_score(base_score=0.7)
        assert score == 0.7

    def test_negative_upvotes_raises_error(self):
        """Negative upvotes raises ValueError."""
        with pytest.raises(ValueError):
            calculate_priority_score(upvotes=-1)


class TestCalculatePriorityScoreFromDict:
    """Test priority score calculation from dictionary."""

    def test_empty_dict(self):
        """Empty dict returns base score (0.5 fallback)."""
        score = calculate_priority_score_from_dict({})
        assert 0.5 <= score <= 1.0

    def test_reddit_format(self):
        """Reddit-style data structure works."""
        item = {
            "score": 50,
            "num_comments": 20,
            "title": "How AI Works",
            "url": "https://reddit.com/r/technology/123",
        }
        score = calculate_priority_score_from_dict(item)
        assert 0.5 < score <= 1.0

    def test_collected_format(self):
        """Collected data format works."""
        item = {
            "upvotes": 50,
            "comments": 20,
            "title": "How AI Works",
            "permalink": "https://example.com/article",
            "collected_at": "2025-10-08T10:00:00Z",
        }
        score = calculate_priority_score_from_dict(item)
        assert 0.5 <= score <= 1.0

    def test_unix_timestamp(self):
        """Unix timestamp is handled correctly."""
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        item = {"upvotes": 50, "title": "Test", "created_utc": one_hour_ago.timestamp()}
        score = calculate_priority_score_from_dict(item)
        assert 0.5 < score <= 1.0

    def test_multiple_key_variants(self):
        """Different key names produce same result."""
        item1 = {"score": 50, "num_comments": 20}
        item2 = {"upvotes": 50, "comments": 20}
        item3 = {"ups": 50, "comment_count": 20}

        score1 = calculate_priority_score_from_dict(item1)
        score2 = calculate_priority_score_from_dict(item2)
        score3 = calculate_priority_score_from_dict(item3)

        assert score1 == score2 == score3

    def test_invalid_timestamp_ignored(self):
        """Invalid timestamp doesn't crash, skips freshness bonus."""
        item = {"upvotes": 50, "title": "Test", "collected_at": "invalid-date"}
        score = calculate_priority_score_from_dict(item)
        assert 0.5 <= score <= 1.0

    def test_missing_fields_use_defaults(self):
        """Missing fields use default values (0, empty string)."""
        item = {"title": "Minimal Article"}
        score = calculate_priority_score_from_dict(item)
        assert 0.5 <= score <= 1.0


class TestPurityAndDeterminism:
    """Test that functions are pure (deterministic, no side effects)."""

    def test_engagement_determinism(self):
        """Same inputs always produce same output."""
        score1 = calculate_engagement_score(50, 25)
        score2 = calculate_engagement_score(50, 25)
        assert score1 == score2

    def test_title_quality_determinism(self):
        """Same title always produces same score."""
        title = "How AI is Changing Technology"
        score1 = calculate_title_quality_score(title)
        score2 = calculate_title_quality_score(title)
        assert score1 == score2

    def test_url_quality_determinism(self):
        """Same URL always produces same score."""
        url = "https://example.com/article"
        score1 = calculate_url_quality_score(url)
        score2 = calculate_url_quality_score(url)
        assert score1 == score2

    def test_priority_score_determinism(self):
        """Same inputs always produce same priority score."""
        now = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        recent = datetime(2025, 10, 8, 11, 0, 0, tzinfo=timezone.utc)

        score1 = calculate_priority_score(
            upvotes=50,
            comments=25,
            title="How AI Works",
            url="https://example.com",
            collected_at=recent,
            now=now,
        )
        score2 = calculate_priority_score(
            upvotes=50,
            comments=25,
            title="How AI Works",
            url="https://example.com",
            collected_at=recent,
            now=now,
        )
        assert score1 == score2

    def test_dict_determinism(self):
        """Same dict always produces same score."""
        item = {"upvotes": 50, "comments": 25, "title": "Test"}
        score1 = calculate_priority_score_from_dict(item)
        score2 = calculate_priority_score_from_dict(item)
        assert score1 == score2

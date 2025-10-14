"""
Tests for timestamp utility functions.

Tests UTC timestamp generation and ISO 8601 formatting.
"""

from datetime import datetime, timezone

import pytest
from freezegun import freeze_time  # type: ignore[import-untyped]
from utils.timestamp_utils import get_utc_timestamp, get_utc_timestamp_str


class TestGetUtcTimestamp:
    """Test get_utc_timestamp() function."""

    def test_returns_datetime_object(self):
        """Test that function returns a datetime object."""
        result = get_utc_timestamp()
        assert isinstance(result, datetime)

    def test_uses_utc_timezone(self):
        """Test that returned datetime uses UTC timezone."""
        result = get_utc_timestamp()
        assert result.tzinfo == timezone.utc

    def test_returns_current_time(self):
        """Test that returned time is approximately current."""
        before = datetime.now(timezone.utc)
        result = get_utc_timestamp()
        after = datetime.now(timezone.utc)

        # Result should be between before and after (within milliseconds)
        assert before <= result <= after

    @freeze_time("2025-10-15 14:30:00")
    def test_frozen_time(self):
        """Test with frozen time for deterministic testing."""
        result = get_utc_timestamp()
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 15
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 0

    def test_multiple_calls_return_different_times(self):
        """Test that consecutive calls return different timestamps."""
        import time

        ts1 = get_utc_timestamp()
        time.sleep(0.01)  # Sleep 10ms
        ts2 = get_utc_timestamp()

        assert ts2 > ts1


class TestGetUtcTimestampStr:
    """Test get_utc_timestamp_str() function."""

    def test_returns_string(self):
        """Test that function returns a string."""
        result = get_utc_timestamp_str()
        assert isinstance(result, str)

    def test_iso_8601_format(self):
        """Test that string is in ISO 8601 format."""
        result = get_utc_timestamp_str()

        # ISO 8601 should contain 'T' separator and timezone info
        assert "T" in result
        assert "+" in result or "Z" in result

    def test_can_parse_back_to_datetime(self):
        """Test that returned string can be parsed back to datetime."""
        result = get_utc_timestamp_str()
        parsed = datetime.fromisoformat(result)

        assert isinstance(parsed, datetime)
        assert parsed.tzinfo is not None

    @freeze_time("2025-10-15 14:30:45")
    def test_frozen_time_format(self):
        """Test exact format with frozen time."""
        result = get_utc_timestamp_str()

        # Should contain date and time components
        assert "2025-10-15" in result
        assert "14:30:45" in result

    def test_consistent_with_get_utc_timestamp(self):
        """Test that string version matches datetime version."""
        dt = get_utc_timestamp()
        dt_str = get_utc_timestamp_str()

        # Parse the string and compare (within 1 second due to timing)
        parsed = datetime.fromisoformat(dt_str)
        diff = abs((parsed - dt).total_seconds())
        assert diff < 1.0

    def test_multiple_calls_return_different_strings(self):
        """Test that consecutive calls return different timestamp strings."""
        import time

        ts1 = get_utc_timestamp_str()
        time.sleep(0.01)  # Sleep 10ms
        ts2 = get_utc_timestamp_str()

        assert ts1 != ts2


class TestTimestampConsistency:
    """Test consistency between timestamp functions."""

    def test_both_functions_use_same_time(self):
        """Test that both functions return the same moment in time."""
        # Get both within a tight loop
        dt = get_utc_timestamp()
        str_val = get_utc_timestamp_str()

        # Parse string back to datetime
        parsed = datetime.fromisoformat(str_val)

        # Should be within 1 second of each other
        diff = abs((parsed - dt).total_seconds())
        assert diff < 1.0

    @freeze_time("2025-10-15 14:30:45.123456")
    def test_microsecond_precision(self):
        """Test that timestamps preserve microsecond precision."""
        dt = get_utc_timestamp()
        assert dt.microsecond == 123456

    @freeze_time("2025-12-31 23:59:59")
    def test_end_of_year(self):
        """Test timestamp generation at end of year."""
        result = get_utc_timestamp()
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 31

    @freeze_time("2025-01-01 00:00:00")
    def test_start_of_year(self):
        """Test timestamp generation at start of year."""
        result = get_utc_timestamp()
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 1

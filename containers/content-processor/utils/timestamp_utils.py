"""
Timestamp utility functions.

Provides standardized UTC timestamp generation for consistent
datetime handling across the application.

All timestamps use UTC timezone and ISO 8601 format.
"""

from datetime import datetime, timezone


def get_utc_timestamp() -> datetime:
    """
    Get current UTC timestamp.

    Returns:
        datetime: Current timestamp in UTC timezone

    Example:
        >>> ts = get_utc_timestamp()
        >>> ts.tzinfo == timezone.utc
        True
    """
    return datetime.now(timezone.utc)


def get_utc_timestamp_str() -> str:
    """
    Get current UTC timestamp as ISO 8601 string.

    Returns:
        str: Current timestamp in ISO 8601 format (e.g., "2025-10-15T10:30:00+00:00")

    Example:
        >>> ts_str = get_utc_timestamp_str()
        >>> "T" in ts_str and "+" in ts_str
        True
    """
    return get_utc_timestamp().isoformat()

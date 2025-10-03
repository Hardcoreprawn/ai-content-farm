"""
Test functional datetime serialization.

This validates the pure function approach to datetime handling
vs the OOP JSON encoder class approach.
"""

import json
from datetime import datetime, timezone

import pytest

from libs.simplified_blob_client import serialize_datetime


class TestDatetimeSerialization:
    """Test suite for functional datetime serialization."""

    def test_serialize_single_datetime(self):
        """Pure function should convert single datetime to ISO string."""
        dt = datetime(2025, 10, 3, 12, 30, 45, tzinfo=timezone.utc)
        result = serialize_datetime(dt)
        assert result == "2025-10-03T12:30:45+00:00"
        assert isinstance(result, str)

    def test_serialize_dict_with_datetime(self):
        """Should recursively convert datetime in dict values."""
        data = {
            "created_at": datetime(2025, 10, 3, 12, 0, tzinfo=timezone.utc),
            "title": "Test Article",
            "priority": 0.85,
        }
        result = serialize_datetime(data)

        assert result["created_at"] == "2025-10-03T12:00:00+00:00"
        assert result["title"] == "Test Article"
        assert result["priority"] == 0.85

    def test_serialize_nested_dict(self):
        """Should handle deeply nested dicts with datetime objects."""
        data = {
            "metadata": {
                "timestamps": {
                    "created": datetime(2025, 10, 3, 10, 0, tzinfo=timezone.utc),
                    "modified": datetime(2025, 10, 3, 11, 0, tzinfo=timezone.utc),
                }
            },
            "title": "Article",
        }
        result = serialize_datetime(data)

        assert (
            result["metadata"]["timestamps"]["created"] == "2025-10-03T10:00:00+00:00"
        )
        assert (
            result["metadata"]["timestamps"]["modified"] == "2025-10-03T11:00:00+00:00"
        )
        assert result["title"] == "Article"

    def test_serialize_list_with_datetime(self):
        """Should convert datetime objects in lists."""
        data = [
            datetime(2025, 10, 3, 10, 0, tzinfo=timezone.utc),
            "text",
            42,
            datetime(2025, 10, 3, 11, 0, tzinfo=timezone.utc),
        ]
        result = serialize_datetime(data)

        assert result[0] == "2025-10-03T10:00:00+00:00"
        assert result[1] == "text"
        assert result[2] == 42
        assert result[3] == "2025-10-03T11:00:00+00:00"

    def test_serialize_complex_nested_structure(self):
        """Should handle complex real-world data structures."""
        # This mimics the actual article structure that was failing
        data = {
            "topic_id": "rss_123456",
            "title": "Test Article",
            "metadata": {
                "collected_at": datetime(2025, 10, 3, 10, 0, tzinfo=timezone.utc),
                "processed_at": datetime(2025, 10, 3, 11, 0, tzinfo=timezone.utc),
            },
            "provenance": [
                {
                    "step": "collection",
                    "timestamp": datetime(2025, 10, 3, 10, 0, tzinfo=timezone.utc),
                    "source": "rss",
                },
                {
                    "step": "processing",
                    "timestamp": datetime(2025, 10, 3, 11, 0, tzinfo=timezone.utc),
                    "ai_model": "gpt-35-turbo",
                },
            ],
            "quality_score": 0.85,
        }

        result = serialize_datetime(data)

        # Check all datetime fields were converted
        assert result["metadata"]["collected_at"] == "2025-10-03T10:00:00+00:00"
        assert result["metadata"]["processed_at"] == "2025-10-03T11:00:00+00:00"
        assert result["provenance"][0]["timestamp"] == "2025-10-03T10:00:00+00:00"
        assert result["provenance"][1]["timestamp"] == "2025-10-03T11:00:00+00:00"

        # Check other fields unchanged
        assert result["topic_id"] == "rss_123456"
        assert result["title"] == "Test Article"
        assert result["quality_score"] == 0.85
        assert result["provenance"][0]["step"] == "collection"

    def test_serialize_primitives_pass_through(self):
        """Primitive types should pass through unchanged."""
        assert serialize_datetime(42) == 42
        assert serialize_datetime(3.14) == 3.14
        assert serialize_datetime("text") == "text"
        assert serialize_datetime(True) is True
        assert serialize_datetime(None) is None

    def test_serialize_empty_structures(self):
        """Empty collections should work correctly."""
        assert serialize_datetime({}) == {}
        assert serialize_datetime([]) == []
        assert serialize_datetime(()) == []  # tuple → list in output

    def test_json_serialization_after_transform(self):
        """Verify result is JSON serializable after transformation."""
        data = {
            "created_at": datetime(2025, 10, 3, 12, 0, tzinfo=timezone.utc),
            "title": "Test",
            "items": [
                {"timestamp": datetime(2025, 10, 3, 13, 0, tzinfo=timezone.utc)},
                {"timestamp": datetime(2025, 10, 3, 14, 0, tzinfo=timezone.utc)},
            ],
        }

        # This should NOT raise "Object of type datetime is not JSON serializable"
        result = serialize_datetime(data)
        json_str = json.dumps(result)

        # Verify it can be parsed back
        parsed = json.loads(json_str)
        assert parsed["created_at"] == "2025-10-03T12:00:00+00:00"
        assert parsed["items"][0]["timestamp"] == "2025-10-03T13:00:00+00:00"

    def test_tuple_converted_to_list(self):
        """Tuples should be converted to lists (JSON has no tuple type)."""
        data = (datetime(2025, 10, 3, 12, 0, tzinfo=timezone.utc), "text", 42)
        result = serialize_datetime(data)

        assert isinstance(result, list)
        assert result[0] == "2025-10-03T12:00:00+00:00"
        assert result[1] == "text"
        assert result[2] == 42

    def test_immutability(self):
        """Pure function should not modify input data."""
        original = {
            "created_at": datetime(2025, 10, 3, 12, 0, tzinfo=timezone.utc),
            "title": "Test",
        }
        original_dt = original["created_at"]

        result = serialize_datetime(original)

        # Original should be unchanged
        assert original["created_at"] is original_dt
        assert isinstance(original["created_at"], datetime)

        # Result should be different
        assert isinstance(result["created_at"], str)


class TestFunctionalVsOOP:
    """Compare functional approach vs OOP JSON encoder approach."""

    def test_functional_approach_is_composable(self):
        """Functional approach can be composed with other transformations."""
        data = {
            "timestamp": datetime(2025, 10, 3, 12, 0, tzinfo=timezone.utc),
            "value": 42,
        }

        # Can compose transformations in a pipeline
        step1 = serialize_datetime(data)  # Convert datetime
        step2 = {
            k: v.upper() if isinstance(v, str) else v for k, v in step1.items()
        }  # Uppercase strings

        # Clean, functional pipeline
        assert step2["timestamp"] == "2025-10-03T12:00:00+00:00"

    def test_functional_approach_is_testable(self):
        """Pure functions are easier to test (no setup, no mocking)."""
        # No need to:
        # - Instantiate a class
        # - Mock json.JSONEncoder
        # - Set up state

        # Just call function and assert
        result = serialize_datetime(
            {"dt": datetime(2025, 10, 3, 12, 0, tzinfo=timezone.utc)}
        )
        assert result["dt"] == "2025-10-03T12:00:00+00:00"

    def test_functional_approach_is_explicit(self):
        """Transformation is explicit in the code, not hidden in encoder."""
        data = {"timestamp": datetime(2025, 10, 3, 12, 0, tzinfo=timezone.utc)}

        # OOP approach (hidden transformation):
        # json.dumps(data, cls=DateTimeEncoder)  # What's happening? Not obvious

        # Functional approach (explicit transformation):
        serializable = serialize_datetime(data)  # Clear: datetime → ISO string
        json_str = json.dumps(serializable)  # Clear: dict → JSON

        # More readable, easier to debug
        assert "2025-10-03" in json_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

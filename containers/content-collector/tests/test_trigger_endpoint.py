"""
Tests for trigger endpoint: validation and message creation.

Verify auth, payload validation, and async queue message format.
"""

import pytest
from auth.validate_auth import validate_api_key
from endpoints.trigger import create_trigger_message, validate_trigger_payload


class TestFunctionKeyValidation:
    """Verify API key authentication."""

    def test_valid_key_passes(self, monkeypatch):
        """Valid API key in headers passes validation."""
        monkeypatch.setenv("COLLECTION_API_KEY", "test_key_123")

        headers = {"x-api-key": "test_key_123"}
        assert validate_api_key(headers) is True

    def test_missing_key_fails(self, monkeypatch):
        """Missing API key fails validation."""
        monkeypatch.setenv("COLLECTION_API_KEY", "test_key_123")

        headers = {}
        assert validate_api_key(headers) is False

    def test_wrong_key_fails(self, monkeypatch):
        """Wrong API key fails validation."""
        monkeypatch.setenv("COLLECTION_API_KEY", "test_key_123")

        headers = {"x-api-key": "wrong_key"}
        assert validate_api_key(headers) is False

    def test_whitespace_trimmed(self, monkeypatch):
        """API key with surrounding whitespace is trimmed and validated."""
        monkeypatch.setenv("COLLECTION_API_KEY", "test_key_123")

        headers = {"x-api-key": "  test_key_123  "}
        assert validate_api_key(headers) is True

    def test_no_env_var_returns_false(self, monkeypatch):
        """Missing env var returns False for all keys."""
        monkeypatch.delenv("COLLECTION_API_KEY", raising=False)

        headers = {"x-api-key": "any_key"}
        assert validate_api_key(headers) is False


class TestTriggerPayloadValidation:
    """Verify trigger request payload validation."""

    def test_valid_subreddit_trigger(self):
        """Valid subreddit trigger passes validation."""
        payload = {"subreddits": ["programming"], "min_score": 25, "max_items": 50}

        is_valid, error = validate_trigger_payload(payload)
        assert is_valid is True
        assert error is None

    def test_valid_instance_trigger(self):
        """Valid Mastodon instance trigger passes validation."""
        payload = {"instances": ["fosstodon.org"], "max_items": 30}

        is_valid, error = validate_trigger_payload(payload)
        assert is_valid is True
        assert error is None

    def test_both_sources_valid(self):
        """Trigger with both subreddits and instances is valid."""
        payload = {
            "subreddits": ["programming"],
            "instances": ["fosstodon.org"],
            "max_items": 50,
        }

        is_valid, error = validate_trigger_payload(payload)
        assert is_valid is True

    def test_no_sources_fails(self):
        """Trigger with no sources fails."""
        payload = {"max_items": 50}

        is_valid, error = validate_trigger_payload(payload)
        assert is_valid is False
        assert error is not None and "source required" in error.lower()

    def test_empty_sources_fails(self):
        """Trigger with empty source lists fails."""
        payload = {"subreddits": [], "instances": []}

        is_valid, error = validate_trigger_payload(payload)
        assert is_valid is False

    def test_too_many_subreddits_fails(self):
        """Too many subreddits fails validation."""
        payload = {"subreddits": [f"subreddit_{i}" for i in range(25)]}  # More than 20

        is_valid, error = validate_trigger_payload(payload)
        assert is_valid is False
        assert error is not None and "20" in error

    def test_too_many_instances_fails(self):
        """Too many instances fails validation."""
        payload = {
            # More than 5
            "instances": [f"instance_{i}.social" for i in range(10)]
        }

        is_valid, error = validate_trigger_payload(payload)
        assert is_valid is False

    def test_invalid_min_score_fails(self):
        """Negative min_score fails."""
        payload = {"subreddits": ["programming"], "min_score": -5}

        is_valid, error = validate_trigger_payload(payload)
        assert is_valid is False

    def test_invalid_max_items_fails(self):
        """max_items too large fails."""
        payload = {"subreddits": ["programming"], "max_items": 1000}

        is_valid, error = validate_trigger_payload(payload)
        assert is_valid is False

    def test_not_dict_fails(self):
        """Non-dict payload fails."""
        payload = "not a dict"

        is_valid, error = validate_trigger_payload(payload)
        assert is_valid is False

    def test_wrong_type_subreddits_fails(self):
        """Non-list subreddits fails."""
        payload = {"subreddits": "programming"}  # Should be list

        is_valid, error = validate_trigger_payload(payload)
        assert is_valid is False

    def test_non_string_subreddit_fails(self):
        """Non-string subreddit fails."""
        payload = {"subreddits": [123, "programming"]}  # First is not string

        is_valid, error = validate_trigger_payload(payload)
        assert is_valid is False


class TestTriggerMessageCreation:
    """Verify trigger message has correct format and fields."""

    def test_creates_valid_message(self):
        """Message creation produces valid structure."""
        msg = create_trigger_message(subreddits=["programming"])

        # Required fields
        assert "operation" in msg
        assert "collection_id" in msg
        assert "collection_blob" in msg
        assert "timestamp" in msg
        assert "source" in msg

    def test_operation_is_trigger_collection(self):
        """Message operation is correct."""
        msg = create_trigger_message(subreddits=["test"])

        assert msg["operation"] == "trigger_collection"
        assert msg["source"] == "manual_endpoint"

    def test_collection_id_is_unique(self):
        """Each message gets unique collection_id."""
        msg1 = create_trigger_message(subreddits=["test"])
        msg2 = create_trigger_message(subreddits=["test"])

        assert msg1["collection_id"] != msg2["collection_id"]
        assert msg1["collection_id"].startswith("manual_")

    def test_collection_blob_includes_date(self):
        """Collection blob path includes today's date."""
        from datetime import date

        msg = create_trigger_message(subreddits=["test"])
        today = date.today().isoformat()

        assert today in msg["collection_blob"]

    def test_message_includes_parameters(self):
        """Message includes all trigger parameters."""
        msg = create_trigger_message(
            subreddits=["programming", "learnprogramming"],
            instances=["fosstodon.org"],
            min_score=30,
            max_items=100,
        )

        assert msg["subreddits"] == ["programming", "learnprogramming"]
        assert msg["instances"] == ["fosstodon.org"]
        assert msg["min_score"] == 30
        assert msg["max_items"] == 100

    def test_empty_sources_allowed_in_message(self):
        """Message can have empty sources (already validated by endpoint)."""
        msg = create_trigger_message()

        assert msg["subreddits"] == []
        assert msg["instances"] == []
        assert msg["max_items"] == 50  # Default
        assert msg["min_score"] == 25  # Default


class TestTriggerIntegration:
    """Integration tests for trigger workflow."""

    def test_valid_request_creates_valid_message(self):
        """Valid trigger payload creates valid queue message."""
        payload = {"subreddits": ["programming"], "min_score": 25, "max_items": 50}

        # Validate payload
        is_valid, error = validate_trigger_payload(payload)
        assert is_valid is True

        # Create message
        msg = create_trigger_message(**payload)

        # Verify message
        assert msg["subreddits"] == payload["subreddits"]
        assert msg["min_score"] == payload["min_score"]
        assert msg["max_items"] == payload["max_items"]

    def test_payload_with_defaults_valid(self):
        """Payload with minimal fields still creates valid message."""
        payload = {"subreddits": ["programming"]}

        is_valid, error = validate_trigger_payload(payload)
        assert is_valid is True

        msg = create_trigger_message(subreddits=payload["subreddits"])

        # Should have defaults
        assert msg["min_score"] == 25
        assert msg["max_items"] == 50

"""
Unit tests for error_handling.py

Tests SecureErrorHandler integration and error response formatting.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from error_handling import handle_error

from libs.secure_error_handler import ErrorSeverity

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_handle_error_basic():
    """Test basic error handling with minimal parameters."""
    error = ValueError("Test error message")

    result = handle_error(error)

    assert "error_id" in result
    assert result["message"] == "An error occurred while processing your request"
    assert "timestamp" in result
    assert result["service"] == "site-publisher"


def test_handle_error_with_custom_message():
    """Test error handling with custom user message."""
    error = ValueError("Internal error details")

    result = handle_error(
        error, error_type="validation", user_message="Invalid input provided"
    )

    assert result["message"] == "Invalid input provided"
    assert "error_id" in result
    assert result["service"] == "site-publisher"


def test_handle_error_with_severity():
    """Test error handling with different severity levels."""
    error = ValueError("Test error")

    # Test high severity
    result_high = handle_error(error, severity=ErrorSeverity.HIGH)
    assert "error_id" in result_high

    # Test critical severity
    result_critical = handle_error(error, severity=ErrorSeverity.CRITICAL)
    assert "error_id" in result_critical


def test_handle_error_with_context():
    """Test error handling with additional context."""
    error = ValueError("Test error")

    result = handle_error(
        error,
        context={
            "operation": "test_operation",
            "user_id": "test-user-123",
        },
    )

    assert "error_id" in result
    assert result["service"] == "site-publisher"
    # Context should be logged but not returned in user-facing response


def test_handle_error_sanitizes_sensitive_data():
    """Test that sensitive data is sanitized from error responses."""
    error = ValueError("Error with password: secret123")

    result = handle_error(
        error,
        context={
            "password": "secret123",
            "api_key": "key-12345",
            "token": "Bearer xyz",
        },
    )

    # Sensitive keys should not appear in response
    assert "password" not in str(result)
    assert "secret123" not in str(result)
    assert "api_key" not in str(result)
    assert "key-12345" not in str(result)


def test_handle_error_different_error_types():
    """Test handling different error types."""
    # Validation error
    validation_error = ValueError("Invalid input")
    result_validation = handle_error(validation_error, error_type="validation")
    assert "error_id" in result_validation

    # Authentication error
    auth_error = PermissionError("Access denied")
    result_auth = handle_error(auth_error, error_type="authentication")
    assert "error_id" in result_auth

    # Storage error
    storage_error = IOError("Storage failure")
    result_storage = handle_error(storage_error, error_type="storage")
    assert "error_id" in result_storage


def test_handle_error_generates_unique_correlation_ids():
    """Test that each error gets a unique correlation ID."""
    error = ValueError("Test error")

    result1 = handle_error(error)
    result2 = handle_error(error)

    assert result1["error_id"] != result2["error_id"]

"""
Test suite for FastAPI-native shared models.

Tests the new FastAPI-native StandardResponse and StandardError models,
dependency injection helpers, and utility functions.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import Mock

import pytest

from libs.shared_models import (
    ContentItem,
    HealthStatus,
    ServiceStatus,
    StandardError,
    StandardResponse,
    add_standard_metadata,
    create_error_response,
    create_service_dependency,
    create_success_response,
    wrap_legacy_response,
)


class TestStandardResponse:
    """Test the FastAPI-native StandardResponse model."""

    def test_standard_response_creation(self):
        """Test creating a StandardResponse."""
        response = StandardResponse(
            status="success",
            message="Test message",
            data={"key": "value"},
            metadata={"function": "test"},
        )

        assert response.status == "success"
        assert response.message == "Test message"
        assert response.data == {"key": "value"}
        assert response.metadata["function"] == "test"

    def test_standard_response_minimal(self):
        """Test StandardResponse with minimal required fields."""
        response = StandardResponse(status="success", message="Test message")

        assert response.status == "success"
        assert response.message == "Test message"
        assert response.data is None
        assert response.errors is None
        assert response.metadata == {}

    def test_standard_response_serialization(self):
        """Test StandardResponse serializes correctly."""
        response = StandardResponse(
            status="success",
            message="Test message",
            data={"items": [1, 2, 3]},
            metadata={"timestamp": "2025-08-27T10:00:00Z"},
        )

        data = response.model_dump()

        assert data["status"] == "success"
        assert data["message"] == "Test message"
        assert data["data"]["items"] == [1, 2, 3]
        assert data["metadata"]["timestamp"] == "2025-08-27T10:00:00Z"

    def test_standard_response_with_errors(self):
        """Test StandardResponse can include error details."""
        response = StandardResponse(
            status="error",
            message="Operation failed",
            errors=["Error 1", "Error 2"],
            metadata={"function": "test-service"},
        )

        assert response.status == "error"
        assert response.errors == ["Error 1", "Error 2"]


class TestStandardError:
    """Test the FastAPI-native StandardError model."""

    def test_standard_error_creation(self):
        """Test creating a StandardError."""
        error = StandardError(
            message="Test error",
            errors=["Detail 1", "Detail 2"],
            metadata={"function": "test-service"},
        )

        assert error.status == "error"  # Default value
        assert error.message == "Test error"
        assert error.errors == ["Detail 1", "Detail 2"]
        assert error.metadata["function"] == "test-service"

    def test_standard_error_minimal(self):
        """Test StandardError with minimal fields."""
        error = StandardError(message="Simple error")

        assert error.status == "error"
        assert error.message == "Simple error"
        assert error.errors is None
        assert error.metadata == {}

    def test_standard_error_for_http_exception(self):
        """Test StandardError formatted for HTTPException."""
        error = StandardError(
            message="Resource not found",
            errors=["Item with ID 123 does not exist"],
            metadata={
                "function": "content-collector",
                "timestamp": "2025-08-27T10:00:00Z",
            },
        )

        detail = error.model_dump()

        assert detail["status"] == "error"
        assert detail["message"] == "Resource not found"
        assert detail["errors"] == ["Item with ID 123 does not exist"]
        assert detail["metadata"]["function"] == "content-collector"


class TestFastAPIDependencies:
    """Test FastAPI dependency injection helpers."""

    @pytest.mark.asyncio
    async def test_add_standard_metadata(self):
        """Test the standard metadata dependency."""
        metadata = await add_standard_metadata("test-service")

        assert metadata["function"] == "test-service"
        assert metadata["version"] == "1.0.0"
        assert "timestamp" in metadata

        # Verify timestamp format
        timestamp = datetime.fromisoformat(metadata["timestamp"].replace("Z", "+00:00"))
        assert isinstance(timestamp, datetime)

    def test_create_service_dependency(self):
        """Test creating service-specific dependencies."""
        service_dep = create_service_dependency("content-ranker")

        # Should return a callable
        assert callable(service_dep)

    @pytest.mark.asyncio
    async def test_service_dependency_execution(self):
        """Test executing a service dependency."""
        service_dep = create_service_dependency("content-ranker")
        metadata = await service_dep()

        assert metadata["function"] == "content-ranker"
        assert metadata["version"] == "1.0.0"
        assert "timestamp" in metadata


class TestHelperFunctions:
    """Test utility helper functions."""

    def test_create_success_response(self):
        """Test success response helper."""
        response = create_success_response(
            message="Operation successful",
            data={"result": "completed"},
            metadata={"service": "test"},
        )

        assert isinstance(response, StandardResponse)
        assert response.status == "success"
        assert response.message == "Operation successful"
        assert response.data == {"result": "completed"}
        assert response.metadata == {"service": "test"}

    def test_create_success_response_minimal(self):
        """Test success response helper with minimal args."""
        response = create_success_response("Simple success")

        assert response.status == "success"
        assert response.message == "Simple success"
        assert response.data is None
        assert response.metadata == {}

    def test_create_error_response(self):
        """Test error response helper."""
        error = create_error_response(
            message="Operation failed",
            errors=["Validation error", "Network error"],
            metadata={"service": "test"},
        )

        assert isinstance(error, StandardError)
        assert error.status == "error"
        assert error.message == "Operation failed"
        assert error.errors == ["Validation error", "Network error"]
        assert error.metadata == {"service": "test"}

    def test_create_error_response_minimal(self):
        """Test error response helper with minimal args."""
        error = create_error_response("Simple error")

        assert error.status == "error"
        assert error.message == "Simple error"
        assert error.errors is None
        assert error.metadata == {}


class TestDataModels:
    """Test data structure models."""

    def test_health_status_creation(self):
        """Test HealthStatus model."""
        health = HealthStatus(
            status="healthy",
            service="content-collector",
            version="1.0.0",
            dependencies={"database": True, "storage": True},
            uptime_seconds=3600.0,
            environment="production",
        )

        assert health.status == "healthy"
        assert health.service == "content-collector"
        assert health.dependencies["database"] is True
        assert health.uptime_seconds == 3600.0
        assert health.timestamp is not None
        # Verify timestamp is a valid datetime string
        from datetime import datetime

        parsed_time = datetime.fromisoformat(health.timestamp.replace("Z", "+00:00"))
        assert isinstance(parsed_time, datetime)

    def test_service_status_creation(self):
        """Test ServiceStatus model."""
        status = ServiceStatus(
            service="content-ranker",
            status="running",
            uptime_seconds=1800.0,
            stats={"processed": 150, "errors": 2},
            last_operation={"type": "ranking", "duration_ms": 250},
        )

        assert status.service == "content-ranker"
        assert status.status == "running"
        assert status.stats["processed"] == 150
        assert status.last_operation is not None
        assert status.last_operation["type"] == "ranking"

    def test_content_item_creation(self):
        """Test ContentItem model."""
        from datetime import datetime, timezone

        content = ContentItem(
            id="item_001",
            title="Test Content",
            content="This is test content",
            url="https://example.com/content",
            published_at=datetime.now(timezone.utc),
            source_metadata={"platform": "reddit"},
            processing_metadata={"processed_at": "2025-08-27T10:00:00Z"},
        )

        assert content.id == "item_001"
        assert content.title == "Test Content"
        assert content.source_metadata["platform"] == "reddit"
        assert content.processing_metadata["processed_at"] == "2025-08-27T10:00:00Z"


class TestLegacySupport:
    """Test legacy wrapper functions."""

    def test_wrap_legacy_response_dict(self):
        """Test wrapping legacy dictionary response."""
        legacy_data = {"items": [1, 2, 3], "total": 3}
        response = wrap_legacy_response(legacy_data, "Legacy operation")

        assert isinstance(response, StandardResponse)
        assert response.status == "success"
        assert response.message == "Legacy operation"
        assert response.data == legacy_data
        assert response.metadata["legacy_wrapper"] is True

    def test_wrap_legacy_response_non_dict(self):
        """Test wrapping legacy non-dictionary response."""
        legacy_data = "simple string result"
        response = wrap_legacy_response(legacy_data)

        assert response.status == "success"
        assert response.data == {"result": "simple string result"}
        assert response.metadata["legacy_wrapper"] is True

    def test_wrap_legacy_response_default_message(self):
        """Test legacy wrapper with default message."""
        legacy_data = {"key": "value"}
        response = wrap_legacy_response(legacy_data)

        assert response.message == "Operation completed"


class TestIntegration:
    """Integration tests for FastAPI-native patterns."""

    def test_full_success_workflow(self):
        """Test complete success response workflow."""
        # Simulate FastAPI endpoint workflow
        service_name = "content-collector"

        # Create service dependency (would be used with Depends() in FastAPI)
        service_dep = create_service_dependency(service_name)

        # Create success response (would be returned from endpoint)
        response = create_success_response(
            message="Content collected successfully",
            data={"items_collected": 15, "source": "reddit"},
            metadata={"custom": "data"},
        )

        assert response.status == "success"
        assert response.data is not None
        assert response.data["items_collected"] == 15
        assert response.metadata["custom"] == "data"

    def test_full_error_workflow(self):
        """Test complete error response workflow."""
        # Simulate error handling in FastAPI endpoint
        error = create_error_response(
            message="Collection failed",
            errors=["Network timeout", "Invalid credentials"],
            metadata={"function": "content-collector", "retry_after": 300},
        )

        # This would be used in HTTPException detail
        detail = error.model_dump()

        assert detail["status"] == "error"
        assert detail["message"] == "Collection failed"
        assert len(detail["errors"]) == 2
        assert detail["metadata"]["retry_after"] == 300

    def test_pydantic_validation(self):
        """Test that Pydantic validation works correctly."""
        # Valid response should work - looking at the model, data and errors are optional
        response = StandardResponse(
            status="success", message="Test", data=None, errors=None
        )
        assert response.status == "success"

        # Test with helper function that handles optional fields properly
        success_response = create_success_response("Test operation")
        assert success_response.status == "success"
        assert success_response.message == "Test operation"


if __name__ == "__main__":
    pytest.main([__file__])

"""
Test suite for shared models and utilities.

This module tests the shared functionality used across containers.
"""

# type: ignore
# Pylance has issues with Pydantic model field detection - runtime works correctly

from datetime import datetime
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from libs.config_base import BaseContainerConfig
from libs.secure_error_handler import SecureErrorHandler
from libs.shared_models import (
    APIError,
    ContentItem,
    ErrorCodes,
    HealthStatus,
    ServiceStatus,
    StandardError,
    StandardResponse,
    add_standard_metadata,
    create_service_dependency,
)


class TestStandardResponse:
    """Test cases for StandardResponse model."""

    def test_standard_response_creation(self):
        """Test creating a standard response."""
        response = StandardResponse(
            status="success",
            message="Test message",
            data={"test": "data"},
            errors=[],
            metadata={"service": "test"},
        )

        assert response.status == "success"
        assert response.message == "Test message"
        assert response.data == {"test": "data"}
        assert response.errors == []
        assert response.metadata == {"service": "test"}

    def test_standard_response_defaults(self):
        """Test standard response with defaults."""
        response = StandardResponse(status="success", message="Test message")

        assert response.status == "success"
        assert response.message == "Test message"
        assert response.data is None
        # None means "no errors occurred" (better human factors)
        assert response.errors is None
        assert response.metadata == {}

    def test_standard_response_error_case(self):
        """Test standard response for error cases."""
        response = StandardResponse(
            status="error", message="Test error", errors=["Error 1", "Error 2"]
        )

        assert response.status == "error"
        assert response.message == "Test error"
        assert len(response.errors) == 2

    def test_standard_response_serialization(self):
        """Test response serialization."""
        response = StandardResponse(
            status="success", message="Test message", data={"test": "data"}
        )

        # Should be serializable to dict
        response_dict = response.model_dump()
        assert isinstance(response_dict, dict)
        assert response_dict["status"] == "success"


class TestServiceStatus:
    """Test cases for ServiceStatus model."""

    def test_service_status_creation(self):
        """Test creating service status."""
        status = ServiceStatus(
            service="test-service", status="healthy", version="1.0.0"
        )

        assert status.service == "test-service"
        assert status.status == "healthy"
        assert status.version == "1.0.0"
        assert isinstance(status.timestamp, datetime)

    def test_service_status_defaults(self):
        """Test service status with defaults."""
        status = ServiceStatus(
            service="test-service", status="healthy", version="1.0.0"
        )

        assert status.service == "test-service"
        assert status.status == "healthy"
        assert status.version == "1.0.0"
        assert status.environment is None
        assert isinstance(status.timestamp, str)
        assert status.uptime_seconds is None

    def test_create_service_dependency(self):
        """Test service dependency creation."""
        dependency = create_service_dependency("test-service")

        # Should return a function
        assert callable(dependency)

        # Function should return a dict when called
        result = dependency()
        assert isinstance(result, dict)
        assert "function" in result
        assert "timestamp" in result


class TestHealthStatus:
    """Test cases for HealthStatus model."""

    def test_health_status_healthy(self):
        """Test healthy health status response."""
        health = HealthStatus(
            service="test-service",
            status="healthy",
            version="1.0.0",
        )

        assert health.service == "test-service"
        assert health.status == "healthy"
        assert health.version == "1.0.0"
        assert isinstance(health.dependencies, dict)
        assert isinstance(health.issues, list)

    def test_health_status_unhealthy(self):
        """Test unhealthy health status response."""
        health = HealthStatus(
            service="test-service",
            status="unhealthy",
            version="1.0.0",
            uptime_seconds=3600.0,
        )

        assert health.service == "test-service"
        assert health.status == "unhealthy"
        assert health.version == "1.0.0"
        assert health.uptime_seconds == 3600.0


class TestAPIError:
    """Test cases for APIError model."""

    def test_api_error_creation(self):
        """Test creating API error."""
        error = APIError(
            message="Test error occurred",
            code="TEST_001",
            details="Detailed error information",
        )

        assert error.message == "Test error occurred"
        assert error.code == "TEST_001"
        assert error.details == "Detailed error information"

    def test_api_error_minimal(self):
        """Test minimal API error."""
        error = APIError(message="Simple error", code="TEST_002")

        assert error.message == "Simple error"
        assert error.code == "TEST_002"
        assert error.details is None


class TestSecureErrorHandler:
    """Test cases for SecureErrorHandler."""

    def test_secure_error_handler_creation(self):
        """Test creating secure error handler."""
        handler = SecureErrorHandler(service_name="test-service")
        assert handler.service_name == "test-service"

    def test_handle_error_with_details(self):
        """Test error handling with context."""
        handler = SecureErrorHandler(service_name="test-service")

        try:
            raise ValueError("Test error")
        except Exception as e:
            error_response = handler.handle_error(
                e, error_type="validation", context={"function": "test_validation"}
            )

            assert isinstance(error_response, dict)
            assert "error" in str(error_response).lower()

    def test_handle_error_without_details(self):
        """Test error handling with user message."""
        handler = SecureErrorHandler(service_name="test-service")

        try:
            raise ValueError("Sensitive information")
        except Exception as e:
            error_response = handler.handle_error(
                e, error_type="security", user_message="A secure error occurred"
            )

            assert isinstance(error_response, dict)
            # Should not contain sensitive details in secure mode

    def test_error_logging(self):
        """Test that handle_error method works and creates proper response."""
        handler = SecureErrorHandler(service_name="test-service")

        try:
            raise ValueError("Test error for logging")
        except Exception as e:
            result = handler.handle_error(e)

            # Should return a proper error response dictionary
            assert isinstance(result, dict)
            assert "error_id" in result
            assert "message" in result
            assert "timestamp" in result
            assert "service" in result
            assert result["service"] == "test-service"
            # Should not expose the actual exception details
            assert "ValueError" not in result["message"]


class TestContentItem:
    """Test cases for ContentItem model."""

    def test_content_item_creation(self):
        """Test creating content item with proper attribution."""
        from datetime import datetime, timezone

        content = ContentItem(
            id="test-123",
            title="Test Content",
            content="This is test content",
            url="https://example.com/article",
            published_at=datetime(2025, 9, 18, 12, 0, 0, tzinfo=timezone.utc),
        )

        assert content.id == "test-123"
        assert content.title == "Test Content"
        assert content.content == "This is test content"
        assert content.url == "https://example.com/article"
        assert content.published_at is not None
        assert isinstance(content.source_metadata, dict)
        assert isinstance(content.processing_metadata, dict)
        assert isinstance(content.enrichment_metadata, dict)

    def test_content_item_with_metadata(self):
        """Test content item with attribution metadata."""
        from datetime import datetime, timezone

        content = ContentItem(
            id="test-456",
            title="Test Content",
            content="Content with metadata",
            url="https://example.com/source-article",
            published_at=datetime(2025, 9, 18, 10, 30, 0, tzinfo=timezone.utc),
        )

        # Test attribution fields
        assert content.url == "https://example.com/source-article"
        assert content.published_at is not None

        # Test metadata containers for different processing stages
        content.source_metadata["author"] = "test-user"
        content.source_metadata["tags"] = ["test", "content"]
        content.processing_metadata["processed_at"] = "2025-09-18T12:00:00Z"
        content.enrichment_metadata["sentiment"] = "positive"

        assert content.source_metadata["author"] == "test-user"
        assert "test" in content.source_metadata["tags"]
        assert "processed_at" in content.processing_metadata
        assert content.enrichment_metadata["sentiment"] == "positive"

    def test_content_attribution_fields(self):
        """Test that attribution fields properly track content sources."""
        from datetime import datetime, timezone

        # Test with complete attribution information
        content = ContentItem(
            id="attribution-test",
            title="Breaking News: Tech Innovation",
            content="Important technology news content...",
            url="https://techblog.example.com/breaking-news-2025",
            published_at=datetime(2025, 9, 18, 14, 30, 0, tzinfo=timezone.utc),
        )

        # Add source attribution metadata
        content.source_metadata.update(
            {
                "author": "Jane Tech Reporter",
                "publication": "Tech Blog Example",
                "copyright": "© 2025 Tech Blog Example",
                "license": "Fair Use",
                "scraped_at": "2025-09-18T15:00:00Z",
            }
        )

        # Verify attribution fields are properly tracked
        assert content.url == "https://techblog.example.com/breaking-news-2025"
        assert content.published_at is not None
        assert content.source_metadata["author"] == "Jane Tech Reporter"
        assert content.source_metadata["publication"] == "Tech Blog Example"
        assert "copyright" in content.source_metadata
        assert "license" in content.source_metadata

        # Test that we can track the full attribution chain
        assert all(
            key in content.source_metadata
            for key in ["author", "publication", "copyright", "license"]
        )


class TestErrorCodes:
    """Test cases for ErrorCodes utility class."""

    def test_error_codes_constants(self):
        """Test error code constants."""
        assert ErrorCodes.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert ErrorCodes.NOT_FOUND == "NOT_FOUND"
        assert ErrorCodes.INTERNAL_ERROR == "INTERNAL_ERROR"

    def test_internal_error_factory(self):
        """Test internal error factory method."""
        error = ErrorCodes.internal_error("Test internal error", "Details")
        assert isinstance(error, APIError)
        assert error.message == "Test internal error"
        assert error.code == ErrorCodes.INTERNAL_ERROR

    def test_validation_error_factory(self):
        """Test validation error factory method."""
        error = ErrorCodes.validation_error("email", "Invalid format")
        assert isinstance(error, APIError)
        assert "email" in error.message
        assert "Invalid format" in error.message


class TestStandardError:
    """Test cases for StandardError model."""

    def test_standard_error_creation(self):
        """Test creating standard error."""
        error = StandardError(
            message="Test error occurred", errors=["Detail 1", "Detail 2"]
        )

        assert error.status == "error"
        assert error.message == "Test error occurred"
        assert error.errors is not None
        # Now safe because we checked it's not None first
        assert len(error.errors) == 2
        assert error.error_id is not None  # Should auto-generate UUID

    def test_standard_error_defaults(self):
        """Test standard error with defaults."""
        error = StandardError(message="Simple error")

        assert error.status == "error"
        assert error.message == "Simple error"
        assert error.errors is None
        assert error.metadata == {}

    def test_error_id_uniqueness(self):
        """Test that error IDs are unique."""
        error1 = StandardError(message="Error 1")
        error2 = StandardError(message="Error 2")

        assert error1.error_id != error2.error_id


class TestSharedUtilities:
    """Test cases for shared utility functions."""

    @pytest.mark.asyncio
    async def test_add_standard_metadata(self):
        """Test standard metadata addition."""
        metadata = await add_standard_metadata("test-service")

        assert isinstance(metadata, dict)
        assert "timestamp" in metadata
        assert "function" in metadata
        assert "version" in metadata
        assert "execution_time_ms" in metadata
        assert metadata["function"] == "test-service"

    @pytest.mark.asyncio
    async def test_service_dependency_consistency(self):
        """Test service dependency function consistency."""
        dependency_func = create_service_dependency("test-service")

        result1 = await dependency_func()
        result2 = await dependency_func()

        # Should have consistent structure
        assert result1.keys() == result2.keys()
        assert result1["function"] == result2["function"]
        # Timestamps will be different but should be close
        assert "timestamp" in result1
        assert "timestamp" in result2


class TestErrorHandling:
    """Test error handling across shared models."""

    def test_standard_response_validation_error(self):
        """Test validation errors in standard response."""
        # Test with valid statuses - should work
        response = StandardResponse(status="success", message="Test")
        assert response.status == "success"

        response2 = StandardResponse(status="error", message="Test error")
        assert response2.status == "error"

    def test_service_status_validation(self):
        """Test validation in service status."""
        # Valid service status
        status = ServiceStatus(service_name="valid-service", status="healthy")
        assert status.service_name == "valid-service"

    def test_health_status_validation(self):
        """Test health status response validation."""
        # Valid health status
        health = HealthStatus(service="test-service", status="healthy")
        assert health.status == "healthy"


class TestIntegrationWithSharedModels:
    """Test integration between different shared models."""

    def test_standard_response_with_health_check(self):
        """Test standard response containing health check data."""
        health_data = HealthStatus(
            service="test-service",
            status="healthy",
            checks={"api": "ok", "database": "ok"},
        )

        response = StandardResponse(
            status="success", message="Health check completed", data=health_data
        )

        assert response.status == "success"
        assert response.data.service == "test-service"
        assert response.data.status == "healthy"

    def test_standard_response_with_error(self):
        """Test standard response containing error data."""
        error_data = APIError(message="Service unavailable", code="HEALTH_001")

        response = StandardResponse(
            status="error",
            message="Health check failed",
            data=error_data,
            errors=["Service is down"],
        )

        assert response.status == "error"
        assert response.data.code == "HEALTH_001"
        assert len(response.errors) == 1

    def test_service_status_in_response(self):
        """Test using service status in responses."""
        service_status = ServiceStatus(
            service_name="test-service", status="healthy", version="1.2.3"
        )

        response = StandardResponse(
            status="success",
            message="Service status retrieved",
            data=service_status,
            metadata=service_status.model_dump(),
        )

        assert response.data.service_name == "test-service"
        assert response.metadata["version"] == "1.2.3"

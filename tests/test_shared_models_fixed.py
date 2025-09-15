"""
Fixed comprehensive tests for shared models based on actual model structures.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from libs.secure_error_handler import ErrorSeverity, SecureErrorHandler
from libs.shared_models import (
    APIError,
    ContentItem,
    ErrorCodes,
    HealthStatus,
    ServiceStatus,
    StandardError,
    StandardResponse,
    add_standard_metadata,
    create_error_response,
    create_service_dependency,
    create_success_response,
)


class TestStandardResponse:
    """Test cases for StandardResponse model."""

    def test_standard_response_creation(self):
        """Test creating standard response."""
        response = StandardResponse(
            status="success",
            message="Operation completed",
            data={"result": "test"},
            errors=None,
            metadata={"timestamp": "2024-01-01T00:00:00Z"},
        )

        assert response.status == "success"
        assert response.message == "Operation completed"
        assert response.data["result"] == "test"
        assert response.errors is None
        assert response.metadata["timestamp"] == "2024-01-01T00:00:00Z"

    def test_standard_response_defaults(self):
        """Test standard response with defaults."""
        response = StandardResponse(status="success", message="Test message")

        assert response.status == "success"
        assert response.message == "Test message"
        assert response.data is None
        assert response.errors is None  # Not empty list, it's None by default
        assert response.metadata == {}

    def test_standard_response_error_case(self):
        """Test standard response for error cases."""
        response = StandardResponse(
            status="error",
            message="Something went wrong",
            errors=["Validation failed", "Database error"],
        )

        assert response.status == "error"
        assert len(response.errors) == 2


class TestServiceStatus:
    """Test cases for ServiceStatus model."""

    def test_service_status_creation(self):
        """Test creating service status with required fields."""
        status = ServiceStatus(
            service="test-service",  # Uses 'service', not 'service_name'
            version="1.0.0",
            status="healthy",
        )

        assert status.service == "test-service"
        assert status.version == "1.0.0"
        assert status.status == "healthy"
        assert status.environment is None
        assert isinstance(status.timestamp, str)
        assert status.stats == {}
        assert status.dependencies == {}

    def test_service_status_with_optional_fields(self):
        """Test service status with optional fields."""
        status = ServiceStatus(
            service="test-service",
            version="1.0.0",
            status="healthy",
            environment="production",
            uptime_seconds=3600.5,
            stats={"requests": 100},
            dependencies={"database": True, "redis": False},
        )

        assert status.environment == "production"
        assert status.uptime_seconds == 3600.5
        assert status.stats["requests"] == 100
        assert status.dependencies["database"] is True
        assert status.dependencies["redis"] is False


class TestHealthStatus:
    """Test cases for HealthStatus model."""

    def test_health_status_healthy(self):
        """Test healthy health status response."""
        health = HealthStatus(
            service="test-service",
            version="1.0.0",  # Required field
            status="healthy",
            dependencies={"database": True, "storage": True},
        )

        assert health.service == "test-service"
        assert health.version == "1.0.0"
        assert health.status == "healthy"
        assert health.dependencies["database"] is True
        assert health.dependencies["storage"] is True
        assert health.issues == []

    def test_health_status_unhealthy(self):
        """Test unhealthy health status response."""
        health = HealthStatus(
            service="test-service",
            version="1.0.0",
            status="unhealthy",
            dependencies={"database": False},
            issues=["Database connection failed"],
            uptime_seconds=3600,
        )

        assert health.status == "unhealthy"
        assert health.dependencies["database"] is False
        assert "Database connection failed" in health.issues
        assert health.uptime_seconds == 3600


class TestContentItem:
    """Test cases for ContentItem model."""

    def test_content_item_creation(self):
        """Test creating content item."""
        content = ContentItem(
            id="test-123",
            title="Test Content",
            content="This is test content",
            url="https://example.com/content",
        )

        assert content.id == "test-123"
        assert content.title == "Test Content"
        assert content.content == "This is test content"
        assert content.url == "https://example.com/content"
        assert content.published_at is None
        assert content.source_metadata == {}
        assert content.processing_metadata == {}
        assert content.enrichment_metadata == {}

    def test_content_item_with_metadata(self):
        """Test content item with metadata."""
        content = ContentItem(
            id="test-456",
            title="Test Content",
            content="Content with metadata",
            source_metadata={"author": "test-user", "tags": ["test", "content"]},
            processing_metadata={"score": 0.85},
            enrichment_metadata={"sentiment": "positive"},
        )

        assert content.source_metadata["author"] == "test-user"
        assert "test" in content.source_metadata["tags"]
        assert content.processing_metadata["score"] == 0.85
        assert content.enrichment_metadata["sentiment"] == "positive"


class TestAPIError:
    """Test cases for APIError model."""

    def test_api_error_creation(self):
        """Test creating API error."""
        error = APIError(
            message="Validation failed",
            code="VALIDATION_001",
            details={"field": "email", "issue": "Invalid format"},
        )

        assert error.message == "Validation failed"
        assert error.code == "VALIDATION_001"
        assert error.details["field"] == "email"

    def test_api_error_minimal(self):
        """Test API error with minimal data."""
        error = APIError(message="Something went wrong")

        assert error.message == "Something went wrong"
        assert error.code == "INTERNAL_ERROR"  # Default value
        assert error.details is None


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
        assert len(error.errors) == 2
        assert error.error_id is not None  # Should auto-generate UUID

    def test_standard_error_defaults(self):
        """Test standard error with defaults."""
        error = StandardError(message="Simple error")

        assert error.status == "error"
        assert error.message == "Simple error"
        assert error.errors is None
        assert error.metadata == {}


class TestSecureErrorHandler:
    """Test cases for SecureErrorHandler."""

    def test_secure_error_handler_creation(self):
        """Test creating secure error handler."""
        handler = SecureErrorHandler(service_name="test-service")

        assert handler.service_name == "test-service"
        assert handler.logger.name == "test-service.security"

    def test_handle_error_basic(self):
        """Test basic error handling."""
        handler = SecureErrorHandler(service_name="test-service")

        try:
            raise ValueError("Test error")
        except Exception as e:
            # Use the actual method signature
            error_response = handler.handle_error(
                error=e, error_type="validation", severity=ErrorSeverity.MEDIUM
            )

            assert isinstance(error_response, dict)
            assert "error_id" in error_response  # Actual key name
            assert "message" in error_response
            assert "timestamp" in error_response
            assert "service" in error_response


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
    async def test_create_service_dependency(self):
        """Test service dependency creation."""
        dependency_func = create_service_dependency("test-service")

        # Should return a function
        assert callable(dependency_func)

        # Function should return a dict when awaited (it's async)
        result = await dependency_func()
        assert isinstance(result, dict)
        assert "function" in result
        assert "timestamp" in result


class TestHelperFunctions:
    """Test cases for helper functions."""

    def test_create_success_response(self):
        """Test success response helper."""
        response = create_success_response(
            message="Operation successful",
            data={"id": "123"},
            metadata={"source": "test"},
        )

        assert isinstance(response, StandardResponse)
        assert response.status == "success"
        assert response.message == "Operation successful"
        assert response.data["id"] == "123"
        assert response.metadata["source"] == "test"

    def test_create_error_response(self):
        """Test error response helper."""
        error_response = create_error_response(
            message="Operation failed",
            errors=["Validation error"],
            metadata={"error_code": "E001"},
        )

        assert isinstance(error_response, StandardError)
        assert error_response.status == "error"
        assert error_response.message == "Operation failed"
        assert "Validation error" in error_response.errors


class TestModelIntegration:
    """Test integration between different models."""

    def test_standard_response_with_health_data(self):
        """Test standard response containing health check data."""
        health_data = HealthStatus(
            service="test-service",
            version="1.0.0",
            status="healthy",
            dependencies={"api": True, "database": True},
        )

        response = StandardResponse(
            status="success", message="Health check completed", data=health_data
        )

        assert response.status == "success"
        assert response.data.service == "test-service"
        assert response.data.status == "healthy"

    def test_standard_response_with_service_status(self):
        """Test using service status in responses."""
        service_status = ServiceStatus(
            service="test-service",
            version="1.2.3",
            status="healthy",
            environment="production",
        )

        response = StandardResponse(
            status="success", message="Service status retrieved", data=service_status
        )

        assert response.data.service == "test-service"
        assert response.data.version == "1.2.3"
        assert response.data.environment == "production"

    def test_content_item_in_response(self):
        """Test content item in standard response."""
        content = ContentItem(
            id="content-789",
            title="Sample Article",
            content="Article content here",
            processing_metadata={"quality_score": 0.9},
        )

        response = StandardResponse(
            status="success", message="Content retrieved", data=content
        )

        assert response.data.id == "content-789"
        assert response.data.processing_metadata["quality_score"] == 0.9

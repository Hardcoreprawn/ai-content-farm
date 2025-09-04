"""
Test suite for FastAPI-native shared models.

Tests the FastAPI-native StandardResponse and StandardError models,
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
            errors=None,
            metadata={"function": "test"},
        )

        assert response.status == "success"
        assert response.message == "Test message"
        assert response.data == {"key": "value"}
        assert response.metadata["function"] == "test"

    def test_json_serialization(self):
        """Test response can be serialized to JSON."""
        response = StandardResponse(
            status="success",
            message="Test message",
            data={"items": [1, 2, 3]},
            errors=None,
            metadata={"timestamp": "2025-08-27T10:00:00Z"},
        )

        data = response.model_dump()

        assert data["status"] == "success"
        assert data["message"] == "Test message"
        assert data["data"]["items"] == [1, 2, 3]


class TestHelperFunctions:
    """Test helper functions for creating responses."""

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
        assert response.data["result"] == "completed"

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
        assert "Validation error" in error.errors


class TestDataModels:
    """Test the data models."""

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

    def test_content_item_creation(self):
        """Test ContentItem model."""
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


class TestIntegrationWorkflows:
    """Test end-to-end workflows with the FastAPI-native models."""

    def test_success_response_workflow(self):
        """Test complete success response workflow."""
        # Create success response (would be returned from endpoint)
        response = create_success_response(
            message="Content collected successfully",
            data={"items_collected": 15, "source": "reddit"},
            metadata={"custom": "data"},
        )

        assert response.status == "success"
        assert response.data is not None
        assert response.data["items_collected"] == 15

    def test_error_response_workflow(self):
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
        assert "Network timeout" in detail["errors"]

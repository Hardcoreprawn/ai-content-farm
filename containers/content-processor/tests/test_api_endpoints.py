"""
Test Suite for Content Processor API Endpoints

Provides test coverage for the standardized API endpoints that match the actual implementation.
"""

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


# Root, Health, and Status endpoints were planned but not implemented in current design
# The container uses /process endpoint for main operations
# Keeping functional endpoint tests below


def test_docs_endpoint(client):
    """Test API documentation endpoint."""
    response = client.get("/docs")

    assert response.status_code == 200
    # OpenAPI docs should return HTML
    assert "text/html" in response.headers.get("content-type", "")


def test_openapi_json(client):
    """Test OpenAPI JSON schema endpoint."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    data = response.json()

    # Should be a valid OpenAPI spec
    assert "openapi" in data
    assert "info" in data
    assert "paths" in data


def test_process_endpoint_post(client):
    """Test main processing endpoint."""
    test_data = {
        "topic_id": "test-topic-123",
        "content": "Test content to process",
        "processing_type": "enhancement",
        "options": {"quality_threshold": 0.8},
    }

    response = client.post("/process", json=test_data)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "data" in data


def test_process_types_endpoint(client):
    """Test processing types information endpoint."""
    response = client.get("/process/types")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "data" in data
    # Check actual field name from API response
    assert "available_types" in data["data"]


def test_process_status_endpoint(client):
    """Test processing status endpoint."""
    response = client.get("/process/status")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "data" in data


def test_error_handling(client):
    """Test error handling with invalid request."""
    # Test invalid JSON to main process endpoint
    response = client.post("/process", json={"invalid": "data"})

    # Should handle the error gracefully with our standardized validation error format
    assert response.status_code == 422
    data = response.json()

    # Our standardized error format
    assert data["status"] == "error"
    assert data["message"] == "Request validation failed"
    assert "errors" in data
    assert "metadata" in data
    assert isinstance(data["errors"], list)
    assert len(data["errors"]) > 0


def test_nonexistent_endpoint(client):
    """Test that nonexistent endpoints return 404."""
    response = client.get("/nonexistent")

    assert response.status_code == 404
    data = response.json()

    assert data["status"] == "error"
    assert data["message"] == "Endpoint not found"
    assert "data" in data
    assert "errors" in data
    assert "metadata" in data

    # Check 404-specific data
    assert data["data"]["requested_path"] == "/nonexistent"
    assert data["data"]["requested_method"] == "GET"
    assert "available_endpoints" in data["data"]
    assert "documentation" in data["data"]

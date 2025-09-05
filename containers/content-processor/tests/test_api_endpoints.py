"""
Test Suite for Content Processor API Endpoints

Provides test coverage for the standardized API endpoints that match the actual implementation.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns service information."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "data" in data
    assert data["data"]["service"] == "content-processor"
    assert data["data"]["version"] == "1.0.0"


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] in ["success", "error"]
    assert "message" in data
    assert "data" in data

    # Health-specific data - check actual fields
    health_data = data["data"]
    assert "service" in health_data
    assert health_data["service"] == "content-processor"
    assert "status" in health_data
    assert "dependencies" in health_data


def test_status_endpoint():
    """Test status endpoint format using standard library test."""
    from libs.standard_tests import StandardAPITestSuite

    test_suite = StandardAPITestSuite(client, "content-processor")
    test_suite.test_status_endpoint_standard_format()


def test_docs_endpoint():
    """Test API documentation endpoint."""
    response = client.get("/docs")

    assert response.status_code == 200
    # OpenAPI docs should return HTML
    assert "text/html" in response.headers.get("content-type", "")


def test_openapi_json():
    """Test OpenAPI JSON schema endpoint."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    data = response.json()

    # Should be a valid OpenAPI spec
    assert "openapi" in data
    assert "info" in data
    assert "paths" in data


def test_process_endpoint_post():
    """Test main processing endpoint."""
    test_data = {
        "content": "Test content to process",
        "processing_type": "enhancement",
        "options": {"quality_threshold": 0.8},
    }

    response = client.post("/process", json=test_data)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "data" in data


def test_process_types_endpoint():
    """Test processing types information endpoint."""
    response = client.get("/process/types")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "data" in data
    # Check actual field name from API response
    assert "available_types" in data["data"]


def test_process_status_endpoint():
    """Test processing status endpoint."""
    response = client.get("/process/status")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "data" in data


def test_error_handling():
    """Test error handling with invalid request."""
    # Test invalid JSON to main process endpoint
    response = client.post("/process", json={"invalid": "data"})

    # Should handle the error gracefully with FastAPI validation error format
    assert response.status_code in [400, 422]
    data = response.json()

    # FastAPI validation errors have "detail" field
    assert "detail" in data


def test_nonexistent_endpoint():
    """Test that nonexistent endpoints return 404."""
    response = client.get("/nonexistent")

    assert response.status_code == 404
    data = response.json()

    assert data["status"] == "error"

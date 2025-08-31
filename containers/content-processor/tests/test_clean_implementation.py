"""
Test Suite for Clean Content Processor Implementation

Tests the new functional, clean implementation with proper test-first patterns.
Follows agent instructions for functional programming and maintainability.
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

    # Standard response format
    assert "status" in data
    assert "message" in data
    assert "data" in data
    assert "metadata" in data

    assert data["status"] == "success"

    # Service-specific data
    service_data = data["data"]
    assert service_data["service"] == "content-processor"
    assert service_data["pattern"] == "wake-up work queue"
    assert "endpoints" in service_data


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/api/processor/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] in ["success", "error"]
    assert "message" in data
    assert "data" in data

    # Health-specific data
    health_data = data["data"]
    assert "processor_id" in health_data
    assert "azure_openai_available" in health_data
    assert "blob_storage_available" in health_data
    assert "last_health_check" in health_data


def test_wake_up_endpoint():
    """Test the primary wake-up endpoint."""
    wake_up_request = {
        "source": "collector",
        "batch_size": 5,
        "priority_threshold": 0.7,
    }

    response = client.post("/api/processor/wake-up", json=wake_up_request)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "data" in data

    # Wake-up specific response
    wake_data = data["data"]
    assert "processor_id" in wake_data
    assert "topics_found" in wake_data
    assert "total_processed" in wake_data
    assert "total_cost" in wake_data
    assert "processing_time_seconds" in wake_data

    # Should be non-negative numbers
    assert wake_data["topics_found"] >= 0
    assert wake_data["total_processed"] >= 0
    assert wake_data["total_cost"] >= 0.0
    assert wake_data["processing_time_seconds"] >= 0.0


def test_status_endpoint():
    """Test processor status endpoint."""
    response = client.get("/api/processor/status")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "data" in data

    # Status-specific data
    status_data = data["data"]
    assert "processor_id" in status_data
    assert "status" in status_data
    assert "session_metrics" in status_data
    assert "system_health" in status_data


def test_docs_endpoint():
    """Test API documentation endpoint."""
    response = client.get("/api/processor/docs")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "data" in data

    # Documentation-specific data
    docs_data = data["data"]
    assert "service" in docs_data
    assert "version" in docs_data
    assert "pattern" in docs_data
    assert "usage" in docs_data
    assert "cost_target" in docs_data


def test_process_batch_endpoint():
    """Test manual batch processing endpoint."""
    batch_request = {
        "topic_ids": ["test-topic-1", "test-topic-2"],
        "force_reprocess": False,
    }

    response = client.post("/api/processor/process-batch", json=batch_request)

    assert response.status_code == 200
    data = response.json()

    # Should work even with mock implementation
    assert data["status"] == "success"
    assert "data" in data


def test_wake_up_with_options():
    """Test wake-up endpoint with processing options."""
    wake_up_request = {
        "source": "test-collector",
        "batch_size": 3,
        "priority_threshold": 0.8,
        "processing_options": {
            "quality_threshold": 0.9,
            "max_cost_per_article": 0.50,
        },
    }

    response = client.post("/api/processor/wake-up", json=wake_up_request)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_error_handling():
    """Test error handling with invalid request."""
    # Missing required field
    invalid_request = {
        "batch_size": 5,
        # Missing "source" field
    }

    response = client.post("/api/processor/wake-up", json=invalid_request)

    # Should return validation error
    assert response.status_code == 422  # FastAPI validation error


def test_functional_immutability():
    """Test that multiple calls don't interfere (functional pattern)."""
    # Make multiple wake-up calls
    requests = [
        {"source": "collector-1", "batch_size": 2},
        {"source": "collector-2", "batch_size": 3},
        {"source": "collector-3", "batch_size": 1},
    ]

    responses = []
    for req in requests:
        response = client.post("/api/processor/wake-up", json=req)
        assert response.status_code == 200
        responses.append(response.json())

    # Each response should be independent
    for i, response_data in enumerate(responses):
        assert response_data["status"] == "success"
        # Each should have its own processor_id and metadata
        assert "metadata" in response_data
        assert "processor_id" in response_data["data"]

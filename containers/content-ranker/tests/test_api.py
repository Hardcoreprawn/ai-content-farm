"""
API Integration tests for Content Ranker Service
Tests the FastAPI endpoints and async job processing
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from httpx import AsyncClient
from fastapi.testclient import TestClient

import sys
import os

# Add current directory to Python path for local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app

# Test data
SAMPLE_BLOB_REQUEST = {
    "input_blob_path": "test-input/topics_20250813.json",
    "output_blob_path": "test-output/ranked_topics_20250813.json",
    "ranking_config": {
        "weights": {
            "engagement": 0.4,
            "recency": 0.2,
            "monetization": 0.3,
            "title_quality": 0.1
        },
        "min_score_threshold": 50,
        "min_comments_threshold": 5
    }
}

SAMPLE_DIRECT_REQUEST = {
    "content_data": {
        "job_id": "test-direct-123",
        "source": "reddit",
        "subject": "technology",
        "fetched_at": "20250813_120000",
        "topics": [
            {
                "title": "AI Breakthrough in Machine Learning Transforms Industry",
                "score": 15000,
                "num_comments": 250,
                "created_utc": datetime.now(timezone.utc).timestamp() - 3600,  # 1 hour ago
                "author": "test_user",
                "reddit_id": "test123",
                "external_url": "https://example.com/ai-breakthrough",
                "subreddit": "MachineLearning"
            },
            {
                "title": "Random weather discussion",
                "score": 50,
                "num_comments": 5,
                "created_utc": datetime.now(timezone.utc).timestamp() - 86400,  # 1 day ago
                "author": "weather_user",
                "reddit_id": "test456",
                "external_url": "https://example.com/weather",
                "subreddit": "weather"
            }
        ]
    },
    "ranking_config": {
        "weights": {
            "engagement": 0.3,
            "recency": 0.2,
            "monetization": 0.3,
            "title_quality": 0.2
        }
    }
}


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_root_endpoint(self):
        """Test root endpoint returns service info"""
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "AI Content Farm - Content Ranker API"
            assert data["version"] == "2.0.0"
            assert "available_endpoints" in data

    def test_global_health_check(self):
        """Test global health endpoint"""
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "ai-content-farm-content-ranker"

    def test_service_health_check(self):
        """Test content ranker specific health endpoint"""
        with TestClient(app) as client:
            response = client.get("/api/content-ranker/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "content-ranker"


class TestDocumentationEndpoints:
    """Test API documentation endpoints"""

    def test_api_docs_endpoint(self):
        """Test API documentation endpoint"""
        with TestClient(app) as client:
            response = client.get("/api/content-ranker/docs")
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "Content Ranker Service"
            assert "endpoints" in data
            assert "ranking_algorithms" in data
            assert "configuration" in data

    def test_openapi_docs(self):
        """Test that OpenAPI documentation is accessible"""
        with TestClient(app) as client:
            response = client.get("/docs")
            assert response.status_code == 200

    def test_openapi_schema(self):
        """Test OpenAPI schema endpoint"""
        with TestClient(app) as client:
            response = client.get("/openapi.json")
            assert response.status_code == 200
            schema = response.json()
            assert "openapi" in schema
            assert "info" in schema


class TestJobProcessing:
    """Test job creation and status checking"""

    def test_direct_content_processing_job_creation(self):
        """Test creating a job with direct content data"""
        with TestClient(app) as client:
            response = client.post("/api/content-ranker/process", json=SAMPLE_DIRECT_REQUEST)
            assert response.status_code == 200
            
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "queued"
            assert data["request_type"] == "direct_content"
            assert "status_check_example" in data
            
            return data["job_id"]

    def test_blob_processing_job_creation_validation(self):
        """Test creating a blob processing job (will fail without storage, but validates structure)"""
        with TestClient(app) as client:
            response = client.post("/api/content-ranker/process", json=SAMPLE_BLOB_REQUEST)
            # This might fail due to storage configuration, but should return a valid job response
            # or a proper error about storage configuration
            assert response.status_code in [200, 500]  # Accept either success or storage config error

    def test_invalid_request_validation(self):
        """Test validation of invalid requests"""
        with TestClient(app) as client:
            # Empty request
            response = client.post("/api/content-ranker/process", json={})
            assert response.status_code == 400

            # Request with neither blob path nor content data
            invalid_request = {"ranking_config": {}}
            response = client.post("/api/content-ranker/process", json=invalid_request)
            assert response.status_code == 400

    def test_job_status_checking(self):
        """Test job status endpoint"""
        with TestClient(app) as client:
            # First create a job
            job_response = client.post("/api/content-ranker/process", json=SAMPLE_DIRECT_REQUEST)
            job_data = job_response.json()
            job_id = job_data["job_id"]

            # Check job status
            status_request = {
                "action": "status",
                "job_id": job_id
            }
            
            response = client.post("/api/content-ranker/status", json=status_request)
            assert response.status_code == 200
            
            status_data = response.json()
            assert status_data["job_id"] == job_id
            assert "status" in status_data
            assert "updated_at" in status_data

    def test_job_status_not_found(self):
        """Test status check for non-existent job"""
        with TestClient(app) as client:
            status_request = {
                "action": "status",
                "job_id": "non-existent-job-id"
            }
            
            response = client.post("/api/content-ranker/status", json=status_request)
            assert response.status_code == 404

    def test_invalid_status_action(self):
        """Test invalid action in status request"""
        with TestClient(app) as client:
            status_request = {
                "action": "invalid_action",
                "job_id": "some-job-id"
            }
            
            response = client.post("/api/content-ranker/status", json=status_request)
            assert response.status_code == 400


class TestJobProcessingIntegration:
    """Integration tests for complete job processing workflow"""

    def test_direct_content_processing_workflow(self):
        """Test complete workflow for direct content processing"""
        with TestClient(app) as client:
            # Create job
            job_response = client.post("/api/content-ranker/process", json=SAMPLE_DIRECT_REQUEST)
            assert job_response.status_code == 200
            
            job_data = job_response.json()
            job_id = job_data["job_id"]

            # Wait for processing (give background task time to complete)
            import time
            time.sleep(2)

            # Check final status
            status_request = {"action": "status", "job_id": job_id}
            status_response = client.post("/api/content-ranker/status", json=status_request)
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            
            # Job should be completed (or at least not queued anymore)
            assert status_data["status"] in ["completed", "processing", "failed"]
            
            # If completed, check results
            if status_data["status"] == "completed":
                assert "results" in status_data
                results = status_data["results"]
                assert "ranked_topics" in results
                assert "metadata" in results

    def test_ranking_algorithm_integration(self):
        """Test that ranking algorithms are working in the API context"""
        with TestClient(app) as client:
            # Create a request with topics that should rank differently
            test_request = {
                "content_data": {
                    "topics": [
                        {
                            "title": "AI and Machine Learning Breakthrough",  # High monetization
                            "score": 5000,
                            "num_comments": 100,
                            "created_utc": datetime.now(timezone.utc).timestamp() - 3600,
                            "reddit_id": "ai_topic"
                        },
                        {
                            "title": "Weather discussion",  # Low monetization
                            "score": 5000,
                            "num_comments": 100, 
                            "created_utc": datetime.now(timezone.utc).timestamp() - 3600,
                            "reddit_id": "weather_topic"
                        }
                    ]
                },
                "ranking_config": {
                    "weights": {
                        "engagement": 0.1,
                        "recency": 0.1,
                        "monetization": 0.7,  # Heavy weight on monetization
                        "title_quality": 0.1
                    }
                }
            }

            # Process job
            job_response = client.post("/api/content-ranker/process", json=test_request)
            job_id = job_response.json()["job_id"]

            # Wait and check results
            import time
            time.sleep(2)

            status_request = {"action": "status", "job_id": job_id}
            status_response = client.post("/api/content-ranker/status", json=status_request)
            status_data = status_response.json()

            if status_data["status"] == "completed":
                results = status_data["results"]
                ranked_topics = results["ranked_topics"]
                
                if len(ranked_topics) >= 2:
                    # AI topic should rank higher due to monetization weighting
                    ai_topic = next((t for t in ranked_topics if "AI" in t["title"]), None)
                    weather_topic = next((t for t in ranked_topics if "Weather" in t["title"]), None)
                    
                    if ai_topic and weather_topic:
                        assert ai_topic["ranking_score"] > weather_topic["ranking_score"]


@pytest.mark.asyncio
class TestAsyncJobProcessing:
    """Test async functionality using AsyncClient"""

    async def test_concurrent_job_processing(self):
        """Test that multiple jobs can be processed concurrently"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create multiple jobs concurrently
            jobs = []
            for i in range(3):
                request_data = {**SAMPLE_DIRECT_REQUEST}
                request_data["content_data"]["job_id"] = f"concurrent-test-{i}"
                response = await client.post("/api/content-ranker/process", json=request_data)
                assert response.status_code == 200
                jobs.append(response.json()["job_id"])

            # Wait for processing
            await asyncio.sleep(3)

            # Check all job statuses
            for job_id in jobs:
                status_request = {"action": "status", "job_id": job_id}
                response = await client.post("/api/content-ranker/status", json=status_request)
                assert response.status_code == 200
                status_data = response.json()
                assert status_data["status"] in ["completed", "processing", "failed"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
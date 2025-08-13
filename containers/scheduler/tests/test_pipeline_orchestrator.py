"""
Test Suite for Scheduler Container Service

Tests the pipeline orchestration and workflow management capabilities.
Ensures reliable coordination between all container services.
"""

import pytest
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import Mock, patch, AsyncMock
import asyncio

# Test data for pipeline orchestration
PIPELINE_CONFIG = {
    "pipeline_id": "test_pipeline_001",
    "sources": ["reddit", "hackernews"],
    "collection_options": {
        "subreddits": ["MachineLearning", "programming"],
        "time_range": "24h",
        "min_score": 10
    },
    "ranking_options": {
        "algorithm": "composite",
        "weights": {"engagement": 0.3, "freshness": 0.3, "quality": 0.4}
    },
    "enhancement_options": {
        "include_summary": True,
        "include_tags": True,
        "include_sentiment": True
    },
    "output_options": {
        "format": "markdown",
        "publish_to_cms": True
    }
}

SERVICE_URLS = {
    "content_processor": "http://content-processor:8000",
    "content_ranker": "http://content-ranker:8001", 
    "content_enricher": "http://content-enricher:8002",
    "ssg": "http://ssg:3000"
}


class TestPipelineOrchestrator:
    """Test the core pipeline orchestration engine"""
    
    @pytest.mark.unit
    def test_create_pipeline_returns_id(self):
        """Test pipeline creation returns trackable ID"""
        from core.pipeline_orchestrator import create_pipeline
        
        pipeline_id = create_pipeline(PIPELINE_CONFIG)
        
        assert isinstance(pipeline_id, str)
        assert len(pipeline_id) > 10  # Should be UUID-like
        assert pipeline_id.startswith("pipeline_")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_start_content_pipeline_orchestrates_services(self):
        """Test that pipeline start coordinates all services"""
        from core.pipeline_orchestrator import start_content_pipeline
        
        with patch('core.service_client.call_content_processor') as mock_processor, \
             patch('core.service_client.call_content_ranker') as mock_ranker, \
             patch('core.service_client.call_content_enricher') as mock_enricher, \
             patch('core.service_client.call_ssg') as mock_ssg:
            
            # Mock successful responses
            mock_processor.return_value = {"job_id": "collection_job_001"}
            mock_ranker.return_value = {"job_id": "ranking_job_001"}
            mock_enricher.return_value = {"job_id": "enhancement_job_001"}
            mock_ssg.return_value = {"job_id": "ssg_job_001"}
            
            result = await start_content_pipeline(PIPELINE_CONFIG)
            
            assert "pipeline_id" in result
            assert "status" in result
            assert result["status"] == "started"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_monitor_pipeline_status_tracks_progress(self):
        """Test pipeline status monitoring across all services"""
        from core.pipeline_orchestrator import monitor_pipeline_status
        
        pipeline_id = "test_pipeline_001"
        
        status = await monitor_pipeline_status(pipeline_id)
        
        assert "pipeline_id" in status
        assert "overall_status" in status
        assert "service_statuses" in status
        assert status["overall_status"] in ["pending", "running", "completed", "failed"]

    @pytest.mark.unit
    def test_calculate_pipeline_progress(self):
        """Test pipeline progress calculation"""
        from core.pipeline_orchestrator import calculate_pipeline_progress
        
        service_statuses = {
            "collection": "completed",
            "ranking": "completed", 
            "enhancement": "processing",
            "generation": "pending"
        }
        
        progress = calculate_pipeline_progress(service_statuses)
        
        assert isinstance(progress, float)
        assert 0.0 <= progress <= 1.0
        assert progress > 0.5  # Should be > 50% with 2 completed services


class TestServiceClient:
    """Test service-to-service communication"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_call_content_processor_service(self):
        """Test calling content processor service"""
        from core.service_client import call_content_processor
        
        request_data = {
            "sources": ["reddit"],
            "collection_options": PIPELINE_CONFIG["collection_options"]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 202
            mock_response.json.return_value = {"job_id": "collection_001"}
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await call_content_processor(request_data)
            
            assert "job_id" in result
            mock_post.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_call_content_ranker_service(self):
        """Test calling content ranker service"""
        from core.service_client import call_content_ranker
        
        request_data = {
            "content_source": "content-raw/reddit_20250813.json",
            "ranking_options": PIPELINE_CONFIG["ranking_options"]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 202
            mock_response.json.return_value = {"job_id": "ranking_001"}
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await call_content_ranker(request_data)
            
            assert "job_id" in result

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_service_health_checks(self):
        """Test health checking all services"""
        from core.service_client import check_all_services_health
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            health_status = await check_all_services_health()
            
            assert isinstance(health_status, dict)
            assert all(service in health_status for service in SERVICE_URLS.keys())

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_service_communication_error_handling(self):
        """Test graceful handling of service communication errors"""
        from core.service_client import call_content_processor
        
        request_data = {"sources": ["reddit"]}
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = Exception("Connection failed")
            
            # Should not raise exception but return error status
            result = await call_content_processor(request_data)
            
            assert "error" in result or "status" in result


class TestSchedulerAPI:
    """Test the FastAPI endpoints for pipeline scheduling"""
    
    @pytest.mark.integration
    def test_health_endpoint(self):
        """Test health check endpoint"""
        from main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "scheduler"

    @pytest.mark.integration
    def test_start_pipeline_endpoint(self):
        """Test pipeline start endpoint"""
        from main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        response = client.post("/api/scheduler/pipeline/start", json=PIPELINE_CONFIG)
        
        assert response.status_code == 202
        data = response.json()
        assert "pipeline_id" in data
        assert "status" in data

    @pytest.mark.integration
    def test_pipeline_status_endpoint(self):
        """Test pipeline status checking endpoint"""
        from main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        pipeline_id = "test_pipeline_001"
        
        response = client.get(f"/api/scheduler/pipeline/status/{pipeline_id}")
        
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "pipeline_id" in data
            assert "overall_status" in data

    @pytest.mark.integration
    def test_trigger_collection_endpoint(self):
        """Test manual collection trigger endpoint"""
        from main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        trigger_request = {
            "sources": ["reddit"],
            "options": PIPELINE_CONFIG["collection_options"]
        }
        
        response = client.post("/api/scheduler/trigger/collection", json=trigger_request)
        
        assert response.status_code == 202
        assert "job_id" in response.json()


class TestRedisJobQueue:
    """Test Redis-based job queue management"""
    
    @pytest.mark.integration
    @pytest.mark.local
    @patch('redis.Redis')
    async def test_queue_pipeline_job(self, mock_redis):
        """Test queuing pipeline jobs in Redis"""
        from core.job_queue import queue_pipeline_job
        
        job_data = {
            "pipeline_id": "test_pipeline_001",
            "type": "content_collection",
            "config": PIPELINE_CONFIG
        }
        
        await queue_pipeline_job(job_data)
        
        # Verify Redis was called
        mock_redis.return_value.lpush.assert_called()

    @pytest.mark.integration
    @pytest.mark.local
    @patch('redis.Redis')
    async def test_process_pipeline_jobs(self, mock_redis):
        """Test processing jobs from Redis queue"""
        from core.job_queue import process_pipeline_jobs
        
        # Mock Redis returning a job
        mock_redis.return_value.brpop.return_value = (
            "pipeline_jobs", 
            '{"pipeline_id": "test_001", "type": "collection"}'
        )
        
        # This should process one job
        await process_pipeline_jobs(max_jobs=1)
        
        mock_redis.return_value.brpop.assert_called()


class TestErrorHandling:
    """Test error handling and recovery mechanisms"""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pipeline_failure_recovery(self):
        """Test pipeline recovery from service failures"""
        from core.pipeline_orchestrator import handle_pipeline_failure
        
        failure_context = {
            "pipeline_id": "test_pipeline_001",
            "failed_service": "content-enricher",
            "error": "Service timeout",
            "stage": "enhancement"
        }
        
        recovery_plan = await handle_pipeline_failure(failure_context)
        
        assert "action" in recovery_plan
        assert recovery_plan["action"] in ["retry", "skip", "abort"]

    @pytest.mark.unit
    @pytest.mark.asyncio 
    async def test_service_timeout_handling(self):
        """Test handling of service timeouts"""
        from core.service_client import call_with_timeout
        
        with patch('asyncio.wait_for') as mock_wait:
            mock_wait.side_effect = asyncio.TimeoutError()
            
            result = await call_with_timeout("test_service", {}, timeout=30)
            
            assert "error" in result
            assert "timeout" in result["error"].lower()


# Pytest fixtures
@pytest.fixture
def pipeline_config():
    """Fixture providing pipeline configuration"""
    return PIPELINE_CONFIG.copy()

@pytest.fixture
def mock_redis():
    """Fixture providing mocked Redis client"""
    with patch('redis.Redis') as mock:
        yield mock

@pytest.fixture
def mock_service_responses():
    """Fixture providing mocked service responses"""
    return {
        "content_processor": {"job_id": "collection_001", "status": "started"},
        "content_ranker": {"job_id": "ranking_001", "status": "started"},
        "content_enricher": {"job_id": "enhancement_001", "status": "started"},
        "ssg": {"job_id": "generation_001", "status": "started"}
    }

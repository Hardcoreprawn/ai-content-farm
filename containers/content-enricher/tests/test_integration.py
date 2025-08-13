"""
Integration tests for Content Enricher service.
Tests API endpoints and data processing workflows.
"""

import asyncio
import json
import pytest
import httpx
import time
from typing import Dict, Any


BASE_URL = "http://localhost:8002"


@pytest.mark.asyncio
class TestContentEnricherAPI:
    """Test Content Enricher API endpoints"""
    
    async def test_health_endpoints(self):
        """Test health check endpoints"""
        async with httpx.AsyncClient() as client:
            # Test main health endpoint
            response = await client.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "ai-content-farm-content-enricher"
            
            # Test service health endpoint
            response = await client.get(f"{BASE_URL}/api/content-enricher/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "content-enricher"
    
    async def test_api_documentation(self):
        """Test API documentation endpoint"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/content-enricher/docs")
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "Content Enricher"
            assert "endpoints" in data
            assert "enhancement_features" in data
    
    async def test_direct_topics_enhancement(self):
        """Test enhancement with direct topics data"""
        test_topics = [
            {
                "title": "AI Revolution in Healthcare Technology",
                "content": "Machine learning algorithms are transforming medical diagnosis and treatment planning.",
                "reddit_id": "integration_test1",
                "score": 1800,
                "num_comments": 120,
                "author": "medical_ai",
                "subreddit": "medicine"
            },
            {
                "title": "Cryptocurrency Market Analysis Report",
                "content": "Bitcoin and Ethereum prices show significant volatility amid regulatory changes.",
                "reddit_id": "integration_test2", 
                "score": 950,
                "num_comments": 75,
                "author": "crypto_analyst",
                "subreddit": "cryptocurrency"
            }
        ]
        
        request_data = {
            "source": "reddit",
            "topics": test_topics,
            "config": {
                "include_sentiment": True,
                "include_tags": True,
                "include_insights": True
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Start enhancement job
            response = await client.post(
                f"{BASE_URL}/api/content-enricher/process",
                json=request_data
            )
            assert response.status_code == 200
            
            job_data = response.json()
            job_id = job_data["job_id"]
            assert job_data["status"] == "queued"
            assert job_data["topics_count"] == 2
            
            # Wait for processing
            await asyncio.sleep(3)
            
            # Check job status
            status_response = await client.get(
                f"{BASE_URL}/api/content-enricher/status/{job_id}"
            )
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            assert status_data["job_id"] == job_id
            assert status_data["status"] in ["completed", "processing"]
            
            # Get results if completed
            if status_data["status"] == "completed":
                result_response = await client.get(
                    f"{BASE_URL}/api/content-enricher/result/{job_id}"
                )
                assert result_response.status_code == 200
                
                result_data = result_response.json()
                assert result_data["job_id"] == job_id
                assert result_data["results"]["total_topics"] == 2
                
                enhanced_topics = result_data["results"]["enhanced_topics"]
                assert len(enhanced_topics) == 2
                
                # Verify enhancement data
                for topic in enhanced_topics:
                    assert topic["enhancement_success"] == True
                    assert len(topic["tags"]) > 0
                    assert topic["sentiment"] in ["positive", "negative", "neutral"]
                    assert topic["ai_summary"] is not None
    
    async def test_job_status_not_found(self):
        """Test job status with non-existent job ID"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/api/content-enricher/status/non-existent-job"
            )
            assert response.status_code == 404
    
    async def test_invalid_request_data(self):
        """Test enhancement with invalid request data"""
        invalid_request = {
            "source": "reddit"
            # Missing both topics and blob_path
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/content-enricher/process",
                json=invalid_request
            )
            assert response.status_code == 400
            error_data = response.json()
            assert "Either 'topics' or 'blob_path' must be provided" in error_data["detail"]
    
    async def test_ranked_topics_format(self):
        """Test enhancement with ranked topics format (from ContentRanker)"""
        ranked_topics_data = [
            {
                "title": "Deep Learning Breakthrough in Computer Vision",
                "content": "New neural network architecture achieves state-of-the-art results.",
                "reddit_id": "ranked_test1",
                "score": 2500,
                "num_comments": 180,
                "author": "vision_researcher", 
                "subreddit": "MachineLearning",
                "ranking_score": 0.92,
                "final_score": 0.92,
                "ranking_position": 1,
                "engagement_score": 0.85,
                "monetization_score": 0.95
            }
        ]
        
        request_data = {
            "source": "reddit",
            "topics": ranked_topics_data
        }
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Start enhancement
            response = await client.post(
                f"{BASE_URL}/api/content-enricher/process",
                json=request_data
            )
            assert response.status_code == 200
            
            job_id = response.json()["job_id"]
            
            # Wait and get results
            await asyncio.sleep(3)
            
            result_response = await client.get(
                f"{BASE_URL}/api/content-enricher/result/{job_id}"
            )
            assert result_response.status_code == 200
            
            result_data = result_response.json()
            enhanced_topic = result_data["results"]["enhanced_topics"][0]
            
            # Verify original ranking data is preserved
            assert enhanced_topic["ranking_score"] == 0.92
            assert enhanced_topic["ranking_position"] == 1
            
            # Verify enhancement data is added
            assert enhanced_topic["enhancement_success"] == True
            assert enhanced_topic["ai_summary"] is not None


if __name__ == "__main__":
    # Note: This requires the service to be running on localhost:8002
    pytest.main([__file__, "-v"])
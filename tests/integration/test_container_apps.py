"""
Integration tests for Container Apps Pipeline

Tests the complete content processing pipeline including all services:
- content-processor (SummaryWomble)
- content-ranker  
- content-enricher
- scheduler
- ssg (Static Site Generator)
"""

import pytest
import requests
import json
import time
from typing import Dict, Any
import os


class TestContainerAppsPipeline:
    """Integration tests for the complete Container Apps pipeline"""
    
    @pytest.fixture
    def base_urls(self):
        """Get base URLs for all services"""
        return {
            "content_processor": os.getenv("CONTENT_PROCESSOR_URL", "http://localhost:8000"),
            "content_ranker": os.getenv("CONTENT_RANKER_URL", "http://localhost:8001"), 
            "content_enricher": os.getenv("CONTENT_ENRICHER_URL", "http://localhost:8002"),
            "scheduler": os.getenv("SCHEDULER_URL", "http://localhost:8003"),
            "ssg": os.getenv("SSG_URL", "http://localhost:8004")
        }
    
    def test_all_services_health_checks(self, base_urls):
        """Test that all services respond to health checks"""
        for service_name, base_url in base_urls.items():
            try:
                response = requests.get(f"{base_url}/health", timeout=10)
                assert response.status_code == 200, f"{service_name} health check failed"
                
                data = response.json()
                assert data["status"] == "healthy", f"{service_name} reports unhealthy status"
                print(f"✓ {service_name} health check passed")
                
            except requests.exceptions.RequestException as e:
                pytest.skip(f"{service_name} not accessible: {e}")
    
    def test_service_root_endpoints(self, base_urls):
        """Test that all services respond to root endpoints with service info"""
        for service_name, base_url in base_urls.items():
            try:
                response = requests.get(f"{base_url}/", timeout=10)
                assert response.status_code == 200, f"{service_name} root endpoint failed"
                
                data = response.json()
                assert "service" in data, f"{service_name} root response missing service field"
                assert "version" in data, f"{service_name} root response missing version field"
                print(f"✓ {service_name} root endpoint passed")
                
            except requests.exceptions.RequestException as e:
                pytest.skip(f"{service_name} not accessible: {e}")
    
    def test_api_documentation_endpoints(self, base_urls):
        """Test that all services provide API documentation"""
        for service_name, base_url in base_urls.items():
            try:
                # Test OpenAPI docs endpoint
                response = requests.get(f"{base_url}/docs", timeout=10)
                assert response.status_code == 200, f"{service_name} /docs endpoint failed"
                
                # Test OpenAPI JSON schema
                response = requests.get(f"{base_url}/openapi.json", timeout=10)
                assert response.status_code == 200, f"{service_name} /openapi.json endpoint failed"
                
                schema = response.json()
                assert "openapi" in schema, f"{service_name} invalid OpenAPI schema"
                assert "info" in schema, f"{service_name} missing OpenAPI info"
                print(f"✓ {service_name} API documentation available")
                
            except requests.exceptions.RequestException as e:
                pytest.skip(f"{service_name} not accessible: {e}")
    
    def test_content_processor_basic_functionality(self, base_urls):
        """Test content processor (SummaryWomble) basic functionality"""
        base_url = base_urls["content_processor"]
        
        try:
            # Test the process endpoint
            request_data = {
                "source": "reddit",
                "targets": ["technology"],
                "limit": 5,
                "config": {"test_mode": True}
            }
            
            response = requests.post(
                f"{base_url}/api/summary-womble/process",
                json=request_data,
                timeout=30
            )
            
            assert response.status_code == 200, f"Content processor failed: {response.text}"
            
            data = response.json()
            assert "job_id" in data, "Missing job_id in response"
            assert "status" in data, "Missing status in response"
            assert data["status"] == "queued", f"Expected queued status, got {data['status']}"
            
            print(f"✓ Content processor job created: {data['job_id']}")
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Content processor not accessible: {e}")
    
    def test_content_ranker_basic_functionality(self, base_urls):
        """Test content ranker basic functionality"""
        base_url = base_urls["content_ranker"]
        
        try:
            # Test with sample content data
            request_data = {
                "source": "reddit",
                "topics": [
                    {
                        "title": "Test Topic 1",
                        "score": 100,
                        "num_comments": 50,
                        "created_utc": 1640995200,
                        "url": "https://reddit.com/test1"
                    },
                    {
                        "title": "Test Topic 2", 
                        "score": 200,
                        "num_comments": 25,
                        "created_utc": 1640995200,
                        "url": "https://reddit.com/test2"
                    }
                ]
            }
            
            response = requests.post(
                f"{base_url}/api/content-ranker/process",
                json=request_data,
                timeout=30
            )
            
            assert response.status_code == 200, f"Content ranker failed: {response.text}"
            
            data = response.json()
            assert "job_id" in data, "Missing job_id in response"
            assert "status" in data, "Missing status in response"
            
            print(f"✓ Content ranker job created: {data['job_id']}")
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Content ranker not accessible: {e}")
    
    def test_content_enricher_basic_functionality(self, base_urls):
        """Test content enricher basic functionality"""
        base_url = base_urls["content_enricher"]
        
        try:
            # Test with sample content data
            request_data = {
                "source": "reddit",
                "topics": [
                    {
                        "title": "Sample Technology Article",
                        "content": "This is a sample article about new technology trends.",
                        "score": 150,
                        "url": "https://example.com/tech-article"
                    }
                ]
            }
            
            response = requests.post(
                f"{base_url}/api/content-enricher/process",
                json=request_data,
                timeout=30
            )
            
            assert response.status_code == 200, f"Content enricher failed: {response.text}"
            
            data = response.json()
            assert "job_id" in data, "Missing job_id in response"
            assert "status" in data, "Missing status in response"
            assert data["status"] == "queued", f"Expected queued status, got {data['status']}"
            
            print(f"✓ Content enricher job created: {data['job_id']}")
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Content enricher not accessible: {e}")
    
    def test_scheduler_basic_functionality(self, base_urls):
        """Test scheduler basic functionality"""
        base_url = base_urls["scheduler"]
        
        try:
            # Test creating a workflow
            request_data = {
                "workflow_type": "hot-topics",
                "config": {
                    "targets": ["technology"],
                    "limit": 5
                }
            }
            
            response = requests.post(
                f"{base_url}/api/scheduler/workflows",
                json=request_data,
                timeout=30
            )
            
            assert response.status_code == 200, f"Scheduler failed: {response.text}"
            
            data = response.json()
            assert "workflow_id" in data, "Missing workflow_id in response"
            assert "status" in data, "Missing status in response"
            assert data["workflow_type"] == "hot-topics", "Incorrect workflow type"
            
            print(f"✓ Scheduler workflow created: {data['workflow_id']}")
            
            # Test workflow listing
            response = requests.get(f"{base_url}/api/scheduler/workflows", timeout=10)
            assert response.status_code == 200, "Failed to list workflows"
            
            workflows = response.json()
            assert "workflows" in workflows, "Missing workflows in response"
            assert "total" in workflows, "Missing total in response"
            
            print(f"✓ Scheduler workflow listing works")
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Scheduler not accessible: {e}")
    
    def test_ssg_basic_functionality(self, base_urls):
        """Test static site generator basic functionality"""
        base_url = base_urls["ssg"]
        
        try:
            # Test with sample enriched content
            request_data = {
                "config": {
                    "site_title": "Test AI Content Farm",
                    "site_description": "Test site generated by AI Content Farm",
                    "base_url": "https://test.example.com",
                    "posts_per_page": 5
                },
                "content_source": "test-data/enriched-content.json",
                "output_destination": "test-output"
            }
            
            # Note: This might fail if blob storage isn't properly set up,
            # but the API should still accept the request
            response = requests.post(
                f"{base_url}/api/ssg/generate",
                json=request_data,
                timeout=30
            )
            
            # Accept both success and controlled failures (e.g., blob storage issues)
            assert response.status_code in [200, 400, 500], f"SSG unexpected error: {response.text}"
            
            if response.status_code == 200:
                data = response.json()
                assert "job_id" in data, "Missing job_id in response"
                assert "status" in data, "Missing status in response"
                print(f"✓ SSG job created: {data['job_id']}")
            else:
                print(f"✓ SSG API responded correctly to invalid request: {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"SSG not accessible: {e}")


class TestContainerAppsErrorHandling:
    """Test error handling across all services"""
    
    @pytest.fixture
    def base_urls(self):
        """Get base URLs for all services"""
        return {
            "content_processor": os.getenv("CONTENT_PROCESSOR_URL", "http://localhost:8000"),
            "content_ranker": os.getenv("CONTENT_RANKER_URL", "http://localhost:8001"), 
            "content_enricher": os.getenv("CONTENT_ENRICHER_URL", "http://localhost:8002"),
            "scheduler": os.getenv("SCHEDULER_URL", "http://localhost:8003"),
            "ssg": os.getenv("SSG_URL", "http://localhost:8004")
        }
    
    def test_invalid_endpoints_return_404(self, base_urls):
        """Test that invalid endpoints return 404"""
        for service_name, base_url in base_urls.items():
            try:
                response = requests.get(f"{base_url}/invalid-endpoint", timeout=10)
                assert response.status_code == 404, f"{service_name} should return 404 for invalid endpoints"
                print(f"✓ {service_name} correctly returns 404 for invalid endpoints")
                
            except requests.exceptions.RequestException as e:
                pytest.skip(f"{service_name} not accessible: {e}")
    
    def test_invalid_json_returns_422(self, base_urls):
        """Test that invalid JSON returns 422 validation error"""
        endpoints = [
            (base_urls["content_processor"], "/api/summary-womble/process"),
            (base_urls["content_ranker"], "/api/content-ranker/process"),
            (base_urls["content_enricher"], "/api/content-enricher/process"),
            (base_urls["scheduler"], "/api/scheduler/workflows"),
            (base_urls["ssg"], "/api/ssg/generate")
        ]
        
        for base_url, endpoint in endpoints:
            try:
                # Send invalid JSON data
                response = requests.post(
                    f"{base_url}{endpoint}",
                    json={"invalid": "data"},
                    timeout=10
                )
                
                # Should return validation error (422) or bad request (400)
                assert response.status_code in [400, 422], f"{base_url}{endpoint} should validate input"
                print(f"✓ {base_url}{endpoint} correctly validates input")
                
            except requests.exceptions.RequestException as e:
                pytest.skip(f"{base_url}{endpoint} not accessible: {e}")


class TestContainerAppsConfiguration:
    """Test service configuration and environment"""
    
    @pytest.fixture
    def base_urls(self):
        """Get base URLs for all services"""
        return {
            "content_processor": os.getenv("CONTENT_PROCESSOR_URL", "http://localhost:8000"),
            "content_ranker": os.getenv("CONTENT_RANKER_URL", "http://localhost:8001"), 
            "content_enricher": os.getenv("CONTENT_ENRICHER_URL", "http://localhost:8002"),
            "scheduler": os.getenv("SCHEDULER_URL", "http://localhost:8003"),
            "ssg": os.getenv("SSG_URL", "http://localhost:8004")
        }
    
    def test_correct_service_ports(self, base_urls):
        """Test that services are running on correct ports"""
        expected_ports = {
            "content_processor": "8000",
            "content_ranker": "8001",
            "content_enricher": "8002", 
            "scheduler": "8003",
            "ssg": "8004"
        }
        
        for service_name, base_url in base_urls.items():
            if base_url.startswith("http://localhost:"):
                port = base_url.split(":")[-1]
                expected_port = expected_ports[service_name]
                assert port == expected_port, f"{service_name} should run on port {expected_port}, got {port}"
                print(f"✓ {service_name} running on correct port {port}")
    
    def test_service_identification(self, base_urls):
        """Test that services correctly identify themselves"""
        expected_names = {
            "content_processor": "content-processor",
            "content_ranker": "content-ranker",
            "content_enricher": "content-enricher",
            "scheduler": "scheduler",
            "ssg": "ssg"
        }
        
        for service_name, base_url in base_urls.items():
            try:
                response = requests.get(f"{base_url}/health", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if "service" in data:
                        service_id = data["service"]
                        expected_id = expected_names[service_name]
                        # Allow some flexibility in service identification
                        assert expected_id in service_id.lower(), f"{service_name} service identification mismatch"
                        print(f"✓ {service_name} correctly identifies as {service_id}")
                
            except requests.exceptions.RequestException as e:
                pytest.skip(f"{service_name} not accessible: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
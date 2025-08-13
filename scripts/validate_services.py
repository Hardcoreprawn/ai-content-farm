#!/usr/bin/env python3
"""
Container Apps Service Validation Script

This script validates that all Container Apps services are properly configured
and can respond to basic requests. It can be run against local Docker Compose
environment or remote Container Apps deployment.

Usage:
    python validate_services.py [--base-url <url>] [--timeout <seconds>]
    
Examples:
    # Local development
    python validate_services.py
    
    # Remote deployment
    python validate_services.py --base-url https://ai-content-farm.azurecontainerapps.io
"""

import argparse
import json
import requests
import sys
import time
from typing import Dict, List, Tuple


class ServiceValidator:
    """Validate Container Apps services"""
    
    def __init__(self, base_url: str = "http://localhost", timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.services = {
            "content-processor": 8000,
            "content-ranker": 8001,
            "content-enricher": 8002,
            "scheduler": 8003,
            "ssg": 8004
        }
        
    def validate_service_health(self, service_name: str, port: int) -> Tuple[bool, str]:
        """Validate a single service health endpoint"""
        url = f"{self.base_url}:{port}/health"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    return True, f"✓ {service_name} is healthy"
                else:
                    return False, f"✗ {service_name} reports unhealthy status: {data.get('status')}"
            else:
                return False, f"✗ {service_name} health check failed: HTTP {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return False, f"✗ {service_name} not accessible: {e}"
    
    def validate_service_root(self, service_name: str, port: int) -> Tuple[bool, str]:
        """Validate a single service root endpoint"""
        url = f"{self.base_url}:{port}/"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if "service" in data and "version" in data:
                    return True, f"✓ {service_name} root endpoint working (v{data.get('version')})"
                else:
                    return False, f"✗ {service_name} root endpoint missing required fields"
            else:
                return False, f"✗ {service_name} root endpoint failed: HTTP {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return False, f"✗ {service_name} root endpoint error: {e}"
    
    def validate_service_docs(self, service_name: str, port: int) -> Tuple[bool, str]:
        """Validate a single service API documentation"""
        docs_url = f"{self.base_url}:{port}/docs"
        openapi_url = f"{self.base_url}:{port}/openapi.json"
        
        try:
            # Check docs endpoint
            response = requests.get(docs_url, timeout=self.timeout)
            if response.status_code != 200:
                return False, f"✗ {service_name} /docs endpoint failed: HTTP {response.status_code}"
            
            # Check OpenAPI schema
            response = requests.get(openapi_url, timeout=self.timeout)
            if response.status_code != 200:
                return False, f"✗ {service_name} /openapi.json endpoint failed: HTTP {response.status_code}"
            
            schema = response.json()
            if "openapi" not in schema or "info" not in schema:
                return False, f"✗ {service_name} invalid OpenAPI schema"
            
            return True, f"✓ {service_name} API documentation available"
            
        except requests.exceptions.RequestException as e:
            return False, f"✗ {service_name} docs error: {e}"
        except json.JSONDecodeError:
            return False, f"✗ {service_name} invalid JSON in OpenAPI schema"
    
    def validate_content_processor_api(self) -> Tuple[bool, str]:
        """Test content processor API with sample request"""
        url = f"{self.base_url}:8000/api/summary-womble/process"
        
        request_data = {
            "source": "reddit",
            "targets": ["technology"],
            "limit": 5,
            "config": {"test_mode": True}
        }
        
        try:
            response = requests.post(url, json=request_data, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if "job_id" in data and "status" in data:
                    return True, f"✓ Content processor API working (job: {data['job_id']})"
                else:
                    return False, f"✗ Content processor API response missing required fields"
            else:
                return False, f"✗ Content processor API failed: HTTP {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return False, f"✗ Content processor API error: {e}"
    
    def validate_scheduler_workflow(self) -> Tuple[bool, str]:
        """Test scheduler workflow creation"""
        url = f"{self.base_url}:8003/api/scheduler/workflows"
        
        request_data = {
            "workflow_type": "hot-topics",
            "config": {
                "targets": ["technology"],
                "limit": 5
            }
        }
        
        try:
            response = requests.post(url, json=request_data, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if "workflow_id" in data and "status" in data:
                    return True, f"✓ Scheduler workflow API working (workflow: {data['workflow_id']})"
                else:
                    return False, f"✗ Scheduler API response missing required fields"
            else:
                return False, f"✗ Scheduler API failed: HTTP {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return False, f"✗ Scheduler API error: {e}"
    
    def run_validation(self) -> Dict[str, List[Tuple[bool, str]]]:
        """Run complete validation suite"""
        results = {
            "health_checks": [],
            "root_endpoints": [],
            "api_documentation": [],
            "api_functionality": []
        }
        
        print(f"Validating Container Apps services at {self.base_url}...")
        print("=" * 60)
        
        # Health checks
        print("\n1. Health Checks:")
        for service_name, port in self.services.items():
            success, message = self.validate_service_health(service_name, port)
            results["health_checks"].append((success, message))
            print(f"   {message}")
        
        # Root endpoints
        print("\n2. Root Endpoints:")
        for service_name, port in self.services.items():
            success, message = self.validate_service_root(service_name, port)
            results["root_endpoints"].append((success, message))
            print(f"   {message}")
        
        # API documentation
        print("\n3. API Documentation:")
        for service_name, port in self.services.items():
            success, message = self.validate_service_docs(service_name, port)
            results["api_documentation"].append((success, message))
            print(f"   {message}")
        
        # API functionality tests
        print("\n4. API Functionality:")
        
        # Test content processor
        success, message = self.validate_content_processor_api()
        results["api_functionality"].append((success, message))
        print(f"   {message}")
        
        # Test scheduler
        success, message = self.validate_scheduler_workflow()
        results["api_functionality"].append((success, message))
        print(f"   {message}")
        
        return results
    
    def print_summary(self, results: Dict[str, List[Tuple[bool, str]]]):
        """Print validation summary"""
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        
        total_tests = 0
        passed_tests = 0
        
        for category, tests in results.items():
            category_passed = sum(1 for success, _ in tests if success)
            category_total = len(tests)
            
            total_tests += category_total
            passed_tests += category_passed
            
            status = "✓" if category_passed == category_total else "✗"
            print(f"{status} {category.replace('_', ' ').title()}: {category_passed}/{category_total}")
        
        print("-" * 60)
        overall_status = "✓ PASS" if passed_tests == total_tests else "✗ FAIL"
        print(f"{overall_status}: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n🎉 All Container Apps services are working correctly!")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Check service logs for details.")
        
        return passed_tests == total_tests


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Validate Container Apps services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Local Docker Compose
  %(prog)s --base-url http://localhost  # Custom local URL
  %(prog)s --timeout 30                 # Longer timeout
        """
    )
    
    parser.add_argument(
        "--base-url",
        default="http://localhost",
        help="Base URL for services (default: http://localhost)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Create validator and run tests
    validator = ServiceValidator(args.base_url, args.timeout)
    results = validator.run_validation()
    success = validator.print_summary(results)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
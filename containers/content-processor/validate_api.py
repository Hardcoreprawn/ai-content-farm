#!/usr/bin/env python3
"""
Content Processor API Validation Script

Tests all standardized endpoints locally and in Azure.
Validates Phase 1 implementation before moving to Phase 2.

Usage:
    python validate_api.py --local     # Test local development server
    python validate_api.py --azure     # Test Azure deployment
    python validate_api.py --both      # Test both environments
"""

import argparse
import json
import sys
import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class APIValidator:
    """Validates Content Processor API endpoints."""

    def __init__(self, base_url: str, environment: str = "local"):
        self.base_url = base_url.rstrip("/")
        self.environment = environment
        self.session = self._create_session()
        self.results = []

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set timeout and headers
        session.timeout = 30
        session.headers.update(
            {
                "User-Agent": "ContentProcessor-Validator/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

        return session

    def _log_test(self, test_name: str, endpoint: str, status: str, details: str = ""):
        """Log test result."""
        result = {
            "test": test_name,
            "endpoint": endpoint,
            "status": status,
            "details": details,
            "timestamp": time.time(),
            "environment": self.environment,
        }
        self.results.append(result)

        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {status}")
        if details:
            print(f"   Details: {details}")

    def test_root_endpoint(self) -> bool:
        """Test GET / endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/")

            if response.status_code != 200:
                self._log_test(
                    "Root Endpoint",
                    "/",
                    "FAIL",
                    f"Expected 200, got {response.status_code}",
                )
                return False

            data = response.json()

            # Validate response structure
            required_fields = ["status", "message", "data"]
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                self._log_test(
                    "Root Endpoint", "/", "FAIL", f"Missing fields: {missing_fields}"
                )
                return False

            # Validate service data
            service_data = data.get("data", {})
            if service_data.get("service") != "content-processor":
                self._log_test(
                    "Root Endpoint",
                    "/",
                    "FAIL",
                    f"Unexpected service name: {service_data.get('service')}",
                )
                return False

            self._log_test(
                "Root Endpoint",
                "/",
                "PASS",
                f"Service: {service_data.get('service')} v{service_data.get('version')}",
            )
            return True

        except Exception as e:
            self._log_test("Root Endpoint", "/", "FAIL", str(e))
            return False

    def test_health_endpoint(self) -> bool:
        """Test GET /health endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/health")

            if response.status_code != 200:
                self._log_test(
                    "Health Check",
                    "/health",
                    "FAIL",
                    f"Expected 200, got {response.status_code}",
                )
                return False

            data = response.json()

            # Validate health response
            if data.get("status") != "healthy":
                self._log_test(
                    "Health Check",
                    "/health",
                    "FAIL",
                    f"Service not healthy: {data.get('status')}",
                )
                return False

            health_data = data.get("data", {})
            dependencies = health_data.get("dependencies", {})

            self._log_test(
                "Health Check", "/health", "PASS", f"Dependencies: {dependencies}"
            )
            return True

        except Exception as e:
            self._log_test("Health Check", "/health", "FAIL", str(e))
            return False

    def test_status_endpoint(self) -> bool:
        """Test GET /status endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/status")

            if response.status_code != 200:
                self._log_test(
                    "Status Info",
                    "/status",
                    "FAIL",
                    f"Expected 200, got {response.status_code}",
                )
                return False

            data = response.json()
            status_data = data.get("data", {})

            # Validate required status fields
            required_fields = [
                "service",
                "version",
                "environment",
                "dependencies",
                "configuration",
            ]
            missing_fields = [
                field for field in required_fields if field not in status_data
            ]

            if missing_fields:
                self._log_test(
                    "Status Info",
                    "/status",
                    "FAIL",
                    f"Missing status fields: {missing_fields}",
                )
                return False

            config_info = status_data.get("configuration", {})
            self._log_test(
                "Status Info",
                "/status",
                "PASS",
                f"Environment: {status_data.get('environment')}, "
                f"Max processes: {config_info.get('max_concurrent_processes', 'N/A')}",
            )
            return True

        except Exception as e:
            self._log_test("Status Info", "/status", "FAIL", str(e))
            return False

    def test_docs_endpoint(self) -> bool:
        """Test GET /docs endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/docs")

            if response.status_code != 200:
                self._log_test(
                    "API Docs",
                    "/docs",
                    "FAIL",
                    f"Expected 200, got {response.status_code}",
                )
                return False

            # Check for HTML content
            if "text/html" not in response.headers.get("content-type", ""):
                self._log_test(
                    "API Docs",
                    "/docs",
                    "FAIL",
                    f"Expected HTML, got {response.headers.get('content-type')}",
                )
                return False

            self._log_test("API Docs", "/docs", "PASS", "FastAPI docs available")
            return True

        except Exception as e:
            self._log_test("API Docs", "/docs", "FAIL", str(e))
            return False

    def test_openapi_spec(self) -> bool:
        """Test GET /openapi.json endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/openapi.json")

            if response.status_code != 200:
                self._log_test(
                    "OpenAPI Spec",
                    "/openapi.json",
                    "FAIL",
                    f"Expected 200, got {response.status_code}",
                )
                return False

            data = response.json()

            # Validate OpenAPI structure
            required_fields = ["openapi", "info", "paths"]
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                self._log_test(
                    "OpenAPI Spec",
                    "/openapi.json",
                    "FAIL",
                    f"Missing OpenAPI fields: {missing_fields}",
                )
                return False

            info = data.get("info", {})
            self._log_test(
                "OpenAPI Spec",
                "/openapi.json",
                "PASS",
                f"Title: {info.get('title')}, Version: {info.get('version')}",
            )
            return True

        except Exception as e:
            self._log_test("OpenAPI Spec", "/openapi.json", "FAIL", str(e))
            return False

    def test_process_endpoint(self) -> bool:
        """Test POST /process endpoint."""
        try:
            test_payload = {
                "topic_id": "test-validation-001",
                "content": "Sample test content for validation",
                "metadata": {
                    "source": "validation_script",
                    "timestamp": time.time(),
                    "environment": self.environment,
                },
            }

            response = self.session.post(f"{self.base_url}/process", json=test_payload)

            # For Phase 1, we expect it to work (placeholder implementation)
            if response.status_code not in [200, 202]:
                self._log_test(
                    "Process Endpoint",
                    "/process",
                    "FAIL",
                    f"Expected 200/202, got {response.status_code}: {response.text}",
                )
                return False

            data = response.json()
            response_data = data.get("data", {})

            if response_data.get("topic_id") != test_payload["topic_id"]:
                self._log_test(
                    "Process Endpoint",
                    "/process",
                    "FAIL",
                    "Topic ID mismatch in response",
                )
                return False

            self._log_test(
                "Process Endpoint",
                "/process",
                "PASS",
                f"Status: {response_data.get('status', 'unknown')}",
            )
            return True

        except Exception as e:
            self._log_test("Process Endpoint", "/process", "FAIL", str(e))
            return False

    def test_error_handling(self) -> bool:
        """Test error handling with invalid requests."""
        try:
            # Test 404 error
            response = self.session.get(f"{self.base_url}/nonexistent-endpoint")

            if response.status_code != 404:
                self._log_test(
                    "Error Handling",
                    "/nonexistent",
                    "FAIL",
                    f"Expected 404, got {response.status_code}",
                )
                return False

            data = response.json()

            # Validate OWASP-compliant error response
            if data.get("status") != "error":
                self._log_test(
                    "Error Handling",
                    "/nonexistent",
                    "FAIL",
                    f"Expected error status, got {data.get('status')}",
                )
                return False

            if "error_id" not in data and "correlation_id" not in data:
                self._log_test(
                    "Error Handling",
                    "/nonexistent",
                    "FAIL",
                    "Missing error tracking ID",
                )
                return False

            self._log_test(
                "Error Handling",
                "/nonexistent",
                "PASS",
                "OWASP-compliant error response",
            )
            return True

        except Exception as e:
            self._log_test("Error Handling", "/nonexistent", "FAIL", str(e))
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation tests."""
        print(f"\n🔬 Testing Content Processor API ({self.environment})")
        print(f"Base URL: {self.base_url}")
        print("=" * 60)

        tests = [
            self.test_root_endpoint,
            self.test_health_endpoint,
            self.test_status_endpoint,
            self.test_docs_endpoint,
            self.test_openapi_spec,
            self.test_process_endpoint,
            self.test_error_handling,
        ]

        passed = 0
        total = len(tests)

        for test in tests:
            if test():
                passed += 1

        success_rate = (passed / total) * 100

        print("=" * 60)
        print(f"📊 Results: {passed}/{total} tests passed ({success_rate:.1f}%)")

        if success_rate == 100:
            print("🎉 All tests passed! API is working correctly.")
        elif success_rate >= 80:
            print("⚠️  Most tests passed, but there are some issues to address.")
        else:
            print("❌ Multiple test failures - API needs attention.")

        return {
            "environment": self.environment,
            "base_url": self.base_url,
            "total_tests": total,
            "passed_tests": passed,
            "success_rate": success_rate,
            "results": self.results,
        }


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description="Validate Content Processor API")
    parser.add_argument(
        "--local", action="store_true", help="Test local development server"
    )
    parser.add_argument("--azure", action="store_true", help="Test Azure deployment")
    parser.add_argument("--both", action="store_true", help="Test both environments")
    parser.add_argument(
        "--local-port", type=int, default=8000, help="Local server port"
    )
    parser.add_argument("--azure-url", type=str, help="Azure deployment URL")

    args = parser.parse_args()

    if not any([args.local, args.azure, args.both]):
        args.local = True  # Default to local testing

    all_results = []

    # Test local environment
    if args.local or args.both:
        local_url = f"http://localhost:{args.local_port}"
        validator = APIValidator(local_url, "local")
        local_results = validator.run_all_tests()
        all_results.append(local_results)

    # Test Azure environment
    if args.azure or args.both:
        if not args.azure_url:
            print("❌ Azure URL required for Azure testing. Use --azure-url flag.")
            sys.exit(1)

        validator = APIValidator(args.azure_url, "azure")
        azure_results = validator.run_all_tests()
        all_results.append(azure_results)

    # Save results
    results_file = f"validation_results_{int(time.time())}.json"
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n📁 Detailed results saved to: {results_file}")

    # Exit with appropriate code
    if all(r["success_rate"] == 100 for r in all_results):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

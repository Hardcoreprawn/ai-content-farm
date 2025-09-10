#!/usr/bin/env python3
"""
Integration Tests for mTLS, Service Discovery, and Monitoring

Tests the complete implementation of dynamic mTLS, service discovery,
and enhanced monitoring features.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import requests
import pytest

# Add repository root to Python path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from libs.mtls_client import mtls_client, get_mtls_health

logger = logging.getLogger(__name__)


class MTLSIntegrationTests:
    """Integration tests for mTLS and service discovery."""
    
    def __init__(self):
        self.resource_group = os.getenv("AZURE_RESOURCE_GROUP", "")
        self.domain_name = os.getenv("DOMAIN_NAME", "ai-content-farm.local")
        self.container_apps = [
            "content-collector",
            "content-processor", 
            "site-generator"
        ]
        self.test_results = []
    
    def log_test_result(self, test_name: str, success: bool, message: str):
        """Log test result."""
        result = {
            "test": test_name,
            "success": success,
            "message": message
        }
        self.test_results.append(result)
        
        if success:
            logger.info(f"✅ {test_name}: {message}")
        else:
            logger.error(f"❌ {test_name}: {message}")
    
    def test_certificate_availability(self) -> bool:
        """Test that mTLS certificates are available in Key Vault."""
        try:
            # This would normally use Azure SDK, but for simplicity using CLI
            import subprocess
            
            # Check if certificate exists
            result = subprocess.run([
                "az", "keyvault", "certificate", "show",
                "--vault-name", f"ai-content-dev-kv",  # Simplified name
                "--name", "mtls-wildcard-cert"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                cert_info = json.loads(result.stdout)
                expires = cert_info.get("attributes", {}).get("expires")
                
                self.log_test_result(
                    "certificate_availability",
                    True,
                    f"mTLS certificate found, expires: {expires}"
                )
                return True
            else:
                self.log_test_result(
                    "certificate_availability",
                    False,
                    "mTLS certificate not found in Key Vault"
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "certificate_availability",
                False,
                f"Certificate check failed: {str(e)}"
            )
            return False
    
    def test_dapr_health(self) -> bool:
        """Test Dapr sidecar health."""
        try:
            # Check local Dapr health endpoint
            response = requests.get("http://localhost:3500/v1.0/healthz", timeout=5)
            
            if response.status_code == 200:
                self.log_test_result(
                    "dapr_health",
                    True,
                    "Dapr sidecar is healthy"
                )
                return True
            else:
                self.log_test_result(
                    "dapr_health",
                    False,
                    f"Dapr health check failed: HTTP {response.status_code}"
                )
                return False
                
        except Exception as e:
            self.log_test_result(
                "dapr_health",
                False,
                f"Dapr health check error: {str(e)}"
            )
            return False
    
    def test_mtls_client_setup(self) -> bool:
        """Test mTLS client configuration."""
        try:
            health = get_mtls_health()
            
            all_healthy = all([
                health.get("ssl_context_loaded", False),
                health.get("dapr_available", False)
            ])
            
            self.log_test_result(
                "mtls_client_setup",
                all_healthy,
                f"mTLS client health: {health}"
            )
            
            return all_healthy
            
        except Exception as e:
            self.log_test_result(
                "mtls_client_setup",
                False,
                f"mTLS client setup failed: {str(e)}"
            )
            return False
    
    async def test_service_communication(self) -> bool:
        """Test mTLS service-to-service communication."""
        try:
            success_count = 0
            total_tests = 0
            
            # Test communication between services
            service_tests = [
                ("content-collector", "/health"),
                ("content-processor", "/health"),
                ("site-generator", "/health")
            ]
            
            for service, endpoint in service_tests:
                total_tests += 1
                try:
                    result = await mtls_client.call_service_async(
                        service, "GET", endpoint
                    )
                    
                    if result.get("status") == "success":
                        success_count += 1
                        logger.info(f"✅ {service}{endpoint} communication successful")
                    else:
                        logger.warning(f"⚠️ {service}{endpoint} returned: {result}")
                        
                except Exception as e:
                    logger.error(f"❌ {service}{endpoint} communication failed: {e}")
            
            success_rate = success_count / total_tests if total_tests > 0 else 0
            success = success_rate >= 0.5  # At least 50% success
            
            self.log_test_result(
                "service_communication",
                success,
                f"Service communication: {success_count}/{total_tests} successful ({success_rate:.1%})"
            )
            
            return success
            
        except Exception as e:
            self.log_test_result(
                "service_communication",
                False,
                f"Service communication test failed: {str(e)}"
            )
            return False
    
    def test_dns_records(self) -> bool:
        """Test DNS service discovery records."""
        try:
            import subprocess
            
            success_count = 0
            total_services = len(self.container_apps)
            
            for service in self.container_apps:
                # Clean service name for DNS
                dns_name = service.replace("content-", "").replace("-", "_")
                fqdn = f"{dns_name}.{self.domain_name}"
                
                # Test DNS resolution
                result = subprocess.run([
                    "nslookup", fqdn
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    success_count += 1
                    logger.info(f"✅ DNS resolution successful for {fqdn}")
                else:
                    logger.warning(f"⚠️ DNS resolution failed for {fqdn}")
            
            success_rate = success_count / total_services
            success = success_rate >= 0.5
            
            self.log_test_result(
                "dns_records",
                success,
                f"DNS resolution: {success_count}/{total_services} successful ({success_rate:.1%})"
            )
            
            return success
            
        except Exception as e:
            self.log_test_result(
                "dns_records",
                False,
                f"DNS records test failed: {str(e)}"
            )
            return False
    
    def test_monitoring_alerts(self) -> bool:
        """Test monitoring and alerting configuration."""
        try:
            import subprocess
            
            # Check if monitoring alerts are configured
            alerts_to_check = [
                "ai-content-dev-cert-expiry-alert",
                "ai-content-dev-mtls-handshake-failures"
            ]
            
            success_count = 0
            
            for alert_name in alerts_to_check:
                result = subprocess.run([
                    "az", "monitor", "metrics", "alert", "show",
                    "--resource-group", self.resource_group,
                    "--name", alert_name
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    alert_info = json.loads(result.stdout)
                    enabled = alert_info.get("enabled", False)
                    
                    if enabled:
                        success_count += 1
                        logger.info(f"✅ Alert configured and enabled: {alert_name}")
                    else:
                        logger.warning(f"⚠️ Alert configured but disabled: {alert_name}")
                else:
                    logger.warning(f"⚠️ Alert not found: {alert_name}")
            
            success = success_count >= len(alerts_to_check) // 2
            
            self.log_test_result(
                "monitoring_alerts",
                success,
                f"Monitoring alerts: {success_count}/{len(alerts_to_check)} configured"
            )
            
            return success
            
        except Exception as e:
            self.log_test_result(
                "monitoring_alerts",
                False,
                f"Monitoring alerts test failed: {str(e)}"
            )
            return False
    
    def test_keda_scaling(self) -> bool:
        """Test KEDA autoscaling configuration."""
        try:
            import subprocess
            
            success_count = 0
            
            for app in self.container_apps:
                app_name = f"ai-content-dev-{app}"
                
                result = subprocess.run([
                    "az", "containerapp", "show",
                    "--resource-group", self.resource_group,
                    "--name", app_name,
                    "--query", "properties.template.scale"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    scale_config = json.loads(result.stdout)
                    
                    min_replicas = scale_config.get("minReplicas", 0)
                    max_replicas = scale_config.get("maxReplicas", 1)
                    rules = scale_config.get("rules", [])
                    
                    if len(rules) > 0 and max_replicas > min_replicas:
                        success_count += 1
                        logger.info(f"✅ KEDA scaling configured for {app}: {min_replicas}-{max_replicas} replicas, {len(rules)} rules")
                    else:
                        logger.warning(f"⚠️ No KEDA scaling rules for {app}")
                else:
                    logger.warning(f"⚠️ Could not check scaling for {app}")
            
            success = success_count >= len(self.container_apps) // 2
            
            self.log_test_result(
                "keda_scaling",
                success,
                f"KEDA scaling: {success_count}/{len(self.container_apps)} apps configured"
            )
            
            return success
            
        except Exception as e:
            self.log_test_result(
                "keda_scaling",
                False,
                f"KEDA scaling test failed: {str(e)}"
            )
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        logger.info("Starting mTLS and Service Discovery Integration Tests")
        logger.info("=" * 60)
        
        # Run tests
        tests = [
            ("Certificate Availability", self.test_certificate_availability),
            ("Dapr Health", self.test_dapr_health),
            ("mTLS Client Setup", self.test_mtls_client_setup),
            ("Service Communication", self.test_service_communication),
            ("DNS Records", self.test_dns_records),
            ("Monitoring Alerts", self.test_monitoring_alerts),
            ("KEDA Scaling", self.test_keda_scaling)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            logger.info(f"\nRunning: {test_name}")
            try:
                if asyncio.iscoroutinefunction(test_func):
                    result = await test_func()
                else:
                    result = test_func()
                
                if result:
                    passed += 1
                else:
                    failed += 1
                    
            except Exception as e:
                logger.error(f"Test {test_name} crashed: {e}")
                failed += 1
        
        # Summary
        total = passed + failed
        success_rate = passed / total if total > 0 else 0
        
        summary = {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "success_rate": success_rate,
            "results": self.test_results
        }
        
        logger.info("\n" + "=" * 60)
        logger.info("Integration Test Summary")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Success Rate: {success_rate:.1%}")
        
        if success_rate >= 0.7:
            logger.info("🎉 Integration tests mostly successful!")
        elif success_rate >= 0.5:
            logger.warning("⚠️ Integration tests partially successful")
        else:
            logger.error("❌ Integration tests failed")
        
        return summary


async def main():
    """Run integration tests."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run tests
    test_suite = MTLSIntegrationTests()
    results = await test_suite.run_all_tests()
    
    # Exit with appropriate code
    if results["success_rate"] >= 0.7:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
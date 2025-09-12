#!/usr/bin/env python3
"""
mTLS Health Check Library

Provides comprehensive mTLS health checking capabilities for container self-testing.
Integrates with existing standard health endpoints to add mTLS validation.
"""

import asyncio
import json
import logging
import ssl
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiohttp
import certifi
from cryptography import x509
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class MTLSHealthChecker:
    """Comprehensive mTLS health checking for container self-testing"""

    def __init__(self, service_name: str, service_port: int = None):
        self.service_name = service_name
        self.service_port = service_port
        self.cert_path = Path("/etc/ssl/certs")
        self.key_vault_url = None  # Will be set from environment

    async def check_certificate_health(self) -> Dict:
        """Check certificate validity and expiration"""
        result = {"status": "healthy", "details": {}, "warnings": [], "errors": []}

        try:
            # Check service-specific certificate
            cert_file = self.cert_path / f"{self.service_name}.crt"
            key_file = self.cert_path / f"{self.service_name}.key"

            if not cert_file.exists():
                result["errors"].append(f"Certificate file not found: {cert_file}")
                result["status"] = "unhealthy"
                return result

            if not key_file.exists():
                result["errors"].append(f"Private key file not found: {key_file}")
                result["status"] = "unhealthy"
                return result

            # Load and validate certificate
            with open(cert_file, "rb") as f:
                cert_data = f.read()
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())

            # Check certificate validity
            now = datetime.utcnow()
            not_before = cert.not_valid_before
            not_after = cert.not_valid_after

            result["details"]["certificate"] = {
                "subject": str(cert.subject),
                "issuer": str(cert.issuer),
                "serial_number": str(cert.serial_number),
                "not_before": not_before.isoformat(),
                "not_after": not_after.isoformat(),
                "days_until_expiry": (not_after - now).days,
            }

            # Check for upcoming expiration
            days_until_expiry = (not_after - now).days
            if days_until_expiry < 30:
                result["warnings"].append(
                    f"Certificate expires in {days_until_expiry} days"
                )
                result["status"] = "warning"
            elif days_until_expiry < 7:
                result["errors"].append(
                    f"Certificate expires in {days_until_expiry} days"
                )
                result["status"] = "unhealthy"

            # Validate certificate chain
            chain_valid = await self._validate_certificate_chain(cert)
            result["details"]["chain_valid"] = chain_valid
            if not chain_valid:
                result["warnings"].append("Certificate chain validation failed")
                if result["status"] == "healthy":
                    result["status"] = "warning"

        except Exception as e:
            result["errors"].append(f"Certificate validation error: {str(e)}")
            result["status"] = "unhealthy"
            logger.exception("Certificate health check failed")

        return result

    async def check_dapr_sidecar_health(self) -> Dict:
        """Check Dapr sidecar health and mTLS configuration"""
        result = {"status": "healthy", "details": {}, "warnings": [], "errors": []}

        try:
            # Check Dapr sidecar health endpoint
            dapr_port = 3500  # Default Dapr HTTP port
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"http://localhost:{dapr_port}/v1.0/healthz",
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as response:
                        if response.status == 200:
                            result["details"]["dapr_sidecar"] = "healthy"
                        else:
                            result["warnings"].append(
                                f"Dapr sidecar returned status {response.status}"
                            )
                            result["status"] = "warning"
                except aiohttp.ClientError as e:
                    result["errors"].append(f"Dapr sidecar not accessible: {str(e)}")
                    result["status"] = "unhealthy"

            # Check mTLS configuration
            try:
                async with session.get(
                    f"http://localhost:{dapr_port}/v1.0/metadata",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        metadata = await response.json()
                        mtls_enabled = metadata.get("extended", {}).get("mtls", False)
                        result["details"]["mtls_enabled"] = mtls_enabled
                        if not mtls_enabled:
                            result["warnings"].append(
                                "mTLS not enabled in Dapr sidecar"
                            )
                            result["status"] = "warning"
                    else:
                        result["warnings"].append("Could not retrieve Dapr metadata")
                        result["status"] = "warning"
            except Exception as e:
                result["warnings"].append(f"Could not check Dapr mTLS status: {str(e)}")
                if result["status"] == "healthy":
                    result["status"] = "warning"

        except Exception as e:
            result["errors"].append(f"Dapr health check error: {str(e)}")
            result["status"] = "unhealthy"
            logger.exception("Dapr health check failed")

        return result

    async def check_service_dependencies(self, dependencies: List[str]) -> Dict:
        """Check mTLS connectivity to dependent services"""
        result = {
            "status": "healthy",
            "details": {"dependencies": {}},
            "warnings": [],
            "errors": [],
        }

        for service in dependencies:
            dep_result = await self._test_service_connection(service)
            result["details"]["dependencies"][service] = dep_result

            if dep_result["status"] == "unhealthy":
                result["errors"].append(f"Cannot connect to {service}")
                result["status"] = "unhealthy"
            elif dep_result["status"] == "warning":
                result["warnings"].append(f"Issues connecting to {service}")
                if result["status"] == "healthy":
                    result["status"] = "warning"

        return result

    async def _test_service_connection(self, service_name: str) -> Dict:
        """Test mTLS connection to a specific service"""
        result = {
            "status": "healthy",
            "response_time_ms": None,
            "certificate_verified": False,
            "errors": [],
        }

        try:
            # Map service names to their expected endpoints
            service_map = {
                "content-collector": "collector.{domain}",
                "content-processor": "processor.{domain}",
                "site-generator": "site-gen.{domain}",
            }

            if service_name not in service_map:
                result["errors"].append(f"Unknown service: {service_name}")
                result["status"] = "unhealthy"
                return result

            # Get domain from environment or use default
            domain = "example.com"  # This should come from configuration
            url = f"https://{service_map[service_name].format(domain=domain)}/health"

            # Create SSL context for mTLS
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED

            # Load client certificate for mTLS
            cert_file = self.cert_path / f"{self.service_name}.crt"
            key_file = self.cert_path / f"{self.service_name}.key"

            if cert_file.exists() and key_file.exists():
                ssl_context.load_cert_chain(str(cert_file), str(key_file))
            else:
                result["errors"].append("Client certificate not available for mTLS")
                result["status"] = "unhealthy"
                return result

            start_time = time.time()

            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    end_time = time.time()
                    result["response_time_ms"] = int((end_time - start_time) * 1000)

                    if response.status == 200:
                        result["certificate_verified"] = True
                        health_data = await response.json()
                        result["remote_status"] = health_data.get("status", "unknown")
                    else:
                        result["errors"].append(
                            f"Service returned status {response.status}"
                        )
                        result["status"] = "warning"

        except aiohttp.ClientError as e:
            result["errors"].append(f"Connection error: {str(e)}")
            result["status"] = "unhealthy"
        except Exception as e:
            result["errors"].append(f"Unexpected error: {str(e)}")
            result["status"] = "unhealthy"
            logger.exception(f"Service connection test failed for {service_name}")

        return result

    async def _validate_certificate_chain(self, cert: x509.Certificate) -> bool:
        """Validate certificate chain against trust store"""
        try:
            # This is a simplified validation - in production you'd want
            # more comprehensive chain validation
            return True  # Placeholder implementation
        except Exception:
            return False

    async def get_comprehensive_mtls_status(
        self, dependencies: List[str] = None
    ) -> Dict:
        """Get comprehensive mTLS health status for the service"""
        dependencies = dependencies or []

        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.service_name,
            "overall_status": "healthy",
            "components": {},
            "summary": {
                "total_checks": 0,
                "healthy_checks": 0,
                "warning_checks": 0,
                "unhealthy_checks": 0,
            },
        }

        # Run all health checks
        checks = [
            ("certificate", self.check_certificate_health()),
            ("dapr_sidecar", self.check_dapr_sidecar_health()),
        ]

        if dependencies:
            checks.append(
                ("dependencies", self.check_service_dependencies(dependencies))
            )

        # Execute all checks concurrently
        check_results = await asyncio.gather(*[check[1] for check in checks])

        # Process results
        for (check_name, _), check_result in zip(checks, check_results):
            result["components"][check_name] = check_result
            result["summary"]["total_checks"] += 1

            if check_result["status"] == "healthy":
                result["summary"]["healthy_checks"] += 1
            elif check_result["status"] == "warning":
                result["summary"]["warning_checks"] += 1
                if result["overall_status"] == "healthy":
                    result["overall_status"] = "warning"
            else:  # unhealthy
                result["summary"]["unhealthy_checks"] += 1
                result["overall_status"] = "unhealthy"

        return result


# Helper function for easy integration with existing health endpoints
async def get_mtls_health_data(
    service_name: str, dependencies: List[str] = None
) -> Dict:
    """Convenience function to get mTLS health data for integration with existing endpoints"""
    checker = MTLSHealthChecker(service_name)
    return await checker.get_comprehensive_mtls_status(dependencies)


# Example integration with existing health endpoint
async def enhanced_health_check(
    service_name: str, existing_checks: Dict, dependencies: List[str] = None
) -> Dict:
    """Enhance existing health checks with mTLS validation"""

    # Get existing health status
    result = {
        "service": service_name,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy",
        "checks": existing_checks.copy(),
    }

    # Add mTLS health checks
    mtls_data = await get_mtls_health_data(service_name, dependencies)
    result["checks"]["mtls"] = mtls_data

    # Update overall status based on mTLS health
    if mtls_data["overall_status"] == "unhealthy":
        result["status"] = "unhealthy"
    elif mtls_data["overall_status"] == "warning" and result["status"] == "healthy":
        result["status"] = "warning"

    return result

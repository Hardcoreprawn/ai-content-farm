#!/usr/bin/env python3
"""
mTLS Integration for Standard Endpoints

Extends the standard endpoint library with mTLS health checking capabilities.
This module provides mTLS validation as a standard dependency check.
"""

import asyncio
import logging
import os
import ssl
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp
import certifi
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class MTLSValidator:
    """mTLS validation for standard health endpoints"""

    def __init__(self, service_name: str, domain: str = None):
        self.service_name = service_name
        self.domain = domain or os.getenv("MTLS_DOMAIN", "jablab.dev")
        self.cert_path = Path("/etc/ssl/certs")
        self.key_vault_url = os.getenv("AZURE_KEY_VAULT_URL")

    async def check_certificates(self) -> Dict:
        """Check certificate health for this service"""
        result = {
            "status": "healthy",
            "certificate_valid": False,
            "days_until_expiry": None,
            "issuer": None,
            "errors": [],
        }

        try:
            cert_file = self.cert_path / f"{self.service_name}.crt"
            key_file = self.cert_path / f"{self.service_name}.key"

            if not cert_file.exists() or not key_file.exists():
                result["status"] = "warning"
                result["errors"].append(
                    "Certificate files not found (may not be deployed yet)"
                )
                return result

            # Load and validate certificate
            with open(cert_file, "rb") as f:
                cert_data = f.read()
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())

            # Check validity period
            now = datetime.utcnow()
            not_after = cert.not_valid_after
            days_until_expiry = (not_after - now).days

            result["certificate_valid"] = True
            result["days_until_expiry"] = days_until_expiry
            result["issuer"] = str(cert.issuer.rfc4514_string())

            # Check for upcoming expiration
            if days_until_expiry < 7:
                result["status"] = "unhealthy"
                result["errors"].append(
                    f"Certificate expires in {days_until_expiry} days"
                )
            elif days_until_expiry < 30:
                result["status"] = "warning"
                result["errors"].append(
                    f"Certificate expires in {days_until_expiry} days"
                )

        except Exception as e:
            result["status"] = "unhealthy"
            result["errors"].append(f"Certificate validation failed: {str(e)}")
            logger.exception("Certificate validation error")

        return result

    async def check_dapr_sidecar(self) -> Dict:
        """Check Dapr sidecar mTLS configuration"""
        result = {
            "status": "healthy",
            "dapr_available": False,
            "mtls_enabled": False,
            "errors": [],
        }

        try:
            # Check Dapr sidecar health
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        "http://localhost:3500/v1.0/healthz",
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as response:
                        if response.status == 200:
                            result["dapr_available"] = True
                        else:
                            result["errors"].append(
                                f"Dapr sidecar returned status {response.status}"
                            )

                except aiohttp.ClientError:
                    result["status"] = "warning"
                    result["errors"].append(
                        "Dapr sidecar not accessible (normal in non-Container Apps environment)"
                    )
                    return result

                # Check mTLS configuration
                try:
                    async with session.get(
                        "http://localhost:3500/v1.0/metadata",
                        timeout=aiohttp.ClientTimeout(total=5),
                    ) as response:
                        if response.status == 200:
                            metadata = await response.json()
                            result["mtls_enabled"] = metadata.get("extended", {}).get(
                                "mtls", False
                            )
                        else:
                            result["errors"].append("Could not retrieve Dapr metadata")

                except Exception as e:
                    result["errors"].append(
                        f"Could not check Dapr mTLS status: {str(e)}"
                    )

        except Exception as e:
            result["status"] = "warning"
            result["errors"].append(f"Dapr check failed: {str(e)}")
            logger.exception("Dapr sidecar check error")

        return result

    async def test_dependency_connection(self, target_service: str) -> Dict:
        """Test mTLS connection to a dependency service"""
        result = {
            "status": "healthy",
            "service": target_service,
            "response_time_ms": None,
            "certificate_verified": False,
            "errors": [],
        }

        try:
            url = f"https://{target_service}.{self.domain}/health"

            # Create SSL context for mTLS
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED

            # Load client certificate if available
            cert_file = self.cert_path / f"{self.service_name}.crt"
            key_file = self.cert_path / f"{self.service_name}.key"

            if cert_file.exists() and key_file.exists():
                ssl_context.load_cert_chain(str(cert_file), str(key_file))
            else:
                result["status"] = "warning"
                result["errors"].append("Client certificate not available for mTLS")
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
                    else:
                        result["status"] = "warning"
                        result["errors"].append(
                            f"Service returned status {response.status}"
                        )

        except Exception as e:
            result["status"] = (
                "warning"  # Don't fail health check for dependency issues
            )
            result["errors"].append(f"Connection failed: {str(e)}")

        return result


def create_mtls_dependency_check(
    service_name: str, dependencies: List[str] = None, domain: str = None
):
    """
    Create an mTLS dependency check function for use with standard health endpoints.

    Args:
        service_name: Name of this service
        dependencies: List of services to test connections to
        domain: Domain for service discovery (defaults to MTLS_DOMAIN env var)

    Returns:
        Async function that can be used as a dependency check
    """
    dependencies = dependencies or []
    validator = MTLSValidator(service_name, domain)

    async def mtls_check() -> Dict:
        """Comprehensive mTLS health check"""
        result = {
            "status": "healthy",
            "certificate": {},
            "dapr": {},
            "dependencies": {},
            "summary": {"total_checks": 0, "healthy": 0, "warnings": 0, "errors": 0},
        }

        # Check certificates
        cert_result = await validator.check_certificates()
        result["certificate"] = cert_result
        result["summary"]["total_checks"] += 1

        if cert_result["status"] == "healthy":
            result["summary"]["healthy"] += 1
        elif cert_result["status"] == "warning":
            result["summary"]["warnings"] += 1
        else:
            result["summary"]["errors"] += 1
            result["status"] = "unhealthy"

        # Check Dapr sidecar
        dapr_result = await validator.check_dapr_sidecar()
        result["dapr"] = dapr_result
        result["summary"]["total_checks"] += 1

        if dapr_result["status"] == "healthy":
            result["summary"]["healthy"] += 1
        elif dapr_result["status"] == "warning":
            result["summary"]["warnings"] += 1
            if result["status"] == "healthy":
                result["status"] = "warning"
        else:
            result["summary"]["errors"] += 1
            result["status"] = "unhealthy"

        # Check dependencies
        if dependencies:
            dep_results = await asyncio.gather(
                *[validator.test_dependency_connection(dep) for dep in dependencies],
                return_exceptions=True,
            )

            for dep, dep_result in zip(dependencies, dep_results):
                if isinstance(dep_result, Exception):
                    dep_result = {
                        "status": "warning",
                        "service": dep,
                        "errors": [str(dep_result)],
                    }

                result["dependencies"][dep] = dep_result
                result["summary"]["total_checks"] += 1

                if dep_result["status"] == "healthy":
                    result["summary"]["healthy"] += 1
                elif dep_result["status"] == "warning":
                    result["summary"]["warnings"] += 1
                    if result["status"] == "healthy":
                        result["status"] = "warning"
                else:
                    result["summary"]["errors"] += 1
                    result["status"] = "unhealthy"

        return result

    return mtls_check


def create_mtls_status_endpoint(
    service_name: str, dependencies: List[str] = None, domain: str = None
):
    """
    Create a dedicated mTLS status endpoint.

    Returns an endpoint that provides detailed mTLS-specific information.
    """
    validator = MTLSValidator(service_name, domain)
    dependencies = dependencies or []

    async def mtls_status_endpoint():
        """Detailed mTLS status endpoint"""
        try:
            # Get comprehensive mTLS status
            mtls_check = create_mtls_dependency_check(
                service_name, dependencies, domain
            )
            mtls_data = await mtls_check()

            # Add metadata
            mtls_data.update(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "service": service_name,
                    "domain": domain or validator.domain,
                    "dependencies_configured": dependencies,
                }
            )

            # Set appropriate HTTP status code
            if mtls_data["status"] == "unhealthy":
                return JSONResponse(status_code=503, content=mtls_data)
            elif mtls_data["status"] == "warning":
                return JSONResponse(status_code=200, content=mtls_data)
            else:
                return JSONResponse(status_code=200, content=mtls_data)

        except Exception as e:
            logger.exception("mTLS status endpoint failed")
            return JSONResponse(
                status_code=500,
                content={
                    "error": f"mTLS status check failed: {str(e)}",
                    "status": "unhealthy",
                    "service": service_name,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

    return mtls_status_endpoint

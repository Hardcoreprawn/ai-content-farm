"""
mTLS Communication Helper for Container Apps

Provides utilities for secure inter-service communication using mTLS
with certificate management through Azure Key Vault and Dapr.
"""

import logging
import os
import ssl
from typing import Optional, Dict, Any
import aiohttp
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


class MTLSClient:
    """Client for mTLS-enabled communication between services."""
    
    def __init__(self):
        self.cert_path = os.getenv("CERT_PATH", "/tmp/certs")
        self.key_vault_name = os.getenv("KEY_VAULT_NAME", "")
        self.cert_secret_name = os.getenv("CERT_SECRET_NAME", "mtls-wildcard-cert")
        self.mtls_enabled = os.getenv("MTLS_ENABLED", "false").lower() == "true"
        
        # Dapr configuration
        self.dapr_port = os.getenv("DAPR_HTTP_PORT", "3500")
        self.dapr_grpc_port = os.getenv("DAPR_GRPC_PORT", "50001")
        
        self._ssl_context = None
        self._setup_ssl_context()
    
    def _setup_ssl_context(self):
        """Set up SSL context for mTLS communication."""
        if not self.mtls_enabled:
            logger.info("mTLS disabled, using standard HTTPS")
            return
            
        try:
            # Create SSL context for client certificates
            self._ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            
            # Load client certificate and key if available
            cert_file = Path(self.cert_path) / "cert.pem"
            key_file = Path(self.cert_path) / "key.pem"
            
            if cert_file.exists() and key_file.exists():
                self._ssl_context.load_cert_chain(str(cert_file), str(key_file))
                logger.info("mTLS client certificates loaded successfully")
            else:
                logger.warning("mTLS certificates not found, attempting to fetch from Key Vault")
                self._fetch_certificates_from_keyvault()
                
        except Exception as e:
            logger.error(f"Failed to setup SSL context: {e}")
            self._ssl_context = None
    
    def _fetch_certificates_from_keyvault(self):
        """Fetch certificates from Azure Key Vault via Dapr secret store."""
        try:
            # Use Dapr secret store to fetch certificates
            dapr_url = f"http://localhost:{self.dapr_port}/v1.0/secrets/certificates/{self.cert_secret_name}"
            
            response = requests.get(dapr_url, timeout=10)
            response.raise_for_status()
            
            secret_data = response.json()
            
            # Save certificates to local files
            cert_dir = Path(self.cert_path)
            cert_dir.mkdir(parents=True, exist_ok=True)
            
            if "certificate" in secret_data:
                with open(cert_dir / "cert.pem", "w") as f:
                    f.write(secret_data["certificate"])
                    
            if "private_key" in secret_data:
                with open(cert_dir / "key.pem", "w") as f:
                    f.write(secret_data["private_key"])
            
            # Reload SSL context with new certificates
            if (cert_dir / "cert.pem").exists() and (cert_dir / "key.pem").exists():
                self._ssl_context.load_cert_chain(
                    str(cert_dir / "cert.pem"), 
                    str(cert_dir / "key.pem")
                )
                logger.info("mTLS certificates fetched and loaded from Key Vault")
            
        except Exception as e:
            logger.error(f"Failed to fetch certificates from Key Vault: {e}")
    
    async def call_service_async(self, service_name: str, method: str, path: str, 
                                data: Optional[Dict[str, Any]] = None, 
                                headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make async mTLS service call using Dapr service invocation."""
        
        # Use Dapr service invocation for mTLS
        dapr_url = f"http://localhost:{self.dapr_port}/v1.0/invoke/{service_name}/method{path}"
        
        call_headers = {"Content-Type": "application/json"}
        if headers:
            call_headers.update(headers)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method, 
                    dapr_url,
                    json=data,
                    headers=call_headers,
                    ssl=self._ssl_context if self.mtls_enabled else None,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response.raise_for_status()
                    return await response.json()
                    
        except Exception as e:
            logger.error(f"mTLS service call failed to {service_name}{path}: {e}")
            raise
    
    def call_service_sync(self, service_name: str, method: str, path: str,
                         data: Optional[Dict[str, Any]] = None,
                         headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make synchronous mTLS service call using Dapr service invocation."""
        
        # Use Dapr service invocation for mTLS
        dapr_url = f"http://localhost:{self.dapr_port}/v1.0/invoke/{service_name}/method{path}"
        
        call_headers = {"Content-Type": "application/json"}
        if headers:
            call_headers.update(headers)
        
        try:
            response = requests.request(
                method,
                dapr_url,
                json=data,
                headers=call_headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"mTLS service call failed to {service_name}{path}: {e}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """Perform mTLS health check."""
        health_status = {
            "mtls_enabled": self.mtls_enabled,
            "ssl_context_loaded": self._ssl_context is not None,
            "cert_path_exists": Path(self.cert_path).exists(),
            "dapr_available": False
        }
        
        # Check Dapr availability
        try:
            dapr_health_url = f"http://localhost:{self.dapr_port}/v1.0/healthz"
            response = requests.get(dapr_health_url, timeout=5)
            health_status["dapr_available"] = response.status_code == 200
        except Exception:
            pass
        
        return health_status


# Global mTLS client instance
mtls_client = MTLSClient()


# Convenience functions for service communication
async def call_content_collector(path: str, method: str = "GET", 
                               data: Optional[Dict] = None) -> Dict[str, Any]:
    """Call content-collector service with mTLS."""
    return await mtls_client.call_service_async("content-collector", method, path, data)


async def call_content_processor(path: str, method: str = "GET",
                               data: Optional[Dict] = None) -> Dict[str, Any]:
    """Call content-processor service with mTLS."""
    return await mtls_client.call_service_async("content-processor", method, path, data)


async def call_site_generator(path: str, method: str = "GET",
                            data: Optional[Dict] = None) -> Dict[str, Any]:
    """Call site-generator service with mTLS."""
    return await mtls_client.call_service_async("site-generator", method, path, data)


def get_mtls_health() -> Dict[str, Any]:
    """Get mTLS client health status."""
    return mtls_client.health_check()
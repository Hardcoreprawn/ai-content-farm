#!/usr/bin/env python3
"""
External API Client with Retry Logic

Implements tenacity-based retry patterns for OpenAI and other external APIs.
Supports multi-region failover and cost tracking.

Features:
- Exponential backoff with jitter
- Multi-region OpenAI endpoint failover
- Request/response logging
- Cost tracking per model
- Circuit breaker pattern
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx
from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import ContentProcessorSettings

logger = logging.getLogger(__name__)


class APIRegion(Enum):
    """Supported OpenAI regions."""

    UK_SOUTH = "uksouth"
    WEST_EUROPE = "westeurope"
    EAST_US = "eastus"
    WEST_US = "westus"


class ExternalAPIError(Exception):
    """Base exception for external API errors."""

    pass


class OpenAIAPIError(ExternalAPIError):
    """OpenAI-specific API errors."""

    pass


class RateLimitError(ExternalAPIError):
    """Rate limiting errors."""

    pass


class ExternalAPIClient:
    """
    High-level client for external API calls with retry logic.

    Handles OpenAI multi-region failover, cost tracking, and logging.
    """

    def __init__(self, settings: ContentProcessorSettings):
        self.settings = settings
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Track costs and performance
        self.request_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_cost": 0.0,
            "region_usage": {},
            "model_usage": {},
        }

        # Regional endpoints
        self.openai_endpoints = self._build_openai_endpoints()
        self.current_region_index = 0

        # HTTP client with proper timeouts
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10.0,
                read=60.0,
                write=30.0,
                pool=5.0,
            ),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
            ),
        )

    def _build_openai_endpoints(self) -> List[Dict[str, str]]:
        """Build list of OpenAI endpoints from configuration."""
        endpoints = []

        # Primary endpoint from config
        if self.settings.azure_openai_endpoint:
            endpoints.append(
                {
                    "name": "primary",
                    "endpoint": self.settings.azure_openai_endpoint,
                    "region": self._extract_region(self.settings.azure_openai_endpoint),
                    "api_key": self.settings.azure_openai_api_key or "",
                }
            )

        # Multi-region endpoints if configured
        for region in [APIRegion.UK_SOUTH, APIRegion.WEST_EUROPE]:
            region_endpoint = self.settings.get_openai_endpoint_for_region(region.value)
            if region_endpoint and region_endpoint not in [
                ep["endpoint"] for ep in endpoints
            ]:
                endpoints.append(
                    {
                        "name": f"secondary_{region.value}",
                        "endpoint": region_endpoint,
                        "region": region.value,
                        "api_key": self.settings.azure_openai_api_key or "",
                    }
                )

        # Log endpoint configuration (extract regions separately to avoid sensitive data flow)
        configured_regions = []

        # Primary endpoint region
        if self.settings.azure_openai_endpoint:
            configured_regions.append(
                self._extract_region(self.settings.azure_openai_endpoint)
            )

        # Multi-region endpoint regions
        for region in [APIRegion.UK_SOUTH, APIRegion.WEST_EUROPE]:
            region_endpoint = self.settings.get_openai_endpoint_for_region(region.value)
            if region_endpoint and region_endpoint not in [
                ep["endpoint"] for ep in endpoints
            ]:
                configured_regions.append(region.value)

        self.logger.info(
            f"Configured {len(configured_regions)} OpenAI endpoints: {configured_regions}"
        )
        return endpoints

    def _extract_region(self, endpoint: str) -> str:
        """Extract region from Azure OpenAI endpoint URL."""
        # Extract region from URL like https://xxx.uksouth.cognitiveservices.azure.com/
        try:
            parts = endpoint.replace("https://", "").split(".")
            if len(parts) >= 2:
                return parts[1]  # uksouth, westeurope, etc.
        except Exception:
            pass
        return "unknown"

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()

    @asynccontextmanager
    async def get_client(self):
        """Context manager for HTTP client."""
        try:
            yield self.http_client
        finally:
            pass  # Don't close in context manager, let close() handle it

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.ConnectError, RateLimitError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
        reraise=True,
    )
    async def _make_openai_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        endpoint_override: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make authenticated request to OpenAI API with retry logic.

        Args:
            method: HTTP method
            path: API path (e.g., "/chat/completions")
            data: Request body
            headers: Additional headers
            endpoint_override: Specific endpoint to use (for region failover)

        Returns:
            API response data

        Raises:
            OpenAIAPIError: On API errors
            RateLimitError: On rate limiting
        """
        # Select endpoint (failover support)
        endpoint = endpoint_override or self._get_current_openai_endpoint()
        if not endpoint:
            raise OpenAIAPIError("No OpenAI endpoints configured")

        # Build request
        url = f"{endpoint['endpoint'].rstrip('/')}{path}"
        request_headers = {
            "api-key": endpoint["api_key"],
            "Content-Type": "application/json",
            **(headers or {}),
        }

        start_time = time.time()

        try:
            # Secure logging - never log headers containing API keys or sensitive data
            self.logger.debug(
                f"Making {method} request to {endpoint['region']}: {path} (url redacted for security)"
            )

            async with self.get_client() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=request_headers,
                )

            # Track request stats
            duration = time.time() - start_time
            self._track_request_stats(endpoint["region"], duration, True)

            # Handle response
            if response.status_code == 429:
                self.logger.warning(f"Rate limited by {endpoint['region']}")
                raise RateLimitError("Rate limited")

            if response.status_code >= 400:
                error_msg = f"OpenAI API error {response.status_code}"
                self.logger.error(error_msg)
                raise OpenAIAPIError(error_msg)

            response_data = response.json()
            self.logger.debug(
                f"Successful request to {endpoint['region']} in {duration:.2f}s"
            )

            return response_data

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            self._track_request_stats(
                endpoint["region"], time.time() - start_time, False
            )
            self.logger.warning(
                f"Connection error to {endpoint['region']}: Connection failed"
            )
            raise OpenAIAPIError("Connection failed")

        except Exception as e:
            self._track_request_stats(
                endpoint["region"], time.time() - start_time, False
            )
            self.logger.error(
                f"Unexpected error with {endpoint['region']}: Request failed"
            )
            raise OpenAIAPIError("Request failed")

    def _get_current_openai_endpoint(self) -> Optional[Dict[str, str]]:
        """Get current OpenAI endpoint for round-robin usage."""
        if not self.openai_endpoints:
            return None

        endpoint = self.openai_endpoints[self.current_region_index]
        self.current_region_index = (self.current_region_index + 1) % len(
            self.openai_endpoints
        )
        return endpoint

    def _track_request_stats(self, region: str, duration: float, success: bool):
        """Track request statistics for monitoring."""
        self.request_stats["total_requests"] += 1

        if success:
            self.request_stats["successful_requests"] += 1
        else:
            self.request_stats["failed_requests"] += 1

        # Track region usage
        if region not in self.request_stats["region_usage"]:
            self.request_stats["region_usage"][region] = {
                "requests": 0,
                "total_duration": 0.0,
                "avg_duration": 0.0,
            }

        region_stats = self.request_stats["region_usage"][region]
        region_stats["requests"] += 1
        region_stats["total_duration"] += duration
        region_stats["avg_duration"] = (
            region_stats["total_duration"] / region_stats["requests"]
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create chat completion with retry logic and region failover.

        Args:
            messages: Chat messages
            model: Model name
            max_tokens: Maximum tokens
            temperature: Response temperature
            **kwargs: Additional parameters

        Returns:
            OpenAI chat completion response
        """
        data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }

        # Try all regions with failover
        last_error = None
        for attempt, endpoint in enumerate(self.openai_endpoints):
            try:
                self.logger.info(
                    f"Attempting chat completion with {endpoint['region']} (attempt {attempt + 1})"
                )

                response = await self._make_openai_request(
                    method="POST",
                    path="/openai/deployments/{model}/chat/completions".format(
                        model=model
                    ),
                    data=data,
                    endpoint_override=endpoint,
                )

                # Track model usage
                self._track_model_usage(model, response.get("usage", {}))

                return response

            except (OpenAIAPIError, RateLimitError) as e:
                last_error = e
                self.logger.warning(f"Failed with {endpoint['region']}: Request failed")

                # If not the last endpoint, try next region
                if attempt < len(self.openai_endpoints) - 1:
                    self.logger.info(f"Failing over to next region...")
                    await asyncio.sleep(1)  # Brief delay between failovers
                    continue

        # All regions failed
        raise OpenAIAPIError("All OpenAI regions failed")

    def _track_model_usage(self, model: str, usage: Dict[str, Any]):
        """Track model usage for cost estimation."""
        if model not in self.request_stats["model_usage"]:
            self.request_stats["model_usage"][model] = {
                "requests": 0,
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }

        model_stats = self.request_stats["model_usage"][model]
        model_stats["requests"] += 1
        model_stats["total_tokens"] += usage.get("total_tokens", 0)
        model_stats["prompt_tokens"] += usage.get("prompt_tokens", 0)
        model_stats["completion_tokens"] += usage.get("completion_tokens", 0)

    async def embeddings(
        self, input_text: str, model: str = "text-embedding-ada-002", **kwargs
    ) -> Dict[str, Any]:
        """
        Create embeddings with retry logic.

        Args:
            input_text: Text to embed
            model: Embedding model
            **kwargs: Additional parameters

        Returns:
            OpenAI embeddings response
        """
        data = {
            "model": model,
            "input": input_text,
            **kwargs,
        }

        response = await self._make_openai_request(
            method="POST",
            path="/openai/deployments/{model}/embeddings".format(model=model),
            data=data,
        )

        self._track_model_usage(model, response.get("usage", {}))
        return response

    def get_stats(self) -> Dict[str, Any]:
        """Get current request statistics."""
        return {
            **self.request_stats,
            "success_rate": (
                self.request_stats["successful_requests"]
                / max(self.request_stats["total_requests"], 1)
            )
            * 100,
            "configured_regions": len(self.openai_endpoints),
        }

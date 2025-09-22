"""
Simplified Content Collector Base Classes - ACTIVE

CURRENT ARCHITECTURE: Simple, reliable base classes for content collection
Status: ACTIVE - Core component of the simplified collector system

Replaces complex adaptive strategies with simple retry logic and exponential backoff.
Provides HTTP client management and standardized error handling.

Features:
- Simple retry logic with exponential backoff
- HTTP client context management
- Standardized item format conversion
- Basic health checking
- Clean error handling without complex state

Simple, testable collectors without complex adaptive strategies.
Focus on reliability and ease of testing.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


class CollectorError(Exception):
    """Base exception for collector errors."""

    def __init__(self, message: str, source: str = "", retryable: bool = True):
        super().__init__(message)
        self.source = source
        self.retryable = retryable


class RateLimitError(CollectorError):
    """Rate limit exceeded."""

    def __init__(self, message: str, retry_after: int = 60, source: str = ""):
        super().__init__(message, source, retryable=True)
        self.retry_after = retry_after


class SimpleCollector(ABC):
    """
    Simple base collector with built-in retry logic and rate limiting.

    No complex adaptive strategies - just simple, reliable collection.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Simple retry configuration
        self.max_retries = self.config.get("max_retries", 3)
        self.base_delay = self.config.get("base_delay", 1.0)
        self.max_delay = self.config.get("max_delay", 300.0)
        self.backoff_multiplier = self.config.get("backoff_multiplier", 2.0)

        # Request configuration
        self.timeout = self.config.get("timeout", 30.0)
        self.max_items = self.config.get("max_items", 50)

        logger.info(f"Initialized {self.get_source_name()} collector")

    @abstractmethod
    def get_source_name(self) -> str:
        """Return the name of this content source."""
        pass

    @abstractmethod
    async def collect_batch(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Collect a batch of content items.

        This is the main method that subclasses must implement.
        Should return a list of standardized content items.
        """
        pass

    async def collect_with_retry(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Collect content with automatic retry logic.

        Handles rate limiting, temporary failures, and exponential backoff.
        """
        last_exception = None
        delay = self.base_delay

        for attempt in range(self.max_retries + 1):
            try:
                logger.info(
                    f"Collecting from {self.get_source_name()} "
                    f"(attempt {attempt + 1}/{self.max_retries + 1})"
                )

                items = await self.collect_batch(**kwargs)

                source_name = self.get_source_name()
                logger.info(
                    f"Successfully collected {len(items)} items from {source_name}"
                )
                return items

            except RateLimitError as e:
                logger.warning(
                    f"Rate limited by {self.get_source_name()}: {e}. "
                    f"Waiting {e.retry_after} seconds"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(e.retry_after)
                last_exception = e

            except CollectorError as e:
                if not e.retryable or attempt >= self.max_retries:
                    logger.error(
                        f"Non-retryable error from {self.get_source_name()}: {e}"
                    )
                    raise

                logger.warning(
                    f"Retryable error from {self.get_source_name()}: {e}. "
                    f"Retrying in {delay} seconds"
                )
                await asyncio.sleep(delay)
                delay = min(delay * self.backoff_multiplier, self.max_delay)
                last_exception = e

            except Exception as e:
                logger.error(f"Unexpected error from {self.get_source_name()}: {e}")
                if attempt >= self.max_retries:
                    raise CollectorError(
                        f"Failed after {self.max_retries} retries: {e}",
                        self.get_source_name(),
                        retryable=False,
                    )

                await asyncio.sleep(delay)
                delay = min(delay * self.backoff_multiplier, self.max_delay)
                last_exception = e

        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        else:
            raise CollectorError(
                f"Collection failed after {self.max_retries} retries",
                self.get_source_name(),
                retryable=False,
            )

    def standardize_item(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert source-specific item format to standard format.

        Override this in subclasses to handle source-specific data structures.
        """
        return {
            "id": raw_item.get("id", ""),
            "title": raw_item.get("title", ""),
            "content": raw_item.get("content", ""),
            "url": raw_item.get("url", ""),
            "author": raw_item.get("author", ""),
            "created_at": raw_item.get(
                "created_at", datetime.now(timezone.utc).isoformat()
            ),
            "source": self.get_source_name(),
            "metadata": raw_item.get("metadata", {}),
        }

    async def health_check(self) -> Tuple[bool, str]:
        """
        Check if the source is accessible.

        Override in subclasses for source-specific health checks.
        """
        try:
            # Default implementation - try to collect one item
            await self.collect_batch(max_items=1)
            return True, f"{self.get_source_name()} is accessible"
        except Exception as e:
            return False, f"{self.get_source_name()} health check failed: {e}"


class HTTPCollector(SimpleCollector):
    """Base class for HTTP-based collectors (Reddit, Mastodon, RSS, etc.)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # HTTP client configuration
        self.user_agent = self.config.get(
            "user_agent", "PersonalContentCurator/1.0 (Educational/Personal Use)"
        )

        # Create HTTP client
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"User-Agent": self.user_agent},
            follow_redirects=True,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def get_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP GET request and return JSON response.

        Handles common HTTP errors and rate limiting.
        """
        try:
            response = await self.client.get(url, **kwargs)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("retry-after", 60))
                raise RateLimitError(
                    f"Rate limited by {url}",
                    retry_after=retry_after,
                    source=self.get_source_name(),
                )

            # Handle authentication errors
            if response.status_code == 401:
                raise CollectorError(
                    f"Authentication failed for {url}",
                    source=self.get_source_name(),
                    retryable=False,
                )

            # Handle other HTTP errors
            if response.status_code >= 400:
                raise CollectorError(
                    f"HTTP {response.status_code} error from {url}: {response.text}",
                    source=self.get_source_name(),
                    retryable=response.status_code >= 500,  # 5xx errors are retryable
                )

            return response.json()

        except httpx.RequestError as e:
            raise CollectorError(
                f"Request error for {url}: {e}",
                source=self.get_source_name(),
                retryable=True,
            )

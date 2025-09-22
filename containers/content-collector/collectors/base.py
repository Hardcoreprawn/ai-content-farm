"""
Base Collector Classes - LEGACY

DEPRECATED: These base classes are replaced by simple_base.py
Contains complex adaptive collection strategies that were causing CI/CD failures.
Status: PENDING REMOVAL - Use simple_base.py instead

Abstract base classes and mixins for content source collectors.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

# Import adaptive collection framework
from .adaptive_strategy import (
    AdaptiveCollectionStrategy,
    SourceHealth,
    StrategyParameters,
)

logger = logging.getLogger(__name__)


class SourceCollector(ABC):
    """Abstract base class for content source collectors with adaptive collection support."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Initialize adaptive collection strategy using collector's own strategy
        self.adaptive_strategy = self._create_adaptive_strategy()

        logger.info(
            f"Initialized {self.get_source_name()} collector with adaptive strategy"
        )

    def _create_adaptive_strategy(self):
        """Create the adaptive strategy for this collector. Override in subclasses."""
        # Default implementation - subclasses should override this method
        return self._get_default_strategy()

    def _get_default_strategy(self):
        """Get a default fallback strategy if collector doesn't define its own."""
        from .adaptive_strategy import AdaptiveCollectionStrategy, StrategyParameters

        # Create a basic strategy as fallback
        class DefaultCollectionStrategy(AdaptiveCollectionStrategy):
            def get_collection_parameters(self):
                return {"max_items": 50, "depth": 2}

        default_params = StrategyParameters(
            base_delay=2.0,
            min_delay=1.0,
            max_delay=300.0,
            backoff_multiplier=2.0,
            success_reduction_factor=0.9,
            rate_limit_buffer=0.2,
            max_requests_per_window=30,
            window_duration=60,
            health_check_interval=300,
            adaptation_sensitivity=0.1,
        )

        return DefaultCollectionStrategy(self.get_source_name(), default_params)

    def _get_strategy_parameters(self) -> StrategyParameters:
        """
        Get source-specific strategy parameters. Override in subclasses for customization.

        Returns:
            StrategyParameters configured for this source type
        """
        # Default conservative parameters - subclasses can override
        return StrategyParameters(
            base_delay=2.0,
            min_delay=1.0,
            max_delay=300.0,
            backoff_multiplier=2.0,
            success_reduction_factor=0.9,
            rate_limit_buffer=0.2,
            max_requests_per_window=30,
            window_duration=60,
            health_check_interval=300,
            adaptation_sensitivity=0.1,
        )

    async def collect_content_adaptive(
        self, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Collect content using adaptive rate limiting and error handling.

        Args:
            params: Source-specific parameters

        Returns:
            List of content items
        """
        # Apply pre-request delay and get adaptive parameters
        await self.adaptive_strategy.before_request()
        adaptive_params = await self.adaptive_strategy.get_collection_parameters()

        # Merge adaptive parameters with provided parameters
        merged_params = {**params, **adaptive_params}

        start_time = time.time()
        success = False
        status_code = None
        headers = {}
        content = []
        error = None

        try:
            # Call the source-specific collection method
            content = await self.collect_content(merged_params)
            success = True
            status_code = 200  # Assume success if no exception

        except Exception as e:
            error = e
            success = False
            # Try to extract status code from common HTTP exceptions
            if hasattr(e, "response") and hasattr(e.response, "status_code"):
                status_code = e.response.status_code
                if hasattr(e.response, "headers"):
                    headers = dict(e.response.headers)
            else:
                status_code = 500  # Generic server error

            logger.warning(f"Collection failed for {self.get_source_name()}: {e}")

        finally:
            # Record the request result for adaptive learning
            response_time = time.time() - start_time
            await self.adaptive_strategy.after_request(
                success=success,
                response_time=response_time,
                status_code=status_code,
                headers=headers,
                error=error,
            )

        return content

    def get_health_status(self) -> SourceHealth:
        """Get the current health status of this collector."""
        return self.adaptive_strategy.session_metrics.health_status

    def get_current_delay(self) -> float:
        """Get the current adaptive delay for this collector."""
        return self.adaptive_strategy.current_delay

    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of collection metrics and performance."""
        return await self.adaptive_strategy.get_metrics_summary()

    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of this source."""
        pass

    @abstractmethod
    async def check_connectivity(self) -> Tuple[bool, str]:
        """
        Check if the source is accessible.

        Returns:
            Tuple of (is_accessible, status_message)
        """
        pass

    @abstractmethod
    async def check_authentication(self) -> Tuple[bool, str]:
        """
        Check if authentication is properly configured.

        Returns:
            Tuple of (is_authenticated, status_message)
        """
        pass

    @abstractmethod
    async def collect_content(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Collect content from the source.

        Args:
            params: Source-specific parameters

        Returns:
            List of content items
        """
        pass


class InternetConnectivityMixin:
    """Mixin for basic internet connectivity checks."""

    def check_internet_connectivity(
        self, test_urls: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        Check basic internet connectivity.

        Args:
            test_urls: URLs to test connectivity against

        Returns:
            Tuple of (has_internet, status_message)
        """
        if test_urls is None:
            test_urls = [
                "https://httpbin.org/status/200",
                "https://www.google.com",
                "https://www.reddit.com",
            ]

        for url in test_urls:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    return True, f"Internet connectivity confirmed via {url}"
            except Exception as e:
                logger.debug(f"Failed to connect to {url}: {e}")
                continue

        return False, "No internet connectivity detected"

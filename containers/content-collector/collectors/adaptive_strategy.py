"""
Adaptive Collection Strategy Framework - LEGACY

DEPRECATED: Complex adaptive strategies causing CI/CD test failures
Status: PENDING REMOVAL - Replaced by simple retry logic in simple_base.py

Provides intelligent, feedback-driven collection strategies that learn and adapt
to each source's rate limits, response patterns, and requirements in real-time.

Updated to use Azure Blob Storage for persistent metrics storage.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .blob_metrics_storage import get_metrics_storage

logger = logging.getLogger(__name__)


class SourceHealth(Enum):
    """Source health status based on recent performance."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    BLOCKED = "blocked"


class AdaptationSignal(Enum):
    """Signals that trigger strategy adaptation."""

    RATE_LIMIT_HIT = "rate_limit_hit"
    SUCCESS_STREAK = "success_streak"
    ERROR_SPIKE = "error_spike"
    SLOW_RESPONSE = "slow_response"
    AUTHENTICATION_FAILURE = "auth_failure"
    CONTENT_QUALITY_DROP = "quality_drop"


@dataclass
class CollectionMetrics:
    """Metrics for tracking collection performance."""

    source_name: str
    timestamp: datetime
    request_count: int
    success_count: int
    error_count: int
    rate_limit_count: int
    avg_response_time: float
    current_rate_limit: Optional[int]
    rate_limit_reset: Optional[datetime]
    health_status: SourceHealth
    adaptive_delay: float
    success_rate: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["rate_limit_reset"] = (
            self.rate_limit_reset.isoformat() if self.rate_limit_reset else None
        )
        data["health_status"] = self.health_status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollectionMetrics":
        """Create from dictionary."""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if data.get("rate_limit_reset"):
            data["rate_limit_reset"] = datetime.fromisoformat(data["rate_limit_reset"])
        data["health_status"] = SourceHealth(data["health_status"])
        return cls(**data)


@dataclass
class StrategyParameters:
    """Adaptive parameters for collection strategy."""

    base_delay: float = 1.0
    min_delay: float = 0.5
    max_delay: float = 300.0
    backoff_multiplier: float = 2.0
    success_reduction_factor: float = 0.8
    rate_limit_buffer: float = 0.1  # 10% safety buffer
    max_requests_per_window: int = 50
    window_duration: int = 60  # seconds
    health_check_interval: int = 300  # seconds
    adaptation_sensitivity: float = 0.1


class AdaptiveCollectionStrategy(ABC):
    """Base class for adaptive collection strategies."""

    def __init__(
        self, source_name: str, strategy_params: Optional[StrategyParameters] = None
    ):
        self.source_name = source_name
        self.params = strategy_params or StrategyParameters()
        self.strategy_key = f"{source_name}_{hash(source_name) % 10000}"

        # Get blob storage for metrics
        self.metrics_storage = get_metrics_storage()

        # Runtime state
        self.current_delay = self.params.base_delay
        self.request_history: List[Tuple[datetime, bool, float]] = []
        self.rate_limit_info: Optional[Tuple[int, datetime]] = None
        self.last_health_check = datetime.now()
        self.consecutive_successes = 0
        self.consecutive_errors = 0

        # Metrics
        self.session_metrics = CollectionMetrics(
            source_name=source_name,
            timestamp=datetime.now(),
            request_count=0,
            success_count=0,
            error_count=0,
            rate_limit_count=0,
            avg_response_time=0.0,
            current_rate_limit=None,
            rate_limit_reset=None,
            health_status=SourceHealth.HEALTHY,
            adaptive_delay=self.current_delay,
            success_rate=1.0,
        )

    async def before_request(self) -> None:
        """Called before making a request. Implements adaptive delay."""
        await self._load_historical_metrics()
        await self._check_rate_limits()

        # Apply adaptive delay
        if self.current_delay > 0:
            logger.debug(
                f"[{self.source_name}] Adaptive delay: {self.current_delay:.2f}s"
            )
            await asyncio.sleep(self.current_delay)

    async def after_request(
        self,
        success: bool,
        response_time: float,
        status_code: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        error: Optional[Exception] = None,
    ) -> None:
        """Called after a request. Updates metrics and adapts strategy."""
        now = datetime.now()

        # Record request
        self.request_history.append((now, success, response_time))
        self.session_metrics.request_count += 1

        if success:
            self.session_metrics.success_count += 1
            self.consecutive_successes += 1
            self.consecutive_errors = 0
        else:
            self.session_metrics.error_count += 1
            self.consecutive_errors += 1
            self.consecutive_successes = 0

            # Check for rate limiting
            if status_code == 429 or (error and "rate limit" in str(error).lower()):
                self.session_metrics.rate_limit_count += 1
                await self._handle_rate_limit(headers)

        # Update metrics
        self._update_metrics(response_time)

        # Extract rate limit info from headers
        if headers:
            await self._extract_rate_limit_info(headers)

        # Adapt strategy based on feedback
        await self._adapt_strategy(success, status_code, error)

        # Persist metrics periodically
        if self.session_metrics.request_count % 10 == 0:
            await self._save_metrics()

    def _update_metrics(self, response_time: float) -> None:
        """Update performance metrics."""
        # Update average response time
        total_time = (
            self.session_metrics.avg_response_time
            * (self.session_metrics.request_count - 1)
            + response_time
        )
        self.session_metrics.avg_response_time = (
            total_time / self.session_metrics.request_count
        )

        # Update success rate
        self.session_metrics.success_rate = (
            self.session_metrics.success_count / self.session_metrics.request_count
        )

        # Update health status
        self._assess_health()

    def _assess_health(self) -> None:
        """Assess current source health based on metrics."""
        if self.session_metrics.rate_limit_count > 0:
            if (
                self.session_metrics.rate_limit_count
                / self.session_metrics.request_count
                > 0.1
            ):
                self.session_metrics.health_status = SourceHealth.RATE_LIMITED
            else:
                self.session_metrics.health_status = SourceHealth.DEGRADED
        elif self.session_metrics.success_rate < 0.5:
            self.session_metrics.health_status = SourceHealth.ERROR
        elif self.session_metrics.success_rate < 0.8:
            self.session_metrics.health_status = SourceHealth.DEGRADED
        elif self.consecutive_errors > 5:
            self.session_metrics.health_status = SourceHealth.ERROR
        else:
            self.session_metrics.health_status = SourceHealth.HEALTHY

    async def _adapt_strategy(
        self, success: bool, status_code: Optional[int], error: Optional[Exception]
    ) -> None:
        """Adapt collection strategy based on feedback."""
        if success:
            await self._handle_success()
        else:
            await self._handle_error(status_code, error)

        # Update strategy parameters
        self.session_metrics.adaptive_delay = self.current_delay

    async def _handle_success(self) -> None:
        """Handle successful request - potentially reduce delay."""
        if self.consecutive_successes >= 3:
            # Reduce delay after consecutive successes
            old_delay = self.current_delay
            self.current_delay = max(
                self.params.min_delay,
                self.current_delay * self.params.success_reduction_factor,
            )

            if old_delay != self.current_delay:
                logger.info(
                    f"[{self.source_name}] Reduced delay: {old_delay:.2f}s → {self.current_delay:.2f}s "
                    f"(consecutive successes: {self.consecutive_successes})"
                )

    async def _handle_error(
        self, status_code: Optional[int], error: Optional[Exception]
    ) -> None:
        """Handle error - increase delay and implement backoff."""
        old_delay = self.current_delay

        if status_code == 429:  # Rate limited
            self.current_delay = min(
                self.params.max_delay,
                self.current_delay
                * self.params.backoff_multiplier
                * 2,  # More aggressive for rate limits
            )
        elif status_code and 400 <= status_code < 500:  # Client errors
            self.current_delay = min(
                self.params.max_delay,
                self.current_delay * self.params.backoff_multiplier,
            )
        elif self.consecutive_errors >= 2:  # Server errors or consecutive failures
            self.current_delay = min(
                self.params.max_delay,
                self.current_delay * self.params.backoff_multiplier,
            )

        if old_delay != self.current_delay:
            logger.warning(
                f"[{self.source_name}] Increased delay: {old_delay:.2f}s → {self.current_delay:.2f}s "
                f"(status: {status_code}, consecutive errors: {self.consecutive_errors})"
            )

    async def _handle_rate_limit(self, headers: Optional[Dict[str, str]]) -> None:
        """Handle rate limit response."""
        if not headers:
            return

        # Try to extract rate limit reset time
        reset_time = None
        for header_name in ["x-ratelimit-reset", "retry-after", "x-rate-limit-reset"]:
            if header_name in headers:
                try:
                    reset_value = headers[header_name]
                    if header_name == "retry-after":
                        reset_time = datetime.now() + timedelta(
                            seconds=int(reset_value)
                        )
                    else:
                        reset_time = datetime.fromtimestamp(int(reset_value))
                    break
                except (ValueError, TypeError):
                    continue

        if reset_time:
            self.rate_limit_info = (
                self.session_metrics.current_rate_limit or 0,
                reset_time,
            )
            wait_time = (reset_time - datetime.now()).total_seconds()
            if wait_time > 0:
                self.current_delay = max(
                    self.current_delay, wait_time + 5
                )  # Add 5s buffer
                logger.warning(
                    f"[{self.source_name}] Rate limit hit. Waiting until {reset_time} "
                    f"(delay increased to {self.current_delay:.2f}s)"
                )

    async def _extract_rate_limit_info(self, headers: Dict[str, str]) -> None:
        """Extract rate limit information from response headers."""
        # Common rate limit headers
        rate_limit_headers = {
            "x-ratelimit-limit": "limit",
            "x-ratelimit-remaining": "remaining",
            "x-ratelimit-reset": "reset",
            "x-rate-limit-limit": "limit",
            "x-rate-limit-remaining": "remaining",
            "x-rate-limit-reset": "reset",
        }

        limit = remaining = reset = None

        for header, info_type in rate_limit_headers.items():
            if header in headers:
                try:
                    value = int(headers[header])
                    if info_type == "limit":
                        limit = value
                    elif info_type == "remaining":
                        remaining = value
                    elif info_type == "reset":
                        reset = datetime.fromtimestamp(value)
                except (ValueError, TypeError):
                    continue

        if limit:
            self.session_metrics.current_rate_limit = limit
        if reset:
            self.session_metrics.rate_limit_reset = reset

        # Adapt based on remaining requests
        if limit and remaining is not None:
            usage_rate = (limit - remaining) / limit
            if usage_rate > (1 - self.params.rate_limit_buffer):
                # Getting close to rate limit
                old_delay = self.current_delay
                self.current_delay = min(
                    self.params.max_delay, self.current_delay * 1.5
                )
                if old_delay != self.current_delay:
                    logger.info(
                        f"[{self.source_name}] Approaching rate limit "
                        f"({remaining}/{limit} remaining). "
                        f"Increased delay to {self.current_delay:.2f}s"
                    )

    async def _check_rate_limits(self) -> None:
        """Check if we're still under rate limits."""
        if self.rate_limit_info:
            limit, reset_time = self.rate_limit_info
            if datetime.now() >= reset_time:
                logger.info(
                    f"[{self.source_name}] Rate limit reset. Resuming normal operation."
                )
                self.rate_limit_info = None
                self.current_delay = self.params.base_delay

    async def _save_metrics(self) -> None:
        """Save metrics to blob storage for persistence."""
        try:
            metrics_data = self.session_metrics.to_dict()
            strategy_params = asdict(self.params)

            await self.metrics_storage.save_strategy_metrics(
                self.strategy_key, metrics_data, strategy_params
            )
        except Exception as e:
            logger.warning(f"Failed to save metrics for {self.source_name}: {e}")

    async def _load_historical_metrics(self) -> None:
        """Load historical metrics from blob storage if available."""
        try:
            historical_data = await self.metrics_storage.load_strategy_metrics(
                self.strategy_key
            )

            if historical_data and "metrics" in historical_data:
                historical_metrics = CollectionMetrics.from_dict(
                    historical_data["metrics"]
                )

                # Use historical adaptive delay as starting point
                if historical_metrics.adaptive_delay > 0:
                    self.current_delay = min(
                        self.params.max_delay,
                        max(self.params.min_delay, historical_metrics.adaptive_delay),
                    )
                    logger.info(
                        f"[{self.source_name}] Loaded historical delay: {self.current_delay:.2f}s"
                    )

                # Restore other relevant state if recent enough
                if historical_data.get("timestamp"):
                    last_save = datetime.fromisoformat(historical_data["timestamp"])
                    if (
                        datetime.now() - last_save
                    ).total_seconds() < 3600:  # Within last hour
                        # Restore rate limit info if still valid
                        if historical_metrics.rate_limit_reset:
                            if historical_metrics.rate_limit_reset > datetime.now():
                                self.rate_limit_info = (
                                    historical_metrics.current_rate_limit or 0,
                                    historical_metrics.rate_limit_reset,
                                )
                                logger.info(
                                    f"[{self.source_name}] Restored rate limit info: "
                                    f"reset at {historical_metrics.rate_limit_reset}"
                                )

        except Exception as e:
            logger.debug(
                f"Could not load historical metrics for {self.source_name}: {e}"
            )

    @abstractmethod
    async def get_collection_parameters(self) -> Dict[str, Any]:
        """Get current collection parameters based on strategy."""
        pass

    def get_health_status(self) -> SourceHealth:
        """Get current health status."""
        return self.session_metrics.health_status

    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of current metrics."""
        return {
            "source": self.source_name,
            "health": self.session_metrics.health_status.value,
            "success_rate": self.session_metrics.success_rate,
            "avg_response_time": self.session_metrics.avg_response_time,
            "adaptive_delay": self.current_delay,
            "requests_made": self.session_metrics.request_count,
            "rate_limit_hits": self.session_metrics.rate_limit_count,
            "consecutive_successes": self.consecutive_successes,
            "consecutive_errors": self.consecutive_errors,
        }

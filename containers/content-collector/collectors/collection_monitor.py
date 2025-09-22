"""
Collection Response Monitor - LEGACY

DEPRECATED: Complex monitoring system for adaptive strategies
Status: PENDING REMOVAL - Not needed with simplified collectors

Provided comprehensive monitoring for complex adaptive collection strategies.
Simplified collectors use basic logging instead.

Provides comprehensive monitoring and feedback collection for all source types,
integrating with the adaptive strategy system to provide real-time adjustments.

Updated to use Azure Blob Storage for persistent metrics storage.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

from .adaptive_strategy import (
    AdaptationSignal,
    AdaptiveCollectionStrategy,
    SourceHealth,
)
from .blob_metrics_storage import get_metrics_storage
from .source_strategies import StrategyFactory

logger = logging.getLogger(__name__)


@dataclass
class ResponseMetrics:
    """Detailed metrics for a single response."""

    timestamp: datetime
    source_type: str
    source_identifier: str  # URL, subreddit, etc.
    status_code: Optional[int]
    response_time: float
    content_length: int
    success: bool
    error_type: Optional[str]
    error_message: Optional[str]
    rate_limit_hit: bool
    headers: Dict[str, str]


class CollectionMonitor:
    """Monitors collection performance and provides feedback to strategies."""

    def __init__(self):
        self.metrics_storage = get_metrics_storage()
        self.active_strategies: Dict[str, AdaptiveCollectionStrategy] = {}
        self.response_history: List[ResponseMetrics] = []
        self.global_metrics = {
            "total_requests": 0,
            "total_successes": 0,
            "total_errors": 0,
            "avg_response_time": 0.0,
            "error_rate": 0.0,
        }

    async def register_source(
        self,
        source_type: str,
        source_identifier: str,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Register a source for monitoring and get strategy key."""
        strategy_key = f"{source_type}:{source_identifier}"

        if strategy_key not in self.active_strategies:
            # Create strategy for this source
            strategy = StrategyFactory.create_strategy(
                source_type=source_type,
                source_name=source_identifier,
                custom_params=custom_params,
            )
            self.active_strategies[strategy_key] = strategy
            logger.info(f"Registered strategy for {strategy_key}")

        return strategy_key

    async def before_request(self, strategy_key: str) -> Dict[str, Any]:
        """Called before making a request. Returns collection parameters."""
        if strategy_key not in self.active_strategies:
            raise ValueError(f"Strategy {strategy_key} not registered")

        strategy = self.active_strategies[strategy_key]
        await strategy.before_request()
        return await strategy.get_collection_parameters()

    async def after_request(
        self,
        strategy_key: str,
        response_data: Dict[str, Any],
        content_collected: int = 0,
        errors: Optional[List[str]] = None,
    ) -> None:
        """Called after a request completes."""
        if strategy_key not in self.active_strategies:
            logger.warning(f"Strategy {strategy_key} not found for after_request")
            return

        strategy = self.active_strategies[strategy_key]

        # Extract response metrics
        success = response_data.get("success", False)
        response_time = response_data.get("response_time", 0.0)
        status_code = response_data.get("status_code")
        headers = response_data.get("headers", {})
        error = response_data.get("error")

        # Record detailed metrics
        source_type, source_identifier = strategy_key.split(":", 1)
        metrics = ResponseMetrics(
            timestamp=datetime.now(),
            source_type=source_type,
            source_identifier=source_identifier,
            status_code=status_code,
            response_time=response_time,
            content_length=response_data.get("content_length", 0),
            success=success,
            error_type=type(error).__name__ if error else None,
            error_message=str(error) if error else None,
            rate_limit_hit=status_code == 429
            or (error and "rate limit" in str(error).lower()),
            headers=headers,
        )

        self.response_history.append(metrics)
        await self._update_global_metrics(metrics)

        # Update strategy
        await strategy.after_request(
            success=success,
            response_time=response_time,
            status_code=status_code,
            headers=headers,
            error=error,
        )

        # Analyze for adaptation signals
        await self._analyze_for_adaptation_signals(strategy_key, metrics)

        # Log significant events
        await self._log_significant_events(strategy_key, metrics, content_collected)

    async def _update_global_metrics(self, metrics: ResponseMetrics) -> None:
        """Update global collection metrics."""
        self.global_metrics["total_requests"] += 1

        if metrics.success:
            self.global_metrics["total_successes"] += 1
        else:
            self.global_metrics["total_errors"] += 1

        # Update average response time
        total_requests = self.global_metrics["total_requests"]
        current_avg = self.global_metrics["avg_response_time"]
        self.global_metrics["avg_response_time"] = (
            current_avg * (total_requests - 1) + metrics.response_time
        ) / total_requests

        # Update error rate
        self.global_metrics["error_rate"] = (
            self.global_metrics["total_errors"] / total_requests
        )

    async def _analyze_for_adaptation_signals(
        self, strategy_key: str, metrics: ResponseMetrics
    ) -> None:
        """Analyze response for adaptation signals."""
        signals = []

        # Rate limiting detection
        if metrics.rate_limit_hit:
            signals.append(AdaptationSignal.RATE_LIMIT_HIT)

        # Slow response detection
        if metrics.response_time > 10.0:
            signals.append(AdaptationSignal.SLOW_RESPONSE)

        # Authentication failure detection
        if metrics.status_code in [401, 403]:
            signals.append(AdaptationSignal.AUTHENTICATION_FAILURE)

        # Error spike detection (check recent history)
        recent_errors = [
            m
            for m in self.response_history[-10:]
            if m.source_identifier == metrics.source_identifier and not m.success
        ]
        if len(recent_errors) >= 3:
            signals.append(AdaptationSignal.ERROR_SPIKE)

        # Success streak detection
        recent_successes = [
            m
            for m in self.response_history[-10:]
            if m.source_identifier == metrics.source_identifier and m.success
        ]
        if len(recent_successes) >= 5:
            signals.append(AdaptationSignal.SUCCESS_STREAK)

        # Log significant signals
        if signals:
            logger.info(
                f"[{strategy_key}] Adaptation signals: {[s.value for s in signals]}"
            )

    async def _log_significant_events(
        self, strategy_key: str, metrics: ResponseMetrics, content_collected: int
    ) -> None:
        """Log significant collection events."""
        strategy = self.active_strategies[strategy_key]

        # Log health status changes
        health_status = strategy.get_health_status()
        if hasattr(strategy, "_last_logged_health"):
            if strategy._last_logged_health != health_status:
                logger.info(
                    f"[{strategy_key}] Health status changed: "
                    f"{strategy._last_logged_health.value} → {health_status.value}"
                )
        strategy._last_logged_health = health_status

        # Log rate limiting
        if metrics.rate_limit_hit:
            logger.warning(
                f"[{strategy_key}] Rate limit hit (status: {metrics.status_code}, "
                f"response_time: {metrics.response_time:.2f}s)"
            )

        # Log successful collection
        if metrics.success and content_collected > 0:
            logger.info(
                f"[{strategy_key}] Collected {content_collected} items "
                f"(response_time: {metrics.response_time:.2f}s, "
                f"health: {health_status.value})"
            )

        # Log errors with context
        if not metrics.success:
            logger.error(
                f"[{strategy_key}] Collection failed: {metrics.error_message} "
                f"(status: {metrics.status_code}, response_time: {metrics.response_time:.2f}s)"
            )

    def get_strategy_summary(self, strategy_key: str) -> Optional[Dict[str, Any]]:
        """Get summary for a specific strategy."""
        if strategy_key not in self.active_strategies:
            return None

        strategy = self.active_strategies[strategy_key]
        return strategy.get_metrics_summary()

    def get_global_summary(self) -> Dict[str, Any]:
        """Get global collection summary."""
        active_sources = len(self.active_strategies)
        healthy_sources = sum(
            1
            for strategy in self.active_strategies.values()
            if strategy.get_health_status() == SourceHealth.HEALTHY
        )

        return {
            **self.global_metrics,
            "active_sources": active_sources,
            "healthy_sources": healthy_sources,
            "health_percentage": (
                (healthy_sources / active_sources * 100) if active_sources > 0 else 0
            ),
            "recent_requests": len(
                [
                    m
                    for m in self.response_history
                    if (datetime.now() - m.timestamp).total_seconds() < 3600
                ]
            ),
        }

    async def get_source_recommendations(self, strategy_key: str) -> List[str]:
        """Get recommendations for improving source performance."""
        if strategy_key not in self.active_strategies:
            return []

        strategy = self.active_strategies[strategy_key]
        summary = strategy.get_metrics_summary()
        recommendations = []

        # Performance recommendations
        if summary["success_rate"] < 0.7:
            recommendations.append(
                f"Success rate is low ({summary['success_rate']:.1%}). "
                "Consider reducing request frequency or checking source availability."
            )

        if summary["avg_response_time"] > 10.0:
            recommendations.append(
                f"Average response time is high ({summary['avg_response_time']:.1f}s). "
                "Consider increasing timeout or reducing payload size."
            )

        if summary["rate_limit_hits"] > 0:
            recommendations.append(
                f"Rate limits hit {summary['rate_limit_hits']} times. "
                "Consider reducing collection frequency or implementing better backoff."
            )

        if summary["consecutive_errors"] > 3:
            recommendations.append(
                f"Multiple consecutive errors ({summary['consecutive_errors']}). "
                "Source may be temporarily unavailable or credentials may need refresh."
            )

        # Health-based recommendations
        health = SourceHealth(summary["health"])
        if health == SourceHealth.RATE_LIMITED:
            recommendations.append(
                "Source is rate limited. Collection will automatically slow down. "
                "Consider reducing collection scope or frequency."
            )
        elif health == SourceHealth.ERROR:
            recommendations.append(
                "Source is experiencing errors. Check connectivity, credentials, "
                "and source availability."
            )
        elif health == SourceHealth.BLOCKED:
            recommendations.append(
                "Source appears to be blocking requests. "
                "Consider changing user agent, IP, or collection patterns."
            )

        return recommendations

    async def save_performance_report(self, report_name: str = "comprehensive") -> str:
        """Save comprehensive performance report to blob storage."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "global_metrics": self.get_global_summary(),
            "source_summaries": {
                key: strategy.get_metrics_summary()
                for key, strategy in self.active_strategies.items()
            },
            "recommendations": {
                key: await self.get_source_recommendations(key)
                for key in self.active_strategies.keys()
            },
            "recent_responses": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "source": f"{m.source_type}:{m.source_identifier}",
                    "success": m.success,
                    "response_time": m.response_time,
                    "status_code": m.status_code,
                    "error_type": m.error_type,
                }
                for m in self.response_history[-100:]  # Last 100 responses
            ],
        }

        blob_name = await self.metrics_storage.save_performance_report(
            report, report_name
        )
        logger.info(f"Performance report saved to blob storage: {blob_name}")
        return blob_name


# Global monitor instance
_global_monitor: Optional[CollectionMonitor] = None


def get_monitor() -> CollectionMonitor:
    """Get or create global collection monitor."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = CollectionMonitor()
    return _global_monitor


async def monitor_collection(
    source_type: str, source_identifier: str, collection_func, *args, **kwargs
) -> Tuple[Any, Dict[str, Any]]:
    """
    Wrapper function to monitor any collection operation.

    Args:
        source_type: Type of source (reddit, rss, web)
        source_identifier: Specific source identifier
        collection_func: Function to execute
        *args, **kwargs: Arguments for collection_func

    Returns:
        Tuple of (collection_result, response_metrics)
    """
    monitor = get_monitor()
    strategy_key = await monitor.register_source(source_type, source_identifier)

    # Get collection parameters
    collection_params = await monitor.before_request(strategy_key)

    # Execute collection with monitoring
    start_time = datetime.now()
    result = None
    error = None
    status_code = None
    headers = {}
    content_collected = 0

    try:
        # Execute the collection function with adaptive parameters
        result = await collection_func(
            *args, collection_params=collection_params, **kwargs
        )

        # Extract metrics from result
        if isinstance(result, dict):
            content_collected = len(result.get("items", []))
            status_code = result.get("status_code", 200)
            headers = result.get("headers", {})
        elif isinstance(result, list):
            content_collected = len(result)
            status_code = 200

    except Exception as e:
        error = e
        logger.exception(f"Collection failed for {strategy_key}")

    # Calculate response time
    response_time = (datetime.now() - start_time).total_seconds()

    # Report to monitor
    response_data = {
        "success": error is None,
        "response_time": response_time,
        "status_code": status_code,
        "headers": headers,
        "error": error,
        "content_length": len(str(result)) if result else 0,
    }

    await monitor.after_request(strategy_key, response_data, content_collected)

    return result, response_data

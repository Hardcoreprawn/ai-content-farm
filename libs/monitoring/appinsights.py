"""
Application Insights integration using Azure Monitor OpenTelemetry.

Provides automatic instrumentation for FastAPI, HTTP requests, and custom telemetry.
"""

import logging
import os
from typing import Any, Optional

from opentelemetry import trace

logger = logging.getLogger(__name__)


def configure_application_insights(
    service_name: str,
    connection_string: Optional[str] = None,
    enable_logging: bool = True,
    enable_metrics: bool = True,
    enable_tracing: bool = True,
) -> Optional[Any]:
    """
    Configure Application Insights monitoring for the service.

    Args:
        service_name: Name of the service for identification in App Insights
        connection_string: Application Insights connection string (defaults to env var)
        enable_logging: Enable log export to Application Insights
        enable_metrics: Enable metrics export
        enable_tracing: Enable distributed tracing

    Returns:
        TracerProvider if configured, None if disabled or connection string missing

    Environment Variables:
        APPLICATIONINSIGHTS_CONNECTION_STRING: Connection string if not provided
        DISABLE_APPLICATION_INSIGHTS: Set to "true" to disable monitoring
    """
    # Check if Application Insights is disabled
    if os.getenv("DISABLE_APPLICATION_INSIGHTS", "").lower() == "true":
        logger.info("Application Insights disabled via environment variable")
        return None

    # Get connection string from parameter or environment
    conn_string = connection_string or os.getenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING"
    )

    if not conn_string:
        logger.warning(
            "Application Insights connection string not provided - monitoring disabled"
        )
        return None

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        # Configure Azure Monitor with OpenTelemetry
        configure_azure_monitor(
            connection_string=conn_string,
            enable_live_metrics=True,
            logger_name=service_name,
            instrumentation_options={
                "azure_sdk": {"enabled": True},
                "fastapi": {"enabled": True},
                "httpx": {"enabled": True},
                "requests": {"enabled": True},
                "urllib": {"enabled": True},
                "urllib3": {"enabled": True},
            },
        )

        logger.info(
            f"✅ Application Insights configured for service: {service_name}",
            extra={"service_name": service_name},
        )

        # Get the tracer provider
        tracer_provider = trace.get_tracer_provider()
        return tracer_provider

    except ImportError as e:
        logger.warning(
            f"Azure Monitor OpenTelemetry not installed: {e} - monitoring disabled"
        )
        return None
    except Exception as e:
        logger.error(
            f"Failed to configure Application Insights: {e}",
            exc_info=True,
        )
        return None


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer for custom span creation.

    Args:
        name: Name of the tracer (typically __name__ of the module)

    Returns:
        OpenTelemetry Tracer instance

    Example:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("my_operation"):
            # Your code here
            pass
    """
    return trace.get_tracer(name)

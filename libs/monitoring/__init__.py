"""
Application Insights monitoring integration for Azure Container Apps.

Provides OpenTelemetry-based monitoring with Azure Monitor integration.
"""

from .appinsights import configure_application_insights, get_tracer

__all__ = ["configure_application_insights", "get_tracer"]

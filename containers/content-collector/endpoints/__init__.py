"""
Endpoints package for content-collector service.
"""

from .content import api_process_content_endpoint
from .diagnostics import reddit_diagnostics_endpoint
from .discovery import discover_topics_endpoint, get_sources_endpoint
from .health import health_endpoint, status_endpoint
from .legacy import api_documentation_endpoint

__all__ = [
    "health_endpoint",
    "status_endpoint",
    "api_process_content_endpoint",
    "discover_topics_endpoint",
    "get_sources_endpoint",
    "reddit_diagnostics_endpoint",
    "api_documentation_endpoint",
]

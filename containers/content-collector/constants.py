"""
Constants for Content Collector - Default Configuration Values

Centralized constants to improve maintainability and consistency.
"""

# Default HTTP User Agent
DEFAULT_USER_AGENT = "azure:content-womble:v2.0.2 (by /u/hardcorepr4wn)"

# Content Collection Limits
DEFAULT_MAX_ITEMS = 50
DEFAULT_TIMEOUT = 30.0

# Retry Configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0
DEFAULT_MAX_DELAY = 300.0
DEFAULT_BACKOFF_MULTIPLIER = 2.0

"""
Base Collector Classes

Abstract base classes and mixins for content source collectors.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class SourceCollector(ABC):
    """Abstract base class for content source collectors."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

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

    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of this source."""
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

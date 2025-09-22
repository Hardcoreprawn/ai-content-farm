"""
Source Collectors for Content Womble - LEGACY

DEPRECATED: Legacy source collectors with complex patterns
Status: PENDING REMOVAL - Replaced by simple factory pattern

Contains complex collector instantiation and management logic.
Replaced by collectors/factory.py which provides simpler patterns.

Collects content from various sources (RSS, Reddit, etc.) for processing.
"""

import logging
import os
import re
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import feedparser
import httpx
import requests
from bs4 import BeautifulSoup
from collectors.base import SourceCollector
from collectors.reddit import RedditPRAWCollector, RedditPublicCollector
from collectors.web import WebContentCollector
from dateutil import parser as date_parser
from keyvault_client import get_reddit_credentials_with_fallback

from config import config as app_config

# Add parent directories to path for imports
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))


class SourceCollectorFactory:
    """Factory for creating appropriate source collectors."""

    @staticmethod
    def create_collector(
        source_type: str, config: Optional[Dict[str, Any]] = None
    ) -> SourceCollector:
        """Create a collector for the specified source type with intelligent credential detection."""

        if source_type == "reddit":
            # Enhanced logic to determine which Reddit collector to use

            # First check if credentials are explicitly provided in config
            if config and config.get("client_id") and config.get("client_secret"):
                return RedditPRAWCollector(config)

            # Check for environment variables (Container Apps secrets)
            env_client_id = app_config.reddit_client_id
            env_client_secret = app_config.reddit_client_secret

            if env_client_id and env_client_secret:
                # Validate they're not placeholder values
                if (
                    len(env_client_id) > 10
                    and len(env_client_secret) > 20
                    and "placeholder" not in env_client_id.lower()
                    and "placeholder" not in env_client_secret.lower()
                ):
                    return RedditPRAWCollector(config)
                else:
                    # Credentials look like placeholders, use public API
                    return RedditPublicCollector(config)

            # Check Key Vault credentials as fallback
            credentials = get_reddit_credentials_with_fallback()
            kv_client_id = credentials.get("client_id")
            kv_client_secret = credentials.get("client_secret")

            if (
                kv_client_id
                and kv_client_secret
                and len(kv_client_id) > 10
                and len(kv_client_secret) > 20
                and "placeholder" not in kv_client_id.lower()
                and "placeholder" not in kv_client_secret.lower()
            ):
                return RedditPRAWCollector(config)

            # Fall back to public API if no valid credentials
            return RedditPublicCollector(config)

        elif source_type == "web":
            return WebContentCollector(config)
        else:
            raise ValueError(f"Unknown source type: {source_type}")

    @staticmethod
    def get_available_sources() -> List[str]:
        """Get list of available source types."""
        return ["reddit", "web"]

    @staticmethod
    def get_reddit_collector_info() -> Dict[str, Any]:
        """Get information about which Reddit collector would be used."""
        # Try environment variables first
        env_client_id = app_config.reddit_client_id
        env_client_secret = app_config.reddit_client_secret

        info = {
            "recommended_collector": "unknown",
            "reason": "",
            "credentials_source": "none",
            "credential_status": {},
        }

        if env_client_id and env_client_secret:
            if (
                len(env_client_id) > 10
                and len(env_client_secret) > 20
                and "placeholder" not in env_client_id.lower()
                and "placeholder" not in env_client_secret.lower()
            ):
                info["recommended_collector"] = "RedditPRAWCollector"
                info["reason"] = "Valid credentials found in environment variables"
                info["credentials_source"] = "environment"
                info["credential_status"] = {
                    "client_id_length": len(env_client_id),
                    "client_secret_length": len(env_client_secret),
                    "appears_valid": True,
                }
            else:
                info["recommended_collector"] = "RedditPublicCollector"
                info["reason"] = "Environment credentials appear to be placeholders"
                info["credentials_source"] = "environment"
                info["credential_status"] = {
                    "client_id_length": len(env_client_id),
                    "client_secret_length": len(env_client_secret),
                    "appears_valid": False,
                }
        else:
            # Check Key Vault
            credentials = get_reddit_credentials_with_fallback()
            kv_client_id = credentials.get("client_id")
            kv_client_secret = credentials.get("client_secret")

            if kv_client_id and kv_client_secret:
                if (
                    len(kv_client_id) > 10
                    and len(kv_client_secret) > 20
                    and "placeholder" not in kv_client_id.lower()
                    and "placeholder" not in kv_client_secret.lower()
                ):
                    info["recommended_collector"] = "RedditPRAWCollector"
                    info["reason"] = "Valid credentials found in Key Vault"
                    info["credentials_source"] = "keyvault"
                    info["credential_status"] = {
                        "client_id_length": len(kv_client_id),
                        "client_secret_length": len(kv_client_secret),
                        "appears_valid": True,
                    }
                else:
                    info["recommended_collector"] = "RedditPublicCollector"
                    info["reason"] = "Key Vault credentials appear to be placeholders"
                    info["credentials_source"] = "keyvault"
                    info["credential_status"] = {
                        "client_id_length": len(kv_client_id),
                        "client_secret_length": len(kv_client_secret),
                        "appears_valid": False,
                    }
            else:
                info["recommended_collector"] = "RedditPublicCollector"
                info["reason"] = "No Reddit credentials found"
                info["credentials_source"] = "none"

        return info

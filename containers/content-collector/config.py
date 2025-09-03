"""
Content Collector Configuration

Uses pydantic-settings for type-safe configuration management.
"""

import os
import sys

from libs.config_base import ContentCollectorConfig

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))


# Create global config instance
config = ContentCollectorConfig()

# Backward compatibility - expose common values as module attributes
SERVICE_NAME = config.service_name
VERSION = config.version
PORT = config.port
ENVIRONMENT = config.environment

# Storage configuration
STORAGE_ACCOUNT_NAME = config.storage_account_name
STORAGE_ACCOUNT_URL = config.storage_account_url
BLOB_CONNECTION_STRING = config.blob_connection_string
COLLECTED_CONTENT_CONTAINER = config.collected_content_container

# Azure Key Vault configuration
AZURE_KEY_VAULT_URL = config.azure_key_vault_url

# Reddit configuration
REDDIT_CLIENT_ID = config.reddit_client_id
REDDIT_CLIENT_SECRET = config.reddit_client_secret
REDDIT_USER_AGENT = config.reddit_user_agent
MAX_ITEMS_PER_COLLECTION = config.max_items_per_collection
DEFAULT_SUBREDDITS = config.default_subreddits

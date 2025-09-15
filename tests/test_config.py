"""
Test Configuration and Utilities

Shared configuration and utilities for testing across the entire project.
Handles module path resolution and test environment setup.
"""

import os
import sys
from pathlib import Path


def setup_test_environment():
    """Setup test environment with proper module paths."""
    # Add project root to Python path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    # Add each container to the path for imports
    containers_dir = project_root / "containers"
    for container_path in containers_dir.iterdir():
        if container_path.is_dir() and not container_path.name.startswith("."):
            sys.path.insert(0, str(container_path))

    # Add libs directory
    libs_dir = project_root / "libs"
    if libs_dir.exists():
        sys.path.insert(0, str(libs_dir))


def get_test_config():
    """Get test configuration from environment variables."""
    return {
        "TESTING": True,
        "SKIP_INTEGRATION_TESTS": os.getenv("SKIP_INTEGRATION_TESTS", "false").lower()
        == "true",
        "SKIP_FUNCTIONAL_TESTS": os.getenv("SKIP_FUNCTIONAL_TESTS", "false").lower()
        == "true",
        "TEST_TIMEOUT": int(os.getenv("TEST_TIMEOUT", "30")),
        "MOCK_EXTERNAL_SERVICES": os.getenv("MOCK_EXTERNAL_SERVICES", "true").lower()
        == "true",
    }


def create_mock_service_config():
    """Create mock configuration for services during testing."""
    return {
        "SERVICE_BUS_NAMESPACE": "test-namespace",
        "SERVICE_BUS_CONNECTION_STRING": "Endpoint=sb://test.servicebus.windows.net/;SharedAccessKeyName=test;SharedAccessKey=test",
        "BLOB_STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test;EndpointSuffix=core.windows.net",
        "OPENAI_API_KEY": "test-key",
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "REDDIT_CLIENT_ID": "test-client-id",
        "REDDIT_CLIENT_SECRET": "test-client-secret",
        "REDDIT_USER_AGENT": "test-user-agent",
    }


# Setup test environment when this module is imported
setup_test_environment()

"""
Pytest configuration and fixtures for AI Content Farm testing.

This file automatically sets up the test environment when pytest runs,
including proper module path resolution and mock configurations.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


def setup_pytest_paths():
    """Configure pytest with proper module paths.

    Only adds project root and libs to sys.path.
    Individual containers manage their own imports via their conftest.py files.
    This prevents namespace collisions when multiple containers have same module names.
    """
    # Add project root and container paths to sys.path
    project_root = Path(__file__).parent

    # Add project root (for workspace-level imports)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Add libs directory (shared libraries available to all containers)
    libs_path = project_root / "libs"
    if libs_path.exists() and str(libs_path) not in sys.path:
        sys.path.insert(0, str(libs_path))

    # NOTE: We do NOT add individual containers to sys.path here.
    # Each container's conftest.py adds its own directory to sys.path.
    # This prevents namespace collisions (e.g., multiple "models.py" files)


def pytest_configure(config):
    """Configure pytest with proper module paths and test markers."""
    # Set up module paths
    setup_pytest_paths()

    # Configure test markers
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "functional: Functional tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables and configurations."""
    # Mock environment variables for testing
    test_env = {
        "TESTING": "true",
        "MOCK_EXTERNAL_SERVICES": "true",
        "SERVICE_BUS_NAMESPACE": "test-namespace",
        "SERVICE_BUS_CONNECTION_STRING": "Endpoint=sb://test.servicebus.windows.net/;SharedAccessKeyName=test;SharedAccessKey=test",  # pragma: allowlist secret
        "BLOB_STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test;EndpointSuffix=core.windows.net",  # pragma: allowlist secret
        "OPENAI_API_KEY": "test-key",  # pragma: allowlist secret
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "REDDIT_CLIENT_ID": "test-client-id",
        "REDDIT_CLIENT_SECRET": "test-client-secret",  # pragma: allowlist secret
        "REDDIT_USER_AGENT": "test-user-agent",
    }

    with patch.dict(os.environ, test_env):
        yield


@pytest.fixture
def mock_service_bus_config():
    """Mock Service Bus configuration for tests."""
    from unittest.mock import MagicMock

    config = MagicMock()
    config.namespace = "test-namespace"
    config.queue_name = "test-queue"
    config.connection_string = "test-connection-string"

    return config


@pytest.fixture
def mock_blob_storage_config():
    """Mock Blob Storage configuration for tests."""
    from unittest.mock import MagicMock

    config = MagicMock()
    config.connection_string = "test-connection-string"
    config.container_name = "test-container"

    return config


@pytest.fixture
def mock_openai_config():
    """Mock OpenAI configuration for tests."""
    return {
        "api_key": "test-key",  # pragma: allowlist secret
        "endpoint": "https://test.openai.azure.com/",
        "api_version": "2023-05-15",
        "deployment_name": "test-deployment",
    }


# Custom markers
pytest_plugins = []

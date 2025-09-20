"""
Pytest configuration for adaptive collection system tests.
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Add the container source to the path
test_dir = Path(__file__).parent
container_dir = test_dir.parent / "containers" / "content-collector"
sys.path.insert(0, str(container_dir))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_modules():
    """Reset module state between tests."""
    # Remove any cached modules that might interfere
    modules_to_remove = [
        mod for mod in sys.modules.keys() if mod.startswith("collectors.")
    ]
    for mod in modules_to_remove:
        if mod in sys.modules:
            del sys.modules[mod]


@pytest.fixture
def sample_datetime():
    """Provide consistent datetime for testing."""
    from datetime import datetime

    return datetime(2023, 10, 22, 12, 0, 0)


# Configure async test timeout
pytest_timeout = 300  # 5 minutes for all tests

# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e

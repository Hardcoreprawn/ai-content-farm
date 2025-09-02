"""
Test configuration for Site Generator

Provides shared fixtures and test utilities following project standards.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add the containers path and workspace root for imports
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))
sys.path.insert(0, str((Path(__file__).parent.parent.parent.parent).resolve()))


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up clean test environment for each test."""
    # Set up test environment variables
    os.environ["BLOB_STORAGE_MOCK"] = "true"
    os.environ["ENVIRONMENT"] = "test"

    # Ensure we're in a clean state
    original_cwd = os.getcwd()

    yield

    # Clean up after test
    os.chdir(original_cwd)


@pytest.fixture
def temp_workdir():
    """Create a temporary working directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        yield Path(temp_dir)
        os.chdir(original_cwd)


@pytest.fixture
def mock_logger():
    """Provide a mock logger for testing."""
    from unittest.mock import Mock

    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    return logger


# Disable logging during tests to reduce noise
@pytest.fixture(autouse=True)
def disable_logging():
    """Disable logging during tests."""
    import logging

    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)

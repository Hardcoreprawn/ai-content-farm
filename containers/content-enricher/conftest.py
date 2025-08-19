"""
Content Enricher Test Configuration

Provides shared test fixtures and configuration for pytest.
Includes Azurite integration for blob storage testing.
"""

import pytest
import os


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment with Azurite connection string."""
    # Configure Azurite connection string for local testing
    azurite_connection = (
        "DefaultEndpointsProtocol=http;"
        "AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
        "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    )

    # Set environment variables for testing
    os.environ["AZURE_STORAGE_CONNECTION_STRING"] = azurite_connection
    os.environ["ENVIRONMENT"] = "local"

    yield

    # Cleanup is handled automatically by Azurite

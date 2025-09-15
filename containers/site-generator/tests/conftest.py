"""
Test configuration for Site Generator

Provides shared fixtures and test utilities following project standards.
"""

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

# Add the containers path and workspace root for imports
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))
sys.path.insert(0, str((Path(__file__).parent.parent.parent.parent).resolve()))

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]


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


@pytest.fixture
def mock_blob_client():
    """Mock blob storage client."""
    mock_client = Mock()

    # Mock synchronous methods (matching shared library interface)
    mock_client.list_containers = Mock(return_value=[])
    mock_client.list_blobs = Mock(
        return_value=[
            {
                "name": "test1.html",
                "size": 1024,
                "last_modified": "2025-01-01T00:00:00Z",
            },
            {
                "name": "test2.html",
                "size": 2048,
                "last_modified": "2025-01-01T00:00:00Z",
            },
        ]
    )
    mock_client.test_connection = Mock(
        return_value={
            "status": "healthy",
            "connection_type": "mock",
            "message": "Mock storage client is working",
        }
    )
    mock_client.upload_binary = AsyncMock(return_value=True)
    mock_client.download_binary = AsyncMock(return_value=b"test content")

    return mock_client


@pytest.fixture
def mock_config():
    """Mock configuration object."""
    mock_config = Mock()
    mock_config.PROCESSED_CONTENT_CONTAINER = "processed-content"
    mock_config.MARKDOWN_CONTENT_CONTAINER = "markdown-content"
    mock_config.STATIC_SITES_CONTAINER = "static-sites"
    return mock_config


@pytest.fixture
def mock_markdown_service():
    """Mock markdown service."""
    from models import GenerationResponse

    mock_service = Mock()
    mock_service.count_markdown_files = AsyncMock(return_value=10)
    mock_service.generate_batch = AsyncMock(
        return_value=GenerationResponse(
            generator_id="test_gen_123",
            operation_type="markdown_generation",
            files_generated=5,
            processing_time=2.5,
            output_location="blob://markdown-content",
            generated_files=["article1.md", "article2.md"],
            errors=[],
        )
    )
    return mock_service


@pytest.fixture
def mock_site_service():
    """Mock site service."""
    from models import GenerationResponse

    mock_service = Mock()
    mock_service.generate_site = AsyncMock(
        return_value=GenerationResponse(
            generator_id="test_site_456",
            operation_type="site_generation",
            files_generated=15,
            pages_generated=8,
            processing_time=8.2,
            output_location="blob://static-sites",
            generated_files=["index.html", "archive.html", "style.css"],
            errors=[],
        )
    )
    mock_service.get_preview_url = AsyncMock(return_value="https://example.com/preview")
    return mock_service


@pytest.fixture
def mock_content_manager():
    """Mock content manager."""
    mock_manager = Mock()
    mock_manager.create_slug = Mock(
        side_effect=lambda title: title.lower().replace(" ", "-")
    )
    return mock_manager


@pytest.fixture
def mock_archive_manager():
    """Mock archive manager."""
    mock_manager = Mock()
    mock_manager.upload_archive = AsyncMock(return_value=True)
    mock_manager.create_site_archive = AsyncMock(
        return_value=Path("/tmp/test_archive.tar.gz")
    )
    return mock_manager


@pytest.fixture
def mock_security_validator():
    """Mock security validator."""
    mock_validator = Mock()
    mock_validator.sanitize_blob_name = Mock(
        side_effect=lambda name: name.replace("/", "_")
    )
    mock_validator.validate_archive_file = Mock(return_value=True)
    return mock_validator


@pytest.fixture
def mock_generator(
    mock_blob_client,
    mock_config,
    mock_markdown_service,
    mock_site_service,
    mock_content_manager,
    mock_archive_manager,
    mock_security_validator,
):
    """Mock site generator with all dependencies mocked."""
    from unittest.mock import patch

    from site_generator import SiteGenerator

    with (
        patch("site_generator.BlobStorageClient", return_value=mock_blob_client),
        patch("site_generator.Config", return_value=mock_config),
        patch("site_generator.ContentManager", return_value=mock_content_manager),
        patch("site_generator.ArchiveManager", return_value=mock_archive_manager),
        patch("site_generator.SecurityValidator", return_value=mock_security_validator),
        patch("site_generator.MarkdownService", return_value=mock_markdown_service),
        patch("site_generator.SiteService", return_value=mock_site_service),
    ):

        generator = SiteGenerator()

        # Override the services with our mocks
        generator.blob_client = mock_blob_client
        generator.config = mock_config
        generator.markdown_service = mock_markdown_service
        generator.site_service = mock_site_service
        generator.content_manager = mock_content_manager
        generator.archive_manager = mock_archive_manager
        generator.security_validator = mock_security_validator

        return generator


@pytest.fixture
def temp_archive(temp_workdir):
    """Create a temporary archive file for testing."""
    import tarfile

    archive_path = temp_workdir / "test_site.tar.gz"

    # Create a simple test archive
    with tarfile.open(archive_path, "w:gz") as tar:
        # Create a simple text file to add to archive
        test_file = temp_workdir / "test.txt"
        test_file.write_text("test content")
        tar.add(test_file, arcname="test.txt")

    return archive_path


@pytest.fixture
def sample_generation_response():
    """Sample generation response for testing."""
    from models import GenerationResponse

    return GenerationResponse(
        generator_id="test_gen_123",
        operation_type="markdown_generation",
        files_generated=5,
        processing_time=2.5,
        output_location="blob://markdown-content",
        generated_files=[
            "article1.md",
            "article2.md",
            "article3.md",
            "article4.md",
            "article5.md",
        ],
        errors=[],
    )


@pytest.fixture
def sample_site_response():
    """Sample site generation response for testing."""
    from models import GenerationResponse

    return GenerationResponse(
        generator_id="test_site_456",
        operation_type="site_generation",
        files_generated=15,
        pages_generated=8,
        processing_time=8.2,
        output_location="blob://static-sites",
        generated_files=["index.html", "archive.html", "style.css"],
        errors=[],
    )

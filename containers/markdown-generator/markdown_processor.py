"""
Core markdown generation orchestration.

This module coordinates the markdown generation pipeline, importing and
re-exporting functions from specialized modules:
- metadata_utils: Pure metadata extraction functions
- blob_operations: Azure Blob Storage I/O
- markdown_generator: Jinja2 template rendering
- services.image_service: Stock image fetching

Main entry point: process_article() - orchestrates the full pipeline.
"""

import logging
from datetime import UTC, datetime
from typing import Any, Dict, Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient
from azure.storage.blob.aio import BlobServiceClient
from blob_operations import read_json_from_blob, write_markdown_to_blob
from jinja2 import Environment
from markdown_generator import (
    create_jinja_environment,
    generate_markdown_blob_name,
    generate_markdown_content,
)

# Import from specialized modules
from metadata_utils import extract_metadata_from_article
from models import MarkdownGenerationResult, ProcessingStatus
from services.image_service import fetch_image_for_article

from config import Settings  # type: ignore[import]

logger = logging.getLogger(__name__)

__all__ = [
    # Re-export pure functions from metadata_utils
    "extract_metadata_from_article",
    # Re-export I/O functions
    "read_json_from_blob",
    "write_markdown_to_blob",
    "create_jinja_environment",
    # Re-export markdown generation
    "generate_markdown_content",
    "generate_markdown_blob_name",
    # Local functions
    "load_unsplash_key",
    "fetch_article_image",
    # Main orchestration
    "process_article",
]


# =============================================================================
# I/O FUNCTIONS (Explicit side effects)
# =============================================================================


async def load_unsplash_key(
    settings: Settings, credential: Optional[DefaultAzureCredential] = None
) -> Optional[str]:
    """
    Load Unsplash API key from Key Vault or environment.

    I/O function with explicit side effects (Key Vault read).

    Args:
        settings: Application settings
        credential: Azure credential (created if None)

    Returns:
        Unsplash access key or None if not found/disabled

    Examples:
        >>> # See integration tests
        >>> pass
    """
    try:
        # Try to get from explicit env var first
        access_key = settings.unsplash_access_key

        # If not in env, try Key Vault
        if not access_key and settings.azure_key_vault_url:
            logger.info(
                f"Fetching Unsplash key from Key Vault: {settings.azure_key_vault_url}"
            )
            if credential is None:
                credential = DefaultAzureCredential()

            secret_client = SecretClient(
                vault_url=settings.azure_key_vault_url,
                credential=credential,
            )
            secret = await secret_client.get_secret("unsplash-access-key")
            access_key = secret.value

        if access_key and access_key != "placeholder-get-from-unsplash-com":
            logger.info("Stock image service initialized successfully")
            return access_key
        else:
            logger.warning("Unsplash access key not found - stock images disabled")
            return None

    except Exception as e:
        logger.warning(f"Failed to load Unsplash key: {e}")
        logger.info("Continuing without stock images")
        return None


async def fetch_article_image(
    article_data: Dict[str, Any], unsplash_access_key: str
) -> Optional[Dict[str, Any]]:
    """
    Fetch stock image for article from Unsplash.

    Async I/O function - calls external Unsplash API.

    Args:
        article_data: Article data with title/tags
        unsplash_access_key: Unsplash API key

    Returns:
        Image metadata dict or None if not found

    Examples:
        >>> # See integration tests with mocked API
        >>> pass
    """
    try:
        title = article_data.get("title", "")
        tags = article_data.get("tags", [])
        content = article_data.get("content", "")[:200]

        # Call functional image service
        image_data = await fetch_image_for_article(
            access_key=unsplash_access_key,
            title=title,
            content=content,
            tags=tags,
        )

        if image_data:
            logger.info(f"Found stock image by {image_data['photographer']}")
        else:
            logger.info(f"No stock image found for article: {title}")

        return image_data

    except Exception as e:
        logger.warning(f"Failed to fetch stock image: {e}")
        return None


# =============================================================================
# ORCHESTRATION FUNCTIONS (Compose pure + I/O functions)
# =============================================================================


async def process_article(
    blob_service_client: BlobServiceClient,
    settings: Settings,
    blob_name: str,
    overwrite: bool = False,
    template_name: str = "default.md.j2",
    jinja_env: Optional[Environment] = None,
    unsplash_access_key: Optional[str] = None,
) -> MarkdownGenerationResult:
    """
    Process single article from JSON to markdown.

    Main orchestration function - composes pure functions and I/O operations.
    All dependencies passed as arguments (no hidden state).

    Args:
        blob_service_client: Azure Blob Service client
        settings: Application settings
        blob_name: Name of JSON blob to process
        overwrite: Whether to overwrite existing markdown
        template_name: Jinja2 template to use
        jinja_env: Jinja2 environment (created if None)
        unsplash_access_key: Unsplash API key (loaded if None and enabled)

    Returns:
        MarkdownGenerationResult: Processing result with status and timing

    Examples:
        >>> # See integration tests
        >>> pass
    """
    start_time = datetime.now(UTC)

    try:
        # Create Jinja environment if not provided
        if jinja_env is None:
            jinja_env = create_jinja_environment()

        # Read JSON from input container (I/O)
        article_data = read_json_from_blob(
            blob_service_client, settings.input_container, blob_name
        )

        # Fetch stock image if enabled (async I/O)
        image_data = None
        if settings.enable_stock_images and unsplash_access_key:
            image_data = await fetch_article_image(article_data, unsplash_access_key)

        # Extract metadata (pure function)
        metadata = extract_metadata_from_article(article_data, image_data)

        # Generate markdown content (mostly pure)
        markdown_content = generate_markdown_content(
            article_data, metadata, jinja_env, template_name
        )

        # Generate blob name (pure function)
        markdown_blob_name = generate_markdown_blob_name(blob_name)

        # Write markdown to output container (I/O)
        write_markdown_to_blob(
            blob_service_client,
            settings.output_container,
            markdown_blob_name,
            markdown_content,
            overwrite,
        )

        processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

        logger.info(
            f"Successfully processed article: {blob_name} -> "
            f"{markdown_blob_name} ({processing_time:.0f}ms) "
            f"using template: {template_name}"
        )

        return MarkdownGenerationResult(
            blob_name=blob_name,
            status=ProcessingStatus.COMPLETED,
            markdown_blob_name=markdown_blob_name,
            error_message=None,
            processing_time_ms=int(processing_time),
        )

    except ResourceNotFoundError:
        error_msg = f"Blob not found: {blob_name}"
        logger.error(error_msg)
        return MarkdownGenerationResult(
            blob_name=blob_name,
            status=ProcessingStatus.FAILED,
            markdown_blob_name=None,
            error_message=error_msg,
            processing_time_ms=None,
        )

    except Exception as e:
        error_msg = f"Failed to process {blob_name}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return MarkdownGenerationResult(
            blob_name=blob_name,
            status=ProcessingStatus.FAILED,
            markdown_blob_name=None,
            error_message=error_msg,
            processing_time_ms=None,
        )

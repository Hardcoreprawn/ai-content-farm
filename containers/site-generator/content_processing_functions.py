"""
Core content processing functions for markdown and site generation.

This module contains the main batch processing and generation functions
that coordinate the overall workflow for content transformation.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

# Import utility functions at module level for better testability
from content_utility_functions import (
    create_complete_site,
    create_empty_generation_response,
    generate_article_markdown,
    get_markdown_articles,
    get_processed_articles,
)
from models import GenerationResponse

from libs import SecureErrorHandler
from libs.retry_utilities import storage_retry, with_secure_retry
from libs.simplified_blob_client import SimplifiedBlobClient

# Import Phase 3 components
from libs.site_generator_exceptions import (
    ContentProcessingError,
    SiteGeneratorError,
    StorageError,
    ValidationError,
)

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("content-processing")


async def generate_markdown_batch(
    source: str,
    batch_size: int,
    force_regenerate: bool,
    blob_client: SimplifiedBlobClient,
    config: Dict[str, Any],
    generator_id: Optional[str] = None,
) -> GenerationResponse:
    """
    Generate markdown files from processed content.

    Pure function with no side effects except I/O operations.
    All dependencies passed as parameters for testability and thread safety.

    Args:
        source: Source identifier for the generation request
        batch_size: Maximum number of articles to process
        force_regenerate: Whether to regenerate existing markdown files
        blob_client: Initialized blob storage client
        config: Configuration dictionary with container names and settings
        generator_id: Optional generator identifier for tracking

    Returns:
        GenerationResponse with processing results
    """
    start_time = datetime.now(timezone.utc)
    generator_id = generator_id or str(uuid4())[:8]
    generated_files = []
    errors = []

    try:
        logger.info(
            f"Starting markdown generation: source={source}, batch_size={batch_size}"
        )

        # Get latest processed content
        processed_articles = await get_processed_articles(
            blob_client=blob_client,
            container_name=config["PROCESSED_CONTENT_CONTAINER"],
            limit=batch_size,
        )

        if not processed_articles:
            logger.info("No processed articles found")
            return create_empty_generation_response(
                generator_id=generator_id, operation_type="markdown_generation"
            )

        # Generate markdown for each article with retry logic
        for article_data in processed_articles:
            article_id = article_data.get("topic_id", "unknown")

            try:
                # Validate article data structure
                if not isinstance(article_data, dict):
                    raise ValidationError(
                        "Article data must be a dictionary",
                        field_name="article_data",
                        validation_rule="type_check",
                    )

                required_fields = ["title", "content"]
                missing_fields = [
                    field for field in required_fields if not article_data.get(field)
                ]
                if missing_fields:
                    raise ValidationError(
                        f"Missing required fields: {missing_fields}",
                        field_name="article_data",
                        validation_rule="required_fields",
                    )

                # Generate markdown with error handling
                try:
                    markdown_filename = await generate_article_markdown(
                        article_data=article_data,
                        blob_client=blob_client,
                        container_name=config["MARKDOWN_CONTENT_CONTAINER"],
                        force_regenerate=force_regenerate,
                    )
                except (StorageError, ConnectionError, OSError) as e:
                    # Convert storage errors to our exception hierarchy
                    raise ContentProcessingError(
                        f"Failed to generate markdown for {article_id}",
                        details={"article_id": article_id, "original_error": str(e)},
                    ) from e
                generated_files.append(markdown_filename)

            except ValidationError as e:
                error_response = error_handler.handle_error(
                    e,
                    "validation",
                    context={"article_id": article_id, "details": e.details},
                )
                logger.warning(
                    f"Validation failed for article {article_id}: {error_response['message']}"
                )
                errors.append(f"Validation error for {article_id}: {e}")
                continue

            except (StorageError, ConnectionError, TimeoutError) as e:
                error_response = error_handler.handle_error(
                    e, "storage", context={"article_id": article_id}
                )
                logger.error(
                    f"Storage operation failed for article {article_id}: {error_response['message']}"
                )
                errors.append(f"Storage error for {article_id}: {e}")
                continue

            except ContentProcessingError as e:
                error_response = error_handler.handle_error(
                    e,
                    "processing",
                    context={"article_id": article_id, "details": e.details},
                )
                logger.error(
                    f"Content processing failed for article {article_id}: {error_response['message']}"
                )
                errors.append(f"Processing error for {article_id}: {e}")
                continue

            except Exception as e:
                # Convert unexpected errors to SiteGeneratorError
                site_error = SiteGeneratorError(
                    f"Unexpected error processing article {article_id}",
                    details={"article_id": article_id, "original_error": str(e)},
                )
                error_response = error_handler.handle_error(
                    site_error, "general", context={"article_id": article_id}
                )
                logger.error(
                    f"Unexpected error processing article {article_id}: {error_response['message']}"
                )
                errors.append(f"Unexpected error for {article_id}: {e}")
                continue

        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        logger.info(
            f"Generated {len(generated_files)} markdown files in {processing_time:.2f}s"
        )

        return GenerationResponse(
            generator_id=generator_id,
            operation_type="markdown_generation",
            files_generated=len(generated_files),
            processing_time=processing_time,
            output_location=f"blob://{config['MARKDOWN_CONTENT_CONTAINER']}",
            generated_files=generated_files,
            errors=errors,
        )

    except ValidationError as e:
        error_response = error_handler.handle_error(
            e,
            "validation",
            user_message="Markdown generation failed with invalid input",
        )
        logger.error(error_response["message"])
        raise ContentProcessingError(
            "Markdown generation validation failed",
            operation="markdown_generation",
            details=e.details,
        ) from e

    except (StorageError, ConnectionError) as e:
        error_response = error_handler.handle_error(
            e,
            "storage",
            user_message="Markdown generation failed due to storage issues",
        )
        logger.error(error_response["message"])
        raise ContentProcessingError(
            "Markdown generation storage operation failed",
            operation="markdown_generation",
        ) from e

    except Exception as e:
        error_response = error_handler.handle_error(
            e, "general", user_message="Markdown generation failed unexpectedly"
        )
        logger.error(error_response["message"])
        raise ContentProcessingError(
            "Markdown generation failed unexpectedly", operation="markdown_generation"
        ) from e
        logger.error(error_response["message"])
        raise RuntimeError(error_response["message"]) from e


async def generate_static_site(
    theme: str,
    force_rebuild: bool,
    blob_client: SimplifiedBlobClient,
    config: Dict[str, Any],
    generator_id: Optional[str] = None,
) -> GenerationResponse:
    """
    Generate complete static HTML site from markdown content.

    Pure function that creates a complete website from markdown files.

    Args:
        theme: Theme name for site styling
        force_rebuild: Whether to force complete site rebuild
        blob_client: Initialized blob storage client
        config: Configuration dictionary with container names and settings
        generator_id: Optional generator identifier for tracking

    Returns:
        GenerationResponse with site generation results
    """
    start_time = datetime.now(timezone.utc)
    generator_id = generator_id or str(uuid4())[:8]

    try:
        logger.info(f"Starting static site generation with theme: {theme}")

        # Get all markdown articles
        markdown_articles = await get_markdown_articles(
            blob_client=blob_client, container_name=config["MARKDOWN_CONTENT_CONTAINER"]
        )

        if not markdown_articles:
            logger.info("No markdown articles found for site generation")
            return create_empty_generation_response(
                generator_id=generator_id, operation_type="site_generation"
            )

        # Generate complete site
        generated_files = await create_complete_site(
            articles=markdown_articles,
            theme=theme,
            blob_client=blob_client,
            config=config,
            force_rebuild=force_rebuild,
        )

        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        logger.info(
            f"Generated static site with {len(generated_files)} files in {processing_time:.2f}s"
        )

        return GenerationResponse(
            generator_id=generator_id,
            operation_type="site_generation",
            files_generated=len(generated_files),
            pages_generated=len(markdown_articles) + 1,  # articles + index
            processing_time=processing_time,
            output_location=f"blob://{config['STATIC_SITES_CONTAINER']}",
            generated_files=generated_files,
            errors=[],
        )

    except (ValueError, TypeError) as e:
        error_response = error_handler.handle_error(
            e,
            "validation",
            user_message="Static site generation failed with invalid input",
        )
        logger.error(error_response["message"])
        raise ValueError(error_response["message"]) from e
    except Exception as e:
        error_response = error_handler.handle_error(
            e, "general", user_message="Static site generation failed unexpectedly"
        )
        logger.error(error_response["message"])
        raise RuntimeError(error_response["message"]) from e

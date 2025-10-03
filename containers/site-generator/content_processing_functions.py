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

# Import Phase 3 components
from libs.queue_triggers import (
    should_trigger_next_stage as should_trigger_html_generation,
)
from libs.queue_triggers import (
    trigger_html_generation,
)
from libs.retry_utilities import storage_retry, with_secure_retry
from libs.simplified_blob_client import SimplifiedBlobClient
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
    blob_client: SimplifiedBlobClient,
    config: Dict[str, Any],
    batch_size: int = 10,
    force_regenerate: bool = False,
    generator_id: str = "",
    trigger_html_generation: bool = True,
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
        trigger_html_generation: Whether to send queue message for HTML generation

    Returns:
        GenerationResponse with processing results and queue trigger status
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

                # Check for required fields - support both 'content' and 'article_content'
                required_fields = ["title"]
                missing_fields = [
                    field for field in required_fields if not article_data.get(field)
                ]

                # Validate content field (accept either 'content' or 'article_content')
                has_content = article_data.get("content") or article_data.get(
                    "article_content"
                )
                if not has_content:
                    missing_fields.append("content or article_content")

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

        # Trigger HTML generation if markdown files were created
        if generated_files and trigger_html_generation:
            from queue_trigger_functions import (
                should_trigger_html_generation,
            )
            from queue_trigger_functions import (
                trigger_html_generation as send_html_trigger,
            )

            # Check if we should trigger (allows for future threshold logic)
            should_trigger = should_trigger_html_generation(
                markdown_files=generated_files,
                config=config,
                force_trigger=False,
            )

            if should_trigger:
                queue_trigger_result = await send_html_trigger(
                    markdown_files=generated_files,
                    queue_name=config.get("QUEUE_NAME", "site-generation-requests"),
                    generator_id=generator_id,
                    correlation_id=generator_id,
                    additional_metadata={
                        "source": source,
                        "batch_size": batch_size,
                    },
                )

                if queue_trigger_result["status"] == "success":
                    logger.info(
                        f"✅ HTML generation triggered: message_id={queue_trigger_result.get('message_id')}"
                    )
                elif queue_trigger_result["status"] == "error":
                    # Log error but don't fail markdown generation
                    logger.warning(
                        f"⚠️  HTML generation trigger failed (non-fatal): {queue_trigger_result.get('error')}"
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
    blob_client: SimplifiedBlobClient,
    config: Dict[str, Any],
    theme: str = "default",
    force_rebuild: bool = False,
    generator_id: str = "",
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

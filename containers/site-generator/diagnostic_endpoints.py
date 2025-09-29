"""
Diagnostic endpoints for pipeline debugging.

Provides comprehensive diagnostic capabilities for investigating pipeline blockages.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import HTTPException

from libs import SecureErrorHandler
from libs.shared_models import StandardResponse, create_success_response

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("site-generator")


async def debug_content_discovery(generator) -> Dict[str, Any]:
    """Debug function: Check what content is discovered in each container."""
    try:
        # Get processed content container info
        from libs.simplified_blob_client import SimplifiedBlobClient

        blob_client = SimplifiedBlobClient()

        # Check processed-content container
        processed_blobs = await blob_client.list_blobs(container="processed-content")
        processed_files = [
            {"name": blob["name"], "size": blob.get("size", 0)}
            for blob in processed_blobs[:20]
        ]

        # Check articles specifically
        articles_blobs = await blob_client.list_blobs(
            container="processed-content", prefix="articles/"
        )
        articles_files = [
            {"name": blob["name"], "size": blob.get("size", 0)}
            for blob in articles_blobs[:20]
        ]

        # Check markdown-content container
        markdown_blobs = await blob_client.list_blobs(container="markdown-content")
        markdown_files = [
            {"name": blob["name"], "size": blob.get("size", 0)}
            for blob in markdown_blobs[:20]
        ]

        # Check $web container
        web_blobs = await blob_client.list_blobs(container="$web")
        web_files = [
            {"name": blob["name"], "size": blob.get("size", 0)}
            for blob in web_blobs[:20]
        ]

        return create_success_response(
            message="Content discovery scan complete",
            data={
                "processed_content": {
                    "total_files": len(processed_blobs),
                    "sample_files": processed_files,
                },
                "articles_subfolder": {
                    "total_files": len(articles_blobs),
                    "sample_files": articles_files,
                },
                "markdown_content": {
                    "total_files": len(markdown_blobs),
                    "sample_files": markdown_files,
                },
                "web_content": {
                    "total_files": len(web_blobs),
                    "sample_files": web_files,
                },
                "config": {
                    "input_prefix": (
                        generator.config.INPUT_PREFIX
                        if hasattr(generator, "config")
                        else "N/A"
                    ),
                    "processed_container": (
                        getattr(
                            generator.config,
                            "PROCESSED_CONTENT_CONTAINER",
                            "processed-content",
                        )
                        if hasattr(generator, "config")
                        else "processed-content"
                    ),
                    "markdown_container": (
                        getattr(
                            generator.config,
                            "MARKDOWN_CONTENT_CONTAINER",
                            "markdown-content",
                        )
                        if hasattr(generator, "config")
                        else "markdown-content"
                    ),
                },
            },
            metadata={
                "function": "site-generator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
            },
        )
    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="general",
            user_message="Content discovery scan failed",
        )
        raise HTTPException(status_code=500, detail=error_response)


async def debug_pipeline_test(generator) -> Dict[str, Any]:
    """Debug function: Test the complete pipeline with real data."""
    try:
        # Test markdown service directly
        markdown_service = generator.markdown_service

        # Get processed articles using the service method
        processed_articles = await markdown_service._get_processed_articles(limit=5)

        pipeline_data = {
            "step_1_content_discovery": {
                "articles_found": len(processed_articles),
                "sample_titles": [
                    article.get("title", "No title")
                    for article in processed_articles[:3]
                ],
            },
            "step_2_markdown_generation": {
                "status": "ready" if processed_articles else "no_content"
            },
            "step_3_site_generation": {"status": "pending"},
        }

        # If we found articles, try to generate markdown for one
        if processed_articles:
            try:
                test_article = processed_articles[0]
                markdown_filename = await markdown_service._generate_single_markdown(
                    test_article
                )
                pipeline_data["step_2_markdown_generation"][
                    "test_result"
                ] = f"Success: {markdown_filename}"
                pipeline_data["step_3_site_generation"]["status"] = "ready"
            except Exception as e:
                pipeline_data["step_2_markdown_generation"][
                    "test_result"
                ] = f"Error: {str(e)}"
                pipeline_data["step_3_site_generation"]["status"] = "blocked"

        return create_success_response(
            message="Pipeline test complete",
            data=pipeline_data,
            metadata={
                "function": "site-generator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
            },
        )
    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="general",
            user_message="Pipeline test failed",
        )
        raise HTTPException(status_code=500, detail=error_response)


async def debug_force_process(generator) -> Dict[str, Any]:
    """Debug function: Force process new content end-to-end."""
    try:
        # Force markdown generation with detailed logging
        markdown_result = await generator.generate_markdown_batch(
            source="debug-force", batch_size=5, force_regenerate=True
        )

        # If we generated markdown, force site generation
        site_result = None
        if markdown_result.files_generated > 0:
            site_result = await generator.generate_static_site(
                theme="minimal", force_rebuild=True
            )

        return create_success_response(
            message=f"Force processing complete: {markdown_result.files_generated} markdown files, site {'updated' if site_result else 'unchanged'}",
            data={
                "markdown_result": markdown_result.model_dump(),
                "site_result": site_result.model_dump() if site_result else None,
                "processing_time": datetime.now(timezone.utc).isoformat(),
            },
            metadata={
                "function": "site-generator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "generator_id": getattr(generator, "generator_id", "unknown"),
            },
        )
    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="general",
            user_message="Force processing failed",
        )
        raise HTTPException(status_code=500, detail=error_response)


logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("site-generator")


async def debug_content_discovery(generator) -> StandardResponse:
    """Debug function: Check what content is discovered in each container."""
    try:

        # Get processed content container info
        from libs.simplified_blob_client import SimplifiedBlobClient

        blob_client = SimplifiedBlobClient()

        # Check processed-content container
        processed_blobs = await blob_client.list_blobs(container="processed-content")
        processed_files = [
            {"name": blob["name"], "size": blob.get("size", 0)}
            for blob in processed_blobs[:20]
        ]

        # Check articles specifically
        articles_blobs = await blob_client.list_blobs(
            container="processed-content", prefix="articles/"
        )
        articles_files = [
            {"name": blob["name"], "size": blob.get("size", 0)}
            for blob in articles_blobs[:20]
        ]

        # Check markdown-content container
        markdown_blobs = await blob_client.list_blobs(container="markdown-content")
        markdown_files = [
            {"name": blob["name"], "size": blob.get("size", 0)}
            for blob in markdown_blobs[:20]
        ]

        # Check $web container
        web_blobs = await blob_client.list_blobs(container="$web")
        web_files = [
            {"name": blob["name"], "size": blob.get("size", 0)}
            for blob in web_blobs[:20]
        ]

        return create_success_response(
            message="Content discovery scan complete",
            data={
                "processed_content": {
                    "total_files": len(processed_blobs),
                    "sample_files": processed_files,
                },
                "articles_subfolder": {
                    "total_files": len(articles_blobs),
                    "sample_files": articles_files,
                },
                "markdown_content": {
                    "total_files": len(markdown_blobs),
                    "sample_files": markdown_files,
                },
                "web_content": {
                    "total_files": len(web_blobs),
                    "sample_files": web_files,
                },
                "config": {
                    "input_prefix": generator.config.INPUT_PREFIX,
                    "processed_container": generator.config.PROCESSED_CONTENT_CONTAINER,
                    "markdown_container": generator.config.MARKDOWN_CONTENT_CONTAINER,
                },
            },
            metadata={
                "function": "site-generator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
            },
        )
    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="general",
            user_message="Content discovery scan failed",
        )
        raise HTTPException(status_code=500, detail=error_response)


async def debug_pipeline_test(generator) -> StandardResponse:
    """Debug function: Test the complete pipeline with real data."""
    try:

        # Test markdown service directly
        markdown_service = generator.markdown_service

        # Get processed articles using the service method
        processed_articles = await markdown_service._get_processed_articles(limit=5)

        pipeline_data = {
            "step_1_content_discovery": {
                "articles_found": len(processed_articles),
                "sample_titles": [
                    article.get("title", "No title")
                    for article in processed_articles[:3]
                ],
            },
            "step_2_markdown_generation": {
                "status": "ready" if processed_articles else "no_content"
            },
            "step_3_site_generation": {"status": "pending"},
        }

        # If we found articles, try to generate markdown for one
        if processed_articles:
            try:
                test_article = processed_articles[0]
                markdown_filename = await markdown_service._generate_single_markdown(
                    test_article
                )
                pipeline_data["step_2_markdown_generation"][
                    "test_result"
                ] = f"Success: {markdown_filename}"
                pipeline_data["step_3_site_generation"]["status"] = "ready"
            except Exception as e:
                pipeline_data["step_2_markdown_generation"][
                    "test_result"
                ] = f"Error: {str(e)}"
                pipeline_data["step_3_site_generation"]["status"] = "blocked"

        return create_success_response(
            message="Pipeline test complete",
            data=pipeline_data,
            metadata={
                "function": "site-generator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
            },
        )
    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="general",
            user_message="Pipeline test failed",
        )
        raise HTTPException(status_code=500, detail=error_response)


async def debug_force_process(generator) -> StandardResponse:
    """Debug function: Force process new content end-to-end."""
    try:

        # Force markdown generation with detailed logging
        markdown_result = await generator.generate_markdown_batch(
            source="debug-force", batch_size=5, force_regenerate=True
        )

        # If we generated markdown, force site generation
        site_result = None
        if markdown_result.files_generated > 0:
            site_result = await generator.generate_static_site(
                theme="minimal", force_rebuild=True
            )

        return create_success_response(
            message=f"Force processing complete: {markdown_result.files_generated} markdown files, site {'updated' if site_result else 'unchanged'}",
            data={
                "markdown_result": markdown_result.model_dump(),
                "site_result": site_result.model_dump() if site_result else None,
                "processing_time": datetime.now(timezone.utc).isoformat(),
            },
            metadata={
                "function": "site-generator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "generator_id": generator.generator_id,
            },
        )
    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="general",
            user_message="Force processing failed",
        )
        raise HTTPException(status_code=500, detail=error_response)

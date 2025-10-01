"""
Diagnostic endpoints for pipeline debugging.

Provides comprehensive diagnostic capabilities for investigating pipeline blockages.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from article_loading import load_article_content
from content_processing_functions import generate_markdown_batch, generate_static_site
from content_utility_functions import get_processed_articles
from fastapi import HTTPException
from html_page_generation import generate_article_page

from libs import SecureErrorHandler
from libs.shared_models import StandardResponse, create_success_response
from libs.simplified_blob_client import SimplifiedBlobClient

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("site-generator")


async def debug_content_discovery(generator_context) -> Dict[str, Any]:
    """Debug function: Check what content is discovered in each container."""
    try:
        # Get functional context
        config = generator_context["config"]
        blob_client = generator_context["blob_client"]

        # Check processed-content container
        processed_blobs = blob_client.list_blobs(
            container_name=config.PROCESSED_CONTENT_CONTAINER, max_results=20
        )
        processed_files = [
            {"name": blob.get("name", "unknown"), "size": blob.get("size", 0)}
            for blob in processed_blobs
        ]

        # Check articles specifically
        articles_blobs = blob_client.list_blobs(
            container_name=config.PROCESSED_CONTENT_CONTAINER,
            prefix="articles/",
            max_results=20,
        )
        articles_files = [
            {"name": blob.get("name", "unknown"), "size": blob.get("size", 0)}
            for blob in articles_blobs
        ]

        # Check markdown-content container
        markdown_blobs = blob_client.list_blobs(
            container_name=config.MARKDOWN_CONTENT_CONTAINER, max_results=20
        )
        markdown_files = [
            {"name": blob.get("name", "unknown"), "size": blob.get("size", 0)}
            for blob in markdown_blobs
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
                    "input_prefix": getattr(config, "INPUT_PREFIX", "articles/"),
                    "processed_container": config.PROCESSED_CONTENT_CONTAINER,
                    "markdown_container": config.MARKDOWN_CONTENT_CONTAINER,
                    "static_sites_container": config.STATIC_SITES_CONTAINER,
                    "site_title": config.SITE_TITLE,
                    "environment": config.ENVIRONMENT,
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


async def debug_pipeline_test(generator_context) -> Dict[str, Any]:
    """Debug function: Test the complete pipeline with real data."""
    try:
        # Get functional context
        config = generator_context["config"]
        blob_client = generator_context["blob_client"]

        # Step 1: Content discovery
        processed_articles = await asyncio.to_thread(
            get_processed_articles,
            blob_client=blob_client,
            config=config.to_dict(),
            limit=5,
        )

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

        # If we found articles, try to generate HTML for one
        if processed_articles:
            try:
                test_article = processed_articles[0]
                html_content = await asyncio.to_thread(
                    generate_article_page, article=test_article, config=config.to_dict()
                )
                pipeline_data["step_2_markdown_generation"][
                    "test_result"
                ] = f"Success: Generated {len(html_content)} chars of HTML"
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


async def debug_force_process(generator_context) -> Dict[str, Any]:
    """Debug function: Force process new content end-to-end."""
    try:
        # Get functional context
        config = generator_context["config"]
        blob_client = generator_context["blob_client"]

        # Use functional modules

        # Force markdown generation with detailed logging
        markdown_result = await asyncio.to_thread(
            generate_markdown_batch,
            blob_client=blob_client,
            config=config.to_dict(),
            source="debug-force",
            batch_size=5,
            force_regenerate=True,
        )

        # If we generated markdown, force site generation
        site_result = None
        files_generated = markdown_result.get("files_generated", 0)
        if files_generated > 0:
            site_result = await asyncio.to_thread(
                generate_static_site,
                blob_client=blob_client,
                config=config.to_dict(),
                theme="minimal",
                force_rebuild=True,
            )

        return create_success_response(
            message=f"Force processing complete: {files_generated} markdown files, site {'updated' if site_result else 'unchanged'}",
            data={
                "markdown_result": markdown_result,
                "site_result": site_result,
                "processing_time": datetime.now(timezone.utc).isoformat(),
            },
            metadata={
                "function": "site-generator",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "generator_id": generator_context["generator_id"],
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


# Duplicate function removed - using functional implementation above

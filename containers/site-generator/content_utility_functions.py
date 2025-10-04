"""
Utility functions for content retrieval, parsing, and article operations.

This module contains helper functions for working with markdown content,
parsing frontmatter, file operations, and data validation.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import yaml
from article_processing import calculate_last_updated, prepare_articles_for_display
from html_page_generation import generate_article_page, generate_index_page
from models import GenerationResponse
from rss_generation import generate_rss_feed

from libs import SecureErrorHandler
from libs.data_contracts import ContractValidator
from libs.simplified_blob_client import SimplifiedBlobClient

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("content-utilities")


# Content Retrieval Functions


async def get_processed_articles(
    blob_client: SimplifiedBlobClient, container_name: str, limit: int
) -> List[Dict[str, Any]]:
    """
    Retrieve latest processed articles from blob storage.

    Supports TWO formats for maximum pipeline flexibility:
    1. Individual article files (one JSON = one article) - for real-time single-item flow
    2. Batch collection files (CollectionResult with multiple items) - for batch efficiency

    Processes ALL JSON files in the container, regardless of prefix or subdirectory.
    Automatically detects format and handles both seamlessly.

    Args:
        blob_client: Blob storage client
        container_name: Container name for processed content
        limit: Maximum number of articles to retrieve

    Returns:
        List of processed article data dictionaries
    """
    try:
        # List ALL blobs in the container (no prefix filter)
        blobs = await blob_client.list_blobs(container=container_name)

        if not blobs:
            logger.info(f"No blobs found in container: {container_name}")
            return []

        # Filter to only JSON files and sort by last modified (newest first)
        json_blobs = [blob for blob in blobs if blob.get("name", "").endswith(".json")]

        if not json_blobs:
            logger.info(f"No JSON files found in container: {container_name}")
            return []

        # Sort by last modified date, newest first
        sorted_blobs = sorted(
            json_blobs, key=lambda x: x.get("last_modified", datetime.min), reverse=True
        )

        logger.info(
            f"Found {len(sorted_blobs)} JSON files in {container_name}, processing up to {limit}"
        )

        # Load and process files, detecting format automatically
        articles = []
        for blob in sorted_blobs:
            if len(articles) >= limit:
                break

            try:
                blob_name = blob.get("name", "")
                content_json = await blob_client.download_text(
                    container=container_name, blob_name=blob_name
                )

                if not content_json:
                    logger.warning(f"Empty content in blob {blob_name}")
                    continue

                # Parse JSON content
                raw_data = json.loads(content_json)

                # Detect format: batch collection or individual article
                if (
                    isinstance(raw_data, dict)
                    and "items" in raw_data
                    and "metadata" in raw_data
                ):
                    # Format 1: Batch collection file (CollectionResult format)
                    try:
                        validated_collection = (
                            ContractValidator.validate_collection_data(raw_data)
                        )
                        # Extract items and convert to dict format
                        for item in validated_collection.items:
                            if len(articles) >= limit:
                                break
                            article_dict = item.model_dump()
                            article_dict["_source_blob"] = blob_name
                            article_dict["_batch_file"] = True
                            articles.append(article_dict)
                        logger.debug(
                            f"Loaded {len(validated_collection.items)} articles from batch file: {blob_name}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to validate collection file {blob_name}: {e}"
                        )
                        continue
                else:
                    # Format 2: Individual article file
                    raw_data["_blob_name"] = blob_name
                    raw_data["_last_modified"] = blob.get("last_modified")
                    raw_data["_batch_file"] = False
                    articles.append(raw_data)
                    logger.debug(f"Loaded individual article from: {blob_name}")

            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in blob {blob_name}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error loading blob {blob_name}: {e}")
                continue

        logger.info(
            f"Successfully loaded {len(articles)} articles from {container_name}"
        )
        return articles

    except Exception as e:
        # Handle unexpected errors securely
        error_response = error_handler.handle_error(
            error=e,
            error_type="service_unavailable",
            context={
                "operation": "get_processed_articles",
                "container": container_name,
            },
        )
        logger.error(
            f"Unexpected article retrieval error: {error_response['error_id']}"
        )
        return []


async def get_markdown_articles(
    blob_client: SimplifiedBlobClient, container_name: str
) -> List[Dict[str, Any]]:
    """
    Retrieve all markdown articles for site generation.

    Args:
        blob_client: Blob storage client
        container_name: Container name for markdown content

    Returns:
        List of article metadata dictionaries
    """
    try:
        # List all markdown files
        markdown_files = await blob_client.list_blobs(container=container_name)

        articles = []
        for blob_info in markdown_files:
            if blob_info["name"].endswith(".md"):
                try:
                    # Download and parse markdown file
                    content = await blob_client.download_text(
                        container=container_name, blob_name=blob_info["name"]
                    )

                    # Skip if content is empty
                    if not content:
                        logger.warning(
                            f"Empty content in markdown file: {blob_info['name']}"
                        )
                        continue

                    # Parse frontmatter and create article metadata
                    article_metadata = parse_markdown_frontmatter(
                        blob_info["name"], content
                    )
                    if article_metadata:
                        articles.append(article_metadata)

                except Exception as e:
                    logger.warning(
                        f"Failed to process article {blob_info['name']}: {e}"
                    )
                    continue

        return articles

    except Exception as e:
        logger.error(f"Failed to get markdown articles: {e}")
        return []


# Generation Helper Functions


async def generate_article_markdown(
    article_data: Dict[str, Any],
    blob_client: SimplifiedBlobClient,
    container_name: str,
    force_regenerate: bool,
) -> str:
    """
    Generate markdown file for a single article.

    Args:
        article_data: Article data dictionary
        blob_client: Blob storage client
        container_name: Container name for markdown output
        force_regenerate: Whether to overwrite existing files

    Returns:
        Generated markdown filename
    """
    # Create safe filename
    filename = create_safe_filename(article_data.get("title", "untitled"))
    markdown_filename = f"{filename}.md"

    # Check if file already exists and skip if not forcing regeneration
    if not force_regenerate:
        existing_blobs = await blob_client.list_blobs(container=container_name)
        if any(blob["name"] == markdown_filename for blob in existing_blobs):
            logger.debug(f"Skipping existing file: {markdown_filename}")
            return markdown_filename

    # Create markdown content
    markdown_content = create_markdown_content(article_data)

    # Upload to blob storage
    await blob_client.upload_text(
        container=container_name,
        blob_name=markdown_filename,
        text=markdown_content,
        overwrite=force_regenerate,
    )

    logger.debug(f"Generated markdown: {markdown_filename}")
    return markdown_filename


async def create_complete_site(
    articles: List[Dict[str, Any]],
    theme: str,
    blob_client: SimplifiedBlobClient,
    config: Dict[str, Any],
    force_rebuild: bool,
) -> List[str]:
    """
    Create complete static site from articles.

    Args:
        articles: List of article metadata
        theme: Theme name for styling
        blob_client: Blob storage client
        config: Configuration dictionary
        force_rebuild: Whether to force complete rebuild

    Returns:
        List of generated file names
    """
    generated_files = []

    # Prepare articles: deduplicate and sort by date (newest first)
    processed_articles = prepare_articles_for_display(articles)

    logger.info(
        f"Processing {len(processed_articles)} unique articles "
        f"(from {len(articles)} raw articles, sorted by date)"
    )

    # Generate individual article pages
    for article in processed_articles:
        # Generate HTML using pure function
        html_content = generate_article_page(
            article=article,
            config=config,
        )

        # Upload to blob storage
        # Use same safe filename logic as markdown generation for traceability
        # Include article ID to prevent collisions with identical titles
        article_id = article.get("id", "article")
        safe_title = create_safe_filename(article.get("title", "untitled"))
        filename = f"articles/{article_id}-{safe_title}.html"
        await blob_client.upload_text(
            container=config["STATIC_SITES_CONTAINER"],
            blob_name=filename,
            text=html_content,
            overwrite=True,
        )
        generated_files.append(filename)

    # Generate index page with processed articles
    html_content = generate_index_page(
        articles=processed_articles,
        config=config,
    )

    # Upload to blob storage
    index_filename = "index.html"
    await blob_client.upload_text(
        container=config["STATIC_SITES_CONTAINER"],
        blob_name=index_filename,
        text=html_content,
        overwrite=True,
    )
    generated_files.append(index_filename)

    # Generate RSS feed with processed articles
    rss_content = generate_rss_feed(
        articles=processed_articles,
        config=config,
    )

    # Upload to blob storage
    rss_filename = "feed.xml"
    await blob_client.upload_text(
        container=config["STATIC_SITES_CONTAINER"],
        blob_name=rss_filename,
        text=rss_content,
        overwrite=True,
    )
    generated_files.append(rss_filename)

    return generated_files


# Utility Functions


def create_markdown_content(article_data: Dict[str, Any]) -> str:
    """
    Create markdown content with frontmatter from article data.

    Generates a complete markdown file with YAML frontmatter containing
    article metadata followed by the article content.

    Args:
        article_data: Article data dictionary containing title, content, topic_id, source

    Returns:
        Complete markdown content string with frontmatter and content

    Examples:
        >>> article = {
        ...     "title": "AI Revolution",
        ...     "content": "AI is changing the world...",
        ...     "topic_id": "ai-123",
        ...     "source": "reddit"
        ... }
        >>> markdown = create_markdown_content(article)
        >>> print(markdown[:50])
        '---\ntitle: "AI Revolution"\ntopic_id: "ai-123"\n...'

        >>> # Handles missing fields gracefully
        >>> minimal = {"content": "Just content"}
        >>> result = create_markdown_content(minimal)
        >>> "Untitled" in result
        True
    """
    # Extract article information
    title = article_data.get("title", "Untitled")
    # Support both 'content' and 'article_content' field names for compatibility
    content = article_data.get("content") or article_data.get("article_content", "")
    topic_id = article_data.get("topic_id", "")
    source = article_data.get("source", "unknown")

    # Create frontmatter
    frontmatter = f"""---
title: "{title}"
topic_id: "{topic_id}"
source: "{source}"
generated_at: "{datetime.now(timezone.utc).isoformat()}"
---

"""

    return frontmatter + content


def create_safe_filename(title: str) -> str:
    """
    Create safe filename from article title.

    Converts article titles to filesystem-safe filenames by removing unsafe characters,
    converting to lowercase, replacing spaces with hyphens, and limiting length.

    Args:
        title: Article title string to convert to safe filename

    Returns:
        Safe filename string (max 50 chars) suitable for filesystem usage

    Examples:
        >>> create_safe_filename("My Great Article!")
        'my-great-article'
        >>> create_safe_filename("Tech Review: AI & Machine Learning")
        'tech-review-ai-machine-learning'
        >>> create_safe_filename("")
        'untitled'
        >>> create_safe_filename("A" * 100)
        'a' * 50  # Truncated to 50 characters
    """
    # Remove unsafe characters and convert to lowercase
    safe_name = re.sub(r"[^\w\s-]", "", title).strip().lower()
    # Replace spaces with hyphens
    safe_name = re.sub(r"\s+", "-", safe_name)
    # Limit length
    return safe_name[:50] if safe_name else "untitled"


def parse_markdown_frontmatter(filename: str, content: str) -> Optional[Dict[str, Any]]:
    """
    Parse markdown frontmatter to create article metadata.

    Extracts YAML frontmatter from markdown content and combines it with
    filename-based metadata to create a complete article metadata dictionary.

    Args:
        filename: Markdown filename (used to extract slug and fallback title)
        content: Complete markdown file content including frontmatter

    Returns:
        Article metadata dictionary with title, content, slug, etc., or None if parsing fails

    Examples:
        >>> content = '''---
        ... title: "My Article"
        ... topic_id: "12345"
        ... ---
        ...
        ... This is the article content.
        ... '''
        >>> result = parse_markdown_frontmatter("my-article.md", content)
        >>> result['title']
        'My Article'
        >>> result['slug']
        'my-article'

        >>> # Handles missing frontmatter gracefully
        >>> parse_markdown_frontmatter("broken.md", "No frontmatter here")
        None
    """
    try:
        if not content.startswith("---"):
            return None

        # Split frontmatter and content
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        # Parse frontmatter
        frontmatter = yaml.safe_load(parts[1])
        if not isinstance(frontmatter, dict):
            return None

        # Create article metadata
        slug = filename.replace(".md", "")
        generated_at = frontmatter.get("generated_at")

        # Skip articles without generated_at (old format from Sept 2025)
        if not generated_at:
            logger.info(
                f"Skipping article {filename} - missing generated_at field (old format)"
            )
            return None

        return {
            "slug": slug,
            "title": frontmatter.get("title", "Untitled"),
            "topic_id": frontmatter.get("topic_id", ""),
            "source": frontmatter.get("source", "unknown"),
            "generated_at": generated_at,
            "published_date": generated_at,  # Use generated_at as published_date
            "url": f"/articles/{slug}.html",  # Generate URL from slug
            "content": parts[2].strip(),
        }

    except Exception as e:
        logger.warning(f"Failed to parse frontmatter for {filename}: {e}")
        return None


def create_empty_generation_response(
    generator_id: str, operation_type: str
) -> GenerationResponse:
    """
    Create empty generation response for when no content is found.

    Args:
        generator_id: Generator identifier
        operation_type: Type of operation performed

    Returns:
        Empty GenerationResponse
    """
    return GenerationResponse(
        generator_id=generator_id,
        operation_type=operation_type,
        files_generated=0,
        processing_time=0.0,
        output_location="",
        generated_files=[],
        errors=[],
    )

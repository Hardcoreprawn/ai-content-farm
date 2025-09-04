#!/usr/bin/env python3
"""
Processor Factory for Content Processing Services

Automatically selects between real OpenAI service and mock service based on
environment configuration and credential availability.

This allows seamless testing and development without requiring OpenAI credentials
while maintaining the same interface for production use.
"""

import logging
from typing import Union

from src.services.mock_service import MockContentProcessor
from src.services.openai_service import ContentProcessor

from config import settings

logger = logging.getLogger(__name__)


def create_processor() -> Union[ContentProcessor, MockContentProcessor]:
    """
    Create appropriate processor based on environment and credential availability.

    Returns:
        ContentProcessor for production with credentials
        MockContentProcessor for testing/development environments
    """

    # Check if we have OpenAI credentials configured
    has_openai_credentials = bool(
        settings.azure_openai_api_key
        and (
            settings.azure_openai_endpoint
            or settings.openai_endpoint_uk_south
            or settings.openai_endpoint_west_europe
        )
    )

    # Use mock service if in testing/development environment or no credentials
    if (
        settings.is_local_environment()
        or settings.environment.lower() in ["test", "testing"]
        or not has_openai_credentials
    ):

        logger.info(
            f"Using mock content processor (environment: {settings.environment}, "
            f"has_credentials: {has_openai_credentials})"
        )
        return MockContentProcessor()

    # Use real OpenAI service for production with credentials
    logger.info(
        f"Using real OpenAI content processor (environment: {settings.environment})"
    )
    return ContentProcessor()


# Global processor instance - automatically selects appropriate implementation
processor = create_processor()

# Log which processor is being used
if (
    hasattr(processor, "processing_stats")
    and "mock_mode" in processor.get_processing_statistics()
):
    logger.info("Content processor initialized in MOCK MODE for testing/development")
else:
    logger.info(
        "Content processor initialized in PRODUCTION MODE with real OpenAI integration"
    )

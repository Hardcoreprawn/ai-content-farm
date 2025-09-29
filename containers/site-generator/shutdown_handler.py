"""
Graceful shutdown handling for site generator container.

Manages container lifecycle and shutdown procedures.
"""

import asyncio
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def graceful_shutdown(exit_code: int = 0):
    """Gracefully shutdown the container after a brief delay."""
    await asyncio.sleep(2)  # Brief delay to ensure logs are flushed
    logger.info(f"Gracefully shutting down container with exit code {exit_code}")
    os._exit(exit_code)


async def handle_startup_auto_shutdown(processed_count: int) -> None:
    """Handle auto-shutdown logic based on startup processing results."""
    # Check if auto-shutdown is disabled (for development/testing)
    disable_auto_shutdown = (
        os.getenv("DISABLE_AUTO_SHUTDOWN", "false").lower() == "true"
    )

    if processed_count > 0:
        logger.info(f"Startup: Processed {processed_count} pending messages")
        if disable_auto_shutdown:
            logger.info(
                "Startup: All messages processed - container will remain active (DISABLE_AUTO_SHUTDOWN=true)"
            )
        else:
            logger.info(
                "Startup: All messages processed - scheduling graceful shutdown"
            )
            # Schedule graceful shutdown after processing
            asyncio.create_task(graceful_shutdown())
    else:
        if disable_auto_shutdown:
            logger.info(
                "Startup: No pending messages found - container will remain active (DISABLE_AUTO_SHUTDOWN=true)"
            )
        else:
            logger.info(
                "Startup: No pending messages found - scheduling graceful shutdown"
            )
            # Schedule shutdown if no work to do
            asyncio.create_task(graceful_shutdown())


async def handle_startup_error_shutdown() -> None:
    """Handle shutdown when startup processing fails."""
    disable_auto_shutdown = (
        os.getenv("DISABLE_AUTO_SHUTDOWN", "false").lower() == "true"
    )

    if disable_auto_shutdown:
        logger.warning(
            "Startup error occurred but container will remain active (DISABLE_AUTO_SHUTDOWN=true)"
        )
    else:
        # Schedule shutdown with error
        asyncio.create_task(graceful_shutdown(exit_code=1))

"""
Container Lifecycle Management

Shared utilities for consistent container startup, shutdown, and lifecycle management
across all Azure Container App instances. Provides environment-based control for
debugging vs production efficiency.
"""

import asyncio
import logging
import os
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class ContainerLifecycleManager:
    """Manages container lifecycle with environment-based shutdown control."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.disable_auto_shutdown = (
            os.getenv("DISABLE_AUTO_SHUTDOWN", "false").lower() == "true"
        )

    async def graceful_shutdown(self, exit_code: int = 0):
        """Gracefully shutdown the container after a brief delay."""
        logger.info(
            f"🛑 SHUTDOWN: Scheduling graceful shutdown in 2 seconds (exit_code: {exit_code})"
        )
        await asyncio.sleep(2)

        # Clean up any service-specific resources
        logger.info("🧹 CLEANUP: Closing service connections...")

        logger.info("✅ SHUTDOWN: Graceful shutdown complete")
        os._exit(exit_code)

    def should_shutdown_after_work(self) -> bool:
        """Check if container should shutdown after completing work."""
        return not self.disable_auto_shutdown

    async def handle_work_completion(self, work_description: str, success: bool = True):
        """Handle post-work lifecycle decision (shutdown or stay alive)."""
        if success:
            if self.disable_auto_shutdown:
                logger.info(
                    f"{work_description} completed - container will remain active (DISABLE_AUTO_SHUTDOWN=true)"
                )
            else:
                logger.info(
                    f"{work_description} completed - scheduling graceful shutdown"
                )
                asyncio.create_task(self.graceful_shutdown())
        else:
            if self.disable_auto_shutdown:
                logger.warning(
                    f"{work_description} failed but container will remain active (DISABLE_AUTO_SHUTDOWN=true)"
                )
            else:
                logger.error(
                    f"{work_description} failed - scheduling graceful shutdown"
                )
                asyncio.create_task(self.graceful_shutdown(exit_code=1))

    async def handle_startup_queue_processing(
        self, process_messages_func: Callable, queue_name: str, max_messages: int = 32
    ) -> None:
        """Handle startup queue processing with consistent lifecycle management."""
        try:
            logger.info(f"Startup: Starting queue processing for {queue_name}")
            processed_count = await process_messages_func(
                queue_name=queue_name, max_messages=max_messages
            )

            await self.handle_work_completion(
                f"Startup queue processing ({processed_count} messages)", success=True
            )

        except Exception as e:
            logger.error(f"Startup queue processing failed: {e}")
            await self.handle_work_completion("Startup queue processing", success=False)

    async def handle_scheduled_work(
        self, work_func: Callable, work_description: str, *args, **kwargs
    ) -> Any:
        """Handle scheduled work (like KEDA cron) with consistent lifecycle management."""
        try:
            logger.info(f"Starting scheduled work: {work_description}")
            result = await work_func(*args, **kwargs)

            await self.handle_work_completion(work_description, success=True)
            return result

        except Exception as e:
            logger.error(f"Scheduled work failed: {work_description} - {e}")
            await self.handle_work_completion(work_description, success=False)
            raise


def create_lifecycle_manager(service_name: str) -> ContainerLifecycleManager:
    """Factory function to create a lifecycle manager for a service."""
    return ContainerLifecycleManager(service_name)


# Legacy compatibility functions for existing containers
async def graceful_shutdown(exit_code: int = 0):
    """Legacy compatibility function - use ContainerLifecycleManager instead."""
    logger.warning(
        "Using legacy graceful_shutdown - consider migrating to ContainerLifecycleManager"
    )
    manager = ContainerLifecycleManager("unknown")
    await manager.graceful_shutdown(exit_code)


def should_auto_shutdown() -> bool:
    """Check if containers should auto-shutdown after work completion."""
    return os.getenv("DISABLE_AUTO_SHUTDOWN", "false").lower() != "true"

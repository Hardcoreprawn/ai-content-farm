"""
Queue Coordinator Service

Handles all queue message operations for the content processing pipeline:
- Markdown generation queue messages
- Site builder queue messages (future)
- Queue trigger logic and coordination
"""

import logging
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from libs.queue_triggers import (
    should_trigger_next_stage,
    trigger_markdown_generation,
)

logger = logging.getLogger(__name__)


class QueueCoordinator:
    """
    Coordinates queue message operations for the content pipeline.

    Responsibilities:
    - Send markdown generation requests
    - Send site build requests (future)
    - Track queue operation success/failure
    - Implement backoff/retry logic (future)
    """

    def __init__(self, correlation_id: Optional[str] = None):
        """
        Initialize queue coordinator.

        Args:
            correlation_id: Optional correlation ID for tracking related operations
        """
        self.correlation_id = correlation_id or str(uuid4())
        self.messages_sent = 0
        self.messages_failed = 0

    async def trigger_markdown_for_article(
        self,
        blob_name: str,
        force_trigger: bool = True,
    ) -> Dict[str, Any]:
        """
        Trigger markdown generation for a single processed article.

        Args:
            blob_name: Name of the processed article blob
            force_trigger: Whether to force triggering regardless of file count

        Returns:
            Dict with status, message_id, and error information
        """
        try:
            logger.info(f"📤 QUEUE: Checking markdown trigger for {blob_name}")

            # Check if we should trigger
            should_trigger = await should_trigger_next_stage(
                files=[blob_name],
                force_trigger=force_trigger,
                minimum_files=1,
            )

            if not should_trigger:
                logger.debug(
                    f"⏭️  QUEUE: Skipping trigger for {blob_name} (threshold not met)"
                )
                return {
                    "status": "skipped",
                    "reason": "trigger_threshold_not_met",
                }

            # Trigger markdown generation
            result = await trigger_markdown_generation(
                processed_files=[blob_name],
                correlation_id=self.correlation_id,
            )

            if result.get("status") == "success":
                self.messages_sent += 1
                message_id = result.get("message_id")
                logger.info(
                    f"✅ QUEUE: Markdown generation queued for {blob_name} (msg_id: {message_id})"
                )
                return {
                    "status": "success",
                    "message_id": message_id,
                    "queue": "markdown-generation-requests",
                }
            else:
                self.messages_failed += 1
                error = result.get("error", "Unknown error")
                logger.error(f"❌ QUEUE: Failed to queue markdown generation: {error}")
                return {
                    "status": "failed",
                    "error": error,
                }

        except Exception as e:
            self.messages_failed += 1
            logger.error(f"❌ QUEUE: Exception triggering markdown generation: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    async def trigger_markdown_batch(
        self,
        blob_names: List[str],
        batch_size: int = 10,
    ) -> Dict[str, Any]:
        """
        Trigger markdown generation for a batch of processed articles.

        Args:
            blob_names: List of processed article blob names
            batch_size: Maximum files per batch message

        Returns:
            Dict with counts of successful/failed triggers
        """
        if not blob_names:
            return {
                "status": "success",
                "messages_sent": 0,
                "files_processed": 0,
            }

        successful = 0
        failed = 0
        message_ids = []

        # Process in batches
        for i in range(0, len(blob_names), batch_size):
            batch = blob_names[i : i + batch_size]

            try:
                result = await trigger_markdown_generation(
                    processed_files=batch,
                    correlation_id=self.correlation_id,
                )

                if result.get("status") == "success":
                    successful += len(batch)
                    self.messages_sent += 1
                    message_ids.append(result.get("message_id"))
                    logger.info(
                        f"✅ QUEUE: Batch queued - {len(batch)} files (msg_id: {result.get('message_id')})"
                    )
                else:
                    failed += len(batch)
                    self.messages_failed += 1
                    logger.error(
                        f"❌ QUEUE: Batch failed - {len(batch)} files: {result.get('error')}"
                    )

            except Exception as e:
                failed += len(batch)
                self.messages_failed += 1
                logger.error(f"❌ QUEUE: Batch exception: {e}")

        return {
            "status": "success" if failed == 0 else "partial",
            "messages_sent": len(message_ids),
            "files_successful": successful,
            "files_failed": failed,
            "message_ids": message_ids,
        }

    async def trigger_site_build(
        self,
        markdown_files: List[str],
        force_rebuild: bool = False,
    ) -> Dict[str, Any]:
        """
        Trigger site build after markdown files are generated.

        This is a placeholder for future site-builder integration.

        Args:
            markdown_files: List of markdown file blob names
            force_rebuild: Whether to force a full site rebuild

        Returns:
            Dict with status and message information
        """
        try:
            logger.info(
                f"📤 QUEUE: Preparing site build trigger for {len(markdown_files)} files"
            )

            # Check if we should trigger (future: configurable threshold)
            should_trigger = await should_trigger_next_stage(
                files=markdown_files,
                force_trigger=force_rebuild,
                minimum_files=5,  # Wait for at least 5 markdown files
            )

            if not should_trigger:
                logger.debug("⏭️  QUEUE: Skipping site build (threshold not met)")
                return {
                    "status": "skipped",
                    "reason": "threshold_not_met",
                }

            # Trigger site build (future implementation)
            # TODO: Implement trigger_site_build in libs/queue_triggers.py
            logger.warning("⚠️  QUEUE: Site build trigger not yet implemented")
            result = {
                "status": "not_implemented",
                "error": "trigger_site_build function not yet created",
            }

            if result.get("status") == "success":
                self.messages_sent += 1
                logger.info(
                    f"✅ QUEUE: Site build queued (msg_id: {result.get('message_id')})"
                )
                return {
                    "status": "success",
                    "message_id": result.get("message_id"),
                    "queue": "site-build-requests",
                }
            else:
                self.messages_failed += 1
                logger.warning(
                    f"⚠️  QUEUE: Site build trigger not yet implemented: {result.get('error')}"
                )
                return {
                    "status": "not_implemented",
                    "error": result.get("error"),
                }

        except Exception as e:
            self.messages_failed += 1
            logger.error(f"❌ QUEUE: Exception triggering site build: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    def get_stats(self) -> Dict[str, Union[int, float]]:
        """Get queue operation statistics."""
        return {
            "messages_sent": self.messages_sent,
            "messages_failed": self.messages_failed,
            "success_rate": (
                self.messages_sent / (self.messages_sent + self.messages_failed)
                if (self.messages_sent + self.messages_failed) > 0
                else 0.0
            ),
        }

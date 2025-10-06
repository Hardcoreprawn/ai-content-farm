"""
Reprocess Endpoints - Bulk Content Reprocessing

RESTful endpoints for reprocessing collected content through the queue system.
Implements OWASP-compliant error handling, input validation, and safety features.

Security Features:
- Dry-run by default to prevent accidental expensive operations
- Input validation and sanitization
- Rate limiting friendly (no excessive API calls)
- Comprehensive error handling without information disclosure
"""

import json
import logging
import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from libs.app_config import BlobContainers
from libs.secure_error_handler import SecureErrorHandler
from libs.shared_models import StandardResponse, create_service_dependency
from libs.simplified_blob_client import SimplifiedBlobClient

# Configure logging
logger = logging.getLogger(__name__)

# Create router for reprocessing
router = APIRouter(prefix="/reprocess", tags=["reprocess"])

# Create service metadata dependency
service_metadata = create_service_dependency("content-womble")

# Initialize secure error handler
error_handler = SecureErrorHandler("content-collector")


class ReprocessRequest(BaseModel):
    """Request model for reprocessing operations."""

    dry_run: bool = Field(
        default=True,
        description="If true, only simulate the operation without queuing messages",
    )
    max_items: int | None = Field(
        default=None,
        ge=1,
        le=10000,
        description="Optional limit on number of items to process",
    )


class ReprocessResponse(BaseModel):
    """Response model for reprocessing operations."""

    status: str
    message: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]


@router.post(
    "",
    response_model=StandardResponse,
    summary="Reprocess All Collections",
    description="Queue all collected content for reprocessing with updated metadata generation (dry-run by default)",
)
async def reprocess_collections(
    request: ReprocessRequest = ReprocessRequest(),
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """
    Reprocess all collected content items.

    This endpoint iterates through all collected content and creates
    queue messages for the content-processor to reprocess each item
    with the latest metadata generation rules.

    **SAFETY FEATURE**: Defaults to dry_run=true to prevent accidental
    expensive operations. Set dry_run=false to actually queue messages.

    Perfect for:
    - Testing the pipeline at scale
    - Applying new metadata generation rules to existing content
    - Regenerating all articles with updated prompts
    - Clean rebuild scenarios

    Args:
        request: Reprocess configuration with dry_run and max_items
        metadata: Service metadata from dependency

    Returns:
        StandardResponse with count of items that would be/were queued

    Security:
    - Dry-run by default prevents accidental costs
    - Max items clamped to reasonable range (1-10000)
    - No user input in queue messages (prevents injection)
    - Comprehensive error handling without information disclosure
    """
    start_time = time.time()

    try:
        # Validate and sanitize inputs
        dry_run = bool(request.dry_run)
        max_items = None
        if request.max_items is not None:
            # Clamp to safe range
            max_items = max(1, min(request.max_items, 10000))

        # Get blob storage client
        blob_client = SimplifiedBlobClient()

        # List all blobs in collected-content container
        blobs = await blob_client.list_blobs(
            container=BlobContainers.COLLECTED_CONTENT,
            prefix="collections/",
        )

        # Initialize queue client only if not dry run
        queue_client = None
        if not dry_run:
            from libs.queue_client import get_queue_client

            queue_client = get_queue_client("content-processing-requests")
            logger.info("Reprocess: Queue client initialized for actual processing")
        else:
            logger.info("Reprocess: DRY RUN mode - no messages will be queued")

        queued_count = 0
        scanned_count = 0
        skipped_count = 0

        # Iterate through collections
        for blob in blobs:
            # Check max_items limit
            if max_items and scanned_count >= max_items:
                logger.info(f"Reprocess: Reached max_items limit ({max_items})")
                break

            blob_name = blob.get("name")
            if not blob_name or not blob_name.endswith(".json"):
                skipped_count += 1
                continue

            scanned_count += 1

            try:
                # Read the collection file metadata (don't need full content)
                collection = await blob_client.download_json(
                    container=BlobContainers.COLLECTED_CONTENT,
                    blob_name=blob_name,
                )

                if not collection:
                    skipped_count += 1
                    continue

                # Create queue message payload (only if not dry run)
                if not dry_run and queue_client:
                    message_payload = {
                        "operation": "process",
                        "service_name": "content-collector",
                        "payload": {
                            "blob_path": blob_name,
                            "collection_id": collection.get("metadata", {}).get(
                                "collection_id", f"reprocess_{int(time.time())}"
                            ),
                            "reprocess": True,
                        },
                        "correlation_id": f"reprocess_{int(time.time())}_{scanned_count}",
                    }

                    # Send message to queue
                    await queue_client.send_message(json.dumps(message_payload))

                queued_count += 1

            except json.JSONDecodeError as json_error:
                # Log but don't fail entire operation
                logger.warning(
                    f"Reprocess: Invalid JSON in blob {blob_name}: {json_error}"
                )
                skipped_count += 1
                continue

            except Exception as item_error:
                # Log error but continue processing other items
                error_handler.log_error(
                    item_error,
                    context={
                        "blob_name": blob_name,
                        "operation": "reprocess_item",
                        "scanned_count": scanned_count,
                    },
                )
                skipped_count += 1
                continue

        execution_time = time.time() - start_time

        # Calculate estimates
        estimated_cost = queued_count * 0.0016
        estimated_time_seconds = queued_count * 6
        estimated_time_minutes = estimated_time_seconds // 60

        # Build response message
        if dry_run:
            response_message = (
                f"DRY RUN: Would queue {queued_count} collections for reprocessing"
            )
        else:
            response_message = f"Queued {queued_count} collections for reprocessing"

        return StandardResponse(
            status="success",
            message=response_message,
            data={
                "dry_run": dry_run,
                "collections_queued": queued_count,
                "collections_scanned": scanned_count,
                "collections_skipped": skipped_count,
                "queue_name": (
                    "content-processing-requests" if not dry_run else "none (dry run)"
                ),
                "estimated_cost": f"${estimated_cost:.2f}",
                "estimated_time": f"{estimated_time_seconds} seconds (~{estimated_time_minutes} min)",
            },
            metadata={
                **metadata,
                "execution_time_ms": int(execution_time * 1000),
            },
        )

    except Exception as e:
        # Use secure error handling to prevent information disclosure
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="reprocess",
            user_message="Failed to reprocess collections",
            context={
                "dry_run": request.dry_run,
                "max_items": request.max_items,
            },
        )

        return StandardResponse(
            status=error_response["status"],
            message=error_response["message"],
            data={},
            errors=error_response["errors"],
            metadata=error_response["metadata"],
        )


@router.get(
    "/status",
    response_model=StandardResponse,
    summary="Get Reprocess Status",
    description="Get current status of reprocessing operations",
)
async def reprocess_status(
    metadata: Dict[str, Any] = Depends(service_metadata),
):
    """
    Get status of reprocessing operations.

    Returns information about the processing queue depth and
    collected content statistics.

    Returns:
        StandardResponse with queue and content statistics
    """
    try:
        from libs.queue_client import get_queue_client

        # Get queue client
        queue_client = get_queue_client("content-processing-requests")
        queue_info = queue_client.get_health_status()

        # Get blob storage client
        blob_client = SimplifiedBlobClient()

        # Count collected items
        blobs = await blob_client.list_blobs(
            container=BlobContainers.COLLECTED_CONTENT,
            prefix="collections/",
        )
        collected_count = sum(
            1 for blob in blobs if blob.get("name", "").endswith(".json")
        )

        # Count processed items
        processed_blobs = await blob_client.list_blobs(
            container=BlobContainers.PROCESSED_CONTENT,
            prefix="",
        )
        processed_count = sum(
            1 for blob in processed_blobs if blob.get("name", "").endswith(".json")
        )

        return StandardResponse(
            status="success",
            message="Reprocess status retrieved",
            data={
                "queue_depth": queue_info.get("approximate_message_count", 0),
                "collected_items": collected_count,
                "processed_items": processed_count,
                "queue_name": "content-processing-requests",
            },
            metadata=metadata,
        )

    except Exception as e:
        error_response = error_handler.create_http_error_response(
            status_code=500,
            error=e,
            error_type="status",
            user_message="Failed to retrieve reprocess status",
        )

        return StandardResponse(
            status=error_response["status"],
            message=error_response["message"],
            data={},
            errors=error_response["errors"],
            metadata=error_response["metadata"],
        )

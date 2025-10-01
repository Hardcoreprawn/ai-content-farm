"""
Storage Verification and Summary Operations

Pure functions for verifying storage containers and creating operation summaries.
Extracted from storage_content_operations.py for better maintainability.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def verify_storage_containers(
    blob_client, required_containers: List[str]
) -> Dict[str, Any]:
    """
    Verify that all required storage containers exist and are accessible.

    Pure function that checks container existence and permissions.

    Args:
        blob_client: Initialized SimplifiedBlobClient
        required_containers: List of container names to verify

    Returns:
        Verification results with container status information
    """
    try:
        container_status = {}
        all_accessible = True

        for container_name in required_containers:
            try:
                # Test container access by listing (limit to 1 item)
                blobs = blob_client.list_blobs(container_name, max_results=1)

                # If we can list, container is accessible
                container_status[container_name] = {
                    "exists": True,
                    "accessible": True,
                    "error": None,
                }

                logger.debug(f"Container {container_name} verified")

            except Exception as e:
                container_status[container_name] = {
                    "exists": False,
                    "accessible": False,
                    "error": str(e),
                }
                all_accessible = False
                logger.error(f"Container {container_name} not accessible: {e}")

        return {
            "status": "success" if all_accessible else "error",
            "all_accessible": all_accessible,
            "containers": container_status,
            "verified_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Container verification failed: {e}")
        return {
            "status": "error",
            "all_accessible": False,
            "containers": {
                container: {"exists": False, "accessible": False, "error": str(e)}
                for container in required_containers
            },
            "error": str(e),
            "verified_at": datetime.utcnow().isoformat(),
        }


def create_storage_summary(
    container_results: Dict[str, Any], operation_results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create comprehensive storage operation summary.

    Pure function that aggregates storage operation results.

    Args:
        container_results: Container verification results
        operation_results: Storage operation results

    Returns:
        Combined storage operation summary
    """
    try:
        # Calculate totals
        total_containers = len(container_results.get("containers", {}))
        accessible_containers = sum(
            1
            for status in container_results.get("containers", {}).values()
            if status.get("accessible", False)
        )

        total_operations = operation_results.get("total_operations", 0)
        successful_operations = operation_results.get("successful", 0)
        failed_operations = operation_results.get("failed", 0)

        # Determine overall status
        container_ok = container_results.get("all_accessible", False)
        operations_ok = operation_results.get("status") in ["success", "partial"]
        overall_status = "success" if container_ok and operations_ok else "error"

        return {
            "status": overall_status,
            "summary": {
                "containers": {
                    "total": total_containers,
                    "accessible": accessible_containers,
                    "failed": total_containers - accessible_containers,
                },
                "operations": {
                    "total": total_operations,
                    "successful": successful_operations,
                    "failed": failed_operations,
                },
            },
            "container_results": container_results,
            "operation_results": operation_results,
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Storage summary creation failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "container_results": container_results,
            "operation_results": operation_results,
            "generated_at": datetime.utcnow().isoformat(),
        }

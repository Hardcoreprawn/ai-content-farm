"""
Content Download Operations for Site Generator

Pure functions specifically for downloading content used in site generation.
Focused on article content retrieval and processing workflows.

This module is distinct from libs/blob_operations.py which provides general blob operations.
"""

import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


def download_blob_content(
    blob_client, container_name: str, blob_name: str, encoding: str = "utf-8"
) -> Dict[str, Any]:
    """
    Download blob content as string.

    Pure function that downloads and decodes blob content.

    Args:
        blob_client: Initialized SimplifiedBlobClient
        container_name: Source container name
        blob_name: Source blob name
        encoding: Text encoding for content

    Returns:
        Download result with content and metadata

    Raises:
        ValueError: If download fails or blob doesn't exist
    """
    try:
        # Download blob
        result = blob_client.download_blob(container_name, blob_name)

        if result.get("status") == "success":
            content = result["content"]

            # Decode if bytes
            if isinstance(content, bytes):
                content = content.decode(encoding)

            logger.debug(f"Downloaded {blob_name} from {container_name}")
            return {
                "status": "success",
                "content": content,
                "container": container_name,
                "blob_name": blob_name,
                "size": len(content.encode(encoding)),
                "downloaded_at": datetime.utcnow().isoformat(),
            }
        else:
            raise ValueError(
                f"Download failed: {result.get('message', 'Blob not found')}"
            )

    except Exception as e:
        logger.error(f"Failed to download {blob_name}: {e}")
        raise ValueError(f"Blob download failed: {e}")

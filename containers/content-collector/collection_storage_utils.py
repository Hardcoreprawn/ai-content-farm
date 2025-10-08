"""
Collection Storage Utilities

Helper functions for storing and querying collected content.
Extracted from service_logic.py for better organization and maintainability.
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from libs import BlobContainers
from libs.extended_data_contracts import (
    CollectionMetadata as EnhancedCollectionMetadata,
)
from libs.extended_data_contracts import (
    ContentItem,
    ExtendedCollectionResult,
    ProcessingStage,
    ProvenanceEntry,
    SourceMetadata,
)
from libs.simplified_blob_client import SimplifiedBlobClient


def generate_collection_id() -> str:
    """Generate a unique collection ID with timestamp."""
    timestamp = datetime.now(timezone.utc)
    return f"content_collection_{timestamp.strftime('%Y%m%d_%H%M%S')}"


def get_storage_path(collection_id: str) -> str:
    """Generate storage path for a collection.

    Args:
        collection_id: Collection identifier (expected format: *_YYYYMMDD_HHMMSS)

    Returns:
        Storage path like: collected-content/collections/YYYY/MM/DD/collection_id.json
    """
    # Extract date from collection ID - look for YYYYMMDD_HHMMSS pattern
    date_match = re.search(r"(\d{8})_(\d{6})", collection_id)

    if date_match:
        date_part = date_match.group(1)  # YYYYMMDD
        # Format as YYYY/MM/DD
        year = date_part[:4]
        month = date_part[4:6]
        day = date_part[6:8]
    else:
        # Fallback to current date if pattern not found
        now = datetime.now(timezone.utc)
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")

    return f"{BlobContainers.COLLECTED_CONTENT}/collections/{year}/{month}/{day}/{collection_id}.json"


def create_enhanced_collection(
    collection_id: str,
    collected_items: List[Dict[str, Any]],
    metadata: Dict[str, Any],
) -> ExtendedCollectionResult:
    """Create enhanced format collection with rich metadata and provenance.

    Args:
        collection_id: Unique collection identifier
        collected_items: Raw collected items
        metadata: Collection metadata

    Returns:
        ExtendedCollectionResult with enhanced metadata and provenance
    """
    enhanced_items = []

    for idx, item in enumerate(collected_items):
        try:
            if not isinstance(item, dict):
                continue

            # Create source metadata based on source type
            source_type = item.get("source", "web").lower()

            if source_type == "reddit":
                source_metadata = SourceMetadata(
                    source_type="reddit",
                    source_identifier=f"r/{item.get('subreddit', 'unknown')}",
                    collected_at=datetime.now(timezone.utc),
                    upvotes=item.get("ups") or item.get("upvotes"),
                    comments=item.get("num_comments") or item.get("comments"),
                    reddit_data={
                        "subreddit": item.get("subreddit"),
                        "flair": item.get("link_flair_text"),
                        "author": item.get("author"),
                        "score": item.get("score"),
                    },
                )
            elif source_type == "rss":
                source_metadata = SourceMetadata(
                    source_type="rss",
                    source_identifier=item.get("feed_url", "unknown"),
                    collected_at=datetime.now(timezone.utc),
                    rss_data={
                        "feed_title": item.get("feed_title"),
                        "category": item.get("category"),
                        "published": item.get("published"),
                        "author": item.get("author"),
                    },
                )
            else:
                # Generic web or other source
                source_metadata = SourceMetadata(
                    source_type=source_type,
                    source_identifier=item.get("url", "unknown"),
                    collected_at=datetime.now(timezone.utc),
                    custom_fields=item.get("source_specific_data", {}),
                )

            # Create enhanced content item
            content_item = ContentItem(
                id=item.get("id", f"{collection_id}_item_{idx}"),
                title=item.get("title", "Untitled"),
                url=item.get("url"),
                content=item.get("content"),
                summary=item.get("summary"),
                source=source_metadata,
            )

            # Add collection provenance
            collection_provenance = ProvenanceEntry(
                stage=ProcessingStage.COLLECTION,
                service_name="content-collector",
                service_version=metadata.get("collector_version", "2.0.0"),
                operation=f"{source_type}_collection",
                processing_time_ms=item.get("processing_time_ms", 0),
                parameters={
                    "collection_method": "adaptive",
                    "source_config": item.get("source_config", {}),
                },
            )
            content_item.add_provenance(collection_provenance)
            enhanced_items.append(content_item)

        except Exception:
            # Skip invalid items silently
            continue

    # Create enhanced metadata
    enhanced_metadata = EnhancedCollectionMetadata(
        timestamp=datetime.now(timezone.utc),
        collection_id=collection_id,
        total_items=len(enhanced_items),
        sources_processed=metadata.get("sources_processed", 1),
        processing_time_ms=metadata.get("processing_time_ms", 0),
        collector_version=metadata.get("collector_version", "2.0.0"),
        collection_strategy="adaptive",
        collection_template=metadata.get("template_name", "default"),
    )

    # Create enhanced collection result
    enhanced_result = ExtendedCollectionResult(
        metadata=enhanced_metadata, items=enhanced_items, schema_version="3.0"
    )

    # Calculate aggregate metrics
    enhanced_result.calculate_aggregate_metrics()

    return enhanced_result


async def get_recent_collections(
    storage: SimplifiedBlobClient, limit: int = 10
) -> List[Dict[str, Any]]:
    """Get list of recent collections from blob storage.

    Args:
        storage: Blob storage client
        limit: Maximum number of collections to return

    Returns:
        List of recent collection metadata
    """
    try:
        # List recent collection files
        container_name = BlobContainers.COLLECTED_CONTENT
        blobs = await storage.list_blobs(
            container=container_name, prefix="collections/"
        )

        # Sort by name (which includes timestamp) and take most recent
        sorted_blobs = sorted([blob["name"] for blob in blobs], reverse=True)[:limit]

        collections = []
        for blob_name in sorted_blobs:
            try:
                # Extract collection info from blob name
                collection_id = blob_name.split("/")[-1].replace(".json", "")
                path_parts = blob_name.split("/")
                if len(path_parts) >= 4:  # collections/YYYY/MM/DD/collection_id.json
                    date_str = f"{path_parts[1]}-{path_parts[2]}-{path_parts[3]}"
                    collections.append(
                        {
                            "collection_id": collection_id,
                            "date": date_str,
                            "storage_path": f"{container_name}/{blob_name}",
                        }
                    )
            except Exception:
                continue  # Skip malformed blob names

        return collections

    except Exception:
        # If we can't access storage, return empty list
        return []


async def get_collection_by_id(
    storage: SimplifiedBlobClient, collection_id: str
) -> Optional[Dict[str, Any]]:
    """Get collection data by ID.

    Args:
        storage: Blob storage client
        collection_id: The collection identifier

    Returns:
        Collection data or None if not found
    """
    try:
        # Search for the collection file
        container_name = "raw-content"
        blobs = await storage.list_blobs(
            container=container_name, prefix="collections/"
        )

        # Find the blob with matching collection ID
        target_blob = None
        for blob in blobs:
            blob_name = blob["name"]
            if collection_id in blob_name and blob_name.endswith(".json"):
                target_blob = blob_name
                break

        if not target_blob:
            return None

        # Load the collection data
        content = await storage.download_text(
            container=container_name, blob_name=target_blob
        )

        if content:
            return json.loads(content)
        return None

    except Exception:
        return None


async def list_collection_files(
    storage: SimplifiedBlobClient, prefix: str = "collections/"
) -> List[Dict[str, Any]]:
    """List collection files from storage.

    Args:
        storage: Blob storage client
        prefix: Prefix filter for blob names

    Returns:
        List of blob metadata dictionaries
    """
    return await storage.list_blobs(
        container=BlobContainers.COLLECTED_CONTENT, prefix=prefix
    )

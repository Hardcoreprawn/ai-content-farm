"""
Pure functional provenance tracking for content pipeline.

This module provides stateless functions for creating and managing
provenance entries that track content flow through the pipeline.

Contract Version: 1.0.0
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4


def create_provenance_entry(
    stage: Literal["collection", "processing", "publishing"],
    timestamp: Optional[datetime] = None,
    source: Optional[str] = None,
    processor_id: Optional[str] = None,
    version: str = "1.0.0",
    cost_usd: float = 0.0,
    tokens_used: int = 0,
    **extra_fields: Any,
) -> Dict[str, Any]:
    """
    Create a provenance entry for pipeline tracking.

    Pure function (when timestamp provided) that creates standardized
    provenance entry dict.

    Args:
        stage: Pipeline stage (collection, processing, publishing)
        timestamp: When this stage occurred (defaults to now)
        source: Source identifier (e.g., 'reddit-praw', 'openai-gpt4')
        processor_id: Processor instance ID (e.g., container ID)
        version: Component version
        cost_usd: Cost of this stage (default 0.0)
        tokens_used: Tokens used in this stage (default 0)
        **extra_fields: Additional fields to include

    Returns:
        Dict with provenance entry data

    Examples:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
        >>> entry = create_provenance_entry(
        ...     stage="processing",
        ...     timestamp=dt,
        ...     source="openai-gpt4o",
        ...     version="1.0.0"
        ... )
        >>> entry["stage"]
        'processing'
        >>> entry["timestamp"]
        '2025-10-08T12:00:00+00:00'
    """
    current_time = timestamp if timestamp is not None else datetime.now(timezone.utc)

    entry = {
        "stage": stage,
        "timestamp": current_time.isoformat(),
        "source": source,
        "processor_id": processor_id,
        "version": version,
        "cost_usd": cost_usd,
        "tokens_used": tokens_used,
    }

    # Add any extra fields
    entry.update(extra_fields)

    return entry


def add_provenance_entry(
    provenance_chain: List[Dict[str, Any]],
    stage: Literal["collection", "processing", "publishing"],
    timestamp: Optional[datetime] = None,
    source: Optional[str] = None,
    processor_id: Optional[str] = None,
    version: str = "1.0.0",
    cost_usd: float = 0.0,
    tokens_used: int = 0,
    **extra_fields: Any,
) -> List[Dict[str, Any]]:
    """
    Add a new provenance entry to an existing chain.

    Pure function that returns a new list with the entry appended.
    Does not modify the original chain.

    Args:
        provenance_chain: Existing provenance entries
        stage: Pipeline stage
        timestamp: When this stage occurred
        source: Source identifier
        processor_id: Processor instance ID
        version: Component version
        cost_usd: Cost of this stage
        tokens_used: Tokens used
        **extra_fields: Additional fields

    Returns:
        New list with entry appended

    Examples:
        >>> chain = []
        >>> chain = add_provenance_entry(chain, "collection", source="reddit")
        >>> len(chain)
        1
        >>> chain = add_provenance_entry(chain, "processing", source="openai")
        >>> len(chain)
        2
    """
    new_entry = create_provenance_entry(
        stage=stage,
        timestamp=timestamp,
        source=source,
        processor_id=processor_id,
        version=version,
        cost_usd=cost_usd,
        tokens_used=tokens_used,
        **extra_fields,
    )

    # Return new list with entry appended (immutable)
    return provenance_chain + [new_entry]


def calculate_total_cost(provenance_chain: List[Dict[str, Any]]) -> float:
    """
    Calculate total cost from provenance chain.

    Pure function with no side effects.

    Args:
        provenance_chain: List of provenance entries

    Returns:
        float: Total cost in USD

    Examples:
        >>> chain = [
        ...     {"cost_usd": 0.001, "stage": "collection"},
        ...     {"cost_usd": 0.015, "stage": "processing"}
        ... ]
        >>> calculate_total_cost(chain)
        0.016
    """
    if not provenance_chain or not isinstance(provenance_chain, list):
        return 0.0

    total = sum(
        entry.get("cost_usd", 0.0)
        for entry in provenance_chain
        if isinstance(entry, dict)
    )

    return round(total, 6)


def calculate_total_tokens(provenance_chain: List[Dict[str, Any]]) -> int:
    """
    Calculate total tokens from provenance chain.

    Pure function with no side effects.

    Args:
        provenance_chain: List of provenance entries

    Returns:
        int: Total tokens used

    Examples:
        >>> chain = [
        ...     {"tokens_used": 100, "stage": "collection"},
        ...     {"tokens_used": 500, "stage": "processing"}
        ... ]
        >>> calculate_total_tokens(chain)
        600
    """
    if not provenance_chain or not isinstance(provenance_chain, list):
        return 0

    return sum(
        entry.get("tokens_used", 0)
        for entry in provenance_chain
        if isinstance(entry, dict)
    )


def filter_provenance_by_stage(
    provenance_chain: List[Dict[str, Any]],
    stage: Literal["collection", "processing", "publishing"],
) -> List[Dict[str, Any]]:
    """
    Filter provenance entries by stage.

    Pure function that returns entries matching the specified stage.

    Args:
        provenance_chain: List of provenance entries
        stage: Stage to filter by

    Returns:
        List of entries matching stage

    Examples:
        >>> chain = [
        ...     {"stage": "collection", "source": "reddit"},
        ...     {"stage": "processing", "source": "openai"},
        ...     {"stage": "collection", "source": "rss"}
        ... ]
        >>> filtered = filter_provenance_by_stage(chain, "collection")
        >>> len(filtered)
        2
    """
    if not provenance_chain or not isinstance(provenance_chain, list):
        return []

    return [
        entry
        for entry in provenance_chain
        if isinstance(entry, dict) and entry.get("stage") == stage
    ]


def get_provenance_summary(provenance_chain: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create summary statistics from provenance chain.

    Pure function that aggregates provenance data.

    Args:
        provenance_chain: List of provenance entries

    Returns:
        Dict with summary statistics:
            - total_entries: Number of entries
            - total_cost_usd: Total cost
            - total_tokens: Total tokens
            - stages: List of unique stages
            - sources: List of unique sources

    Examples:
        >>> chain = [
        ...     {"stage": "collection", "source": "reddit", "cost_usd": 0.001, "tokens_used": 100},
        ...     {"stage": "processing", "source": "openai", "cost_usd": 0.015, "tokens_used": 500}
        ... ]
        >>> summary = get_provenance_summary(chain)
        >>> summary["total_entries"]
        2
        >>> summary["total_cost_usd"]
        0.016
    """
    if not provenance_chain or not isinstance(provenance_chain, list):
        return {
            "total_entries": 0,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "stages": [],
            "sources": [],
        }

    stages = set()
    sources = set()

    for entry in provenance_chain:
        if isinstance(entry, dict):
            if "stage" in entry:
                stages.add(entry["stage"])
            if "source" in entry and entry["source"]:
                sources.add(entry["source"])

    return {
        "total_entries": len(provenance_chain),
        "total_cost_usd": calculate_total_cost(provenance_chain),
        "total_tokens": calculate_total_tokens(provenance_chain),
        "stages": sorted(list(stages)),
        "sources": sorted(list(sources)),
    }


def validate_provenance_entry(entry: Dict[str, Any]) -> bool:
    """
    Validate that provenance entry has required fields.

    Pure function with no side effects.

    Args:
        entry: Provenance entry to validate

    Returns:
        bool: True if valid, False otherwise

    Examples:
        >>> entry = {
        ...     "stage": "processing",
        ...     "timestamp": "2025-10-08T12:00:00Z",
        ...     "version": "1.0.0"
        ... }
        >>> validate_provenance_entry(entry)
        True
        >>> validate_provenance_entry({"stage": "processing"})
        False
    """
    if not isinstance(entry, dict):
        return False

    required_fields = ["stage", "timestamp", "version"]
    if not all(field in entry for field in required_fields):
        return False

    # Validate stage value
    valid_stages = ["collection", "processing", "publishing"]
    if entry["stage"] not in valid_stages:
        return False

    return True


def generate_processor_id(short: bool = True) -> str:
    """
    Generate a unique processor ID.

    Uses UUID4 for uniqueness. Can return short (8 chars) or full UUID.

    Args:
        short: Return 8-char prefix instead of full UUID (default True)

    Returns:
        str: Processor ID

    Examples:
        >>> pid = generate_processor_id()
        >>> len(pid)
        8
        >>> pid = generate_processor_id(short=False)
        >>> len(pid)
        36
    """
    full_id = str(uuid4())
    return full_id[:8] if short else full_id


def sort_provenance_by_timestamp(
    provenance_chain: List[Dict[str, Any]], reverse: bool = False
) -> List[Dict[str, Any]]:
    """
    Sort provenance entries by timestamp.

    Pure function that returns a new sorted list.

    Args:
        provenance_chain: List of provenance entries
        reverse: Sort descending (newest first) if True

    Returns:
        New sorted list

    Examples:
        >>> chain = [
        ...     {"timestamp": "2025-10-08T12:00:00Z", "stage": "processing"},
        ...     {"timestamp": "2025-10-08T10:00:00Z", "stage": "collection"}
        ... ]
        >>> sorted_chain = sort_provenance_by_timestamp(chain)
        >>> sorted_chain[0]["stage"]
        'collection'
    """
    if not provenance_chain or not isinstance(provenance_chain, list):
        return []

    # Filter out entries without timestamps
    valid_entries = [
        entry
        for entry in provenance_chain
        if isinstance(entry, dict) and "timestamp" in entry
    ]

    # Sort by timestamp
    return sorted(valid_entries, key=lambda x: x["timestamp"], reverse=reverse)

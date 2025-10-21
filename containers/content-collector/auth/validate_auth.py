"""Container App API key validation for collection endpoint."""

import os
from typing import Dict


def get_expected_key() -> str:
    """Get expected API key from environment."""
    return os.getenv("COLLECTION_API_KEY", "").strip()


def validate_api_key(headers: Dict[str, str]) -> bool:
    """
    Validate API key from x-api-key header.

    Args:
        headers: Request headers dict

    Returns:
        True if valid key provided, False otherwise
    """
    expected_key = get_expected_key()
    if not expected_key:
        return False

    provided_key = headers.get("x-api-key", "").strip()
    return provided_key == expected_key

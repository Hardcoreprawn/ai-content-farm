#!/usr/bin/env python3
"""
Test configuration and fixtures for site-generator tests.

Uses smart contract-based mocking for fast, reliable tests.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock

import pytest

from tests.contracts.blob_storage_contract import (
    BlobItemContract,
    RankedContentContract,
    SiteGenerationResultContract,
)
from tests.contracts.template_contract import StaticAssetContract, TemplateContract

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent)
)  # Add workspace root

# Set test environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["PYTEST_CURRENT_TEST"] = "true"

# Import contracts


# Smart mocking classes for fast tests
class MockBlobStorageClient:
    """Mock blob storage client with contract-based responses."""

    def __init__(self):
        self.containers = {}
        self.blobs = {}

    def download_json(self, container: str, blob_name: str) -> Dict[str, Any]:
        """Smart mock that returns realistic content based on blob name."""
        if "ranked" in blob_name or "content" in blob_name:
            return RankedContentContract.create_mock(num_articles=3).__dict__
        return {"data": "mock_json_data"}

    def upload_text(self, container: str, blob_name: str, content: str) -> bool:
        """Mock successful upload."""
        self.blobs[f"{container}/{blob_name}"] = content
        return True

    def upload_json(self, container: str, blob_name: str, data: Dict[str, Any]) -> bool:
        """Mock successful JSON upload."""
        self.blobs[f"{container}/{blob_name}"] = data
        return True

    def list_blobs(self, container: str, prefix: str = "") -> List[Dict[str, Any]]:
        """Mock blob listing with realistic data."""
        if "ranked" in prefix:
            return [
                BlobItemContract.create_mock(
                    name=f"ranked-topics/2025-08-24.json"
                ).__dict__
            ]
        return [BlobItemContract.create_mock().__dict__]

    def ensure_container(self, container: str) -> bool:
        """Mock container creation."""
        self.containers[container] = True
        return True


class MockTemplateManager:
    """Mock template manager with contract-based rendering."""

    def render_template(self, template_name: str, **context) -> str:
        """Smart mock that returns realistic HTML based on template."""
        template = TemplateContract.create_mock(
            template_type="index" if "index" in template_name else "rss"
        )

        # Simple template rendering simulation
        if "index" in template_name:
            return f"""<!DOCTYPE html>
<html>
<head><title>{context.get('site_title', 'Test Site')}</title></head>
<body>
    <h1>{context.get('site_title', 'Test Site')}</h1>
    {f'<p>{len(context.get("articles", []))} articles</p>' if context.get("articles") else ''}
</body>
</html>"""
        elif "rss" in template_name or "feed" in template_name:
            return f"""<?xml version="1.0"?>
<rss version="2.0">
<channel>
    <title>{context.get('site_title', 'Test Site')}</title>
    <description>{context.get('site_description', 'Test Description')}</description>
</channel>
</rss>"""
        return "<html><body>Mock Template</body></html>"

    def get_static_assets(self) -> Dict[str, str]:
        """Mock static assets."""
        return {
            "style.css": StaticAssetContract.create_mock("css").content,
            "script.js": StaticAssetContract.create_mock("js").content,
        }


# Fast test fixtures
@pytest.fixture
def mock_blob_client():
    """Fast mock blob storage client."""
    return MockBlobStorageClient()


@pytest.fixture
def mock_template_manager():
    """Fast mock template manager."""
    return MockTemplateManager()


@pytest.fixture
def sample_ranked_content():
    """Fast sample ranked content using contracts."""
    return RankedContentContract.create_mock(num_articles=3).__dict__


@pytest.fixture
def sample_articles():
    """Fast sample articles for testing."""
    ranked_content = RankedContentContract.create_mock(num_articles=2)
    return ranked_content.ranked_topics


@pytest.fixture
def test_site_metadata():
    """Sample site metadata for testing."""
    return {
        "title": "AI Content Farm - Test",
        "description": "Test site for AI content curation",
        "theme": "modern",
        "max_articles": 10,
        "generated_at": "2025-08-24T10:00:00Z",
    }


@pytest.fixture
def mock_site_processor(mock_blob_client, mock_template_manager):
    """Fast mock site processor with dependency injection."""
    from service_logic import SiteProcessor

    # Create processor with mocked dependencies
    processor = SiteProcessor()
    processor.blob_client = mock_blob_client
    processor.template_manager = mock_template_manager

    return processor

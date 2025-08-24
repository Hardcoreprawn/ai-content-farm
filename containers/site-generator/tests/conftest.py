#!/usr/bin/env python3
"""
Test configuration and fixtures for site-generator tests.

Uses smart contract-based mocking for fast, reliable tests.
"""

import builtins
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient

from tests.contracts.blob_storage_contract import (
    BlobItemContract,
    RankedContentContract,
    SiteGenerationResultContract,
)
from tests.contracts.template_contract import StaticAssetContract, TemplateContract

try:
    # Provide global client/import_error for tests that reference them directly
    from main import app as _app_for_tests

    builtins.client = TestClient(_app_for_tests)
    builtins.import_error = None
except Exception as e:
    builtins.client = None
    builtins.import_error = str(e)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent)
)  # Add workspace root

# Set test environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["PYTEST_CURRENT_TEST"] = "true"
os.environ["AZURE_STORAGE_CONNECTION_STRING"] = (
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=test;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
)

# Import contracts


# Smart mocking classes for fast tests
class MockBlobStorageClient:
    """Mock blob storage client with contract-based responses."""

    def __init__(self):
        self.containers = {}
        self.blobs = {}

        def _upload_text(
            container: str, blob_name: str, content: str, **kwargs
        ) -> bool:
            self.blobs[f"{container}/{blob_name}"] = content
            return True

        def _upload_json(
            container: str, blob_name: str, data: Dict[str, Any], **kwargs
        ) -> bool:
            self.blobs[f"{container}/{blob_name}"] = data
            return True

        def _list_blobs(container: str, prefix: str = "") -> List[Dict[str, Any]]:
            if "ranked" in prefix or str(container).startswith("ranked"):
                return [
                    BlobItemContract.create_mock(
                        name="ranked-topics/2025-08-24.json"
                    ).__dict__
                ]
            return [BlobItemContract.create_mock().__dict__]

        def _ensure_container(container: str) -> bool:
            self.containers[container] = True
            return True

        # Expose MagicMock methods so tests can assert .called; allow overriding return_value in tests
        self.download_json = MagicMock(
            return_value=RankedContentContract.create_mock(num_articles=3).__dict__
        )

        def _download_text_default(container: str, blob_name: str) -> str:
            if str(blob_name).endswith("style.css"):
                return "body { color: red; }"
            return "<html>Test Template</html>"

        self.download_text = MagicMock(side_effect=_download_text_default)
        self.upload_text = MagicMock(side_effect=_upload_text)
        self.upload_json = MagicMock(side_effect=_upload_json)
        self.list_blobs = MagicMock(side_effect=_list_blobs)
        self.ensure_container = MagicMock(side_effect=_ensure_container)


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
    data = RankedContentContract.create_mock(num_articles=3).__dict__
    # Add ranking_score alias for compatibility with certain tests
    for item in data.get("ranked_topics", []):
        if "score" in item and "ranking_score" not in item:
            item["ranking_score"] = item["score"]
    return data


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


@pytest.fixture
def temp_templates_dir(tmp_path) -> str:
    """Create a temporary local templates directory with minimal files."""
    base = tmp_path / "templates"
    base.mkdir()

    (base / "base.html").write_text(
        """<!DOCTYPE html><html><head><title>{{ site_metadata.title if site_metadata else site_title }}</title></head><body>{% block content %}{% endblock %}</body></html>""",
        encoding="utf-8",
    )
    (base / "index.html").write_text(
        """{% extends 'base.html' %}{% block content %}<h1>{{ site_metadata.title if site_metadata else site_title }}</h1>{% for a in articles %}<article><h2>{{ a.title }}</h2><span>{{ a.ranking_score or a.score }}</span></article>{% endfor %}{% endblock %}""",
        encoding="utf-8",
    )
    (base / "article.html").write_text(
        """{% extends 'base.html' %}{% block content %}<article><h1>{{ title }}</h1><div class='content'>{{ article.content }}</div></article>{% endblock %}""",
        encoding="utf-8",
    )
    (base / "style.css").write_text(
        "body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; }",
        encoding="utf-8",
    )

    return str(base)

#!/usr/bin/env python3
"""
Test utilities and shared fixtures for AI Content Farm testing.

Provides common test fixtures, mock utilities, and test data
for use across unit, integration, and function tests.
"""

import pytest
import json
import os
import tempfile
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone


# Test Data Fixtures
@pytest.fixture
def sample_reddit_topic():
    """Sample Reddit topic data for testing"""
    return {
        "title": "AI Content Generation Best Practices",
        "external_url": "https://example.com/ai-content",
        "reddit_url": "https://reddit.com/r/technology/comments/example",
        "reddit_id": "example123",
        "score": 1500,
        "created_utc": 1692000000.0,
        "num_comments": 125,
        "author": "test_user",
        "subreddit": "technology",
        "fetched_at": "20250812_120000",
        "selftext": "Sample content about AI best practices..."
    }


@pytest.fixture
def sample_reddit_topics(sample_reddit_topic):
    """Multiple Reddit topics for batch testing"""
    topics = []
    for i in range(3):
        topic = sample_reddit_topic.copy()
        topic["reddit_id"] = f"example{i}"
        topic["score"] = 1000 + (i * 200)
        topic["num_comments"] = 50 + (i * 25)
        topics.append(topic)
    return topics


@pytest.fixture
def ranking_config():
    """Standard ranking configuration for testing"""
    return {
        "min_score_threshold": 100,
        "min_comments_threshold": 10,
        "weights": {
            "engagement": 0.3,
            "freshness": 0.2,
            "monetization": 0.3,
            "seo_potential": 0.2
        },
        "engagement_thresholds": {
            "high_score": 1000,
            "high_comments": 100
        },
        "freshness_hours": {
            "very_fresh": 6,
            "fresh": 24,
            "recent": 72
        }
    }


@pytest.fixture
def enrichment_config():
    """Standard enrichment configuration for testing"""
    return {
        "max_external_sources": 3,
        "content_quality_threshold": 0.7,
        "domain_credibility_threshold": 0.6,
        "research_depth": "standard",
        "citation_format": "apa"
    }


# Mock Utilities
@pytest.fixture
def mock_azure_blob_client():
    """Mock Azure Blob client for testing"""
    mock_client = Mock()
    mock_blob = Mock()
    mock_blob.download_blob.return_value.readall.return_value = json.dumps({
        "topics": [],
        "metadata": {"timestamp": "2025-08-12T12:00:00Z"}
    }).encode('utf-8')
    mock_client.get_blob_client.return_value = mock_blob
    return mock_client


@pytest.fixture
def mock_key_vault_client():
    """Mock Azure Key Vault client for testing"""
    mock_client = Mock()
    mock_client.get_secret.return_value.value = "test-secret-value"
    return mock_client


@pytest.fixture
def mock_requests_session():
    """Mock requests session for HTTP testing"""
    mock_session = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_response.text = "<html><body>Test content</body></html>"
    mock_session.get.return_value = mock_response
    mock_session.post.return_value = mock_response
    return mock_session


# File System Utilities
@pytest.fixture
def temp_directory():
    """Temporary directory for test files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_json_file(temp_directory, sample_reddit_topics):
    """Create a sample JSON file with test data"""
    file_path = os.path.join(temp_directory, "test_topics.json")
    with open(file_path, 'w') as f:
        json.dump({
            "topics": sample_reddit_topics,
            "metadata": {
                "timestamp": "2025-08-12T12:00:00Z",
                "source": "test"
            }
        }, f, indent=2)
    return file_path


# Environment Utilities
@pytest.fixture
def clean_environment():
    """Clean environment variables for testing"""
    # Store original values
    original_env = {}
    test_vars = [
        'AZURE_CLIENT_ID',
        'AZURE_CLIENT_SECRET', 
        'AZURE_TENANT_ID',
        'KEY_VAULT_URL',
        'STORAGE_ACCOUNT_NAME'
    ]
    
    for var in test_vars:
        if var in os.environ:
            original_env[var] = os.environ[var]
            del os.environ[var]
    
    # Set test values
    os.environ.update({
        'AZURE_CLIENT_ID': 'test-client-id',
        'AZURE_TENANT_ID': 'test-tenant-id',
        'KEY_VAULT_URL': 'https://test-vault.vault.azure.net/',
        'STORAGE_ACCOUNT_NAME': 'testaccount'
    })
    
    yield
    
    # Restore original values
    for var in test_vars:
        if var in os.environ:
            del os.environ[var]
        if var in original_env:
            os.environ[var] = original_env[var]


# HTTP Testing Utilities
@pytest.fixture
def function_app_base_url():
    """Base URL for function app testing"""
    return os.getenv('FUNCTION_APP_URL', 'http://localhost:7071')


def create_function_url(base_url: str, function_name: str, endpoint: str = '') -> str:
    """Helper to create function URLs"""
    url = f"{base_url}/api/{function_name}"
    if endpoint:
        url += f"/{endpoint}"
    return url


# Test Markers and Utilities
def requires_azure():
    """Decorator for tests that require Azure connectivity"""
    return pytest.mark.azure


def requires_external():
    """Decorator for tests that require external network access"""
    return pytest.mark.external


def slow_test():
    """Decorator for slow-running tests"""
    return pytest.mark.slow


# Assertion Helpers
def assert_valid_function_response(response_data: Dict[str, Any]):
    """Assert that a response follows the standard function response format"""
    required_fields = ['status', 'message', 'metadata']
    
    for field in required_fields:
        assert field in response_data, f"Missing required field: {field}"
    
    assert response_data['status'] in ['success', 'error', 'processing'], \
        f"Invalid status: {response_data['status']}"
    
    metadata = response_data['metadata']
    assert 'timestamp' in metadata, "Missing timestamp in metadata"
    assert 'function' in metadata, "Missing function name in metadata"


def assert_valid_topic_data(topic: Dict[str, Any]):
    """Assert that topic data has required fields"""
    required_fields = [
        'title', 'reddit_id', 'score', 'num_comments', 
        'subreddit', 'created_utc', 'fetched_at'
    ]
    
    for field in required_fields:
        assert field in topic, f"Missing required field: {field}"
    
    assert isinstance(topic['score'], (int, float)), "Score must be numeric"
    assert isinstance(topic['num_comments'], int), "Comments must be integer"
    assert topic['score'] >= 0, "Score must be non-negative"
    assert topic['num_comments'] >= 0, "Comments must be non-negative"

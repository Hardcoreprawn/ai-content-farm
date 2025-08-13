"""
Test Suite for SSG (Static Site Generator) Container Service

Tests markdown generation and headless CMS publishing capabilities.
Validates the final output stage of the content pipeline.
"""

import pytest
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import Mock, patch, AsyncMock

# Test data for static site generation
ENHANCED_CONTENT_ITEMS = [
    {
        "id": "enhanced_001",
        "title": "Revolutionary AI Breakthrough in Machine Learning",
        "content": "Researchers at MIT have developed...",
        "url": "https://example.com/ai-breakthrough",
        "source": "tech_news",
        "created_at": "2025-08-13T10:00:00Z",
        "score": 95,
        "enhancement": {
            "summary": "MIT researchers developed a new neural network achieving 95% accuracy...",
            "key_insights": [
                "95% accuracy on language understanding tasks",
                "Revolutionary neural network architecture",
                "Applications in healthcare, finance, autonomous systems"
            ],
            "tags": ["AI", "machine learning", "neural networks", "MIT"],
            "sentiment": "positive",
            "credibility_score": 0.92,
            "reading_time_minutes": 2
        }
    }
]

MARKDOWN_TEMPLATE_CONFIG = {
    "frontmatter": {
        "include_title": True,
        "include_date": True,
        "include_tags": True,
        "include_summary": True
    },
    "content": {
        "include_source_link": True,
        "include_key_insights": True,
        "include_reading_time": True
    },
    "cms": {
        "platform": "headless",
        "publish_status": "draft",
        "categories": ["tech", "ai"]
    }
}


class TestMarkdownGenerator:
    """Test the core markdown generation engine"""
    
    @pytest.mark.unit
    def test_generate_markdown_from_enhanced_content(self):
        """Test markdown generation from enhanced content"""
        from core.markdown_generator import generate_markdown
        
        item = ENHANCED_CONTENT_ITEMS[0]
        markdown = generate_markdown(item, MARKDOWN_TEMPLATE_CONFIG)
        
        assert isinstance(markdown, str)
        assert len(markdown) > 100  # Should be substantial content
        
        # Check for essential markdown elements
        assert "# " in markdown  # Headers
        assert "---" in markdown  # Frontmatter
        assert item["title"] in markdown
        assert item["enhancement"]["summary"] in markdown

    @pytest.mark.unit
    def test_generate_frontmatter(self):
        """Test YAML frontmatter generation"""
        from core.markdown_generator import generate_frontmatter
        
        item = ENHANCED_CONTENT_ITEMS[0]
        frontmatter = generate_frontmatter(item, MARKDOWN_TEMPLATE_CONFIG["frontmatter"])
        
        assert isinstance(frontmatter, str)
        assert "title:" in frontmatter
        assert "date:" in frontmatter
        assert "tags:" in frontmatter
        assert "summary:" in frontmatter

    @pytest.mark.unit
    def test_format_content_body(self):
        """Test content body formatting"""
        from core.markdown_generator import format_content_body
        
        item = ENHANCED_CONTENT_ITEMS[0]
        body = format_content_body(item, MARKDOWN_TEMPLATE_CONFIG["content"])
        
        assert isinstance(body, str)
        assert "## Key Insights" in body  # Should include insights section
        assert "Reading time:" in body   # Should include reading time
        assert item["url"] in body       # Should include source link

    @pytest.mark.unit
    def test_generate_filename_from_content(self):
        """Test filename generation from content"""
        from core.markdown_generator import generate_filename
        
        item = ENHANCED_CONTENT_ITEMS[0]
        filename = generate_filename(item)
        
        assert isinstance(filename, str)
        assert filename.endswith(".md")
        assert len(filename) > 10
        # Should be URL-safe
        assert " " not in filename
        assert all(c.isalnum() or c in "-_." for c in filename)

    @pytest.mark.unit
    def test_batch_markdown_generation(self):
        """Test generating markdown for multiple items"""
        from core.markdown_generator import generate_batch_markdown
        
        result = generate_batch_markdown(ENHANCED_CONTENT_ITEMS, MARKDOWN_TEMPLATE_CONFIG)
        
        assert isinstance(result, list)
        assert len(result) == len(ENHANCED_CONTENT_ITEMS)
        assert all("filename" in item and "content" in item for item in result)


class TestTemplateEngine:
    """Test the template engine for customizable output"""
    
    @pytest.mark.unit
    def test_load_template_configuration(self):
        """Test template configuration loading"""
        from core.template_engine import load_template_config
        
        config = load_template_config("default")
        
        assert isinstance(config, dict)
        assert "frontmatter" in config
        assert "content" in config

    @pytest.mark.unit
    def test_apply_template_to_content(self):
        """Test applying template to content item"""
        from core.template_engine import apply_template
        
        item = ENHANCED_CONTENT_ITEMS[0]
        template_name = "tech_article"
        
        result = apply_template(item, template_name)
        
        assert isinstance(result, str)
        assert len(result) > 200  # Should be formatted content

    @pytest.mark.unit
    def test_custom_template_variables(self):
        """Test custom template variable substitution"""
        from core.template_engine import substitute_template_variables
        
        template = "Title: {{title}}, Score: {{score}}, Tags: {{tags}}"
        item = ENHANCED_CONTENT_ITEMS[0]
        
        result = substitute_template_variables(template, item)
        
        assert item["title"] in result
        assert str(item["score"]) in result


class TestCMSPublisher:
    """Test headless CMS publishing capabilities"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_publish_to_headless_cms(self):
        """Test publishing markdown to headless CMS"""
        from core.cms_publisher import publish_to_cms
        
        markdown_items = [
            {
                "filename": "ai-breakthrough-2025-08-13.md",
                "content": "# Test Article\n\nContent here...",
                "metadata": {"tags": ["AI"], "category": "tech"}
            }
        ]
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 201
            mock_response.json.return_value = {"id": "cms_001", "status": "published"}
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await publish_to_cms(markdown_items, "headless_cms")
            
            assert "published_items" in result
            assert len(result["published_items"]) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_git_based_publishing(self):
        """Test Git-based content publishing"""
        from core.cms_publisher import publish_to_git_repo
        
        markdown_items = [
            {
                "filename": "test-article.md",
                "content": "# Test\n\nContent",
                "path": "content/posts/"
            }
        ]
        
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value.returncode = 0
            
            result = await publish_to_git_repo(markdown_items, "github")
            
            assert "commit_hash" in result or "status" in result

    @pytest.mark.unit
    def test_cms_configuration_validation(self):
        """Test CMS configuration validation"""
        from core.cms_publisher import validate_cms_config
        
        config = {
            "platform": "headless",
            "api_endpoint": "https://api.example.com",
            "auth_token": "test_token"
        }
        
        is_valid = validate_cms_config(config)
        
        assert isinstance(is_valid, bool)
        assert is_valid == True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cms_publishing_error_handling(self):
        """Test graceful handling of CMS publishing errors"""
        from core.cms_publisher import publish_to_cms
        
        markdown_items = [{"filename": "test.md", "content": "test"}]
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = Exception("CMS API Error")
            
            result = await publish_to_cms(markdown_items, "headless_cms")
            
            assert "error" in result or "failed_items" in result


class TestSSGAPI:
    """Test the FastAPI endpoints for SSG service"""
    
    @pytest.mark.integration
    def test_health_endpoint(self):
        """Test health check endpoint"""
        from main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/api/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "ssg"

    @pytest.mark.integration
    def test_generate_endpoint(self):
        """Test markdown generation endpoint"""
        from main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        request_data = {
            "enhanced_content": ENHANCED_CONTENT_ITEMS,
            "template_config": MARKDOWN_TEMPLATE_CONFIG,
            "output_options": {
                "format": "markdown",
                "publish": False
            }
        }
        
        response = client.post("/api/ssg/generate", json=request_data)
        
        assert response.status_code == 202  # Accepted for async processing
        assert "job_id" in response.json()

    @pytest.mark.integration
    def test_publish_endpoint(self):
        """Test publishing endpoint"""
        from main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        publish_request = {
            "markdown_items": [
                {"filename": "test.md", "content": "# Test"}
            ],
            "cms_config": {
                "platform": "headless",
                "publish_status": "draft"
            }
        }
        
        response = client.post("/api/ssg/publish", json=publish_request)
        
        assert response.status_code == 202
        assert "job_id" in response.json()

    @pytest.mark.integration
    def test_status_endpoint_returns_generation_status(self):
        """Test status endpoint returns generation job status"""
        from main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        job_id = "test_ssg_job_001"
        
        response = client.get(f"/api/ssg/status/{job_id}")
        
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] in ["pending", "processing", "completed", "failed"]


class TestBlobStorageIntegration:
    """Test Azure Blob Storage integration for SSG"""
    
    @pytest.mark.integration
    @pytest.mark.local
    @patch('azure.storage.blob.BlobServiceClient')
    async def test_read_enhanced_content(self, mock_blob_client):
        """Test reading enhanced content from content-enricher"""
        from core.storage_client import read_enhanced_content
        
        # Mock blob data from content-enricher
        mock_blob_data = {
            "enhanced_items": ENHANCED_CONTENT_ITEMS,
            "enhancement_metadata": {"total_enhanced": 1}
        }
        
        mock_blob_client.get_blob_client.return_value.download_blob.return_value.readall.return_value = \
            str(mock_blob_data).encode()
        
        result = await read_enhanced_content("content-enhanced", "enhanced_20250813.json")
        
        assert isinstance(result, dict)
        assert "enhanced_items" in result

    @pytest.mark.integration
    @pytest.mark.local
    @patch('azure.storage.blob.BlobServiceClient')
    async def test_write_generated_content(self, mock_blob_client):
        """Test writing generated markdown to blob storage"""
        from core.storage_client import write_generated_content
        
        generated_data = {
            "markdown_files": [{"filename": "test.md", "content": "# Test"}],
            "generation_metadata": {"total_generated": 1}
        }
        
        await write_generated_content("content-output", "generated_20250813.json", generated_data)
        
        # Verify blob client was called
        mock_blob_client.get_blob_client.assert_called()


# Pytest fixtures
@pytest.fixture
def enhanced_content_items():
    """Fixture providing enhanced content items"""
    return [item.copy() for item in ENHANCED_CONTENT_ITEMS]

@pytest.fixture
def markdown_template_config():
    """Fixture providing markdown template configuration"""
    return MARKDOWN_TEMPLATE_CONFIG.copy()

@pytest.fixture
def mock_cms_client():
    """Fixture providing mocked CMS client"""
    with patch('aiohttp.ClientSession') as mock:
        yield mock

@pytest.fixture
def mock_blob_client():
    """Fixture providing mocked Azure Blob client"""
    with patch('azure.storage.blob.BlobServiceClient') as mock:
        yield mock

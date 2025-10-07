# Site Generator Split Implementation Plan

**Date:** October 7, 2025  
**Status:** 📋 **READY FOR IMPLEMENTATION**  
**PR Title:** `Split site-generator into markdown-generator and site-builder`  
**Target Branch:** `feature/split-site-generator`

---

## 🎯 Objectives

### Primary Goals
1. Split `site-generator` into two specialized containers:
   - `markdown-generator`: Fast per-article JSON → Markdown conversion
   - `site-builder`: Batched full-site HTML generation
2. Implement clean, testable, PEP8-compliant code (<500 lines per file)
3. Create comprehensive unit tests (outcome-focused, not method-focused)
4. Provide monitoring and control endpoints for each container
5. Maintain backward compatibility during migration
6. Document cleanup and deprecation plan

### Success Criteria
- ✅ Both new containers pass 100% of unit tests
- ✅ KEDA scaling works correctly for each pattern
- ✅ Cost reduction: 50%+ vs current implementation
- ✅ Zero data loss during migration
- ✅ All code follows PEP8, type hints, no inline exports
- ✅ Complete documentation and runbooks

---

## 📐 Architecture Overview

### New Container Structure

```
containers/
├── markdown-generator/          # NEW: Fast per-article converter
│   ├── Dockerfile
│   ├── main.py                 # FastAPI app (~150 lines)
│   ├── markdown_processor.py   # Core logic (~250 lines)
│   ├── models.py               # Pydantic models (~100 lines)
│   ├── config.py               # Configuration (~100 lines)
│   ├── requirements.txt
│   ├── pytest.ini
│   └── tests/
│       ├── conftest.py
│       ├── test_markdown_generation.py
│       ├── test_queue_processing.py
│       ├── test_api_endpoints.py
│       └── test_outcomes.py    # Outcome-based tests
│
├── site-builder/                # NEW: Batch site generator
│   ├── Dockerfile
│   ├── main.py                 # FastAPI app (~150 lines)
│   ├── site_builder.py         # Core logic (~300 lines)
│   ├── index_manager.py        # Index regeneration (~150 lines)
│   ├── models.py               # Pydantic models (~100 lines)
│   ├── config.py               # Configuration (~100 lines)
│   ├── requirements.txt
│   ├── pytest.ini
│   └── tests/
│       ├── conftest.py
│       ├── test_site_building.py
│       ├── test_index_management.py
│       ├── test_queue_processing.py
│       ├── test_api_endpoints.py
│       └── test_outcomes.py    # Outcome-based tests
│
└── site-generator/              # DEPRECATED: Keep for migration
    ├── README.md               # Updated with deprecation notice
    └── ... (existing files)
```

### Shared Libraries (No Changes Required)
```
libs/
├── simplified_blob_client.py   # Blob storage operations
├── queue_client.py             # Queue message handling
├── shared_models.py            # Common data models
├── retry_utilities.py          # Retry logic
└── data_contracts.py           # Data validation
```

---

## 🏗️ Implementation Phases

### Phase 1: Container Scaffolding (Week 1, Days 1-2)

#### Day 1: Create markdown-generator

**Step 1.1: Create Directory Structure**
```bash
mkdir -p containers/markdown-generator/{tests,templates}
cd containers/markdown-generator
```

**Step 1.2: Core Files**

**`main.py`** (~150 lines)
```python
"""
Markdown Generator Container

Converts JSON articles to markdown with frontmatter.
Optimized for per-article processing with KEDA scaling.

API Endpoints:
  POST /api/markdown/generate        - Generate markdown from JSON
  POST /api/markdown/batch           - Generate multiple markdown files
  GET  /api/markdown/status          - Get generation status
  GET  /health                       - Health check
  POST /storage-queue/process        - Queue message handler
"""
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging

from markdown_processor import MarkdownProcessor
from models import (
    MarkdownGenerationRequest,
    MarkdownGenerationResponse,
    BatchGenerationRequest,
    GenerationStatus
)
from config import get_config
from libs.shared_models import StandardResponse, create_success_response
from libs.queue_client import QueueMessageModel, get_queue_client

logger = logging.getLogger(__name__)
app = FastAPI(title="Markdown Generator", version="1.0.0")

# Initialize processor
processor: MarkdownProcessor = None

@app.on_event("startup")
async def startup_event() -> None:
    """Initialize markdown processor on startup."""
    global processor
    config = get_config()
    processor = MarkdownProcessor(config)
    logger.info("Markdown Generator started")

@app.get("/health")
async def health_check() -> StandardResponse:
    """Health check endpoint."""
    return create_success_response(
        data={"status": "healthy", "service": "markdown-generator"}
    )

@app.get("/api/markdown/status")
async def get_status() -> StandardResponse:
    """Get current generation status and metrics."""
    status = await processor.get_status()
    return create_success_response(data=status)

@app.post("/api/markdown/generate")
async def generate_markdown(
    request: MarkdownGenerationRequest
) -> MarkdownGenerationResponse:
    """
    Generate markdown from a single JSON article.
    
    Args:
        request: Article data or blob path
        
    Returns:
        Generated markdown metadata
    """
    result = await processor.generate_markdown(request)
    return result

@app.post("/api/markdown/batch")
async def generate_batch(
    request: BatchGenerationRequest
) -> StandardResponse:
    """
    Generate markdown for multiple articles.
    
    Args:
        request: Batch processing configuration
        
    Returns:
        Batch generation results
    """
    result = await processor.generate_batch(request)
    return create_success_response(data=result)

@app.post("/storage-queue/process")
async def process_queue_messages() -> StandardResponse:
    """
    Process messages from storage queue (KEDA trigger).
    
    Returns:
        Processing results
    """
    try:
        async def message_handler(message: QueueMessageModel) -> Dict[str, Any]:
            """Handle individual queue message."""
            if message.operation == "generate_markdown":
                # Extract blob path or article data
                blob_path = message.payload.get("blob_path")
                if not blob_path:
                    return {"status": "error", "error": "Missing blob_path"}
                
                # Generate markdown
                request = MarkdownGenerationRequest(blob_path=blob_path)
                result = await processor.generate_markdown(request)
                
                # Trigger site builder if successful
                if result.status == "success":
                    await processor.trigger_site_build(result.markdown_path)
                
                return {"status": "success", "result": result.dict()}
            
            return {"status": "ignored", "reason": "Unknown operation"}
        
        # Process queue messages
        processed = await processor.process_queue(message_handler)
        
        return create_success_response(
            data={"messages_processed": processed}
        )
    except Exception as e:
        logger.error(f"Queue processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**`markdown_processor.py`** (~250 lines)
```python
"""
Markdown Processor Core Logic

Handles conversion of JSON articles to markdown with frontmatter.
Optimized for single-article processing with proper error handling.
"""
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime, timezone
import json
import logging

from pydantic import BaseModel

from models import (
    MarkdownGenerationRequest,
    MarkdownGenerationResponse,
    GenerationStatus
)
from libs.simplified_blob_client import SimplifiedBlobClient
from libs.queue_client import QueueMessageModel, get_queue_client
from libs.retry_utilities import with_secure_retry

logger = logging.getLogger(__name__)


class MarkdownProcessor:
    """
    Core markdown generation processor.
    
    Responsibilities:
    - Load JSON articles from blob storage
    - Generate markdown with proper frontmatter
    - Save to markdown container
    - Trigger site builder queue
    - Track generation metrics
    """
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize processor with configuration."""
        self.config = config
        self.blob_client = SimplifiedBlobClient(
            account_name=config["AZURE_STORAGE_ACCOUNT_NAME"],
            credential=config.get("AZURE_CLIENT_ID")
        )
        self.stats = {
            "total_generated": 0,
            "total_errors": 0,
            "last_generation": None
        }
    
    async def get_status(self) -> GenerationStatus:
        """Get current processor status and metrics."""
        return GenerationStatus(
            total_generated=self.stats["total_generated"],
            total_errors=self.stats["total_errors"],
            last_generation=self.stats["last_generation"],
            queue_depth=await self._get_queue_depth()
        )
    
    async def generate_markdown(
        self,
        request: MarkdownGenerationRequest
    ) -> MarkdownGenerationResponse:
        """
        Generate markdown from JSON article.
        
        Args:
            request: Generation request with blob path or article data
            
        Returns:
            Generation response with markdown path
        """
        try:
            # Load article data
            article_data = await self._load_article(request)
            
            # Validate article data
            self._validate_article_data(article_data)
            
            # Generate markdown content
            markdown_content = self._create_markdown(article_data)
            
            # Generate safe filename
            filename = self._generate_filename(article_data)
            
            # Save to blob storage
            markdown_path = await self._save_markdown(
                filename=filename,
                content=markdown_content
            )
            
            # Update stats
            self.stats["total_generated"] += 1
            self.stats["last_generation"] = datetime.now(timezone.utc)
            
            return MarkdownGenerationResponse(
                status="success",
                markdown_path=markdown_path,
                article_id=article_data.get("topic_id", "unknown"),
                processing_time_ms=0.0  # Calculate actual time
            )
            
        except Exception as e:
            self.stats["total_errors"] += 1
            logger.error(f"Markdown generation failed: {e}")
            return MarkdownGenerationResponse(
                status="error",
                error=str(e),
                markdown_path=None,
                article_id=request.blob_path or "unknown",
                processing_time_ms=0.0
            )
    
    async def generate_batch(
        self,
        request: BatchGenerationRequest
    ) -> Dict[str, Any]:
        """Generate markdown for multiple articles."""
        # Implementation for batch processing
        pass
    
    async def trigger_site_build(self, markdown_path: str) -> None:
        """
        Trigger site builder after markdown generation.
        
        Args:
            markdown_path: Path to generated markdown file
        """
        try:
            queue_client = get_queue_client("site-build-requests")
            message = QueueMessageModel(
                service_name="markdown-generator",
                operation="build_site",
                payload={
                    "trigger": "new_markdown",
                    "markdown_path": markdown_path,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            await queue_client.send_message(message)
            logger.info(f"Site build triggered for: {markdown_path}")
        except Exception as e:
            logger.warning(f"Failed to trigger site build: {e}")
    
    async def process_queue(
        self,
        message_handler: Callable[[QueueMessageModel], Awaitable[Dict[str, Any]]]
    ) -> int:
        """Process messages from queue."""
        from libs.queue_client import process_queue_messages
        
        processed = await process_queue_messages(
            queue_name=self.config["QUEUE_NAME"],
            message_handler=message_handler,
            max_messages=10
        )
        return processed
    
    # Private helper methods
    async def _load_article(
        self,
        request: MarkdownGenerationRequest
    ) -> Dict[str, Any]:
        """Load article data from blob or request."""
        if request.article_data:
            return request.article_data
        
        if request.blob_path:
            content = await self.blob_client.download_text(
                container=self.config["PROCESSED_CONTENT_CONTAINER"],
                blob_name=request.blob_path
            )
            return json.loads(content)
        
        raise ValueError("Must provide either article_data or blob_path")
    
    def _validate_article_data(self, article_data: Dict[str, Any]) -> None:
        """Validate required article fields."""
        required_fields = ["title", "content"]
        missing = [f for f in required_fields if not article_data.get(f)]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
    
    def _create_markdown(self, article_data: Dict[str, Any]) -> str:
        """Create markdown content with frontmatter."""
        # Generate frontmatter
        frontmatter = self._generate_frontmatter(article_data)
        
        # Get article content
        content = article_data.get("content", "")
        
        return f"---\n{frontmatter}\n---\n\n{content}"
    
    def _generate_frontmatter(self, article_data: Dict[str, Any]) -> str:
        """Generate YAML frontmatter from article data."""
        import yaml
        
        frontmatter_data = {
            "title": article_data["title"],
            "date": article_data.get("published_date", datetime.now().isoformat()),
            "tags": article_data.get("tags", []),
            "source": article_data.get("source", {}),
            "topic_id": article_data.get("topic_id", "")
        }
        
        return yaml.dump(frontmatter_data, default_flow_style=False)
    
    def _generate_filename(self, article_data: Dict[str, Any]) -> str:
        """Generate safe filename from article title."""
        import re
        
        title = article_data["title"]
        # Convert to lowercase, replace spaces with hyphens
        safe_title = re.sub(r'[^a-z0-9]+', '-', title.lower())
        safe_title = safe_title.strip('-')
        
        return f"{safe_title}.md"
    
    async def _save_markdown(
        self,
        filename: str,
        content: str
    ) -> str:
        """Save markdown to blob storage."""
        await self.blob_client.upload_text(
            container=self.config["MARKDOWN_CONTENT_CONTAINER"],
            blob_name=filename,
            text=content
        )
        return filename
    
    async def _get_queue_depth(self) -> int:
        """Get current queue depth."""
        try:
            queue_client = get_queue_client(self.config["QUEUE_NAME"])
            props = await queue_client.get_queue_properties()
            return props.get("approximate_message_count", 0)
        except Exception:
            return 0
```

**`models.py`** (~100 lines)
```python
"""
Markdown Generator Data Models

Pydantic models for request/response validation.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class MarkdownGenerationRequest(BaseModel):
    """Request to generate markdown from article."""
    
    blob_path: Optional[str] = Field(
        None,
        description="Path to JSON article in blob storage"
    )
    article_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Article data directly provided"
    )
    force_regenerate: bool = Field(
        False,
        description="Force regeneration even if markdown exists"
    )


class MarkdownGenerationResponse(BaseModel):
    """Response from markdown generation."""
    
    status: str = Field(..., description="success or error")
    markdown_path: Optional[str] = Field(None, description="Path to generated markdown")
    article_id: str = Field(..., description="Article identifier")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if failed")


class BatchGenerationRequest(BaseModel):
    """Request to generate markdown for multiple articles."""
    
    blob_paths: Optional[List[str]] = Field(None, description="List of article blob paths")
    discover_articles: bool = Field(
        False,
        description="Auto-discover articles from container"
    )
    max_articles: int = Field(100, description="Maximum articles to process")
    force_regenerate: bool = Field(False, description="Force regeneration")


class GenerationStatus(BaseModel):
    """Current generation status and metrics."""
    
    total_generated: int = Field(..., description="Total markdown files generated")
    total_errors: int = Field(..., description="Total generation errors")
    last_generation: Optional[datetime] = Field(None, description="Last generation timestamp")
    queue_depth: int = Field(0, description="Current queue depth")
```

**`config.py`** (~100 lines)
```python
"""
Markdown Generator Configuration

Environment-based configuration management.
"""
import os
from typing import Dict, Any


def get_config() -> Dict[str, Any]:
    """
    Get configuration from environment variables.
    
    Returns:
        Configuration dictionary
    """
    return {
        # Azure Storage
        "AZURE_STORAGE_ACCOUNT_NAME": os.getenv(
            "AZURE_STORAGE_ACCOUNT_NAME",
            ""
        ),
        "AZURE_CLIENT_ID": os.getenv("AZURE_CLIENT_ID"),
        
        # Container Names
        "PROCESSED_CONTENT_CONTAINER": os.getenv(
            "PROCESSED_CONTENT_CONTAINER",
            "processed-content"
        ),
        "MARKDOWN_CONTENT_CONTAINER": os.getenv(
            "MARKDOWN_CONTENT_CONTAINER",
            "markdown-content"
        ),
        
        # Queue Configuration
        "QUEUE_NAME": os.getenv(
            "QUEUE_NAME",
            "markdown-generation-requests"
        ),
        "SITE_BUILD_QUEUE": os.getenv(
            "SITE_BUILD_QUEUE",
            "site-build-requests"
        ),
        
        # Processing Settings
        "MAX_BATCH_SIZE": int(os.getenv("MAX_BATCH_SIZE", "10")),
        "ENABLE_AUTO_TRIGGER": os.getenv("ENABLE_AUTO_TRIGGER", "true").lower() == "true",
    }


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate required configuration values.
    
    Args:
        config: Configuration dictionary
        
    Raises:
        ValueError: If required configuration is missing
    """
    required_keys = [
        "AZURE_STORAGE_ACCOUNT_NAME",
        "PROCESSED_CONTENT_CONTAINER",
        "MARKDOWN_CONTENT_CONTAINER",
        "QUEUE_NAME"
    ]
    
    missing = [key for key in required_keys if not config.get(key)]
    if missing:
        raise ValueError(f"Missing required configuration: {missing}")
```

**`requirements.txt`**
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.2
pyyaml==6.0.2
azure-storage-blob==12.23.1
azure-identity==1.19.0
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==5.0.0
httpx==0.27.2
```

**`Dockerfile`**
```dockerfile
FROM python:3.11-slim

# Security: Create non-root user
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=app:app . .

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Start application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Day 2: Create site-builder

**Similar structure to markdown-generator**, but with these key differences:

**`site_builder.py`** (~300 lines) - Core site building logic
- Full site generation from all markdown files
- Index page generation
- RSS feed generation
- Sitemap generation

**`index_manager.py`** (~150 lines) - Index management
- Add single page to existing index
- Remove page from index
- Regenerate index from all markdown
- Sort and filter articles

**API Endpoints:**
```python
POST /api/site/build-full          # Full site rebuild (all markdown)
POST /api/site/build-incremental   # Add single page, update index
POST /api/site/regenerate-index    # Regenerate index only
GET  /api/site/status              # Site build status
GET  /health                       # Health check
POST /storage-queue/process        # Queue message handler
```

---

### Phase 2: Unit Tests (Week 1, Days 3-4)

#### Outcome-Based Test Strategy

**Focus on WHAT, not HOW:**
- ✅ Test observable outcomes (files created, queue messages sent)
- ✅ Test error handling and edge cases
- ✅ Test API contract compliance
- ❌ Don't test internal method calls
- ❌ Don't test implementation details

#### markdown-generator Tests

**`tests/test_outcomes.py`** - Core outcome tests
```python
"""
Outcome-Based Tests for Markdown Generator

Tests focus on observable outcomes, not implementation details.
"""
import pytest
from typing import Dict, Any


@pytest.mark.asyncio
async def test_markdown_generated_from_json_article(
    processor,
    sample_article_data,
    mock_blob_client
):
    """
    GIVEN a valid JSON article
    WHEN markdown generation is requested
    THEN markdown file should be created in blob storage
    AND frontmatter should contain article metadata
    AND site build should be triggered
    """
    # Arrange
    request = MarkdownGenerationRequest(article_data=sample_article_data)
    
    # Act
    result = await processor.generate_markdown(request)
    
    # Assert - Outcome 1: Markdown file created
    assert result.status == "success"
    assert result.markdown_path is not None
    assert mock_blob_client.upload_text.called
    
    # Assert - Outcome 2: Frontmatter contains metadata
    uploaded_content = mock_blob_client.upload_text.call_args[1]["text"]
    assert "---" in uploaded_content
    assert sample_article_data["title"] in uploaded_content
    
    # Assert - Outcome 3: Site build triggered
    assert mock_queue_client.send_message.called
    message = mock_queue_client.send_message.call_args[0][0]
    assert message.operation == "build_site"


@pytest.mark.asyncio
async def test_markdown_not_regenerated_if_exists(
    processor,
    sample_article_data,
    mock_blob_client
):
    """
    GIVEN markdown already exists for an article
    WHEN generation is requested without force_regenerate
    THEN existing markdown should be returned
    AND blob storage should not be written to
    """
    # Arrange
    mock_blob_client.exists.return_value = True
    request = MarkdownGenerationRequest(
        article_data=sample_article_data,
        force_regenerate=False
    )
    
    # Act
    result = await processor.generate_markdown(request)
    
    # Assert
    assert result.status == "success"
    assert not mock_blob_client.upload_text.called


@pytest.mark.asyncio
async def test_error_handling_for_invalid_article(processor):
    """
    GIVEN an article missing required fields
    WHEN markdown generation is attempted
    THEN error response should be returned
    AND stats should show error count increased
    AND no markdown file should be created
    """
    # Arrange
    invalid_article = {"title": "Test"}  # Missing content
    request = MarkdownGenerationRequest(article_data=invalid_article)
    initial_errors = processor.stats["total_errors"]
    
    # Act
    result = await processor.generate_markdown(request)
    
    # Assert
    assert result.status == "error"
    assert "content" in result.error.lower()
    assert processor.stats["total_errors"] == initial_errors + 1
    assert not mock_blob_client.upload_text.called


@pytest.mark.asyncio
async def test_queue_message_processing(processor, mock_queue_client):
    """
    GIVEN queue messages for markdown generation
    WHEN queue processing is triggered
    THEN all messages should be processed
    AND markdown files should be created
    AND messages should be deleted from queue
    """
    # Arrange
    messages = [
        create_test_message("article1.json"),
        create_test_message("article2.json"),
        create_test_message("article3.json"),
    ]
    mock_queue_client.receive_messages.return_value = messages
    
    # Act
    async def handler(msg):
        return await processor.handle_queue_message(msg)
    
    processed = await processor.process_queue(handler)
    
    # Assert
    assert processed == 3
    assert mock_queue_client.delete_message.call_count == 3


@pytest.mark.asyncio
async def test_batch_processing_limits(processor):
    """
    GIVEN a batch request for 150 articles
    WHEN max_articles is set to 100
    THEN only 100 articles should be processed
    AND result should indicate limit was reached
    """
    # Arrange
    request = BatchGenerationRequest(
        discover_articles=True,
        max_articles=100
    )
    
    # Act
    result = await processor.generate_batch(request)
    
    # Assert
    assert result["articles_processed"] == 100
    assert result["limit_reached"] is True
```

**`tests/test_api_endpoints.py`** - API contract tests
```python
"""
API Endpoint Tests

Validates API contracts and HTTP semantics.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_returns_200(client: AsyncClient):
    """Health endpoint should return 200 with healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_status_endpoint_returns_metrics(client: AsyncClient):
    """Status endpoint should return current metrics."""
    response = await client.get("/api/markdown/status")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "total_generated" in data
    assert "total_errors" in data
    assert "queue_depth" in data


@pytest.mark.asyncio
async def test_generate_endpoint_validates_input(client: AsyncClient):
    """Generate endpoint should validate required fields."""
    # Missing both blob_path and article_data
    response = await client.post("/api/markdown/generate", json={})
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_generate_endpoint_returns_markdown_path(client: AsyncClient):
    """Successful generation should return markdown path."""
    request_data = {
        "article_data": {
            "title": "Test Article",
            "content": "Test content"
        }
    }
    response = await client.post("/api/markdown/generate", json=request_data)
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert result["markdown_path"] is not None
```

**`tests/conftest.py`** - Test fixtures
```python
"""
Test Fixtures for Markdown Generator

Provides reusable test fixtures and mock objects.
"""
import pytest
from unittest.mock import AsyncMock, Mock
from typing import Dict, Any


@pytest.fixture
def sample_article_data() -> Dict[str, Any]:
    """Sample article data for testing."""
    return {
        "topic_id": "test-123",
        "title": "Test Article Title",
        "content": "This is the article content.",
        "published_date": "2025-10-07T12:00:00Z",
        "tags": ["test", "article"],
        "source": {
            "name": "reddit",
            "url": "https://example.com/article"
        }
    }


@pytest.fixture
def mock_blob_client():
    """Mock blob client for testing."""
    client = AsyncMock()
    client.upload_text = AsyncMock()
    client.download_text = AsyncMock()
    client.exists = AsyncMock(return_value=False)
    return client


@pytest.fixture
def mock_queue_client():
    """Mock queue client for testing."""
    client = AsyncMock()
    client.send_message = AsyncMock()
    client.receive_messages = AsyncMock(return_value=[])
    client.delete_message = AsyncMock()
    client.get_queue_properties = AsyncMock(return_value={
        "approximate_message_count": 0
    })
    return client


@pytest.fixture
def processor(mock_blob_client, mock_queue_client):
    """Markdown processor with mocked dependencies."""
    from markdown_processor import MarkdownProcessor
    from config import get_config
    
    config = get_config()
    processor = MarkdownProcessor(config)
    processor.blob_client = mock_blob_client
    
    return processor


@pytest.fixture
async def client():
    """Async HTTP client for API testing."""
    from httpx import AsyncClient
    from main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

#### site-builder Tests

Similar test structure focusing on:
- Full site generation creates all required files (index.html, feed.xml, sitemap.xml)
- Incremental updates only modify changed files
- Index regeneration includes all markdown files
- Error handling for missing markdown
- Queue message processing

---

### Phase 3: Infrastructure (Week 1, Day 5)

#### Terraform Configuration

**`infra/container_app_markdown_generator.tf`**
```terraform
# Markdown Generator Container App
resource "azurerm_container_app" "markdown_generator" {
  name                         = "${local.resource_prefix}-markdown-gen"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  lifecycle {
    ignore_changes = [
      template[0].custom_scale_rule[0].authentication,
      template[0].container[0].image
    ]
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    ip_security_restriction {
      action           = "Allow"
      ip_address_range = "81.2.90.47/32"
      name             = "AllowStaticIP"
    }

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    container {
      name   = "markdown-generator"
      image  = local.container_images["markdown-generator"]
      cpu    = 0.25  # Lighter workload
      memory = "0.5Gi"

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.containers.client_id
      }

      env {
        name  = "AZURE_STORAGE_ACCOUNT_NAME"
        value = azurerm_storage_account.main.name
      }

      env {
        name  = "PROCESSED_CONTENT_CONTAINER"
        value = "processed-content"
      }

      env {
        name  = "MARKDOWN_CONTENT_CONTAINER"
        value = "markdown-content"
      }

      env {
        name  = "QUEUE_NAME"
        value = azurerm_storage_queue.markdown_generation_requests.name
      }

      env {
        name  = "SITE_BUILD_QUEUE"
        value = azurerm_storage_queue.site_build_requests.name
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
    }

    min_replicas = 0
    max_replicas = 5  # Can scale for bursts

    # KEDA scaling: Immediate per-article processing
    custom_scale_rule {
      name             = "markdown-queue-scaler"
      custom_rule_type = "azure-queue"
      metadata = {
        queueName   = azurerm_storage_queue.markdown_generation_requests.name
        accountName = azurerm_storage_account.main.name
        queueLength = "1"  # Immediate processing
        cloud       = "AzurePublicCloud"
      }
    }
  }

  tags = local.common_tags

  depends_on = [
    azurerm_storage_queue.markdown_generation_requests,
    azurerm_role_assignment.containers_storage_blob_data_contributor
  ]
}
```

**`infra/container_app_site_builder.tf`**
```terraform
# Site Builder Container App
resource "azurerm_container_app" "site_builder" {
  name                         = "${local.resource_prefix}-site-builder"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  lifecycle {
    ignore_changes = [
      template[0].custom_scale_rule[0].authentication,
      template[0].custom_scale_rule[1].authentication,
      template[0].container[0].image
    ]
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    ip_security_restriction {
      action           = "Allow"
      ip_address_range = "81.2.90.47/32"
      name             = "AllowStaticIP"
    }

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    container {
      name   = "site-builder"
      image  = local.container_images["site-builder"]
      cpu    = 0.5  # Heavier workload
      memory = "1Gi"

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.containers.client_id
      }

      env {
        name  = "AZURE_STORAGE_ACCOUNT_NAME"
        value = azurerm_storage_account.main.name
      }

      env {
        name  = "MARKDOWN_CONTENT_CONTAINER"
        value = "markdown-content"
      }

      env {
        name  = "STATIC_SITES_CONTAINER"
        value = "$web"
      }

      env {
        name  = "SITE_TITLE"
        value = "JabLab Tech News"
      }

      env {
        name  = "SITE_URL"
        value = "https://jablab.dev"
      }

      env {
        name  = "QUEUE_NAME"
        value = azurerm_storage_queue.site_build_requests.name
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
    }

    min_replicas = 0
    max_replicas = 1  # Only need one for full rebuild

    # KEDA scaling rule 1: Queue-based (batching)
    custom_scale_rule {
      name             = "site-build-queue-scaler"
      custom_rule_type = "azure-queue"
      metadata = {
        queueName   = azurerm_storage_queue.site_build_requests.name
        accountName = azurerm_storage_account.main.name
        queueLength = "5"  # Wait for batch
        cloud       = "AzurePublicCloud"
      }
    }

    # KEDA scaling rule 2: Cron (hourly rebuild)
    custom_scale_rule {
      name             = "hourly-rebuild"
      custom_rule_type = "cron"
      metadata = {
        timezone        = "America/Los_Angeles"
        start           = "0 * * * *"  # Top of every hour
        end             = "0 * * * *"
        desiredReplicas = "1"
      }
    }
  }

  tags = local.common_tags

  depends_on = [
    azurerm_storage_queue.site_build_requests,
    azurerm_role_assignment.containers_storage_blob_data_contributor
  ]
}
```

**`infra/storage_queues.tf`** (add new queues)
```terraform
# Markdown Generation Queue
resource "azurerm_storage_queue" "markdown_generation_requests" {
  name                 = "markdown-generation-requests"
  storage_account_name = azurerm_storage_account.main.name
}

# Site Build Queue
resource "azurerm_storage_queue" "site_build_requests" {
  name                 = "site-build-requests"
  storage_account_name = azurerm_storage_account.main.name
}
```

---

### Phase 4: CI/CD Integration (Week 2, Day 1)

#### GitHub Actions Workflow Updates

**`.github/workflows/container-build.yml`** (update)
```yaml
# Add new containers to build matrix
strategy:
  matrix:
    container:
      - name: content-collector
        path: containers/content-collector
      - name: content-processor
        path: containers/content-processor
      - name: markdown-generator  # NEW
        path: containers/markdown-generator
      - name: site-builder  # NEW
        path: containers/site-builder
      - name: site-generator  # DEPRECATED (keep for migration)
        path: containers/site-generator
```

---

### Phase 5: Migration & Cleanup (Week 2, Days 2-5)

#### Migration Strategy

**Phase 5.1: Parallel Deployment (Day 2)**
1. Deploy markdown-generator and site-builder containers
2. Keep site-generator running (no traffic)
3. Update content-processor to send to markdown-generation-requests queue
4. Monitor both systems in parallel

**Phase 5.2: Traffic Cutover (Day 3)**
1. Verify new containers handling traffic correctly
2. Validate markdown and site generation
3. Check monitoring and metrics
4. Confirm cost reductions

**Phase 5.3: Deprecation (Day 4)**
1. Add deprecation notice to site-generator README
2. Stop sending traffic to site-generator
3. Scale site-generator to 0 replicas
4. Monitor for any issues

**Phase 5.4: Cleanup (Day 5)**
1. Remove site-generator container app (Terraform)
2. Remove old queue (site-generation-requests)
3. Archive site-generator code to docs/deprecated/
4. Update all documentation
5. Close migration PR

#### Deprecation Notice Template

**`containers/site-generator/README.md`** (update)
```markdown
# ⚠️ DEPRECATED: Site Generator Container

**Status:** DEPRECATED as of October 14, 2025  
**Replacement:** `markdown-generator` + `site-builder`

This container has been split into two specialized containers for better
performance and cost optimization:

- **markdown-generator**: Fast per-article JSON → Markdown conversion
- **site-builder**: Batched full-site HTML generation

## Migration Information

- **Old Queue:** `site-generation-requests` (removed)
- **New Queues:** 
  - `markdown-generation-requests` (per-article)
  - `site-build-requests` (full site)

## Archive Location

Code archived to: `docs/deprecated/site-generator/`

For questions, see: `docs/SITE_GENERATOR_SPLIT_IMPLEMENTATION_PLAN.md`
```

---

## 📋 Checklist & Acceptance Criteria

### Code Quality
- [ ] All Python files < 500 lines
- [ ] PEP8 compliant (run `black` and `flake8`)
- [ ] Type hints on all functions
- [ ] No inline exports (all imports at top)
- [ ] Docstrings on all public functions
- [ ] No hardcoded values (use config)

### Testing
- [ ] Unit tests cover 90%+ of code
- [ ] Tests focus on outcomes, not methods
- [ ] All tests pass locally
- [ ] Integration tests validate queue flow
- [ ] Performance tests verify latency targets

### Monitoring
- [ ] Health endpoints return proper status
- [ ] Status endpoints show metrics
- [ ] Logging follows standards (no sensitive data)
- [ ] Metrics exported to Application Insights
- [ ] Alerts configured for failures

### Documentation
- [ ] README files complete for both containers
- [ ] API endpoints documented (OpenAPI/Swagger)
- [ ] Configuration options documented
- [ ] Runbooks for common operations
- [ ] Migration guide complete

### Infrastructure
- [ ] Terraform applies cleanly
- [ ] KEDA scaling rules validated
- [ ] Queue auth configured (managed identity)
- [ ] Network security rules applied
- [ ] Cost estimates validated

### Migration
- [ ] Parallel deployment successful
- [ ] Traffic cutover validated
- [ ] Old container deprecated
- [ ] Old infrastructure removed
- [ ] Documentation updated

---

## 🎯 Success Metrics

### Performance Targets
- **Markdown Generation**: < 5 seconds per article (90th percentile)
- **Full Site Build**: < 60 seconds for 100 articles (90th percentile)
- **Queue Processing Latency**: < 2 seconds from queue to processing
- **Container Startup**: < 10 seconds (cold start)

### Cost Targets
- **Markdown Generator**: $0.25/month (10 articles/day)
- **Site Builder**: $0.15/month (hourly + burst rebuilds)
- **Total**: $0.40/month vs $1.08/month current (63% reduction)

### Reliability Targets
- **Uptime**: 99.5% (KEDA scaling + health checks)
- **Error Rate**: < 1% of requests
- **Queue Processing**: 100% of messages processed
- **Data Loss**: Zero tolerance

---

## 📚 Related Documents

- [Architecture Decision](./SITE_GENERATOR_ARCHITECTURE_DECISION.md)
- [Cost Optimization](./infrastructure/cost-optimization.md)
- [KEDA Scaling Patterns](./SITE_REGENERATION_TRIGGER.md)
- [PEP8 Style Guide](https://pep8.org/)

---

## 🚀 Getting Started

### Development Setup
```bash
# Create feature branch
git checkout -b feature/split-site-generator

# Create directory structure
mkdir -p containers/{markdown-generator,site-builder}/{tests,templates}

# Copy template files (from this plan)
# ... create initial files ...

# Install dependencies
cd containers/markdown-generator
pip install -r requirements.txt

# Run tests
pytest tests/ -v --cov

# Start development server
uvicorn main:app --reload
```

### Testing Locally
```bash
# Test markdown generation
curl -X POST http://localhost:8000/api/markdown/generate \
  -H "Content-Type: application/json" \
  -d '{"article_data": {"title": "Test", "content": "Content"}}'

# Test queue processing
curl -X POST http://localhost:8000/storage-queue/process

# Check health
curl http://localhost:8000/health
```

### Deploy to Azure
```bash
# Build and push containers
make build-container CONTAINER=markdown-generator
make build-container CONTAINER=site-builder

# Apply Terraform
cd infra
terraform plan
terraform apply

# Verify deployment
az containerapp show -n ai-content-prod-markdown-gen -g ai-content-prod-rg
```

---

**Next Steps:**
1. Review this plan and provide feedback
2. Create GitHub issue from this plan
3. Create feature branch
4. Begin Phase 1 implementation
5. Submit PR when Phase 1-3 complete

---

*Last Updated: October 7, 2025*

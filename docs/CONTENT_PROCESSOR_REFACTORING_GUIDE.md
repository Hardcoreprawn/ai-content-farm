# Content Processor Functional Refactoring Guide
**Implementation Roadmap for Pure Functional Architecture**

## Quick Reference

**Current State**: 15+ classes, 5-level deep nesting, shared mutable state  
**Target State**: Pure functions, immutable data, 2-level composition  
**Timeline**: 8 weeks (40 working days)  
**Risk Level**: Medium (phased migration minimizes risk)

---

## Phase 1: Extract Pure Functions (Weeks 1-2)

### Objective
Create parallel functional implementations without breaking existing code.

### Files to Create

#### 1. `functional/__init__.py`
```python
"""Functional programming implementations for content processor.

Pure functions with immutable data structures and explicit dependencies.
"""

from .topic_conversion import (
    calculate_priority_score,
    collection_item_to_topic_metadata,
    validate_topic_metadata,
)
from .pricing import calculate_openai_cost, get_pricing_data
from .metadata import generate_slug, clean_title, build_url

__all__ = [
    "calculate_priority_score",
    "collection_item_to_topic_metadata",
    "validate_topic_metadata",
    "calculate_openai_cost",
    "get_pricing_data",
    "generate_slug",
    "clean_title",
    "build_url",
]
```

#### 2. `functional/topic_conversion.py`
```python
"""Pure functions for topic conversion and priority scoring."""

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from models import TopicMetadata


def calculate_priority_score(
    upvotes: int,
    comments: int,
    age_hours: float,
    source_weight: float = 1.0
) -> float:
    """Calculate priority score for topic.
    
    Pure function with explicit dependencies.
    
    Args:
        upvotes: Number of upvotes
        comments: Number of comments
        age_hours: Age of topic in hours
        source_weight: Weight factor for source (0.0-1.0)
    
    Returns:
        Priority score between 0.0 and 1.0
    
    Example:
        >>> calculate_priority_score(100, 50, 2.0, 1.0)
        0.85
    """
    if age_hours <= 0:
        age_hours = 0.1
    
    # Engagement score (weighted)
    engagement = (upvotes * 0.7) + (comments * 0.3)
    
    # Time decay (exponential)
    time_factor = 1.0 / (1.0 + (age_hours / 24.0))
    
    # Combined score with source weight
    raw_score = (engagement * time_factor * source_weight) / 1000.0
    
    # Normalize to 0-1 range
    return min(max(raw_score, 0.0), 1.0)


def collection_item_to_topic_metadata(
    item: Dict[str, Any],
    source: str,
    collection_date: Optional[datetime] = None
) -> Optional[TopicMetadata]:
    """Convert collection item to TopicMetadata.
    
    Pure function with validation.
    
    Args:
        item: Raw collection item dictionary
        source: Source identifier (e.g., "reddit", "hackernews")
        collection_date: When item was collected
    
    Returns:
        TopicMetadata if valid, None if invalid
    """
    try:
        # Extract required fields
        topic_id = item.get("id")
        title = item.get("title")
        
        if not topic_id or not title:
            return None
        
        # Calculate priority
        priority_score = calculate_priority_score(
            upvotes=item.get("upvotes", 0),
            comments=item.get("comments", 0),
            age_hours=item.get("age_hours", 24.0),
            source_weight=_get_source_weight(source)
        )
        
        # Create immutable metadata
        return TopicMetadata(
            topic_id=topic_id,
            title=title,
            source=source,
            collected_at=collection_date or datetime.now(timezone.utc),
            priority_score=priority_score,
            url=item.get("url"),
            upvotes=item.get("upvotes"),
            comments=item.get("comments"),
            enhanced_metadata=item.get("metadata")
        )
    except Exception:
        return None


def validate_topic_metadata(topic: TopicMetadata) -> bool:
    """Validate topic metadata completeness.
    
    Pure function - no side effects.
    """
    return bool(
        topic.topic_id and
        topic.title and
        topic.source and
        0.0 <= topic.priority_score <= 1.0
    )


def _get_source_weight(source: str) -> float:
    """Get weight factor for content source."""
    weights = {
        "reddit": 1.0,
        "hackernews": 0.9,
        "twitter": 0.8,
        "rss": 0.7
    }
    return weights.get(source.lower(), 0.5)
```

#### 3. `functional/pricing.py`
```python
"""Pure functions for OpenAI pricing calculations."""

from typing import Dict, Optional


def calculate_openai_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    pricing_data: Optional[Dict[str, Dict[str, float]]] = None
) -> float:
    """Calculate cost for OpenAI API usage.
    
    Pure function - no external dependencies.
    
    Args:
        model: Model name (e.g., "gpt-35-turbo")
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        pricing_data: Optional pricing dictionary, uses defaults if not provided
    
    Returns:
        Cost in USD
    
    Example:
        >>> calculate_openai_cost("gpt-35-turbo", 1000, 500)
        0.00075
    """
    if pricing_data is None:
        pricing_data = _get_default_pricing()
    
    model_pricing = pricing_data.get(model, pricing_data["gpt-35-turbo"])
    
    prompt_cost = (prompt_tokens / 1000.0) * model_pricing["input"]
    completion_cost = (completion_tokens / 1000.0) * model_pricing["output"]
    
    return prompt_cost + completion_cost


def get_pricing_data(
    blob_accessor: callable,
    cache_duration_days: int = 7
) -> Dict[str, Dict[str, float]]:
    """Fetch pricing data from blob storage.
    
    Functional wrapper around blob access.
    """
    # TODO: Implement blob access with caching
    return _get_default_pricing()


def _get_default_pricing() -> Dict[str, Dict[str, float]]:
    """Fallback pricing data (as of October 2025)."""
    return {
        "gpt-35-turbo": {
            "input": 0.0005,   # $0.50 per 1M tokens
            "output": 0.0015    # $1.50 per 1M tokens
        },
        "gpt-4": {
            "input": 0.01,      # $10 per 1M tokens
            "output": 0.03      # $30 per 1M tokens
        }
    }
```

#### 4. `functional/metadata.py`
```python
"""Pure functions for SEO metadata generation."""

import re
from datetime import datetime
from typing import Tuple


def generate_slug(title: str, max_length: int = 60) -> str:
    """Generate URL-safe slug from title.
    
    Pure function - deterministic output.
    
    Args:
        title: Article title
        max_length: Maximum slug length
    
    Returns:
        URL-safe slug
    
    Example:
        >>> generate_slug("How to Build AI Applications")
        "how-to-build-ai-applications"
    """
    # Convert to lowercase
    slug = title.lower()
    
    # Remove special characters
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    
    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)
    
    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    
    # Trim hyphens from ends
    slug = slug.strip('-')
    
    # Truncate to max length
    return slug[:max_length]


def clean_title(title: str) -> str:
    """Clean title for SEO optimization.
    
    Pure function - removes markdown, emojis, etc.
    """
    # Remove markdown formatting
    title = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', title)
    
    # Remove emojis and special chars
    title = re.sub(r'[^\w\s\-\.,!?]', '', title)
    
    # Normalize whitespace
    title = ' '.join(title.split())
    
    return title.strip()


def build_url(
    slug: str,
    published_date: datetime,
    base_url: str = "https://content.example.com"
) -> str:
    """Build full URL for article.
    
    Pure function - consistent URL structure.
    
    Args:
        slug: URL-safe article slug
        published_date: Publication date
        base_url: Base domain URL
    
    Returns:
        Full article URL
    
    Example:
        >>> build_url("ai-article", datetime(2025, 10, 8))
        "https://content.example.com/2025/10/ai-article"
    """
    return f"{base_url}/{published_date.year}/{published_date.month:02d}/{slug}"


def generate_filename(
    slug: str,
    published_date: datetime,
    extension: str = "md"
) -> str:
    """Generate filename for article.
    
    Pure function - consistent naming.
    """
    date_str = published_date.strftime("%Y%m%d")
    return f"{date_str}-{slug}.{extension}"
```

### Testing Strategy

Create test files alongside implementations:

```python
# functional/test_topic_conversion.py
import pytest
from datetime import datetime, timezone
from .topic_conversion import (
    calculate_priority_score,
    collection_item_to_topic_metadata
)

def test_calculate_priority_score_high_engagement():
    """Test priority calculation for high-engagement content."""
    score = calculate_priority_score(
        upvotes=1000,
        comments=200,
        age_hours=2.0,
        source_weight=1.0
    )
    
    assert 0.8 <= score <= 1.0
    assert isinstance(score, float)

def test_calculate_priority_score_old_content():
    """Test priority decay for old content."""
    recent_score = calculate_priority_score(100, 50, 2.0)
    old_score = calculate_priority_score(100, 50, 48.0)
    
    assert recent_score > old_score

def test_collection_item_conversion():
    """Test conversion from collection item to TopicMetadata."""
    item = {
        "id": "test123",
        "title": "Test Article",
        "upvotes": 100,
        "comments": 50,
        "age_hours": 5.0,
        "url": "https://example.com"
    }
    
    topic = collection_item_to_topic_metadata(
        item,
        source="reddit",
        collection_date=datetime.now(timezone.utc)
    )
    
    assert topic is not None
    assert topic.topic_id == "test123"
    assert topic.title == "Test Article"
    assert 0.0 <= topic.priority_score <= 1.0

def test_collection_item_missing_required_fields():
    """Test that invalid items return None."""
    item = {"id": "test123"}  # Missing title
    
    topic = collection_item_to_topic_metadata(item, "reddit")
    
    assert topic is None
```

### Deliverables (End of Week 2)

- ✅ `functional/` directory with pure function implementations
- ✅ Unit tests with 100% coverage for pure functions
- ✅ Documentation with examples
- ✅ Existing code still works (parallel implementation)

---

## Phase 2: Replace Client Classes (Weeks 3-4)

### Objective
Replace OpenAIClient and related classes with functional API.

### Files to Create

#### 1. `functional/openai_integration.py`
```python
"""Functional OpenAI integration with automatic resource management."""

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional, Tuple

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI


@dataclass(frozen=True)
class OpenAIConfig:
    """Immutable OpenAI configuration."""
    endpoint: str
    model: str
    api_version: str = "2024-07-01-preview"
    max_tokens: int = 4000
    temperature: float = 0.7


def create_openai_config_from_env() -> OpenAIConfig:
    """Create OpenAI config from environment variables.
    
    Pure function - reads env vars but creates immutable config.
    """
    return OpenAIConfig(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        model=os.getenv("AZURE_OPENAI_CHAT_MODEL", "gpt-35-turbo"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-07-01-preview")
    )


@asynccontextmanager
async def openai_client(
    config: OpenAIConfig
) -> AsyncIterator[AsyncAzureOpenAI]:
    """Async context manager for OpenAI client.
    
    Automatic resource cleanup.
    
    Usage:
        config = create_openai_config_from_env()
        async with openai_client(config) as client:
            response = await client.chat.completions.create(...)
        # Cleanup happens automatically!
    """
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default"
    )
    
    client = AsyncAzureOpenAI(
        api_version=config.api_version,
        azure_endpoint=config.endpoint,
        azure_ad_token_provider=token_provider
    )
    
    try:
        yield client
    finally:
        await client.close()


async def generate_article_content(
    config: OpenAIConfig,
    prompt: str,
    system_message: Optional[str] = None
) -> Tuple[str, int, int]:
    """Generate article content using OpenAI.
    
    Pure function with automatic cleanup.
    
    Args:
        config: OpenAI configuration
        prompt: Article prompt
        system_message: Optional system message
    
    Returns:
        Tuple of (content, prompt_tokens, completion_tokens)
    """
    if system_message is None:
        system_message = (
            "You are an expert writer creating trustworthy, "
            "unbiased articles for a personal content curation platform."
        )
    
    async with openai_client(config) as client:
        response = await client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )
        
        content = response.choices[0].message.content
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        
        return content, prompt_tokens, completion_tokens


async def test_openai_connection(config: OpenAIConfig) -> bool:
    """Test OpenAI connectivity.
    
    Pure function - returns boolean.
    """
    try:
        async with openai_client(config) as client:
            await client.chat.completions.create(
                model=config.model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=10
            )
        return True
    except Exception:
        return False
```

### Migration Strategy

1. **Week 3**: Implement `openai_integration.py` with tests
2. **Week 3**: Update `ArticleGenerationService` to use new API
3. **Week 4**: Update all references to `OpenAIClient`
4. **Week 4**: Delete old `OpenAIClient` class
5. **Week 4**: Update integration tests

### Deliverables (End of Week 4)

- ✅ Functional OpenAI API with context managers
- ✅ Migration of ArticleGenerationService
- ✅ All tests passing
- ✅ Old OpenAIClient removed

---

## Phase 3: Decompose ContentProcessor (Weeks 5-6)

### Objective
Replace ContentProcessor class with functional orchestration.

### Files to Create

#### 1. `functional/processing_context.py`
```python
"""Processing context for functional workflows."""

from dataclasses import dataclass
from typing import Callable

from functional.openai_integration import OpenAIConfig


@dataclass(frozen=True)
class ProcessingContext:
    """Immutable context for processing operations.
    
    Contains all dependencies as function objects or configs.
    """
    processor_id: str
    blob_accessor: Callable  # Async function for blob operations
    openai_config: OpenAIConfig
    queue_sender: Callable  # Async function for queue operations


async def create_processing_context() -> ProcessingContext:
    """Create fresh processing context for request.
    
    Factory function for dependency injection.
    """
    from functional.openai_integration import create_openai_config_from_env
    from libs.simplified_blob_client import create_blob_accessor
    from libs.queue_client import create_queue_sender
    from uuid import uuid4
    
    return ProcessingContext(
        processor_id=str(uuid4())[:8],
        blob_accessor=await create_blob_accessor(),
        openai_config=create_openai_config_from_env(),
        queue_sender=await create_queue_sender()
    )
```

#### 2. `functional/orchestration.py`
```python
"""Functional orchestration for content processing workflows."""

from datetime import datetime, timezone
from typing import List, Optional

from models import ProcessingResult, TopicMetadata
from functional.processing_context import ProcessingContext
from functional.topic_discovery import find_available_topics
from functional.article_generation import generate_article_from_topic
from functional.storage import save_processed_article
from functional.queue_operations import send_to_markdown_queue


async def process_available_work(
    context: ProcessingContext,
    batch_size: int,
    priority_threshold: float,
    debug_bypass: bool = False
) -> ProcessingResult:
    """Process available topics with functional workflow.
    
    Pure function - no side effects except I/O.
    
    Args:
        context: Immutable processing context
        batch_size: Maximum topics to process
        priority_threshold: Minimum priority score
        debug_bypass: Skip filtering for diagnostics
    
    Returns:
        ProcessingResult with immutable metrics
    """
    start_time = datetime.now(timezone.utc)
    processed_topics = []
    failed_topics = []
    total_cost = 0.0
    
    # Find topics
    topics = await find_available_topics(
        context.blob_accessor,
        batch_size,
        priority_threshold,
        debug_bypass
    )
    
    if not topics:
        return _create_empty_result(processing_time=0.0)
    
    # Process each topic
    for topic in topics:
        try:
            # Generate article
            article_result = await generate_article_from_topic(
                topic,
                context.openai_config
            )
            
            if not article_result:
                failed_topics.append(topic.topic_id)
                continue
            
            # Save article
            blob_name = await save_processed_article(
                context.blob_accessor,
                article_result
            )
            
            if not blob_name:
                failed_topics.append(topic.topic_id)
                continue
            
            # Trigger next stage
            await send_to_markdown_queue(
                context.queue_sender,
                blob_name
            )
            
            processed_topics.append(topic.topic_id)
            total_cost += article_result.get("cost", 0.0)
            
        except Exception:
            failed_topics.append(topic.topic_id)
    
    processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
    
    return ProcessingResult(
        success=True,
        topics_processed=len(processed_topics),
        articles_generated=len(processed_topics),
        total_cost=total_cost,
        processing_time=processing_time,
        completed_topics=processed_topics,
        failed_topics=failed_topics
    )


def _create_empty_result(processing_time: float = 0.0) -> ProcessingResult:
    """Create empty result for no-work scenarios."""
    return ProcessingResult(
        success=True,
        topics_processed=0,
        articles_generated=0,
        total_cost=0.0,
        processing_time=processing_time
    )
```

### Migration Steps

1. **Week 5**: Create orchestration module
2. **Week 5**: Update endpoints to use functional orchestration
3. **Week 6**: Test functional workflow end-to-end
4. **Week 6**: Remove ContentProcessor class
5. **Week 6**: Update all documentation

### Deliverables (End of Week 6)

- ✅ Functional orchestration pipeline
- ✅ ContentProcessor removed
- ✅ All service classes replaced with functions
- ✅ End-to-end tests passing

---

## Phase 4: Refactor Endpoints (Week 7)

### Objective
Remove singletons and use FastAPI dependency injection.

### Implementation

```python
# endpoints/storage_queue.py (refactored)
from fastapi import APIRouter, Depends
from functional.processing_context import ProcessingContext, create_processing_context
from functional.orchestration import process_available_work

router = APIRouter(prefix="/storage-queue")


@router.post("/process")
async def process_queue_message(
    message: QueueMessage,
    context: ProcessingContext = Depends(create_processing_context)
):
    """Process queue message using functional workflow.
    
    Context is created per-request via dependency injection.
    """
    result = await process_available_work(
        context=context,
        batch_size=message.batch_size,
        priority_threshold=message.priority_threshold
    )
    
    return StandardResponse(
        status="success" if result.success else "error",
        data=result.dict(),
        message=f"Processed {result.topics_processed} topics"
    )
```

### Deliverables (End of Week 7)

- ✅ Stateless endpoints
- ✅ FastAPI dependency injection
- ✅ No singletons
- ✅ Request-scoped contexts

---

## Phase 5: Documentation & Cleanup (Week 8)

### Tasks

1. **Update Docstrings**: Convert all to Google style
2. **Code Formatting**: Run `black`, `isort`, `mypy`
3. **API Documentation**: Generate with mkdocs
4. **Migration Guide**: Document patterns for other containers
5. **Best Practices**: Create functional programming guide
6. **Cleanup**: Delete deprecated files

### Deliverables (End of Week 8)

- ✅ Complete documentation
- ✅ All code formatted and type-checked
- ✅ Migration guide published
- ✅ Clean repository (no deprecated code)

---

## Risk Mitigation

### Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking changes | Medium | High | Phased migration with parallel implementations |
| Performance regression | Low | Medium | Benchmark before/after, use FastAPI caching |
| Test coverage gaps | Low | High | Require 100% coverage for new code |
| Team learning curve | Medium | Low | Provide examples and pair programming |

### Rollback Plan

Each phase has a rollback strategy:

1. **Phase 1-2**: Keep old code, delete new code if needed
2. **Phase 3-4**: Feature branch `refactor/functional`, can merge back to main
3. **Phase 5**: Git tags for each milestone

---

## Success Metrics

### Code Quality Metrics

- **Test Coverage**: > 95% (target: 100%)
- **Type Coverage**: 100% (mypy strict mode)
- **Cyclomatic Complexity**: < 10 per function
- **Function Length**: < 50 lines per function

### Performance Metrics

- **Request Latency**: No regression (< 5% increase acceptable)
- **Memory Usage**: Reduced by 20% (no class instances)
- **Concurrent Requests**: Increased by 50% (no singleton bottleneck)

### Development Metrics

- **Test Execution Time**: < 30 seconds for unit tests
- **Build Time**: < 2 minutes for full pipeline
- **New Developer Onboarding**: < 1 day (vs current 3 days)

---

## References

- [PEP 8 – Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [PEP 257 – Docstring Conventions](https://peps.python.org/pep-0257/)
- [PEP 484 – Type Hints](https://peps.python.org/pep-0484/)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Python Async Context Managers](https://docs.python.org/3/library/contextlib.html#contextlib.asynccontextmanager)

---

**End of Refactoring Guide**

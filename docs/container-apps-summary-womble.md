# Container Apps SummaryWomble Implementation

## Overview

This is a Container Apps implementation of the SummaryWomble function using FastAPI and pure functions architecture. It addresses the Azure Functions deployment complexity while maintaining the same API contract and functionality.

## Architecture

### Pure Functions Model
Following the agent instructions, all business logic is implemented as pure functions:

- **No side effects**: Functions don't modify external state
- **Deterministic**: Same input always produces same output  
- **Thread-safe**: No shared mutable state
- **Easy to test**: Clear inputs and outputs

### Content Source Abstraction
The system supports multiple content sources through a pluggable architecture:

```python
# Abstract interface
class ContentCollector(ABC):
    def collect(self, request: CollectionRequest) -> CollectionResult:
        pass

# Implementations
RedditCollector  # Uses PRAW for Reddit content
RSSCollector     # Future: RSS feed parsing
APICollector     # Future: Generic API endpoints
```

### Separation of Concerns

```
├── core/                    # Pure business logic
│   ├── content_model.py     # Data structures and pure functions
│   └── __init__.py
├── collectors/              # Content source implementations
│   ├── reddit_collector.py  # Reddit/PRAW integration
│   └── __init__.py
├── routers/                 # FastAPI HTTP handling
│   ├── summary_womble.py    # HTTP API and async job processing
│   └── __init__.py
├── main.py                  # FastAPI application setup
├── requirements.txt         # Dependencies
├── Dockerfile              # Container configuration
└── tests/                  # Test suite
    └── test_pure_functions.py
```

## API Compatibility

The Container Apps version maintains 100% API compatibility with the original Azure Function:

### Create Content Collection Job
```http
POST /api/summary-womble/process
Content-Type: application/json

{
  "source": "reddit",
  "targets": ["technology", "programming"],
  "limit": 25,
  "time_period": "hot",
  "filters": {
    "min_score": 10,
    "min_comments": 5
  }
}
```

### Response
```json
{
  "job_id": "uuid-here",
  "status": "queued",
  "message": "Content processing started. Use job_id to check status.",
  "timestamp": "2025-08-13T...",
  "source": "reddit", 
  "topics_requested": ["technology", "programming"],
  "limit": 25,
  "status_check_example": {
    "method": "POST",
    "url": "/api/summary-womble/status",
    "body": {"action": "status", "job_id": "uuid-here"}
  }
}
```

### Check Job Status
```http
POST /api/summary-womble/status
Content-Type: application/json

{
  "action": "status",
  "job_id": "uuid-here"
}
```

## Key Improvements

### 1. Pure Functions Architecture
- **Business logic separation**: Core content processing logic is isolated from HTTP/storage concerns
- **Testability**: Each function can be tested independently with clear inputs/outputs
- **Reusability**: Pure functions can be used in different contexts (HTTP, batch processing, etc.)

### 2. Content Source Extensibility
- **Plugin architecture**: Easy to add new content sources beyond Reddit
- **Standardized data model**: All sources return consistent `ContentItem` objects
- **Future-ready**: RSS feeds, APIs, web scraping can be added without changing core logic

### 3. Development Experience
- **Local development**: Standard Docker container development workflow
- **No Azure Functions complexity**: No function.json, host.json, or programming model conflicts
- **Standard debugging**: Use normal Python debugging tools
- **Fast iteration**: Code changes reflect immediately in development

### 4. Deployment Simplicity
- **Container deployment**: Standard Docker container to Azure Container Apps
- **No special packaging**: No zip files or Azure Functions-specific deployment
- **Infrastructure as Code**: Clean Terraform deployment without Azure Functions quirks

## Content Sources

### Current: Reddit (PRAW)
- ✅ Subreddit content collection
- ✅ Multiple time periods (hot, new, top, rising)
- ✅ Filtering by score, comments, keywords
- ✅ Maintains original functionality

### Future Extensions
- **RSS Feeds**: Parse RSS/Atom feeds from news sites
- **Hacker News**: Official API integration
- **Twitter/X**: API v2 integration (with credentials)
- **Generic APIs**: Configurable JSON API endpoints
- **Web Scraping**: BeautifulSoup-based content extraction

## Pure Functions Examples

### Content Filtering
```python
def filter_content_items(items: List[ContentItem], filters: Dict[str, Any]) -> List[ContentItem]:
    """Pure function to filter content items based on criteria"""
    # No side effects, deterministic, testable
    if not filters:
        return items
    
    # Apply filters and return new list
    return filtered_items
```

### Content Transformation
```python
def transform_collection_result(result: CollectionResult, transformations: Dict[str, Any]) -> CollectionResult:
    """Pure function to transform collection results"""
    # Sort, filter, limit content items
    # Returns new result object, doesn't modify input
    return transformed_result
```

## Testing Strategy

### Unit Tests for Pure Functions
```python
def test_filter_content_items_min_score():
    items = [ContentItem(..., score=10), ContentItem(..., score=5)]
    filtered = filter_content_items(items, {"min_score": 8})
    assert len(filtered) == 1
    assert filtered[0].score == 10
```

### Integration Tests for Collectors
```python
@patch('collectors.reddit_collector.praw.Reddit')
def test_reddit_collector(mock_reddit):
    # Mock Reddit API, test collector behavior
    result = collector.collect(request)
    assert result.success is True
```

### API Tests for HTTP Endpoints
```python
@pytest.mark.asyncio
async def test_create_job_endpoint():
    # Test FastAPI endpoints with test client
    response = await client.post("/api/summary-womble/process", json=request_data)
    assert response.status_code == 202
```

## Local Development

### Start Development Environment
```bash
# Set environment variables (optional for testing)
export REDDIT_CLIENT_ID="your_id"
export REDDIT_CLIENT_SECRET="your_secret" 
export REDDIT_USER_AGENT="your_agent"

# Start container
./scripts/start-container-apps.sh
```

### Test the API
```bash
# Health check
curl http://localhost:8000/health

# Create job
curl -X POST http://localhost:8000/api/summary-womble/process \
  -H 'Content-Type: application/json' \
  -d '{"source": "reddit", "targets": ["technology"], "limit": 5}'

# Check status  
curl -X POST http://localhost:8000/api/summary-womble/status \
  -H 'Content-Type: application/json' \
  -d '{"action": "status", "job_id": "your-job-id"}'
```

### View API Documentation
- OpenAPI/Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Custom docs: http://localhost:8000/api/summary-womble/docs

## Production Deployment

### Container Apps Configuration
```hcl
resource "azurerm_container_app" "content_processor" {
  name = "${local.resource_prefix}-processor"
  container_app_environment_id = azurerm_container_app_environment.main.id
  
  template {
    container {
      name   = "content-processor"
      image  = "your-registry/content-processor:latest"
      cpu    = 0.25
      memory = "0.5Gi"
      
      env {
        name = "REDDIT_CLIENT_ID"
        secret_name = "reddit-client-id"
      }
    }
  }
  
  ingress {
    external_enabled = true
    target_port     = 8000
  }
}
```

### CI/CD Pipeline
```yaml
- name: Build and Push Container
  run: |
    docker build -t $REGISTRY/content-processor:$GITHUB_SHA .
    docker push $REGISTRY/content-processor:$GITHUB_SHA

- name: Deploy to Container Apps
  run: |
    az containerapp update \
      --name content-processor \
      --image $REGISTRY/content-processor:$GITHUB_SHA
```

## Migration from Azure Functions

### Benefits
1. **Eliminates deployment complexity**: No more 403 errors or zip packaging issues
2. **Improves development experience**: Standard Docker workflow
3. **Enables content source extensibility**: Easy to add non-Reddit sources
4. **Simplifies testing**: Pure functions are easy to test
5. **Future-proofs architecture**: Not locked into Azure Functions programming models

### Migration Path
1. ✅ **SummaryWomble** (current): Full Container Apps implementation with API compatibility
2. **ContentRanker**: Migrate ranker_core.py to Container Apps
3. **ContentEnricher**: Add as new router to content-processor container
4. **Timer/Blob Functions**: Convert to scheduled Container Apps jobs

## Conclusion

This Container Apps implementation provides:
- **Same functionality** as Azure Functions SummaryWomble
- **Better development experience** with pure functions and standard containers
- **Extensible architecture** for multiple content sources
- **Simplified deployment** without Azure Functions complexity
- **Foundation for content pipeline expansion**

The pure functions approach ensures the code is maintainable, testable, and reusable across different deployment scenarios.

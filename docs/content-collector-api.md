# Content Collector (SummaryWombles) - Technical Documentation

## Overview

The Content Collector is the entry point of the AI Content Farm pipeline. It fetches, normalizes, filters, and deduplicates content from various sources (primarily Reddit) to feed into the content processing workflow.

## API Endpoints

### Health Check
```http
GET /health
```
**Response**: Service status, configuration issues, and version information
```json
{
  "status": "healthy|warning",
  "timestamp": "2025-08-13T15:55:35.720043+00:00", 
  "version": "1.0.0",
  "config_issues": ["REDDIT_CLIENT_ID not set"]
}
```

### Collect Content
```http
POST /collect
```
**Request Body**:
```json
{
  "sources": [
    {
      "type": "reddit",
      "subreddits": ["technology", "programming"],
      "limit": 10,
      "criteria": {
        "min_score": 100,
        "min_comments": 5,
        "include_keywords": ["AI", "machine learning"],
        "exclude_keywords": ["meme", "joke"]
      }
    }
  ],
  "deduplicate": true,
  "similarity_threshold": 0.8
}
```

**Response**:
```json
{
  "collected_items": [
    {
      "id": "1mp24b6",
      "title": "What Does Palantir Actually Do?",
      "score": 1524,
      "num_comments": 232,
      "created_utc": 1755085367.0,
      "url": "https://www.wired.com/story/palantir-what-the-company-does/",
      "author": "rezwenn",
      "subreddit": "technology",
      "source": "reddit",
      "collected_at": "2025-08-13T15:55:47.215924+00:00"
    }
  ],
  "metadata": {
    "total_collected": 2,
    "sources_processed": 1,
    "errors": 0,
    "processing_time_seconds": 0.265,
    "deduplication": {
      "enabled": true,
      "original_count": 2,
      "deduplicated_count": 2,
      "removed_count": 0
    }
  },
  "collection_id": "collection_1755100547_2",
  "timestamp": "2025-08-13T15:55:47.216405+00:00"
}
```

### Service Status
```http
GET /status
```
**Response**: Service uptime, collection statistics, and configuration
```json
{
  "service": "content-collector",
  "status": "running",
  "uptime": 82.904942,
  "stats": {
    "total_collections": 0,
    "successful_collections": 0,
    "failed_collections": 0
  },
  "config": {
    "default_subreddits": ["technology", "programming"],
    "max_posts_per_request": 100
  }
}
```

### Available Sources
```http
GET /sources
```
**Response**: List of available content sources and their parameters
```json
{
  "available_sources": [
    {
      "type": "reddit",
      "name": "Reddit API",
      "description": "Fetch posts from Reddit subreddits",
      "status": "configuration_required",
      "parameters": ["subreddits", "limit", "sort_by"]
    }
  ]
}
```

## Core Functions

### Content Collection
- **Reddit Integration**: Fetches posts using Reddit JSON API
- **Multi-source Support**: Extensible architecture for additional content sources
- **Rate Limiting**: Respects API rate limits and implements backoff strategies

### Content Processing
- **Normalization**: Standardizes content format across different sources
- **Filtering**: Applies quality criteria (score, comments, keywords)
- **Deduplication**: Removes similar content using configurable similarity thresholds

### Data Flow
```
External APIs → Raw Content → Normalization → Filtering → Deduplication → Standardized Output
```

## Configuration

### Environment Variables
```bash
# Reddit API Configuration
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=YourApp/1.0

# Service Configuration  
PORT=8004
DEBUG=false
LOG_LEVEL=INFO

# Quality Filters
MIN_SCORE_THRESHOLD=5
MIN_COMMENTS_THRESHOLD=2
SIMILARITY_THRESHOLD=0.8

# Rate Limiting
REQUEST_TIMEOUT=10
MAX_POSTS_PER_REQUEST=100
```

### Default Configuration
- **Port**: 8004
- **Default Subreddits**: technology, programming, MachineLearning, datascience, artificial, Futurology
- **Request Timeout**: 10 seconds
- **Max Posts per Request**: 100
- **Similarity Threshold**: 0.8

## Error Handling

### HTTP Status Codes
- **200**: Successful content collection
- **422**: Validation error (invalid request parameters)
- **500**: Internal server error (collection failure)

### Common Error Scenarios
- **Missing Required Fields**: Returns 422 with validation details
- **Invalid Source Type**: Handled gracefully with error count in metadata
- **API Rate Limiting**: Implements exponential backoff
- **Network Timeouts**: Configurable timeout with retry logic

## Testing

### Test Coverage: 44 Tests (100% Passing)

#### Unit Tests (22 tests)
- Reddit content fetching and error handling
- Content normalization with various data structures
- Filtering logic with different criteria combinations
- Deduplication algorithms with similarity detection
- Configuration validation and defaults

#### API Tests (22 tests)  
- All endpoint functionality and response formats
- Input validation and error responses
- Performance testing with large datasets
- Integration testing with mock external APIs

### Test Categories
```python
# Business Logic Tests
test_fetch_from_subreddit_success()
test_normalize_reddit_post_complete()
test_filter_content_by_criteria()
test_deduplicate_content_by_title_similarity()

# API Endpoint Tests  
test_collect_reddit_content()
test_health_check_success()
test_status_endpoint()
test_input_validation()
```

## Dependencies

### Core Dependencies
```
fastapi>=0.104.1
pydantic>=2.5.0
uvicorn>=0.24.0
requests>=2.31.0
```

### Development Dependencies
```
pytest>=7.4.3
pytest-asyncio>=0.21.1
pytest-mock>=3.12.0
```

## Performance Considerations

### Optimization Features
- **Concurrent Requests**: Parallel processing of multiple subreddits
- **Caching**: In-memory caching of recent requests
- **Streaming**: Large dataset processing with streaming responses
- **Rate Limiting**: Respects external API limits

### Scalability
- **Stateless Design**: Horizontal scaling capability
- **Resource Efficiency**: Minimal memory footprint per request
- **Configurable Limits**: Adjustable processing limits based on resources

## Integration Points

### Upstream Dependencies
- **Reddit API**: Primary content source
- **External APIs**: Extensible for additional content sources

### Downstream Consumers
- **Content Processor**: Receives normalized content for analysis
- **Content Enricher**: Uses collected content for AI enhancement
- **Direct API Consumers**: External services via REST API

## Monitoring and Observability

### Health Metrics
- Service availability and response times
- API endpoint success/failure rates
- Content collection statistics
- Error rates and types

### Logging
- Structured JSON logging
- Request/response logging for debugging
- Error tracking with stack traces
- Performance metrics collection

---

**Port**: 8004  
**Service Name**: content-collector  
**Version**: 1.0.0  
**Status**: ✅ Production Ready

# Content Processor Container

A containerized microservice that transforms raw Reddit data into structured content for the AI Content Farm pipeline.

## 🎯 Purpose

This service accepts Reddit post data and transforms it into standardized, structured content with:
- Cleaned and normalized titles
- Engagement scoring
- Content type detection
- Metadata extraction
- Source attribution

## 🚀 Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest

# Start server
python main.py
```

### Docker

```bash
# Build container
docker build -t content-processor .

# Run container
docker run -p 8000:8000 content-processor

# Test health endpoint
curl http://localhost:8000/health
```

## 📡 API Endpoints

### Health Check
```
GET /health
```
Returns service health status and dependency connectivity.

### Process Content
```
POST /process
Content-Type: application/json

{
  "source": "reddit",
  "data": [
    {
      "title": "Amazing AI breakthrough!",
      "score": 1250,
      "num_comments": 89,
      "created_utc": 1692000000,
      "subreddit": "MachineLearning",
      "url": "https://reddit.com/r/MachineLearning/comments/test123",
      "selftext": "Researchers have developed...",
      "id": "test123"
    }
  ],
  "options": {
    "format": "structured"
  }
}
```

Returns processed content with normalized fields, engagement scores, and metadata.

## 🧪 Testing

```bash
# Run all tests
python -m pytest

# Run specific test types
python -m pytest tests/test_processor.py  # Business logic
python -m pytest tests/test_main.py       # API layer
python -m pytest -m "not slow"            # Skip performance tests

# Type checking
python -m mypy main.py processor.py config.py --ignore-missing-imports
```

## 🔧 Configuration

### Environment Variables

- `ENVIRONMENT`: `local` (default) or `production`
- `AZURE_KEY_VAULT_URL`: Azure Key Vault URL (production)
- `AZURE_STORAGE_ACCOUNT`: Azure Storage account (production)
- `REDDIT_CLIENT_ID`: Reddit API client ID (local dev)
- `REDDIT_CLIENT_SECRET`: Reddit API secret (local dev)
- `REDDIT_USER_AGENT`: Reddit API user agent (local dev)

### Local Development

For local development, the service runs with minimal dependencies and mock Azure services.

### Production

In production, the service integrates with:
- Azure Key Vault for secrets management
- Azure Storage for data persistence
- Application Insights for monitoring

## 📊 Monitoring

The service includes:
- Health checks at `/health`
- Structured logging
- Error tracking
- Performance metrics

## 🏗️ Architecture

- **API Layer**: FastAPI with Pydantic models
- **Business Logic**: Pure functions in `processor.py`
- **Configuration**: Environment-based in `config.py`
- **Testing**: Comprehensive test coverage with pytest

## 📋 Development Guidelines

1. **Test-First**: Write tests before implementation
2. **Pure Functions**: Minimize side effects
3. **Type Safety**: Use mypy for type checking
4. **Clean Code**: Follow established patterns
5. **Zero Warnings**: Keep tests and linting clean

## 🐳 Container Details

- **Base Image**: python:3.11-slim
- **Port**: 8000
- **User**: Non-root (appuser:1000)
- **Health Check**: Built-in
- **Multi-stage Build**: Optimized for size

## 📈 Performance

- Processes 1000 Reddit posts in under 5 seconds
- Lightweight container (<100MB)
- Fast startup time (<2 seconds)
- Memory efficient (<50MB runtime)

## 🔒 Security

- Runs as non-root user
- No hardcoded secrets
- Input validation on all endpoints
- Comprehensive error handling
- Security-focused Docker build

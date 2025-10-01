# Site Generator Container

**A functional, event-driven static site generator for the AI Content Farm pipeline.**

## Overview

The Site Generator transforms processed content into optimized static websites using a clean functional architecture. It operates as part of the content processing pipeline, triggered by storage queue messages and producing deployable static sites.

## Architecture

### Functional Design
- **Pure Functions**: All core logic implemented as testable pure functions
- **Dependency Injection**: Configuration and clients passed as parameters
- **Event-Driven**: Triggered by storage queue messages via KEDA scaling
- **Stateless**: No persistent state, fully containerized

### Key Components

#### Core Processing Functions
- `generate_markdown_batch()` - Converts processed content to markdown files
- `generate_static_site()` - Creates complete HTML sites from markdown
- `create_generator_context()` - Initializes configuration and dependencies

#### API Endpoints
- `POST /generate-markdown` - Manual markdown generation
- `POST /generate-site` - Manual site generation  
- `GET /health` - Health check and status
- `GET /wake-up` - Wake-up check for scaling

#### Storage Integration
- **Input**: Processed content from blob storage
- **Output**: Generated markdown files and static HTML sites
- **Triggers**: Storage queue messages for automated processing

## Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export PYTHONPATH="/workspaces/ai-content-farm"
export AZURE_STORAGE_ACCOUNT_NAME="your-storage-account"

# Run locally
python main.py

# Run tests
pytest tests/ -v --cov=.
```

### Docker Deployment
```bash
# Build container
docker build -t site-generator .

# Run container
docker run -p 8000:8000 site-generator
```

## Configuration

### Environment Variables
- `AZURE_STORAGE_ACCOUNT_NAME` - Azure Storage account name
- `PROCESSED_CONTENT_CONTAINER` - Input container for processed content
- `MARKDOWN_CONTENT_CONTAINER` - Output container for markdown files
- `STATIC_SITE_CONTAINER` - Output container for static sites

### Blob Storage Containers
- `processed-content` - Input: AI-enhanced articles from content-processor
- `markdown-content` - Output: Generated markdown files with frontmatter
- `static-sites` - Output: Complete HTML sites ready for deployment

## API Reference

### Generate Markdown
```http
POST /generate-markdown
Content-Type: application/json

{
  "source": "manual",
  "batch_size": 10,
  "force_regenerate": false
}
```

**Response:**
```json
{
  "generator_id": "abc123",
  "operation_type": "markdown_generation",
  "files_generated": 10,
  "processing_time": 2.5,
  "output_location": "blob://markdown-content",
  "generated_files": ["article1.md", "article2.md"],
  "errors": []
}
```

### Generate Site
```http
POST /generate-site
Content-Type: application/json

{
  "theme": "default",
  "force_rebuild": false
}
```

**Response:**
```json
{
  "generator_id": "def456", 
  "operation_type": "site_generation",
  "files_generated": 25,
  "pages_generated": 12,
  "processing_time": 8.3,
  "output_location": "blob://static-sites",
  "generated_files": ["index.html", "article1.html", "feed.xml"],
  "errors": []
}
```

## Testing

### Test Strategy
The site generator uses a **clean testing approach** focused on:
- **Essential Contracts**: API data models and validation
- **Function Coverage**: Core business logic with proper mocking
- **Integration Smoke Tests**: Critical workflows and imports

### Running Tests
```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html

# Specific test suites
pytest tests/test_essential_contracts.py -v
pytest tests/test_function_coverage.py -v
```

### Test Coverage
- **models.py**: 100% (API contracts)
- **content_processing_functions.py**: 83% (core business logic)
- **Overall**: 51% focused coverage on critical components

## Pipeline Integration

### Content Processing Flow
1. **Content Collector** → Saves raw content to blob storage
2. **Content Processor** → Enhances content, saves to `processed-content`
3. **Queue Message** → Processor sends generation request to storage queue
4. **KEDA Scaling** → Scales site-generator based on queue messages
5. **Site Generator** → Processes queue messages, generates sites
6. **Output** → Static sites ready for deployment

### Storage Queue Integration
- **Queue Name**: `site-generation-requests`
- **Message Format**: JSON with container paths and generation parameters
- **KEDA Scaler**: `azure-queue` with managed identity authentication
- **Scaling**: 0-10 replicas based on queue depth

## Deployment

### Azure Container Apps
The site generator deploys as an Azure Container App with:
- **KEDA Scaling**: Queue-driven autoscaling
- **Managed Identity**: Secure access to storage and queues
- **Health Checks**: Built-in health monitoring
- **Resource Limits**: Optimized CPU/memory allocation

### CI/CD Pipeline
Automated deployment via GitHub Actions:
1. **Build**: Docker container build with dependency caching
2. **Test**: Full test suite execution with coverage reporting
3. **Security**: OWASP security scanning and vulnerability assessment
4. **Deploy**: Azure Container Apps deployment with blue-green strategy

## Monitoring

### Health Endpoints
- `GET /health` - Application health and dependency status
- `GET /metrics` - Performance metrics and processing statistics
- `GET /ready` - Readiness probe for container orchestration

### Logging
- **Structured Logging**: JSON format with correlation IDs
- **Azure Application Insights**: Centralized log aggregation
- **Performance Metrics**: Processing times, success rates, error tracking

## Development

### Adding New Features
1. **Write Tests First**: Add tests to `tests/test_function_coverage.py`
2. **Implement Function**: Add pure functions to appropriate modules
3. **Add API Endpoint**: Expose functionality via FastAPI endpoints
4. **Update Documentation**: Keep README and API docs current

### Code Standards  
- **Functional Architecture**: Pure functions with dependency injection
- **Type Hints**: Full type annotations for better IDE support
- **Error Handling**: Comprehensive error handling with proper HTTP status codes
- **Testing**: Maintain 80%+ coverage on core business logic

## Troubleshooting

### Common Issues
- **Import Errors**: Ensure `PYTHONPATH` includes workspace root
- **Azure Authentication**: Verify managed identity permissions
- **Queue Processing**: Check KEDA scaler configuration and queue permissions
- **Storage Access**: Confirm blob container permissions and naming

### Debug Tools
```bash
# Check container health
curl http://localhost:8000/health

# View processing logs
docker logs <container-id>

# Test storage connectivity
python -c "from functional_config import validate_storage_connectivity; print(validate_storage_connectivity())"
```

## Contributing

### Development Workflow
1. **Create Feature Branch**: `git checkout -b feature/description`
2. **Run Tests**: Ensure all tests pass before changes
3. **Implement Changes**: Follow functional architecture patterns
4. **Add Tests**: Maintain test coverage for new functionality
5. **Update Docs**: Keep documentation current
6. **Create PR**: Submit for review with clear description

### Code Review Checklist  
- [ ] All tests passing
- [ ] Test coverage maintained
- [ ] Function signatures documented
- [ ] Error handling implemented
- [ ] Security considerations addressed

---

**Version**: 1.0.0 - Functional Architecture  
**Last Updated**: September 30, 2025  
**Status**: Production Ready
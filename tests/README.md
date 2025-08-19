# Tests Directory

This directory contains all test files for the AI Content Farm project, organized by test type and scope.

## 📁 Directory Structure

```
tests/
├── integration/          # Integration and end-to-end tests
├── unit/                # Unit tests for individual components  
├── functions/           # Azure Functions specific tests
└── README.md           # This file
```

## 🧪 Test Categories

### Integration Tests (`integration/`)
End-to-end tests that validate complete workflows and inter-service communication:

- **`test_event_driven_pipeline.py`** - Test the complete event-driven pipeline flow
- **`test_pipeline_integration.py`** - Test integration between pipeline components
- **`test_web_pipeline.py`** - Test web interface and site generation pipeline
- **`test_keyvault_integration.py`** - Test Azure Key Vault integration
- **`test_mock_pipeline.py`** - Test pipeline with mocked external dependencies

### Unit Tests (`unit/`)
Isolated tests for individual components and functions.

### Function Tests (`functions/`)
Tests specific to Azure Functions runtime and deployment.

## 🚀 Running Tests

### Run All Tests
```bash
# Run complete test suite
pytest tests/

# Run with coverage report
pytest tests/ --cov=containers --cov-report=html
```

### Run Specific Test Categories
```bash
# Tests Directory

This directory contains system-level and integration tests for the AI Content Farm platform.

## Directory Structure

```
tests/
├── README.md                      # This file
├── integration/                   # Integration tests across multiple containers
├── test_article_delivery.py       # End-to-end article delivery pipeline tests
├── test_complete_pipeline.py      # Complete event-driven pipeline validation
├── test_event_driven.py          # Event-driven blob processing tests
└── test_ranked_content.json      # Sample test data for ranked content
```

## Test Categories

### System Tests
- **test_complete_pipeline.py**: Validates the entire event-driven architecture
- **test_event_driven.py**: Tests real-time blob event processing

### Integration Tests
- **test_article_delivery.py**: End-to-end content generation and delivery
- **integration/**: Cross-container integration tests

### Container-Specific Tests
Container-specific tests are located in each container's `tests/` directory:
- `containers/content-collector/tests/`
- `containers/content-processor/tests/`
- `containers/content-enricher/tests/`
- `containers/content-ranker/tests/`
- `containers/content-generator/tests/`
- `containers/site-generator/tests/`

## Running Tests

### All Tests
```bash
pytest tests/
```

### Specific Test Categories
```bash
# System tests
pytest tests/test_complete_pipeline.py

# Integration tests
pytest tests/integration/

# Container-specific tests
pytest containers/content-generator/tests/
```

### With Coverage
```bash
pytest --cov=libs --cov=containers tests/
```

## Test Data

- **test_ranked_content.json**: Sample ranked content data for testing content generation
- Test data should be realistic but not use real API keys or production data
- Use mock objects for external services in unit tests

## Environment Setup

Tests require certain environment variables for integration testing:
- `AZURE_STORAGE_ACCOUNT_NAME`: For blob storage tests
- `AZURE_OPENAI_ENDPOINT`: For AI service tests (optional)
- `AZURE_OPENAI_API_KEY`: For AI service tests (optional)

For local development, tests gracefully handle missing cloud resources.

# Unit tests only  
pytest tests/unit/

# Azure Functions tests
pytest tests/functions/
```

### Run Individual Test Files
```bash
# Test specific pipeline functionality
pytest tests/integration/test_event_driven_pipeline.py

# Test with verbose output
pytest tests/integration/test_pipeline_integration.py -v
```

## 🔧 Test Configuration

### Environment Setup
```bash
# Set up test environment
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1;"

# Start test dependencies
docker-compose up -d azurite
```

### Test Data
- Test data is stored in `tests/fixtures/` (when needed)
- Tests use Azurite for blob storage operations
- Mock data is generated programmatically where possible

## 📊 Test Standards

### Coverage Requirements
- **Minimum coverage**: 80% for all new code
- **Critical components**: 95% coverage required
- **Integration tests**: Must cover all major user workflows

### Test Structure
```python
class TestComponentName:
    """Test cases for ComponentName."""
    
    @pytest.fixture
    def setup_component(self):
        """Set up test component."""
        return ComponentName()
    
    def test_basic_functionality(self, setup_component):
        """Test basic component functionality."""
        # Arrange
        input_data = {"test": "data"}
        
        # Act
        result = setup_component.process(input_data)
        
        # Assert
        assert result["status"] == "success"
```

### Test Naming
- **Classes**: `TestComponentName`
- **Methods**: `test_specific_functionality`
- **Files**: `test_component_name.py`
- **Integration tests**: `test_integration_workflow_name.py`

## 🚨 Common Issues

### Azurite Connection Issues
```bash
# Restart Azurite if tests fail
docker-compose restart azurite

# Check Azurite is running
curl http://localhost:10000/devstoreaccount1
```

### Test Environment Cleanup
```bash
# Clean up test containers
pytest tests/ --cleanup

# Remove test data
rm -rf tests/temp_data/
```

### Performance Test Issues
```bash
# Run tests with timeout
pytest tests/ --timeout=300

# Skip slow tests for development
pytest tests/ -m "not slow"
```

## 🔄 Test Maintenance

### Adding New Tests
1. Choose appropriate test category (unit/integration/functions)
2. Follow existing naming conventions
3. Include proper setup and teardown
4. Add to appropriate test suite
5. Update coverage requirements if needed

### Test Data Management
- Keep test data minimal and focused
- Use factories for generating test data
- Clean up test data after test completion
- Mock external services where possible

### Continuous Integration
Tests are automatically run on:
- Pull request creation
- Push to main branch
- Scheduled nightly runs
- Before deployment to staging/production

---
**Last Updated**: August 18, 2025

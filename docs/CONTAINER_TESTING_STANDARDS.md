 # Container Testing Standards & Patterns

## Overview

This document establishes testing standards for our multi-container monorepo, based on lessons learned from the content-collector implementation. These patterns ensure reliable, fast, and maintainable tests across all containers.

## Core Principles

### 1. **Layered Testing Architecture**
```
├── Container-level Tests (containers/*/tests/)
│   ├── Unit Tests - Business logic with mocked dependencies
│   ├── API Tests - FastAPI endpoints with contract-based mocks
│   └── Integration Tests - Container behavior with external services
├── System-level Tests (tests/)
│   ├── End-to-end Tests - Full pipeline testing
│   └── Cross-container Integration - Service interactions
```

### 2. **Environment Management**
- **Single unified dev environment** with all dependencies
- **Virtual environment isolation** for development
- **Container isolation** for production/deployment
- **Contract-based mocking** for external dependencies

### 3. **Dependency Management Strategy**
- **Relaxed version constraints** (`~=` for minor updates, `>=` for patches)
- **Consistent base requirements** across containers via layered inheritance
- **Security-first updates** (allow security patches, prevent breaking changes)
- **Regular dependency audits** (safety scans in CI/CD only)

## Testing Patterns

### Pattern 1: Contract-Based Mocking

**Problem**: Simple mocks don't match real API behavior, causing production failures.
**Solution**: Define contracts that mirror external API structures exactly.

```python
# contracts/reddit_api_contract.py
@dataclass
class RedditPostContract:
    id: str
    title: str
    score: int
    # ... matches Reddit API exactly
    
    @classmethod
    def create_mock(cls, **overrides) -> "RedditPostContract":
        """Create realistic test data."""
        defaults = {
            "id": "mock_post_123",
            "title": "Realistic AI breakthrough article",
            "score": 1247,  # Realistic score
            # ... realistic defaults
        }
        defaults.update(overrides)
        return cls(**defaults)
```

**Benefits**:
- Tests validate against real API structure
- Catches API changes that would break production
- Provides living documentation of external APIs
- Higher confidence in integration tests

### Pattern 2: Dependency Injection for Testability

**Problem**: Hard-coded dependencies make testing slow and brittle.
**Solution**: Inject dependencies with test-time overrides.

```python
class ContentCollectorService:
    def __init__(self, storage_client: Optional[BlobStorageClient] = None):
        if storage_client:
            self.storage = storage_client
        elif os.getenv("PYTEST_CURRENT_TEST"):
            self.storage = MockBlobStorageClient()
        else:
            self.storage = BlobStorageClient()
```

**Benefits**:
- Fast unit tests (no external dependencies)
- Easy mocking for different test scenarios
- Production code remains unchanged
- Clear separation of concerns

### Pattern 3: Test Organization by Scope

**Unit Tests** (`test_*.py`)
- Test individual functions/methods
- Mock all external dependencies
- Fast execution (< 1s per test)
- High code coverage

**API Tests** (`test_main.py`)
- Test FastAPI endpoints
- Use contract-based mocks
- Validate request/response formats
- Test error handling

**Integration Tests** (`test_*_integration.py`)
- Test with real external services
- Use docker-compose for dependencies
- Slower execution (acceptable for CI/CD)
- End-to-end validation

### Pattern 4: Consistent File Structure

```
containers/{service}/
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── contracts/               # API contracts for mocking
│   │   ├── __init__.py
│   │   ├── reddit_api_contract.py
│   │   └── blob_storage_contract.py
│   ├── test_collector.py        # Unit tests
│   ├── test_main.py             # API tests
│   └── test_integration.py      # Integration tests
├── service_logic.py             # ~300 lines max
├── main.py                      # FastAPI app
├── requirements.txt             # Container-specific deps
└── pyproject.toml               # Test configuration
```

## File Size Guidelines

- **Maximum 300 lines per file**
- **Single responsibility principle**
- **Extract helper functions to separate modules**
- **Use imports to compose functionality**

## Dependency Strategy

### Base Layer Architecture
```
containers/base/
├── requirements-core.txt        # Essential packages (azure, pydantic)
├── requirements-common.txt      # Shared utilities (httpx, requests)
└── requirements-web.txt         # Web services (fastapi, uvicorn)
```

### Version Constraint Strategy
```txt
# Allow minor updates, security patches
pydantic~=2.11.0           # 2.11.x allowed
fastapi>=0.115.0,<1.0.0    # Security patches, no breaking changes
azure-storage-blob~=12.24.0 # Minor updates allowed
```

### Dev Environment Setup
```bash
# Single environment for all containers
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Testing Commands

### Container-level Testing
```bash
cd containers/{service}
python -m pytest                    # All tests
python -m pytest -m unit           # Unit tests only
python -m pytest -m integration    # Integration tests only
python -m pytest --cov             # With coverage
```

### System-level Testing
```bash
cd /workspaces/ai-content-farm
python -m pytest tests/            # System tests
docker-compose -f docker-compose.test.yml up  # Integration environment
```

## Migration Strategy

### Phase 1: Establish Patterns (content-collector) ✅
- Implement all testing patterns
- Document successful approaches
- Create reusable contracts and fixtures

### Phase 2: Apply to Other Containers
- content-processor
- content-enricher  
- content-ranker
- markdown-generator
- site-generator

### Phase 3: System Integration
- Cross-container contracts
- End-to-end test scenarios
- Performance testing
- Load testing

## Best Practices

### DO ✅
- Use contract-based mocking for external APIs
- Keep file sizes under 300 lines
- Separate unit, API, and integration tests
- Use dependency injection for testability
- Mock at the boundary (external services)
- Use realistic test data
- Run fast unit tests frequently
- Run integration tests in CI/CD

### DON'T ❌
- Mock internal business logic (test real code)
- Use global mocks (prefer dependency injection)
- Mix test scopes in same file
- Create overly complex mocks
- Skip tests for "simple" functions
- Use production services in unit tests
- Ignore test performance
- Create tests that depend on external state

## Success Metrics

- **Test Speed**: Unit tests < 1s, API tests < 5s
- **Coverage**: >90% line coverage for business logic
- **Reliability**: <1% flaky test rate
- **Maintainability**: Tests update automatically with contract changes
- **Developer Experience**: Fast feedback, clear failure messages

## Examples

See `containers/content-collector/tests/` for reference implementations of all patterns.

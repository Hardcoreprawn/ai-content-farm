# Testing Strategy & Patterns

## Overview

The Site Generator uses a **clean, focused testing approach** that prioritizes real value over test complexity. Our strategy emphasizes testing outcomes rather than implementations, with fast feedback loops and maintainable test code.

## Testing Philosophy

### Core Principles
1. **Test Outcomes, Not Implementations** - Focus on what functions return, not how they work internally
2. **Fast Feedback** - All tests run in under 5 seconds
3. **Mock at Boundaries** - Mock I/O operations, test business logic
4. **Standard Patterns** - Use consistent, simple mocking patterns
5. **Essential Coverage** - Cover critical paths, not every line

### What We Test

#### ✅ High Value Tests
- **API Contracts** - Request/response data models
- **Business Logic** - Core processing functions  
- **Integration Points** - Function imports and callability
- **Error Handling** - Critical failure scenarios

#### ❌ Low Value Tests  
- Implementation details (internal method calls)
- Complex integration scenarios (handled by E2E testing)
- Framework code (FastAPI, Pydantic internals)
- Configuration loading (environment-dependent)

## Test Structure

### Test Organization
```
tests/
├── test_essential_contracts.py    # Data models and API contracts
├── test_function_coverage.py      # Core business logic functions  
├── conftest.py                    # Shared fixtures and utilities
└── __init__.py
```

### Test Categories

#### 1. Essential Contracts Tests (12 tests)
**Purpose**: Validate API data models and request/response handling

```python
class TestDataContracts:
    def test_generation_request_validation(self):
        """GenerationRequest accepts valid data and rejects invalid data."""
        
    def test_generation_response_serialization(self):
        """GenerationResponse serializes correctly for API responses."""
```

**Coverage**: 
- Data model validation
- Serialization/deserialization
- Default values and optional fields
- API contract compliance

#### 2. Function Coverage Tests (9 tests)
**Purpose**: Test core business logic with proper mocking

```python
class TestContentProcessingFunctionsCoverage:
    @pytest.mark.asyncio
    async def test_generate_markdown_batch_success_path(self):
        """Test successful markdown generation with articles found."""
        with (
            patch('content_processing_functions.get_processed_articles') as mock_get,
            patch('content_processing_functions.generate_article_markdown') as mock_gen
        ):
            mock_get.return_value = test_articles
            mock_gen.side_effect = ["article1.md", "article2.md"]
            
            result = await generate_markdown_batch(...)
            
            assert result.files_generated == 2
```

**Coverage**:
- Success paths with valid data
- Empty data scenarios  
- Partial failure handling
- Error propagation

## Testing Patterns

### Standard Import Fix Pattern

**Problem**: Relative imports inside functions break testing
```python
# ❌ BAD - Hard to test
def some_function():
    from .other_module import helper  # Breaks mocking
```

**Solution**: Module-level imports  
```python
# ✅ GOOD - Easy to test
from content_utility_functions import helper

def some_function():
    return helper()  # Easy to mock with patch()
```

### Functional Mocking Pattern

**Pattern**: Mock at module level for functional architecture
```python
# ✅ Standard pattern for functional testing
with patch('content_processing_functions.utility_function') as mock_util:
    mock_util.return_value = expected_result
    
    result = await target_function(...)
    
    assert result.expected_field == expected_value
    mock_util.assert_called_once_with(expected_args)
```

### Async Function Mocking  
```python
# ✅ Proper async function mocking
with patch('module.async_function', new_callable=AsyncMock) as mock_async:
    mock_async.return_value = expected_result
    
    result = await function_under_test(...)
```

### Configuration Mocking
```python
# ✅ Simple config mocking
@pytest.fixture
def basic_config():
    return {
        "PROCESSED_CONTENT_CONTAINER": "processed-content",
        "MARKDOWN_CONTENT_CONTAINER": "markdown-content",
        "STATIC_SITE_CONTAINER": "static-site"
    }
```

## Coverage Strategy

### Target Coverage
- **models.py**: 100% (API contracts must be fully validated)
- **content_processing_functions.py**: 80%+ (core business logic)
- **content_utility_functions.py**: 20%+ (basic smoke tests)
- **Overall**: 50%+ focused on critical components

### Current Metrics
- **Total Tests**: 21 (all passing)
- **Test Runtime**: ~3 seconds
- **Models Coverage**: 100% ✅
- **Core Functions**: 83% ✅
- **Overall Coverage**: 51% ✅

### Coverage Command
```bash
# Run with coverage reporting
pytest tests/ --cov=content_processing_functions \
               --cov=content_utility_functions \  
               --cov=models \
               --cov=functional_config \
               --cov-report=term-missing \
               --cov-report=html
```

## Test Execution

### Local Development
```bash
# Run all tests
pytest tests/ -v

# Run specific test suites  
pytest tests/test_essential_contracts.py -v
pytest tests/test_function_coverage.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Fast test run (skip slow tests)
pytest tests/ -m "not slow"
```

### CI/CD Pipeline
```yaml
# GitHub Actions test step
- name: Run Tests
  run: |
    cd containers/site-generator
    PYTHONPATH="/workspaces/ai-content-farm" \
    python -m pytest tests/ -v \
      --cov=. --cov-report=xml \
      --junitxml=test-results.xml
```

## Common Testing Issues & Solutions

### Issue: Import Errors
**Problem**: `ImportError: attempted relative import with no known parent package`

**Solution**: Set PYTHONPATH correctly
```bash
export PYTHONPATH="/workspaces/ai-content-farm"
```

### Issue: Mock Not Applied
**Problem**: `AttributeError: <module> does not have the attribute 'function_name'`

**Solution**: Use correct import path for patching
```python
# ❌ Wrong - patches where imported from
patch('content_utility_functions.get_articles')

# ✅ Right - patches where used  
patch('content_processing_functions.get_articles')
```

### Issue: Async Mock Problems
**Problem**: `PydanticSerializationError: Unable to serialize unknown type: <class 'coroutine'>`

**Solution**: Use AsyncMock properly
```python
# ✅ Correct async mocking
with patch('module.async_func', new_callable=AsyncMock) as mock:
    mock.return_value = expected_result  # Not a coroutine
```

### Issue: Pydantic Serialization
**Problem**: Mock objects in Pydantic model responses

**Solution**: Return proper data structures
```python
# ❌ Wrong - returns Mock object
mock.return_value = Mock(field="value")

# ✅ Right - returns proper dict/object  
mock.return_value = {"field": "value"}
```

## Test Development Guidelines

### Writing New Tests

#### 1. Start with Contract Tests
```python
def test_new_function_contract(self):
    """Test that new function accepts valid inputs and returns expected format."""
    result = new_function(valid_input)
    
    assert isinstance(result, ExpectedModel)
    assert result.required_field is not None
```

#### 2. Add Business Logic Tests
```python  
@pytest.mark.asyncio
async def test_new_function_business_logic(self):
    """Test core business logic with mocked dependencies."""
    with patch('module.dependency') as mock_dep:
        mock_dep.return_value = test_data
        
        result = await new_function(test_input)
        
        assert result.meets_business_requirements
```

#### 3. Cover Error Cases
```python
@pytest.mark.asyncio  
async def test_new_function_error_handling(self):
    """Test that function handles errors gracefully."""
    with patch('module.dependency') as mock_dep:
        mock_dep.side_effect = Exception("Test error")
        
        with pytest.raises(SpecificException):
            await new_function(test_input)
```

### Test Naming Convention
- **test_function_name_scenario** - Describe what scenario is being tested
- **test_function_name_success_path** - Happy path testing
- **test_function_name_error_case** - Error handling testing
- **test_function_name_edge_case** - Boundary condition testing

### Fixture Guidelines
```python
@pytest.fixture
def descriptive_fixture_name():
    """Clear docstring explaining what this fixture provides."""
    return simple_test_data  # Keep fixtures simple
```

## Performance Testing

### Load Testing (Future)
```python
# Example load test structure
@pytest.mark.slow
@pytest.mark.asyncio
async def test_function_under_load():
    """Test function performance with high concurrency."""
    tasks = [target_function(test_input) for _ in range(100)]
    results = await asyncio.gather(*tasks)
    
    assert all(r.success for r in results)
    assert max(r.processing_time for r in results) < 5.0
```

### Memory Testing (Future)  
```python
import tracemalloc

def test_function_memory_usage():
    """Test that function doesn't leak memory."""
    tracemalloc.start()
    
    # Run function multiple times
    for _ in range(1000):
        result = target_function(test_input)
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    assert peak < 50 * 1024 * 1024  # Less than 50MB
```

## Integration with Development Workflow

### Pre-commit Testing
```bash
# Run before every commit
pytest tests/ -x --tb=short

# Quick smoke test
pytest tests/test_essential_contracts.py -v
```

### Code Review Checklist
- [ ] New functions have corresponding tests
- [ ] Test coverage maintained (80%+ on core functions)
- [ ] Tests follow standard patterns
- [ ] No complex test setup required
- [ ] Tests run fast (< 5 seconds total)

---

**Testing Strategy Version**: 1.0  
**Last Updated**: September 30, 2025  
**Test Framework**: pytest + AsyncMock + Pydantic  
**Status**: Production Ready
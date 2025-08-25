# Content Processor Test Performance Issues & Solutions

## Current State Analysis

### Slow Tests Identified:
1. **test_phase2b_integration.py** - Real Azure Blob Storage operations (~5-8 minutes)
2. **test_integration.py** - Performance test with 1000 items (~1-2 minutes)
3. **Multiple async blob operations** - Network latency accumulation

### Root Causes:
- **Real Azure Storage**: Each blob operation takes 2-5 seconds over network
- **Serial Operations**: Tests run storage operations sequentially
- **Large Test Data**: Performance test processes 1000 items unnecessarily
- **No Mocking**: Integration tests hit real external services
- **Complex Workflows**: End-to-end pipeline simulation with multiple storage round-trips

## Recommended Solutions

### 1. Split Test Categories
```python
# Fast unit tests (< 1 second each)
containers/content-processor/tests/
├── unit/
│   ├── test_processor_functions.py     # Pure functions only
│   ├── test_api_endpoints.py          # FastAPI with mocked storage
│   └── test_validation.py             # Input validation only
├── integration/
│   ├── test_storage_integration.py    # Real Azure (mark as slow)
│   └── test_pipeline_integration.py   # End-to-end (mark as slow)
└── performance/
    └── test_performance.py            # Large datasets (mark as slow)
```

### 2. Mock Azure Blob Storage for Unit Tests
```python
# Use pytest fixtures with mock storage
@pytest.fixture
def mock_blob_client():
    with patch('libs.blob_storage.BlobStorageClient') as mock:
        # In-memory storage simulation
        mock.return_value.upload_text = Mock()
        mock.return_value.download_text = Mock(return_value="mock_content")
        mock.return_value.list_blobs = Mock(return_value=[])
        yield mock.return_value
```

### 3. Reduce Test Data Size
```python
# Instead of 1000 items, use 10-50 for performance testing
large_dataset = {
    "data": [create_test_item(i) for i in range(50)]  # Down from 1000
}
# Still validates performance, runs in seconds not minutes
```

### 4. Parallel Test Execution
```python
# Mark slow tests appropriately
@pytest.mark.slow
@pytest.mark.integration
class TestAzureIntegration:
    # Only run these when specifically requested
    pass

# Run fast tests by default
pytest containers/content-processor/tests/unit/

# Run slow tests separately
pytest -m slow containers/content-processor/tests/
```

### 5. Use Test Containers for Local Development
```python
# For local dev, use testcontainers-python with Azurite
@pytest.fixture(scope="session")
def azure_emulator():
    with AzuriteContainer() as azurite:
        # Local Azure Storage emulator - much faster
        yield azurite.get_connection_string()
```

## Implementation Priority

### Phase 1: Quick Wins (1-2 hours)
1. **Mark slow tests**: Add `@pytest.mark.slow` to integration tests
2. **Reduce dataset size**: Change 1000 → 50 items in performance test
3. **Split test run**: Update CI to run unit vs integration separately

### Phase 2: Mock Implementation (3-4 hours)
1. **Create mock blob client**: In-memory storage for unit tests
2. **Refactor existing tests**: Use mocks for pure logic testing
3. **Keep integration tests**: But mark them as slow/optional

### Phase 3: Test Architecture (4-6 hours)
1. **Reorganize test structure**: unit/ vs integration/ vs performance/
2. **Local emulator setup**: Azurite for faster local development
3. **Parallel execution**: Configure pytest-xdist for concurrent runs

## Expected Performance Improvements

### Before:
- Unit test run: ~10 minutes
- Multiple Azure calls per test
- Serial execution only

### After:
- Unit tests: ~30 seconds (with mocks)
- Integration tests: ~3 minutes (when needed)
- Performance tests: ~1 minute (smaller datasets)
- Total developer feedback loop: < 1 minute for unit tests

## CI/CD Integration

### Updated Test Strategy:
```yaml
# Fast feedback (every commit)
- name: Unit Tests
  run: pytest containers/content-processor/tests/unit/ -v

# Comprehensive testing (nightly/release)
- name: Integration Tests  
  run: pytest containers/content-processor/tests/ -m "not slow" -v

# Full validation (pre-deployment)
- name: All Tests
  run: pytest containers/content-processor/tests/ -v
```

This approach provides:
✅ Fast developer feedback (30s unit tests)
✅ Comprehensive validation when needed (3min integration)
✅ Confidence in real Azure integration (slow tests)
✅ Better test organization and maintainability

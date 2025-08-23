# Container Testing Migration Guide

## Quick Migration Checklist

Use this checklist to systematically apply the content-collector patterns to other containers.

### Phase 1: Assessment (5 minutes)
- [ ] **Check current test status**: `cd containers/{service} && python -m pytest`
- [ ] **Count lines**: `wc -l *.py` (target: < 300 lines per file)
- [ ] **Identify external dependencies**: Reddit API, Azure Storage, AI services, etc.
- [ ] **List test files**: Check what tests already exist

### Phase 2: Structure Setup (15 minutes)
- [ ] **Copy test structure** from content-collector
  ```bash
  cp -r containers/content-collector/tests/contracts containers/{service}/tests/
  cp containers/content-collector/tests/conftest.py containers/{service}/tests/
  ```
- [ ] **Create pyproject.toml** if missing:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  markers = [
      "unit: Unit tests",
      "integration: Integration tests", 
      "performance: Performance tests"
  ]
  ```

### Phase 3: Dependency Injection (20 minutes)
- [ ] **Identify external clients** (BlobStorageClient, AI clients, etc.)
- [ ] **Add dependency injection pattern** to main service class:
  ```python
  def __init__(self, client: Optional[ExternalClient] = None):
      if client:
          self.client = client
      elif os.getenv("PYTEST_CURRENT_TEST"):
          self.client = MockClient()
      else:
          self.client = RealClient()
  ```
- [ ] **Create mock classes** for external dependencies

### Phase 4: Contract Creation (30 minutes)
- [ ] **Define API contracts** for external services:
  ```python
  # tests/contracts/{service}_api_contract.py
  @dataclass 
  class ServiceResponseContract:
      # Mirror real API response structure
  ```
- [ ] **Create realistic mock data** using contracts
- [ ] **Validate contract completeness** with real API documentation

### Phase 5: Test Organization (45 minutes)
- [ ] **Organize tests by scope**:
  - `test_{service}.py` → Unit tests (business logic)
  - `test_main.py` → API tests (FastAPI endpoints)  
  - `test_integration.py` → Integration tests (external services)
- [ ] **Update conftest.py** with service-specific fixtures
- [ ] **Create smart mocks** that respond to request content

### Phase 6: Validation (10 minutes)
- [ ] **Run tests**: `python -m pytest --tb=short -q`
- [ ] **Check performance**: Target < 5 seconds total
- [ ] **Verify coverage**: All major code paths tested
- [ ] **Test file sizes**: `wc -l *.py` (< 300 lines each)

## Container-Specific Patterns

### content-processor
**External Dependencies**: OpenAI API, Azure Storage
**Key Contracts**: OpenAI response format, processing pipeline data
**Special Focus**: AI service mocking, token usage tracking

### content-enricher  
**External Dependencies**: Multiple AI services, knowledge bases
**Key Contracts**: AI enrichment responses, knowledge graph data
**Special Focus**: Multi-service orchestration, enrichment pipeline

### content-ranker
**External Dependencies**: Analytics services, scoring algorithms
**Key Contracts**: Ranking algorithm responses, analytics data
**Special Focus**: Scoring consistency, performance metrics

### markdown-generator
**External Dependencies**: Template engines, file systems
**Key Contracts**: Template formats (Jekyll, Hugo), file generation
**Special Focus**: Template rendering, file I/O mocking

### site-generator
**External Dependencies**: Static site generators, CDN services  
**Key Contracts**: Site generation tools, deployment APIs
**Special Focus**: Build process mocking, deployment validation

## Time Estimates

| Container | Estimated Time | Priority | Complexity |
|-----------|----------------|----------|------------|
| content-processor | 2 hours | High | Medium (AI services) |
| content-enricher | 3 hours | High | High (multiple AI services) |
| content-ranker | 2 hours | Medium | Medium (analytics) |
| markdown-generator | 1.5 hours | Medium | Low (file generation) |
| site-generator | 2 hours | Low | Medium (build tools) |

## Success Criteria

Each container should achieve:
- ✅ **All tests passing** (no failures)
- ✅ **Fast execution** (< 5 seconds total)
- ✅ **File size compliance** (< 300 lines per file)
- ✅ **Contract-based mocking** (realistic external API simulation)
- ✅ **Layered test organization** (unit → API → integration)

## Troubleshooting

### Common Issues
1. **Import errors**: Check Python path in conftest.py
2. **Slow tests**: Ensure external dependencies are mocked
3. **Flaky tests**: Use deterministic mock data, not random values
4. **Large files**: Extract helper functions to separate modules

### Getting Help
- Reference: `containers/content-collector/` (working example)
- Documentation: `docs/CONTAINER_TESTING_STANDARDS.md`
- Patterns: `docs/CONTENT_COLLECTOR_REFERENCE.md`
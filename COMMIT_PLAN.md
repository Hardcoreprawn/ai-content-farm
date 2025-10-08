# Commit Plan: Fanout Architecture & Functional Refactor

**Total Files**: 94 files changed
**Strategy**: Break into logical, reviewable commits

---

## Commit 1: Documentation Cleanup
**Purpose**: Remove outdated temporary docs, add STATUS.md

**Files** (9 files):
- DELETE: CLEAN_REBUILD_PLAN.md
- DELETE: COMMIT_SUCCESS_SUMMARY.md  
- DELETE: FILENAME_MISMATCH_BUG.md
- DELETE: REPROCESSING_MONITORING_GUIDE.md
- DELETE: REPROCESS_ENDPOINT_IMPLEMENTATION.md
- DELETE: REPROCESS_FLOW_ANALYSIS.md
- DELETE: REPROCESS_FLOW_VERIFIED.md
- DELETE: REPROCESS_REFACTORING_SUMMARY.md
- ADD: STATUS.md

**Message**: `docs: remove outdated temporary docs, add comprehensive STATUS.md`

---

## Commit 2: Content Collector - Fanout Pattern
**Purpose**: Add fanout logic to collector (1 topic = 1 message)

**Files** (3 new, 2 modified):
- ADD: containers/content-collector/topic_fanout.py
- ADD: containers/content-collector/collection_storage_utils.py
- ADD: containers/content-collector/tests/test_topic_fanout.py
- MODIFY: containers/content-collector/service_logic.py
- MODIFY: containers/content-collector/tests/test_coverage_improvements.py

**Message**: 
```
feat(collector): implement fanout pattern for 1:1 topic-to-message processing

- Add topic_fanout.py: Pure functions for creating individual topic messages
- Add collection_storage_utils.py: Save collections to blob for audit trail
- Update service_logic.py: Integrate fanout after collection
- Add comprehensive unit tests for fanout logic

Part of fanout architecture migration (Phase 2)
```

---

## Commit 3: Content Processor - Remove Legacy Code
**Purpose**: Clean up old batch processing artifacts

**Files** (7 files):
- DELETE: containers/content-processor/IMPORT_STANDARDS.md
- DELETE: containers/content-processor/METADATA_GENERATION_PHASE1_COMPLETE.md
- DELETE: containers/content-processor/deploy_azure.sh
- DELETE: containers/content-processor/test_local.sh
- DELETE: containers/content-processor/services/topic_discovery.py
- DELETE: containers/content-processor/tests/test_article_metadata.py
- DELETE: containers/content-processor/tests/test_azure_integration.py
- DELETE: containers/content-processor/validation_results_1756978440.json

**Message**: `refactor(processor): remove legacy batch processing code and old docs`

---

## Commit 4: Content Processor - Pure Function Modules
**Purpose**: Add functional programming modules (no side effects)

**Files** (8 new files):
- ADD: containers/content-processor/api_contracts.py
- ADD: containers/content-processor/blob_operations.py
- ADD: containers/content-processor/cost_calculator.py
- ADD: containers/content-processor/metadata.py
- ADD: containers/content-processor/openai_operations.py
- ADD: containers/content-processor/provenance.py
- ADD: containers/content-processor/queue_operations.py
- ADD: containers/content-processor/ranking.py
- ADD: containers/content-processor/seo.py

**Message**: 
```
feat(processor): add pure function modules for functional architecture

- api_contracts.py: Pydantic models for type-safe requests/responses
- blob_operations.py: Azure Storage operations
- cost_calculator.py: OpenAI cost tracking
- metadata.py: Article metadata generation
- openai_operations.py: OpenAI API interactions
- provenance.py: Content source tracking
- queue_operations.py: Queue message handling
- ranking.py: Content ranking algorithms
- seo.py: SEO optimization functions

All modules follow functional programming principles (pure functions, no classes)
```

---

## Commit 5: Content Processor - Service Layer Updates
**Purpose**: Update service layer to use new functional modules

**Files** (5 modified, 2 new):
- MODIFY: containers/content-processor/services/__init__.py
- MODIFY: containers/content-processor/services/mock_service.py
- MODIFY: containers/content-processor/services/openai_service.py
- MODIFY: containers/content-processor/services/processor_storage.py
- ADD: containers/content-processor/services/queue_coordinator.py
- ADD: containers/content-processor/services/session_tracker.py

**Message**: 
```
refactor(processor): update service layer for functional architecture

- Refactor services to use new pure function modules
- Add queue_coordinator.py: Coordinate multi-queue operations
- Add session_tracker.py: Track processing sessions
- Update openai_service.py: Use openai_operations.py functions
- Update processor_storage.py: Use blob_operations.py functions
```

---

## Commit 6: Content Processor - Core Logic Updates
**Purpose**: Update main processing logic for fanout pattern

**Files** (4 modified):
- MODIFY: containers/content-processor/processor.py
- MODIFY: containers/content-processor/endpoints/storage_queue_router.py
- MODIFY: containers/content-processor/models.py
- MODIFY: containers/content-processor/requirements.txt
- ADD: containers/content-processor/requirements-pinned.txt

**Message**: 
```
feat(processor): refactor core logic for fanout pattern

- processor.py: Process individual topics (not batches)
- storage_queue_router.py: Handle process_topic messages from queue
- models.py: Add TopicMetadata for structured topic data
- requirements.txt: Update dependencies for new modules
- requirements-pinned.txt: Pin all versions for reproducibility

Breaking change: Expects individual topic messages, not batch collections
```

---

## Commit 7: Content Processor - Test Suite Updates
**Purpose**: Add comprehensive test coverage for new architecture

**Files** (10 new/modified):
- ADD: containers/content-processor/tests/conftest.py
- ADD: containers/content-processor/tests/test_blob_operations.py
- ADD: containers/content-processor/tests/test_cost_pure_functions.py
- ADD: containers/content-processor/tests/test_data_contracts.py
- ADD: containers/content-processor/tests/test_e2e_workflow.py
- ADD: containers/content-processor/tests/test_input_formats.py
- ADD: containers/content-processor/tests/test_metadata_pure_functions.py
- ADD: containers/content-processor/tests/test_openai_operations.py
- ADD: containers/content-processor/tests/test_queue_message_handling.py
- MODIFY: containers/content-processor/tests/test_api_endpoints.py

**Message**: 
```
test(processor): add comprehensive test suite for functional architecture

- Add conftest.py: Shared pytest fixtures and mocks
- Add unit tests for all pure function modules
- Add end-to-end workflow tests
- Add data contract validation tests
- Add queue message handling tests
- Update API endpoint tests for new patterns

All tests follow functional programming style (no classes, standalone functions)
```

---

## Commit 8: Integration Tests
**Purpose**: Add end-to-end integration tests

**Files** (5 new):
- ADD: tests/integration/test_collector_fanout.py
- ADD: tests/integration/test_processor_queue_handling.py
- ADD: tests/integration/test_e2e_fanout_flow.py
- ADD: tests/integration/test_markdown_generation.py
- ADD: tests/integration/conftest.py

**Message**: 
```
test: add integration tests for fanout architecture

- test_collector_fanout.py: Validate collector creates fanout messages (12 tests)
- test_processor_queue_handling.py: Validate processor handles individual topics (7 tests)
- test_e2e_fanout_flow.py: End-to-end pipeline validation (5 tests)
- test_markdown_generation.py: Markdown output validation
- conftest.py: Shared integration test fixtures

Total: 24+ integration tests covering complete pipeline
```

---

## Pre-Push Checklist

Before pushing:
- [ ] Run `make test` - all tests pass
- [ ] Run `make security-scan` - no critical issues
- [ ] Check line endings: `git diff --check` (no CRLF)
- [ ] Verify imports follow strategy
- [ ] Check no secrets in code

---

## Expected CI/CD Impact

**What will happen**:
1. CI/CD detects changes in `containers/content-collector` and `containers/content-processor`
2. Runs security scans (Checkov, Trivy, Terrascan)
3. Runs unit tests for changed containers
4. Builds new Docker images
5. Pushes to GitHub Container Registry
6. **Deploys to production** (breaking changes!)

**Risk**: New code expects `process-topic` queue, production uses `content-processing-requests`

**Mitigation**: 
- Monitor deployment closely
- Be ready to rollback
- Check logs immediately after deploy
- Have Terraform fix for KEDA scaler ready

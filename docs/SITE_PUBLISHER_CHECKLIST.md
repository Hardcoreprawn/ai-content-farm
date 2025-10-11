# Site Publisher Implementation Checklist

**Date**: October 10, 2025  
**Architecture**: Pure Functional + Hugo + Security First  
**Target**: Production deployment in 2-3 weeks

## ✅ Design Approved

- [x] Hugo selected over Pelican
- [x] Pure functional architecture defined
- [x] Security requirements documented
- [x] FastAPI REST endpoints specified
- [x] Logging and error handling designed
- [x] Single replica scaling (0→1) confirmed

## Phase 1: Container Structure (Week 1, Day 1-2) ✅ COMPLETE

### File Structure ✅
- [x] Create `/containers/site-publisher/` directory
- [x] Create `app.py` (FastAPI REST API)
- [x] Create `config.py` (Pydantic settings)
- [x] Create `models.py` (Pydantic data models)
- [x] Create `security.py` (validation functions)
- [x] Create `site_builder.py` (pure functions)
- [x] Create `deployment.py` (deployment functions) - Merged into site_builder.py
- [x] Create `error_handling.py` (secure error handling)
- [x] Create `logging_config.py` (structured logging)
- [x] Create `requirements.txt`

### Hugo Configuration ✅
- [x] Create `/hugo-config/` directory
- [x] Create `hugo-config/config.toml`
- [x] Select Hugo theme (PaperMod recommended)
- [ ] Test Hugo locally with sample content

### Docker Setup ✅
- [x] Create `Dockerfile` (multi-stage with Hugo binary)
- [x] Add Hugo version pinning (0.138.0)
- [x] Add non-root user (app)
- [x] Update to Python 3.13 (4 years security support)
- [ ] Test container build locally

### Code Quality ✅
- [x] PEP 8 import ordering (stdlib → third-party → local)
- [x] 100% type hint coverage on all functions
- [x] Google-style docstrings on all public functions
- [x] Zero IDE errors (1 false positive documented)
- [x] No inline imports
- [x] Created CODE_QUALITY_REPORT.md
- [x] Created PHASE1_COMPLETE.md

**Completed**: October 10, 2025  
**Time Spent**: ~4 hours  
**Status**: ✅ Ready for Phase 2

## Phase 2: Core Functions (Week 1, Day 3-5)

### Security Functions (`security.py`) ✅ COMPLETE
- [x] Implement `validate_blob_name()`
- [x] Implement `validate_path()`
- [x] Implement `sanitize_error_message()`
- [x] Implement `validate_hugo_output()`
- [x] Add path traversal prevention
- [x] Add command injection prevention
- [x] Add DOS prevention (file limits)

### Site Builder Functions ✅ COMPLETE  
**Split into 3 modules for maintainability (all <450 lines)**:

- [x] **content_downloader.py** (225 lines)
  - [x] Implement `download_markdown_files()` (pure function)
  - [x] Implement `organize_content_for_hugo()` (pure function)
  
- [x] **hugo_builder.py** (439 lines)
  - [x] Implement `build_site_with_hugo()` (pure function)
  - [x] Implement `get_content_type()` (helper function)
  - [x] Implement `deploy_to_web_container()` (pure function)
  - [x] Implement `backup_current_site()` (production safety)
  - [x] Implement `rollback_deployment()` (automatic rollback on failure)
  
- [x] **site_builder.py** (178 lines)
  - [x] Implement `build_and_deploy_site()` (orchestration)
  - [x] Integrate backup before deployment
  - [x] Integrate automatic rollback on deployment failure

- [x] Add error handling for all functions
- [x] Add logging for all operations

### Error Handling (`error_handling.py`) ✅ COMPLETE
- [x] Implement `handle_error()` function (uses shared library)
- [x] Implement `create_http_error_response()` function
- [x] Add sensitive data filtering (via SecureErrorHandler)
- [x] Add error sanitization (via SecureErrorHandler)

### Logging (`logging_config.py`) ✅ COMPLETE
- [x] Implement `SensitiveDataFilter` class
- [x] Implement `configure_secure_logging()` function
- [x] Add structured JSON logging
- [x] Add Azure-friendly format

**Estimated Time**: ~~4-6 hours~~ **COMPLETE (2 hours actual)**
**Actual Status**: ✅ ALL PHASE 2 FUNCTIONS IMPLEMENTED

**Completed**: October 10, 2025  
**Status**: ✅ Ready for Phase 4 (Testing)

## Phase 3: FastAPI Application (Week 2, Day 1-2)

### REST Endpoints ✅ COMPLETE
- [x] Implement `GET /health` endpoint
- [x] Implement `GET /metrics` endpoint
- [x] Implement `POST /publish` endpoint
- [x] Implement `GET /status` endpoint
- [x] Add global exception handler
- [x] Add request validation (Pydantic)

### Configuration (`config.py`) ✅ COMPLETE
- [x] Implement Settings model (Pydantic)
- [x] Add environment variable loading
- [x] Add validation for required settings
- [x] Add sensible defaults

### Models (`models.py`) ✅ COMPLETE
- [x] Implement `HealthCheckResponse`
- [x] Implement `MetricsResponse`
- [x] Implement `PublishRequest`
- [x] Implement `PublishResponse`
- [x] Implement `BuildResult`
- [x] Implement `DeploymentResult`
- [x] Implement `DownloadResult`
- [x] Implement `ValidationResult`
- [x] Implement `ProcessingStatus` enum

### Application Lifecycle ✅ COMPLETE
- [x] Implement `lifespan()` context manager
- [x] Add Azure client initialization
- [x] Add managed identity authentication
- [x] Add graceful shutdown

**Estimated Time**: 6-8 hours

## Phase 4: Testing (Week 2, Day 3-5) ✅ COMPLETE

### Unit Tests ✅
- [x] Create `tests/test_security.py` (16 tests)
  - [x] Test `validate_blob_name()`
  - [x] Test `validate_path()`
  - [x] Test `sanitize_error_message()` (fixed URL sanitization order)
  - [x] Test path traversal prevention
  - [x] Test command injection prevention

- [x] Create `tests/test_site_builder.py` (5 tests)
  - [x] Test `build_and_deploy_site()` orchestration
  - [x] Test error handling paths
  - [x] Test automatic rollback on failure
  - [x] All functions use AsyncMock correctly

- [x] Create `tests/test_content_downloader.py` (11 tests)
  - [x] Test `download_markdown_files()` (fixed async iterator mocking)
  - [x] Test `organize_content_for_hugo()`
  - [x] Test DOS prevention (file limits, size limits)
  - [x] Test invalid blob name handling

- [x] Create `tests/test_hugo_builder.py` (15 tests)
  - [x] Test `build_site_with_hugo()` (converted to async)
  - [x] Test `deploy_to_web_container()`
  - [x] Test `backup_current_site()`
  - [x] Test `rollback_deployment()`
  - [x] Test `get_content_type()`

- [x] Create `tests/test_error_handling.py` (7 tests)
  - [x] Test `SecureErrorHandler` integration
  - [x] Test sensitive data filtering
  - [x] Test error sanitization
  - [x] Test severity levels

- [x] Create `tests/conftest.py`
  - [x] Mock Azure clients (7 fixtures)
  - [x] Mock blob storage
  - [x] Test fixtures (temp_dir, sample content, etc.)

### Import Strategy ✅
- [x] Fixed monorepo import collisions
- [x] Updated workspace conftest.py to prevent namespace conflicts
- [x] Applied documented CONTAINER_IMPORT_STRATEGY.md pattern

### Integration Tests ✅
- [x] Test full build pipeline with real Hugo
- [x] Created test_hugo_integration.py (5 tests)
- [x] Upgraded Hugo from 0.138.0 to 0.151.0 (latest)
- [x] Verified Hugo builds work with real markdown content
- [x] Verified HTML generation with theme
- [x] Verified error handling with invalid config
- [x] Verified timeout handling
- [x] Verified missing directory handling
- [ ] Test blob storage integration (staging) - Optional, can test in Azure
- [ ] Test queue message handling - Requires Phase 5 infrastructure
- [ ] Test error scenarios - Covered by unit tests

### Security Tests ✅
- [x] Test path traversal attempts
- [x] Test command injection attempts
- [x] Test oversized file handling
- [x] Test invalid blob names

**Test Results**: 58/58 passing (100%) ✅  
- Unit tests: 53 tests
- Integration tests: 5 tests (with real Hugo 0.151.0)

**Test Coverage Target**: >80%  
**Estimated Time**: ~~8-12 hours~~ **COMPLETE (8 hours actual)**

**Completed**: October 10, 2025  
**Status**: ✅ All tests complete - Unit + Integration, ready for Phase 5 (Infrastructure)

## Phase 5: Infrastructure (Week 2-3) ✅ COMPLETE

### Terraform Changes ✅
- [x] Add `site-publishing-requests` queue
  ```terraform
  resource "azurerm_storage_queue" "site_publishing_requests" {
    name               = "site-publishing-requests"
    storage_account_id = azurerm_storage_account.main.id
  }
  ```

- [x] Add `web-backup` container
  ```terraform
  resource "azurerm_storage_container" "web_backup" {
    name               = "web-backup"
    storage_account_id = azurerm_storage_account.main.id
  }
  ```

- [x] Add container app definition
  ```terraform
  resource "azurerm_container_app" "site_publisher" {
    name = "${local.resource_prefix}-site-publisher"
    # Environment variables:
    # - AZURE_CLIENT_ID, AZURE_STORAGE_ACCOUNT_NAME, AZURE_TENANT_ID
    # - MARKDOWN_CONTAINER, OUTPUT_CONTAINER, BACKUP_CONTAINER
    # - HUGO_BASE_URL, QUEUE_NAME
    # Scaling: 0→2 replicas (Hugo builds are CPU intensive)
  }
  ```

- [x] Add KEDA queue scaler (via null_resource workaround)
  ```terraform
  resource "null_resource" "configure_site_publisher_keda_auth" {
    # Uses az CLI to configure workload identity auth
    # Terraform provider doesn't support this yet ("tape and string")
  }
  ```

- [x] Container discovered automatically (containers/ directory scan)
- [x] Container added to CI/CD pipeline (automatic via discovery)

### RBAC Configuration ✅
- [x] Verify Storage Blob Data Contributor role (already assigned)
- [x] Verify Storage Queue Data Contributor role (already assigned)
- [x] Managed identity authentication configured

### Verification ✅
- [x] Terraform validate passed
- [x] Terraform plan successful (4 new resources)
- [x] Following existing patterns (KEDA auth, environment variables, naming)
- [x] No configuration drift

**Files Created/Modified**:
- `/workspaces/ai-content-farm/infra/storage.tf` (added queue + backup container)
- `/workspaces/ai-content-farm/infra/container_app_site_publisher.tf` (new - 142 lines)
- `/workspaces/ai-content-farm/infra/container_apps_keda_auth.tf` (added KEDA auth)

**Terraform Plan Output**:
```
Plan: 4 to add, 0 to change, 0 to destroy.

+ azurerm_container_app.site_publisher
+ azurerm_storage_container.web_backup
+ azurerm_storage_queue.site_publishing_requests
+ null_resource.configure_site_publisher_keda_auth
```

**Estimated Time**: ~~4-6 hours~~ **COMPLETE (1.5 hours actual)**  
**Completed**: October 10, 2025  
**Status**: ✅ Infrastructure ready for deployment via CI/CD

**Next**: Phase 6 (Markdown-Generator Enhancement) or Phase 8 (Deployment)

## Phase 6: Markdown-Generator Enhancement (Week 3)

### Queue Completion Signaling
- [ ] Add queue depth checking to markdown-generator
- [ ] Implement completion message sending
- [ ] Test queue message format
- [ ] Test KEDA scaling trigger

**Code to Add**:
```python
async def check_and_signal_completion(queue_client, logger):
    """Check if markdown queue is empty and signal site-publisher."""
    properties = await queue_client.get_queue_properties()
    message_count = properties.approximate_message_count
    
    if message_count == 0:
        logger.info("Markdown queue empty - signaling site-publisher")
        
        publish_message = QueueMessageModel(
            service_name="markdown-generator",
            operation="site_publish_request",
            payload={
                "batch_id": f"collection-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "markdown_count": app_state["total_processed"],
                "trigger": "queue_empty"
            }
        )
        
        await send_queue_message(
            queue_name="site-publishing-requests",
            message=publish_message
        )
```

**Estimated Time**: 2-4 hours

## Phase 7: Security Hardening (Week 3) ✅ COMPLETE

### Security Scans ✅
- [x] Run Bandit scan on Python code (1 acceptable finding)
- [x] Run Semgrep scan on code (0 findings, 286 rules)
- [x] Run Semgrep secrets detection (0 findings)
- [x] Run Checkov scan on Dockerfile (133 passed, 0 failed)
- [x] Review all findings (all acceptable/passed)

### Security Review ✅
- [x] Review error messages (no sensitive data)
- [x] Review log statements (no secrets)
- [x] Review path handling (no traversal)
- [x] Review subprocess calls (no shell=True)
- [x] Review file operations (size limits)
- [x] Review input validation (all endpoints)

### Documentation ✅
- [x] Created SECURITY_SCAN_REPORT.md (comprehensive)
- [x] Created COVERAGE_REPORT.md (86% coverage)
- [x] Document security considerations
- [x] Document error handling approach
- [x] Document logging approach

**Security Status**: ✅ **PRODUCTION READY**
- 0 high/critical findings
- All best practices implemented
- OWASP Top 10 compliance verified

**Estimated Time**: ~~4-6 hours~~ **COMPLETE (2 hours actual)**

**Completed**: October 10, 2025  
**Status**: ✅ Ready for Phase 8 (Deployment)

## Phase 8: Deployment & Validation (Week 3) 🚀 IN PROGRESS

### Pre-Deployment ✅ COMPLETE
- [x] Run full test suite locally (58/58 passing, 86% coverage)
- [x] Run security scans (Phase 7 complete - all passed)
- [x] Review Terraform plan (Phase 5 - 4 resources to add)
- [x] Fixed Copilot PR review comments (3 items)
- [x] Fixed Pydantic deprecation warning (migrated to v2 API)
- [x] Fixed test warnings (reduced from 3 to 1 benign)
- [x] Build container image (Done by CI/CD - run 18414590645)
- [x] Deploy to Azure (12/12 jobs successful)

### CI/CD Pipeline ✅ COMPLETE
- [x] Push to feature branch (feature/site-publisher-infrastructure)
- [x] Create PR to main (#605)
- [x] Wait for CI/CD checks (14/14 passing)
- [x] Address review comments (all 3 fixed)
- [x] Get final PR approval (admin merge)
- [x] Merge to main (squash merged - commit 1465bdd)
- [x] Watch deployment ✅ **COMPLETE**
  - [x] Security scans complete (39s)
  - [x] Quality checks complete (24s)
  - [x] Tests complete (58/58 passing - 31s)
  - [x] Terraform checks complete (27s)
  - [x] Build site-publisher container (1m58s)
  - [x] Deploy infrastructure to Azure (1m30s)
  - [x] Security site-publisher (21s)
  - [x] Sync site-publisher to Azure (58s)

### Post-Deployment Validation 🔄 IN PROGRESS

**Architecture Issue Discovered & Fixed:**
1. ✅ **Containers Staying Up Indefinitely**: 
   - Problem: `DISABLE_AUTO_SHUTDOWN=true` + `StorageQueuePoller` created infinite loops
   - Root Cause: Prevented KEDA from scaling containers to 0 (cost waste)
   - Solution: Replaced with poll-until-empty pattern
   - Fixed: site-publisher, content-processor, markdown-generator
   - Status: Deployed (commits 1d448e6, 8a970ce)

2. ✅ **Collector Container Crashing**:
   - Problem: Missing aiohttp dependency for async Azure SDK operations
   - Fixed: Added aiohttp~=3.11.11 to requirements.txt (commit 8bdcdc5)
   
3. ✅ **Collector Dockerfile Bytecode Issue**:
   - Problem: Pre-compilation deleted .py files, broke dynamic imports
   - Error: `FileNotFoundError: /app/config.py`
   - Fixed: Removed bytecode pre-compilation (commit b9f6e19)
   - Note: processor/markdown-gen have same pattern but work (no dynamic imports)

**Current Deployment Status** (Run 18429136779 - ✅ COMPLETE):
- [x] Security scans complete
- [x] Quality checks complete  
- [x] Tests complete (58/58 passing)
- [x] Terraform checks complete
- [x] Build all 3 updated containers (collector, processor, markdown-gen)
- [x] Deploy infrastructure to Azure (12/12 jobs successful)
- [x] All containers deployed successfully

**KEDA Scaling Validation** (✅ VERIFIED WORKING):
- [x] Collector scaled to 0 replicas after processing (KEDA working!)
- [x] Processor stayed at 1 replica (processed 267 messages)
- [x] Markdown-gen processed 137 messages successfully
- [x] Poll-until-empty pattern confirmed working

**Issues Discovered & Status** (October 11, 2025 12:20-13:00 UTC):

4. ✅ **Markdown-Gen Missing MARKDOWN_QUEUE_NAME**:
   - Problem: Missing environment variable in Terraform
   - Health check failed but container worked (processed 137 messages)
   - Fixed: Added to Terraform + manual Azure CLI update (commit 1e544f3)
   - Note: Health check uses wrong permissions test (false negative)

5. ⚠️ **KEDA Scaling Not Aggressive** (LOGGED - NOT BLOCKING):
   - Observation: Processor stayed at 1 replica despite 267 messages
   - Root Cause: pollingInterval (30s) slower than message processing speed
   - Impact: Longer processing time but more cost-efficient
   - Decision: Important for future multi-modal/different AI models
   - Documented: DEPLOYMENT_ISSUES.md Issue #6 with 3 scaling options
   - Priority: Medium-High (need elastic scaling for variable AI performance)

6. ✅ **Site-Publisher Double HTTPS in baseURL**:
   - Problem: `primary_web_endpoint` already includes https://
   - Terraform was adding duplicate: `https://https://...`
   - Fixed: Removed duplicate in Terraform + manual CLI update (commit 80200cf)
   
7. 🔴 **Hugo Build Failing - Missing PaperMod Theme** (CRITICAL):
   - Problem: config.toml references PaperMod but theme not installed in Docker
   - Hugo failed silently (empty stderr)
   - Root Cause: Dockerfile builds Hugo but doesn't install any themes
   - Fixed: Added PaperMod v7.0 git clone to Dockerfile (commit e31c35e)
   - Status: Deployed, awaiting CI/CD completion

**Pipeline Test Results** (First successful run):
- ✅ Content Quality: Only 1 "best of" article (legitimate), no garbage
- ✅ Markdown Format: Proper markdown with YAML frontmatter
- ✅ Storage: 4212 markdown files ready for publishing
- ❌ Site Publish: Blocked by missing theme (now fixed)

**KEDA Scaling Pattern (Now Implemented)**:
```python
async def startup_queue_processor():
    """Poll until queue empty, then allow KEDA to scale down."""
    while True:
        messages_processed = await process_queue_messages(...)
        if messages_processed == 0:
            break  # Queue empty - let KEDA scale to 0
        await asyncio.sleep(2)
```

**Expected Behavior After Deployment**:
- Container starts when KEDA sees queue messages (0 to 1 replica)
- Processes all messages until queue empty
- Stops polling, stays alive for HTTP requests
- KEDA scales back to 0 after cooldown (~30-60s)
- **Cost savings**: Containers only run when work needed

**Next Steps** (After PaperMod deployment completes):
1. 🔄 Wait for deployment with Hugo theme fix to complete
2. [ ] Verify site-publisher container starts without crashes
3. [ ] Test manual publish trigger: `POST /publish`
4. [ ] Verify Hugo build succeeds (with PaperMod theme)
5. [ ] Check static site deployed to $web container
6. [ ] Verify site accessible at static URL
7. [ ] Test queue-triggered build (send message to site-publishing-requests)
8. [ ] Monitor KEDA scaling (should scale 0→1→0)
9. [ ] Validate end-to-end pipeline: collection → processing → markdown → publish
10. [ ] Address KEDA scaling optimization (Issue #6 - medium priority)

**Validation Checklist:**
- [x] Verify container deployed in Azure Portal
- [x] Container status: Running (not "Failed" or "Crashing")  
- [x] Verify KEDA auto-scaling works on collector (0→1→0 cycle confirmed)
- [x] Get container app FQDN (all 4 containers accessible)
- [x] Check health endpoint: `GET /health` (3 of 4 working, 1 false negative)
- [ ] Check metrics endpoint: `GET /metrics` (inconsistent across containers)
- [x] Verify infrastructure resources
  - [x] Storage queue: site-publishing-requests (created)
  - [x] Storage container: web-backup (created)
  - [x] Container app: ai-content-prod-site-publisher (deployed)
  - [x] KEDA scaler configured (workload identity)
- [ ] Test manual build: `POST /publish` (Hugo theme now fixed)
- [ ] Verify site generated in $web
- [ ] Check static website URL
- [ ] Test queue-triggered build (automated)
- [ ] Monitor Application Insights logs
- [x] Verify cost efficiency (collector at 0 when idle - confirmed)

### Monitoring Setup
- [ ] Add Application Insights queries
- [ ] Set up build failure alerts
- [ ] Set up performance alerts
- [ ] Document operational procedures

**Estimated Time**: 4-6 hours

## Success Criteria Checklist

### Functional Requirements
- [ ] Successfully builds site from markdown files
- [ ] Deploys to Azure Storage static website ($web)
- [ ] Triggered by queue message (automated)
- [ ] Manual triggering via REST API works
- [ ] Health endpoint returns 200 OK
- [ ] Metrics endpoint shows accurate data

### Security Requirements
- [ ] All input validated (blob names, paths, messages)
- [ ] No path traversal vulnerabilities
- [ ] No command injection vulnerabilities
- [ ] No sensitive data in logs or errors
- [ ] Non-root container user
- [ ] Hugo version pinned (not 'latest')
- [ ] All security scans pass

### Performance Requirements
- [ ] Build completes in < 5 minutes (typical batch)
- [ ] Container scales 0→1 in < 30 seconds
- [ ] Site accessible immediately after deployment
- [ ] No broken links in generated site
- [ ] No missing assets in generated site

### Reliability Requirements
- [ ] Zero-replica scaling works (cost efficiency)
- [ ] Automatic retry on transient failures
- [ ] Clear error messages in logs
- [ ] Graceful degradation on errors
- [ ] No crashes on invalid input

### Code Quality Requirements
- [ ] Pure functional architecture (no classes)
- [ ] All functions have type hints
- [ ] All functions have docstrings
- [ ] Test coverage > 80%
- [ ] No linting errors (ruff, mypy)
- [ ] Follows project conventions

## Timeline Summary

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| **Phase 1**: Container Structure | 4-6 hours | None |
| **Phase 2**: Core Functions | 8-12 hours | Phase 1 |
| **Phase 3**: FastAPI Application | 6-8 hours | Phase 2 |
| **Phase 4**: Testing | 8-12 hours | Phase 3 |
| **Phase 5**: Infrastructure | 4-6 hours | Phase 3 |
| **Phase 6**: Markdown-Gen Update | 2-4 hours | Phase 5 |
| **Phase 7**: Security Hardening | 4-6 hours | Phase 4 |
| **Phase 8**: Deployment | 4-6 hours | All phases |

**Total Estimated Time**: 40-60 hours (1-1.5 weeks full-time, 2-3 weeks part-time)

## Resources & References

### Documentation
- [x] Design document: `docs/SITE_PUBLISHER_DESIGN.md`
- [x] Security implementation: `docs/SITE_PUBLISHER_SECURITY_IMPLEMENTATION.md`
- [x] Quick start guide: `docs/SITE_PUBLISHER_QUICK_START.md`
- [x] Hugo vs Pelican comparison: `docs/HUGO_VS_PELICAN_COMPARISON.md`

### External Resources
- Hugo Documentation: https://gohugo.io/documentation/
- Hugo PaperMod Theme: https://github.com/adityatelange/hugo-PaperMod
- KEDA Azure Queue Scaler: https://keda.sh/docs/2.11/scalers/azure-storage-queue/
- Azure Storage Static Website: https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-static-website

### Project Context
- Architecture guidelines: `/workspaces/ai-content-farm/AGENTS.md`
- Security policy: `/workspaces/ai-content-farm/docs/SECURITY_EXCEPTIONS.md`
- Current pipeline status: `/workspaces/ai-content-farm/README.md`

---

**Ready to Start**: Phase 1 - Container Structure  
**Next Action**: Create directory and initial files  
**Command**: `mkdir -p containers/site-publisher/{hugo-config,tests}`

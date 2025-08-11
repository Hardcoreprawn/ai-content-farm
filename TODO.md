# TODO

## **Current Focus: Content Processing Pipeline Completion** 
- [x] **ContentRanker Function**: Implemented event-driven blob-triggered ranking function
- [x] **Functional Programming Architecture**: Built with pure functions for scalability
- [x] **Comprehensive Testing**: 11 unit tests with baseline validation
- [x] **Event-Driven Pipeline**: SummaryWomble -> ContentRanker -> [ContentEnricher]
- [ ] **ContentEnricher Function**: Implement research and fact-checking stage
- [ ] **ContentPublisher Function**: Create markdown article generation with frontmatter
- [ ] **End-to-End Pipeline Testing**: Validate complete Reddit -> published articles flow
- [ ] **Production Testing**: Validate 6-hour timer schedule works with new pipeline

## **Next Phase: Content Functions Implementation**
- [ ] **ContentEnricher Function**:
  - [ ] Create blob-triggered function for ranked topics
  - [ ] Implement external content fetching with rate limiting
  - [ ] Add domain credibility assessment
  - [ ] Generate citations and research notes
  - [ ] Apply functional programming principles
  - [ ] Create comprehensive test suite
- [ ] **ContentPublisher Function**:
  - [ ] Create blob-triggered function for enriched topics
  - [ ] Generate SEO-optimized markdown with YAML frontmatter
  - [ ] Implement social sharing metadata
  - [ ] Add reading time estimation
  - [ ] Create monetization-ready structure
  - [ ] Apply functional programming principles
  - [ ] Create comprehensive test suite

## **Pipeline Enhancement & Reliability**
- [ ] **Job Queueing System**: Implement proper job queue with Azure Service Bus or Storage Queues
  - [ ] Handle multiple concurrent job requests
  - [ ] Implement job priority levels (urgent vs normal)
  - [ ] Add job retry logic with exponential backoff
  - [ ] Queue management endpoint for monitoring
- [ ] **Enhanced Status Tracking**: 
  - [ ] Add job completion notifications (email/webhook)
  - [ ] Implement job cancellation capability
  - [ ] Add job execution metrics and timing
  - [ ] Create job history cleanup (auto-delete old status files)
- [ ] **Cross-Stage Job Tracking**:
  - [ ] Extend job tickets across all pipeline stages
  - [ ] Add cross-stage dependency tracking
  - [ ] Implement pipeline-wide status monitoring
- [ ] **Monitoring & Alerting**:
  - [ ] Add Application Insights custom metrics for job success/failure rates
  - [ ] Set up alerts for failed jobs or queue backlog
  - [ ] Create dashboard for job monitoring
  - [ ] Track content quality metrics
- [ ] **Performance Optimization**:
  - [ ] Implement parallel processing for multiple subreddits
  - [ ] Add caching for Reddit API responses
  - [ ] Optimize blob storage patterns
  - [ ] Add content processing performance metrics

## **Code Quality & Architecture**
- [ ] **Clean Up Legacy Code**: Remove emojis from all functions for better log parsing
- [ ] **Function Dependencies**: Ensure all functions are self-contained with local requirements.txt
- [ ] **API Documentation**: Complete API contracts for all pipeline stages
- [ ] **Integration Testing**: Add tests for blob trigger chains
- [ ] **Error Handling**: Standardize error handling across all functions

## ~~COMPLETED: ContentRanker Implementation~~ ✅
- [x] **Event-Driven Architecture**: Implemented blob-triggered ContentRanker function
- [x] **Functional Programming**: Built with pure functions for thread safety and scalability
- [x] **Ranking Algorithm**: Multi-factor scoring (engagement, monetization, freshness, SEO)
- [x] **Quality Controls**: Deduplication, filtering, and content validation
- [x] **Comprehensive Testing**: 11 unit tests with baseline validation against real data
- [x] **Self-Contained Structure**: Independent function with local dependencies
- [x] **Production Ready**: Comprehensive error handling, logging, and configuration

## ~~COMPLETED: Async Job System~~ ✅
- [x] **Async Job System**: Implemented job tickets for SummaryWomble with status tracking
- [x] **Function Authentication**: Fixed Key Vault secret management for function-to-function calls
- [x] **Timer Function**: Updated GetHotTopics to work with async job tickets

## ~~COMPLETED: Terraform State Management~~ ✅
- [x] **Configure Bootstrap Remote State**: Migrated to remote state with proper backend config
- [x] **Configure Application Backend**: Added environment-specific backend configs (staging.hcl, production.hcl)
- [x] **Create State Migration Process**: Documented in docs/terraform-state-migration.md
- [x] **Add Backend Config Files**: Created backend.hcl files for bootstrap and application environments
- [x] **Test State Migration**: Successfully migrated and tested with CI/CD pipeline

## ~~COMPLETED: Key Vault Separation~~ ✅  
- [x] **CI/CD Key Vault**: Created dedicated vault for GitHub Actions OIDC credentials
- [x] **Application Key Vault**: Separated application secrets (Reddit API) from CI/CD secrets
- [x] **Consistent Naming**: Standardized all secrets to kebab-case naming
- [x] **Function Integration**: Updated SummaryWomble to use environment variables with Key Vault references
- [x] **Setup Script**: Enhanced to handle both vaults with simplified secret management

## ~~COMPLETED: OIDC & Deployment~~ ✅
- [x] Run `scripts/fix-oidc-environment-credentials.sh`
- [x] Grant Azure permissions to OIDC service principal  
- [x] Fix pipeline workflows to use repository variables instead of secrets
- [x] Deploy bootstrap infrastructure
- [x] Deploy to staging (in progress)

## Clean up scripts
- [ ] Delete duplicate setup scripts
- [ ] Fix Makefile
- [ ] Test clean setup

## Add tests
- [ ] Unit tests for functions
- [ ] End-to-end test
- [ ] Add to CI/CD

## Immediate follow-ups (this PR)
- [ ] Run full lint suite (yamllint + actionlint) and fix ShellCheck warnings in workflow scripts (quote variables, remove unused vars)
- [ ] Validate CI workflow: run consolidated pipeline on develop, confirm staging deploy succeeds
- [ ] Smoke test staging: admin-trigger GetHotTopics, verify logs and blob outputs
- [ ] Document lint instructions (Makefile targets) in docs/development-log.md

## Workflow refactor (maintainability)
- [ ] Split consolidated workflow into smaller, reusable pieces
  - [ ] Extract security scan job into .github/workflows/reusable/security-scan.yml (workflow_call)
  - [ ] Extract cost gate into .github/workflows/reusable/cost-gate.yml (workflow_call)
  - [ ] Extract deploy job(s) into .github/workflows/reusable/deploy.yml with environment input
  - [ ] Extract integration tests into .github/workflows/reusable/integration-tests.yml
  - [ ] Convert repeated shell snippets to Makefile targets where reasonable
  - [ ] Update consolidated workflow to call reusables with inputs and minimal glue
- [ ] Add CODEOWNERS checks for workflow changes
- [ ] Add scheduled lint run for workflows (weekly)

## Pipeline Optimization (Future)
- [ ] **Simplify GitHub Actions by reusing Makefile targets**
  - Benefits: Reduce duplication, easier maintenance, consistent behavior between local and CI
  - Current state: Some duplication between workflow steps and Makefile targets
  - Target: Replace more workflow steps with `make verify`, `make deploy`, etc.
  - Status: Partially implemented, could be further optimized

## Clean up scripts
- [x] Delete duplicate setup scripts → Moved to scripts/deprecated/
- [x] Fix Makefile → Updated with comprehensive targets
- [x] Test clean setup → Validated with CI/CD pipeline

## Plan improvements
- [ ] Split up GetHotTopics function
- [ ] Design better content pipeline
- [ ] Research MCP integration

## Maintenance
- [ ] Update Terraform version (currently 1.12.2) quarterly
- [ ] Update GitHub Actions versions quarterly
- [ ] Update Python dependencies monthly

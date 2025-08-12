# TODO

# TODO

## **COMPLETED: ContentRanker Function Implementation** ✅
- [x] **Event-Driven Architecture**: Implemented blob-triggered ContentRanker function
- [x] **Functional Programming**: Built with pure functions for thread safety and scalability
- [x] **Ranking Algorithm**: Multi-factor scoring (engagement, monetization, freshness, SEO)
- [x] **Quality Controls**: Deduplication, filtering, and content validation
- [x] **Comprehensive Testing**: 11 unit tests with baseline validation against real data
- [x] **Self-Contained Structure**: Independent function with local dependencies
- [x] **Production Ready**: Comprehensive error handling, logging, and configuration
- [x] **API Documentation**: Created API contracts for content pipeline data flow
- [x] **Clean Architecture**: Removed emojis, organized in ContentRanker folder

# TODO

## **Current Focus: Complete Content Pipeline (Staging-First)** 
- [x] **ContentRanker Function**: Implemented event-driven blob-triggered ranking function (2025-08-11)
- [x] **Functional Programming Architecture**: Built with pure functions for scalability (2025-08-11)
- [x] **HTTP Trigger for Testing**: Added authenticated manual trigger for ContentRanker (2025-08-11)
- [x] **Terraform Documentation**: Updated infrastructure code with HTTP trigger configuration (2025-08-11)
- [x] **Line Ending Standards**: Created development standards doc to prevent CRLF deployment failures (2025-08-11)
- [x] **Comprehensive Testing**: 11 unit tests with baseline validation (2025-08-11)
- [x] **Event-Driven Pipeline**: SummaryWomble -> ContentRanker -> [ContentEnricher] (2025-08-11)
- [x] **API Documentation**: Created data format specifications for all pipeline stages (2025-08-11)
- [x] **Self-Contained Functions**: Each function independent with local dependencies (2025-08-11)
- [ ] **ContentEnricher Function**: Implement research and fact-checking stage
- [ ] **ContentPublisher Function**: Create markdown article generation with frontmatter
- [ ] **End-to-End Pipeline Testing**: Validate complete Reddit -> published articles flow (staging)
- [ ] **Content Generation**: Get actual articles generated and stored before worrying about production
- [ ] **Refactor to Architecture Pattern**: Apply event→HTTP processor pattern to existing functions
  - [ ] **GetHotTopics**: Extract timer logic from business logic (create GetHotTopicsProcessor HTTP function)
  - [ ] **SummaryWomble**: Already HTTP, fits pattern - no changes needed

## **Future: Production & Traffic Optimization** (After content pipeline works)
- [ ] **Production Deployment**: Once content generation is proven in staging
- [ ] **SEO & Rankings**: Track search rankings and optimize for visibility  
- [ ] **Traffic Analytics**: Monitor visitor patterns and content performance
- [ ] **Content Freshness**: Address stale content issues after initial success

## **Future: Scale Sources & Monetization** (After basic pipeline proven)
- [ ] **Multiple Content Sources**: Expand beyond Reddit (HackerNews, dev.to, Medium, etc.)
- [ ] **Topic Diversification**: Add more subreddits/topic areas for broader content
- [ ] **Site Architecture Decision**: Single site vs multiple topic-specific sites
- [ ] **Monetization Experiments**: Ad networks, affiliate links, sponsored content
- [ ] **Content Quality Scaling**: Maintain quality while increasing volume
- [ ] **Learning Documentation**: Track what works/doesn't for future projects

## **Future: Content Repurposing & AI Integration** (Headless CMS approach)
- [ ] **Multi-Channel Content Strategy**: Markdown + frontmatter as base for multiple outputs
  - [ ] **Static Site**: Current approach (Astro/Hugo/Next.js)
  - [ ] **Microsoft AI App Framework**: Load content into MS's new AI framework
  - [ ] **Podcast Generation**: Text-to-speech of articles for audio content
  - [ ] **Industry Intelligence**: Sentiment analysis and company insights
- [ ] **AI-Native Applications**: 
  - [ ] **Industry Reports**: Automated summaries of sector trends
  - [ ] **Company Intelligence**: Sentiment tracking and news aggregation
  - [ ] **Topic Briefings**: AI-digestible content for other systems
- [ ] **Content as Data**: Structured content for AI training/fine-tuning

## **CI/CD Pipeline Optimization** 
- [ ] **Split Workflow Architecture**: Replace single long pipeline with two focused workflows
  - [ ] **Validation Workflow**: Security scans, cost analysis, validation (fast)
  - [ ] **Deployment Workflow**: Infrastructure + Function deployment (triggered by PR)
  - [ ] **Benefits**: Faster feedback, clearer separation of concerns, better resource usage
- [ ] **Staging-to-Production Strategy**: 
  - [ ] PR from develop -> main triggers production deployment
  - [ ] Remove redundant staging/production split in single workflow
  - [ ] Focus on "validate then deploy" rather than "deploy to both"

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

## **Code Quality & Pipeline Reliability** 
- [ ] **Clean Up Legacy Code**: Remove emojis from SummaryWomble and GetHotTopics functions
- [ ] **Function Dependencies**: Verify all functions have proper self-contained structure
- [ ] **Cross-Stage Job Tracking**: Extend job tickets across ContentRanker -> ContentEnricher -> ContentPublisher
- [ ] **Integration Testing**: Add tests for complete blob trigger chains
- [ ] **Error Handling**: Standardize error handling patterns across all functions
- [ ] **Performance Monitoring**: Add Application Insights metrics for pipeline stages

## **Future Enhancements** 
- [ ] **Job Queueing System**: Implement Azure Service Bus for advanced job management
- [ ] **Enhanced Status Tracking**: Pipeline-wide job monitoring and notifications
- [ ] **Performance Optimization**: Parallel processing and caching strategies
- [ ] **Content Quality Metrics**: Track and improve article generation quality

## ~~COMPLETED: ContentRanker Implementation~~ ✅
- [x] **Event-Driven Architecture**: Implemented blob-triggered ContentRanker function
- [x] **Functional Programming**: Built with pure functions for thread safety and scalability
- [x] **Ranking Algorithm**: Multi-factor scoring (engagement, monetization, freshness, SEO)
- [x] **Quality Controls**: Deduplication, filtering, and content validation
- [x] **Comprehensive Testing**: 11 unit tests with baseline validation against real data
- [x] **Self-Contained Structure**: Independent function with local dependencies
- [x] **Production Ready**: Comprehensive error handling, logging, and configuration
- [x] **API Documentation**: Created comprehensive API contracts documentation
- [x] **Clean Logging**: Removed emojis for better log parsing
- [x] **Deployment**: Successfully committed and pushed to CI/CD pipeline

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

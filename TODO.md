# TODO

## **Current Focus: Staging Validation** 🎯
- [ ] **Validate Staging Deployment**: Ensure Key Vault separation works correctly
- [ ] **Test Function App**: Verify Reddit API credentials work via Key Vault references
- [ ] **Test End-to-End**: Run GetHotTopics function and verify data flows
- [ ] **Monitor Pipeline**: Ensure CI/CD works with new infrastructure
- [ ] **Merge to Main**: After staging validation, promote to production

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

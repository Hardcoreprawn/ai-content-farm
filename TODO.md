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

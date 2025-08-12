# Pipeline Performance Test Plan

## Baseline
- Current workflow push should trigger with workflow changes detected
- Expected jobs: changes, workflow-lint, security-gate, (cost-gate skipped), (deploy skipped for non-infra/function changes)

## Test Series

### Test 1: Documentation-Only Change (Fastest)
**Purpose**: Validate docs-only changes skip all deployment steps
**Expected Outcome**: 
- Jobs: changes, (security-gate skipped for docs-only)
- Duration: ~1-2 minutes
- All deployment jobs should be skipped

**Test Change**: Update README.md with timestamp

### Test 2: Infrastructure-Only Change 
**Purpose**: Test infra changes trigger security, cost, and deployment
**Expected Outcome**:
- Jobs: changes, security-gate, cost-gate, deploy-to-staging
- Duration: ~3-4 minutes (with optimizations)
- Cost analysis and security scans run in parallel

**Test Change**: Add comment to a .tf file in infra/application/

### Test 3: Test-Only Change
**Purpose**: Validate test changes trigger minimal pipeline
**Expected Outcome**:
- Jobs: changes, security-gate, (deploy skipped), run-integration-tests
- Duration: ~2-3 minutes

**Test Change**: Add comment to test file

### Test 4: Function-Only Change
**Purpose**: Test function changes trigger deployment without infra
**Expected Outcome**:
- Jobs: changes, security-gate, (cost-gate skipped), deploy-to-staging
- Duration: ~3-4 minutes
- No Terraform operations

**Test Change**: Add comment to a function file

### Test 5: Full Change (Complete Pipeline)
**Purpose**: Test full pipeline with all components changed
**Expected Outcome**:
- All jobs execute: changes, security-gate, cost-gate, deploy-to-staging, run-integration-tests
- Duration: ~4-5 minutes (target)
- All optimizations active

**Test Change**: Touch files in functions/, infra/, and tests/

## Performance Targets
- Docs-only: 1-2 min (vs ~10 min baseline)
- Single component: 3-4 min (vs ~10 min baseline) 
- Full pipeline: 4-5 min (vs ~10 min baseline)
- ~50-60% improvement overall

## Key Metrics to Monitor
1. **Conditional Execution**: Jobs correctly skipped based on changes
2. **Parallel Execution**: Security and cost jobs run simultaneously
3. **Caching Effectiveness**: Tool installations and Terraform providers cached
4. **Wait Time Reductions**: Faster function registration and key setting
5. **Overall Duration**: End-to-end time for each test scenario

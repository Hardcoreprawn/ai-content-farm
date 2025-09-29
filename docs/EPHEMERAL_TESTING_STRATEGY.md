# Ephemeral Testing Strategy for AI Content Farm

**Document Version**: 1.0  
**Date**: September 29, 2025  
**Status**: Proposal  
**Author**: GitHub Copilot  

## Executive Summary

This document outlines a comprehensive strategy for implementing ephemeral, PR-based testing environments for the AI Content Farm project. The approach prioritizes cost-effectiveness while providing production-like validation for infrastructure changes, ensuring safe deployments without breaking our £30-40/month budget target.

### Key Benefits
- **Safety**: Validate infrastructure changes in production-like environments before deployment
- **Cost Control**: Selective testing only for infrastructure changes, with automatic cleanup
- **Speed**: Parallel testing with existing container revision strategy
- **Reliability**: End-to-end validation of Azure Container Apps, Storage Queues, and KEDA scaling

## Project Context

### Current Architecture
The AI Content Farm operates a 3-container architecture on Azure Container Apps:
```
Reddit/Web → content-collector → [Storage Queue] → content-processor → site-generator → jablab.com
```

### Current Testing Approach
- **Container Changes**: Deploy as 0% traffic revisions, blend over as tests pass
- **Infrastructure Changes**: Deploy directly to production (risk)
- **Site Changes**: Deploy to staging site, manual approval for promotion

### The Problem
Infrastructure changes currently lack production-like validation, creating deployment risks for:
- Storage Queue connectivity changes
- KEDA scaling configuration updates
- Managed identity authentication modifications
- Cross-container communication patterns

## Proposed Three-Tier Testing Strategy

### Tier 1: Container-Level Testing (Current - Low Cost)
**Status**: ✅ Implemented and Working  
**Use Case**: Application code changes within containers  
**Cost**: ~£0 additional (existing traffic blending)

**Implementation**:
- Deploy new container revisions with 0% traffic allocation
- Run health checks and unit tests against new revision
- Gradually blend traffic as tests pass
- Immediate rollback capability

**Benefits**:
- Zero downtime deployments
- Safe application updates
- No additional infrastructure costs

### Tier 2: Ephemeral Infrastructure Testing (Proposed - Medium Cost)
**Status**: 🚧 Proposed Implementation  
**Use Case**: Infrastructure changes requiring full environment validation  
**Cost**: ~£2-5 per test run, ~£40-100/month total

**Trigger Conditions**:
- Pull requests affecting `infra/**` directory
- Changes to `container-config/**` affecting infrastructure
- CI/CD pipeline modifications
- Manual trigger with `test-infrastructure` label

**Implementation Flow**:
1. **Automated Deployment**: Create PR-specific Azure resources
2. **Functional Testing**: Validate end-to-end functionality
3. **Integration Testing**: Test cross-container communication
4. **Automatic Cleanup**: Destroy resources after 4-hour maximum

**Resource Naming Strategy**:
```
Base: ai-content-production-*
Ephemeral: ai-content-pr-123-*
```

### Tier 3: Pre-production Validation (Current - Controlled Cost)
**Status**: ✅ Implemented via Staging  
**Use Case**: Site generator testing and content validation  
**Cost**: Existing staging environment costs

**Implementation**:
- Long-lived staging environment (develop branch)
- Content validation and editorial review
- Manual promotion to production site

## Technical Implementation

### Infrastructure Foundation

#### Terraform Variables (Already Implemented)
The project already includes ephemeral environment support:

```hcl
variable "environment_name" {
  description = "Dynamic environment name for ephemeral environments"
  type        = string
  default     = ""
}

variable "branch_name" {
  description = "Git branch name for ephemeral environments"
  type        = string
  default     = ""
}

locals {
  effective_environment = var.environment_name != "" ? var.environment_name : var.environment
  resource_prefix = var.resource_prefix != "" ? var.resource_prefix :
    var.environment_name != "" ? "ai-content-${var.environment_name}" : "ai-content-${local.short_env}"
}
```

#### State Management Strategy
- **Production**: Persistent state in Azure Storage
- **Ephemeral**: Separate state files per PR (`terraform-state-pr-123`)
- **Cleanup**: Automatic state file deletion on environment destruction

### GitHub Actions Workflow

#### Ephemeral Environment Deployment
```yaml
name: Ephemeral Environment Testing

on:
  pull_request:
    paths:
      - 'infra/**'
      - 'container-config/**'
      - '.github/workflows/**'

jobs:
  deploy-ephemeral:
    if: contains(github.event.pull_request.labels.*.name, 'test-infrastructure')
    environment: ephemeral-testing
    timeout-minutes: 240  # 4-hour maximum
    steps:
      - name: Deploy Infrastructure
        run: |
          export TF_VAR_environment_name="pr-${{ github.event.number }}"
          export TF_VAR_branch_name="${{ github.head_ref }}"
          export TF_VAR_image_tag="${{ github.sha }}"
          cd infra && terraform apply -auto-approve

      - name: Wait for Container Apps Ready
        run: |
          # Poll container apps until healthy
          make wait-for-deployment ENVIRONMENT="pr-${{ github.event.number }}"

      - name: Run Functional Tests
        run: |
          make test-functional ENVIRONMENT="pr-${{ github.event.number }}"

      - name: Cleanup (Always Runs)
        if: always()
        run: |
          export TF_VAR_environment_name="pr-${{ github.event.number }}"
          cd infra && terraform destroy -auto-approve
```

### Functional Test Suite

#### Core Test Categories
1. **Infrastructure Connectivity**
   - Storage Account accessibility
   - Key Vault secret retrieval
   - Container Registry authentication

2. **Queue System Validation**
   - Storage Queue creation and permissions
   - Message sending and receiving
   - KEDA scaling trigger validation

3. **Container Communication**
   - HTTP health endpoints
   - Cross-container API calls
   - Managed identity authentication

4. **End-to-End Pipeline**
   - Content collection simulation
   - Processing workflow validation
   - Output generation verification

#### Implementation Structure
```python
# tests/functional/test_ephemeral_environment.py
class TestEphemeralInfrastructure:
    def test_storage_queues_accessible(self):
        """Verify storage queues exist and are accessible"""
        
    def test_keda_scaling_configured(self):
        """Verify KEDA scaling triggers are properly configured"""
        
    def test_managed_identity_authentication(self):
        """Verify containers can authenticate with managed identity"""
        
    def test_end_to_end_content_flow(self):
        """Simulate full content processing pipeline"""
```

## Cost Analysis

### Resource Sizing for Ephemeral Environments

#### Optimized Container App Configuration
```hcl
resource "azurerm_container_app" "ephemeral" {
  # Minimal sizing for testing
  template {
    min_replicas = 0
    max_replicas = 1
    
    container {
      cpu    = 0.25
      memory = "0.5Gi"
    }
  }
}
```

#### Cost Breakdown (Per Test Run)
- **Container Apps**: £1.50 (4 hours × minimal sizing)
- **Storage Account**: £0.20 (temporary data)
- **Log Analytics**: £0.30 (test logs)
- **Total per run**: ~£2-5

#### Monthly Impact Analysis
- **Assumption**: 20 infrastructure PRs per month
- **Average test time**: 2 hours per PR
- **Monthly cost**: £40-100
- **Mitigation**: Resource auto-shutdown, minimal sizing

### Cost Control Mechanisms

#### Time-Based Controls
- Maximum 4-hour environment lifetime
- Automatic cleanup regardless of test outcome
- Off-hours restrictions for non-critical PRs

#### Resource Controls
- Minimal Container App replicas (0-1)
- Reduced CPU/memory allocation
- Standard storage tier (not premium)

#### Trigger Controls
- Manual label requirement (`test-infrastructure`)
- Path-based filtering (infrastructure changes only)
- Weekend/holiday restrictions

## Risk Assessment

### Technical Risks

#### High-Risk Scenarios
1. **Cleanup Failure**: Ephemeral resources not destroyed
   - **Mitigation**: Multiple cleanup mechanisms, monitoring alerts
   
2. **Cost Overrun**: Too many concurrent environments
   - **Mitigation**: Concurrency limits, budget alerts

3. **Test Reliability**: Flaky tests causing false positives
   - **Mitigation**: Retry mechanisms, test isolation

#### Medium-Risk Scenarios
1. **State File Conflicts**: Terraform state corruption
   - **Mitigation**: Separate state files per PR, state locking

2. **Resource Naming Conflicts**: Collisions between environments
   - **Mitigation**: PR-specific naming scheme, validation checks

### Business Risks

#### Budget Impact
- **Current Budget**: £30-40/month
- **Projected Addition**: £40-100/month
- **Total**: £70-140/month
- **Mitigation**: Gradual rollout, strict controls

#### Development Velocity
- **Positive**: Faster feedback on infrastructure changes
- **Negative**: Additional complexity in PR workflow
- **Net Impact**: Positive after initial learning curve

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Create functional test suite structure
- [ ] Implement basic ephemeral deployment workflow
- [ ] Add automatic cleanup mechanisms
- [ ] Test with single infrastructure change

### Phase 2: Integration (Week 3-4)
- [ ] Integrate with existing CI/CD pipeline
- [ ] Add PR status checks and reporting
- [ ] Implement cost monitoring and alerts
- [ ] Test with multiple parallel PRs

### Phase 3: Enhancement (Week 5-6)
- [ ] Add advanced test scenarios
- [ ] Implement performance benchmarking
- [ ] Add test result analytics
- [ ] Optimize resource sizing

### Phase 4: Production Hardening (Week 7-8)
- [ ] Add monitoring and alerting
- [ ] Implement failure recovery procedures
- [ ] Create runbook for troubleshooting
- [ ] Conduct security review

## Success Metrics

### Technical Metrics
- **Test Coverage**: >80% of infrastructure components tested
- **Test Reliability**: <5% false positive rate
- **Deployment Speed**: <30 minutes from PR to test results
- **Cleanup Success**: 100% automatic resource cleanup

### Business Metrics
- **Cost Control**: Stay within £100/month additional budget
- **Developer Productivity**: Reduce production incidents by 50%
- **Deployment Confidence**: Increase infrastructure change velocity
- **Time to Recovery**: Reduce MTTR for infrastructure issues

## Alternative Approaches Considered

### Local Testing with Docker Compose
**Pros**: No cloud costs, fast feedback
**Cons**: Doesn't test Azure-specific features (managed identity, KEDA, etc.)
**Decision**: Insufficient for infrastructure validation

### Shared Staging Environment
**Pros**: Lower cost, simpler setup
**Cons**: Test conflicts, slower feedback, less isolation
**Decision**: Supplement but don't replace ephemeral testing

### Azure Container Instances
**Pros**: Lower cost than Container Apps
**Cons**: Doesn't test actual production platform
**Decision**: Not suitable for infrastructure validation

## Conclusion

The proposed ephemeral testing strategy provides a balanced approach to infrastructure validation that prioritizes safety while maintaining cost control. By implementing selective testing for infrastructure changes only, we can achieve production-like validation without excessive costs.

### Key Success Factors
1. **Selective Implementation**: Only test infrastructure changes
2. **Automatic Cleanup**: Prevent cost overruns through automation
3. **Minimal Sizing**: Use cost-optimized resource configurations
4. **Clear Triggers**: Manual label requirements for cost control

### Next Steps
1. Review and approve this strategy
2. Begin Phase 1 implementation
3. Monitor costs and adjust resource sizing
4. Iterate based on real-world usage patterns

This strategy aligns with the project's security-first, cost-conscious development philosophy while providing the infrastructure validation needed for safe production deployments.

---

**Document Status**: Ready for Review  
**Implementation Priority**: Medium  
**Estimated Effort**: 4-6 weeks (gradual rollout)  
**Budget Impact**: +£40-100/month (monitored and controlled)
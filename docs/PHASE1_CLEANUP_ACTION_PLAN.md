# Phase 1 Cleanup Action Plan
*Generated: September 9, 2025*

## Immediate Success Status
✅ **Phase 1 deployment pipeline now working successfully!**
- All container tests passing
- Service Bus dependencies resolved
- Requirements structure simplified
- CI/CD pipeline stable (Run #17594891358 completed successfully)

## Priority Cleanup Tasks

### 1. Terraform Infrastructure Cleanup (HIGH PRIORITY)
**Estimated Time**: 2-3 hours
**Dependencies**: None
**Risk Level**: Medium

#### Current Issues:
- Multiple terraform files with unclear relationships
- Potential orphaned resources
- Inconsistent naming conventions
- Resource lock removal may have exposed configuration drift

#### Action Items:
```bash
# 1. Audit current terraform state
cd /workspaces/ai-content-farm/infra
terraform state list
terraform plan

# 2. Identify and document all resources
terraform show > current-state.txt

# 3. Check for orphaned resources
az resource list --resource-group ai-content-prod-rg --output table

# 4. Validate terraform configuration
terraform validate
terraform fmt -check
```

#### Expected Outcomes:
- Clean, documented terraform configuration
- No orphaned Azure resources
- Consistent resource naming
- Validated infrastructure state

---

### 2. Azure / JaBLaB Environment Cleanup (HIGH PRIORITY)
**Estimated Time**: 1-2 hours
**Dependencies**: Terraform cleanup
**Risk Level**: Medium-High (Cost implications)

#### Current Issues:
- Unknown resource sprawl after lock removal
- Potential duplicate or unused resources
- Cost optimization opportunities

#### Action Items:
```bash
# 1. Full resource audit
az resource list --output table > azure-resources-audit.txt

# 2. Cost analysis
az consumption usage list --top 10

# 3. Resource group consolidation assessment
az group list --output table

# 4. JaBLaB configuration review
# (Specific to your JaBLaB setup - need access to review configurations)
```

#### Expected Outcomes:
- Documented resource inventory
- Cost optimization plan
- Consolidated resource groups
- Updated JaBLaB configurations

---

### 3. Python Requirements Version Updates (MEDIUM PRIORITY)
**Estimated Time**: 1-2 hours
**Dependencies**: None
**Risk Level**: Low-Medium

#### Current Issues:
- Mixed version constraint formats
- Potentially outdated dependencies
- Security patch opportunities

#### Action Items:
```bash
# 1. Check for outdated packages
pip list --outdated

# 2. Security vulnerability scan
pip-audit

# 3. Update to latest stable versions
# For each container, update requirements.txt with latest stable versions
```

#### Current Versions to Update:
| Package | Current | Latest Stable | Update Action |
|---------|---------|---------------|---------------|
| fastapi | ~=0.116.1 | Check 0.117.x | Test compatibility |
| uvicorn | ~=0.35.0 | Check latest | Update if stable |
| pydantic | ~=2.11.7 | Check 2.12.x | Test breaking changes |
| azure-servicebus | ~=7.12.3 | Check 7.13.x | Update for security |

#### Expected Outcomes:
- All dependencies on latest stable versions
- Consistent version constraint format
- Security vulnerabilities addressed
- Requirements documentation updated

---

### 4. Production Requirements Management (HIGH PRIORITY)
**Estimated Time**: 2-3 hours
**Dependencies**: None
**Risk Level**: High (Security/Performance)

#### Current Issues:
- Development tools included in production containers
- No separation of dev vs prod dependencies
- Potential security and performance impact

#### Recommended Approach: Multi-Stage Docker Build

```dockerfile
# Development stage
FROM python:3.11-slim as development
COPY requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

# Production stage
FROM python:3.11-slim as production
COPY requirements-prod.txt ./
RUN pip install -r requirements-prod.txt --no-cache-dir
# Copy only application code, not dev tools

# Testing stage
FROM development as testing
COPY requirements-test.txt ./
RUN pip install -r requirements-test.txt
```

#### File Structure:
```
containers/{container-name}/
├── requirements-prod.txt     # Core runtime dependencies only
├── requirements-dev.txt      # Development tools (black, mypy, etc.)
├── requirements-test.txt     # Testing dependencies (pytest, etc.)
└── requirements.txt          # Combined for local development
```

#### Implementation Steps:
1. **Separate dependencies** in each container
2. **Update Dockerfiles** for multi-stage builds
3. **Modify CI/CD pipeline** to build both dev and prod images
4. **Test production builds** without dev dependencies
5. **Update deployment scripts** to use production images

#### Expected Outcomes:
- Smaller production container images
- Improved security (no dev tools in production)
- Better performance (fewer dependencies)
- Clear separation of concerns

---

## Implementation Schedule

### Week 1 (Immediate)
- [ ] **Day 1**: Terraform cleanup and audit
- [ ] **Day 2**: Azure resource audit and cost analysis
- [ ] **Day 3**: Begin production requirements separation

### Week 2 (Follow-up)
- [ ] **Day 1**: Complete production requirements implementation
- [ ] **Day 2**: Python version updates and testing
- [ ] **Day 3**: JaBLaB configuration updates

### Week 3 (Validation)
- [ ] **Day 1**: End-to-end testing of all changes
- [ ] **Day 2**: Documentation updates
- [ ] **Day 3**: Final validation and monitoring setup

---

## Risk Mitigation

### High-Risk Items:
1. **Terraform State Changes**: Always backup state before modifications
2. **Production Requirements**: Test thoroughly in staging environment
3. **Azure Resource Cleanup**: Verify dependencies before deletion

### Backup Strategy:
```bash
# Before any changes
terraform state pull > terraform-state-backup-$(date +%Y%m%d).json
az group export --name ai-content-prod-rg > azure-resources-backup-$(date +%Y%m%d).json
```

### Rollback Plan:
- Keep previous container images tagged
- Maintain terraform state backups
- Document all Azure resource dependencies

---

## Success Metrics

### Technical Metrics:
- [ ] All containers build successfully with production requirements
- [ ] Container image sizes reduced by >30%
- [ ] No security vulnerabilities in dependencies
- [ ] Terraform plan shows no unexpected changes

### Operational Metrics:
- [ ] Deployment time improved
- [ ] Azure costs optimized
- [ ] Clear documentation for all processes
- [ ] Automated testing for production builds

---

## Next Immediate Action

**Priority 1**: Start with Terraform cleanup since it's foundational and affects all other Azure resources.

```bash
# First command to run:
cd /workspaces/ai-content-farm/infra && terraform state list
```

This will show us exactly what resources are currently managed by Terraform and help identify any inconsistencies from the resource lock removal.

---
*Action plan by: GitHub Copilot*
*Created: September 9, 2025*
*Status: Ready for implementation*

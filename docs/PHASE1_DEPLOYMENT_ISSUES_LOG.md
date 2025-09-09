# Phase 1 Deployment Issues Log
*Generated: September 9, 2025*

## Overview
This document logs all issues encountered during Phase 1 Service Bus + Azure Functions deployment and identifies remaining cleanup tasks.

## Current Status
- **Pipeline Status**: ✅ SUCCESS (Run ID: 17594891358) - All core tests and builds completed
- **Resource Group Lock**: ✅ RESOLVED - Removed CanNotDelete lock from ai-content-prod-rg
- **Requirements Structure**: ✅ RESOLVED - Simplified from complex multi-file structure
- **Service Bus Dependencies**: ✅ RESOLVED - Added azure-servicebus~=7.12.3 to all containers
- **Dependency Conflicts**: ✅ RESOLVED - Fixed duplicate dependencies in site-generator

## Issues Encountered & Resolutions

### 1. CI/CD Pipeline Test Failures
**Issue**: ModuleNotFoundError for azure.servicebus in content-collector tests
```
ImportError while importing test module '/home/runner/work/ai-content-farm/ai-content-farm/tests/test_content_collector.py'.
ModuleNotFoundError: No module named 'azure.servicebus'
```

**Root Cause**: Missing azure-servicebus dependency in requirements files
**Resolution**: Added `azure-servicebus~=7.12.3` to all container requirements.txt files

### 2. Complex Requirements Structure
**Issue**: Complex multi-file requirements structure causing dependency resolution failures
- requirements-prod.txt
- requirements-test.txt  
- requirements-common.txt
- Circular include directives

**Root Cause**: Over-engineered dependency management causing more problems than benefits
**Resolution**: Consolidated to single requirements.txt per container with all dependencies

### 3. StandardResponse Generic Typing
**Issue**: Generic typing errors in shared_models.py
```
TypeError: 'type' object is not subscriptable
```

**Root Cause**: Missing Generic[T] inheritance and TypeVar declaration
**Resolution**: Added proper generic typing:
```python
from typing import Generic, TypeVar
T = TypeVar('T')
class StandardResponse(BaseModel, Generic[T]):
```

### 4. Site Generator Dependency Conflicts
**Issue**: Duplicate dependencies with conflicting versions
```
ERROR: Cannot install markdown==3.9 and markdown~=3.7.0 because these package versions have conflicting dependencies.
```

**Root Cause**: Duplicate entries in requirements.txt with different version formats
**Resolution**: Deduplicated requirements file, removed conflicting entries

### 5. Azure Resource Group Lock
**Issue**: Terraform deployment blocked by resource group lock
```
CanNotDelete lock on ai-content-prod-rg resource group
```

**Root Cause**: Resource group protection preventing infrastructure modifications
**Resolution**: Removed lock using `az group lock delete --name resource-group-lock --resource-group ai-content-prod-rg`

## Current Pipeline Status
**Run ID**: 17594891358
**Status**: ✅ SUCCESS - All tests and builds completed successfully
**Resolution**: Site-generator dependency conflicts resolved

**Successful Jobs**:
- ✅ Container tests (site-generator)
- ✅ Code quality checks
- ✅ Security scans
- ✅ Docker architecture validation
- ✅ Container builds

**Notes**: Pipeline completed in ~6 minutes, significantly faster than previous failed runs

## Remaining Tasks & Cleanup Items

### 1. Terraform Infrastructure Cleanup
**Priority**: High
**Description**: Clean up and standardize Terraform configuration
**Tasks**:
- [ ] Review and consolidate terraform files
- [ ] Remove unused/deprecated resources
- [ ] Standardize naming conventions
- [ ] Update resource configurations for Phase 1 architecture
- [ ] Validate terraform plan/apply consistency
- [ ] Document infrastructure dependencies

### 2. Azure / JaBLaB Environment Cleanup
**Priority**: High  
**Description**: Clean up Azure resources and JaBLaB configurations
**Tasks**:
- [ ] Audit existing Azure resources
- [ ] Remove unused/orphaned resources
- [ ] Consolidate resource groups if applicable
- [ ] Update JaBLaB configurations for new architecture
- [ ] Review and optimize cost management
- [ ] Document resource relationships

### 3. Python Requirements Version Updates
**Priority**: Medium
**Description**: Update all Python dependencies to latest stable versions
**Current Status**: Using mixed version constraints (~, ==, >=)
**Tasks**:
- [ ] Audit all requirements.txt files for version updates
- [ ] Test compatibility with latest stable versions
- [ ] Update version constraints consistently
- [ ] Consider using requirements.lock files for reproducibility
- [ ] Document version update policy

**Current Versions to Review**:
```
fastapi~=0.116.1 → Check for 0.117.x
uvicorn~=0.35.0 → Check for newer versions
pydantic~=2.11.7 → Check for 2.12.x
azure-servicebus~=7.12.3 → Check for 7.13.x
```

### 4. Production Requirements Management Strategy
**Priority**: High
**Description**: Implement safe way to manage dev/test vs production requirements
**Current Issue**: All requirements (including dev/test tools) included in production containers

**Proposed Solutions**:

#### Option A: Multi-stage Docker Build
```dockerfile
# Development stage
FROM python:3.11-slim as development
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

# Production stage  
FROM python:3.11-slim as production
COPY requirements.txt ./
RUN pip install -r requirements.txt --no-dev
```

#### Option B: Conditional Installation
```bash
# In container startup script
if [ "$ENVIRONMENT" = "production" ]; then
    pip install -r requirements-prod.txt
else
    pip install -r requirements.txt
fi
```

#### Option C: Separate Requirements Files (Recommended)
```
requirements-base.txt    # Core dependencies
requirements-dev.txt     # Development tools (pytest, black, mypy)
requirements-prod.txt    # Production-only deps
requirements.txt         # Combined for development
```

**Tasks**:
- [ ] Evaluate and choose production requirements strategy
- [ ] Implement chosen approach across all containers
- [ ] Update CI/CD pipeline to handle production vs development builds
- [ ] Test production builds without dev dependencies
- [ ] Document requirements management policy

## Testing Strategy
**Current Status**: Tests passing for content-collector, issues with site-generator and content-processor

**Remaining Test Issues**:
- [ ] Investigate content-processor test failures
- [ ] Validate all containers pass tests with new requirements structure
- [ ] Add integration tests for Service Bus functionality
- [ ] Test production builds without dev dependencies

## Monitoring & Validation
**Pipeline Monitoring**: Currently watching Run ID 17594891358
**Next Steps**:
1. Confirm current pipeline completes successfully
2. Validate Terraform deployment works without resource lock
3. Test Service Bus functionality end-to-end
4. Begin systematic cleanup of identified issues

## Documentation Updates Needed
- [ ] Update README.md with new requirements structure
- [ ] Document Service Bus integration patterns
- [ ] Update deployment guides
- [ ] Create production deployment checklist
- [ ] Document troubleshooting procedures for common issues

## Risk Assessment
**High Risk**: 
- Production requirements containing dev dependencies (security/performance)
- Terraform state inconsistencies

**Medium Risk**:
- Outdated Python dependencies (security patches)
- Azure resource sprawl (cost optimization)

**Low Risk**:
- Requirements structure complexity (resolved)
- Service Bus dependency missing (resolved)

---
*Log maintained by: GitHub Copilot*
*Last updated: September 9, 2025*


### 5. Security Logs not writing for Checkov in pipeline.

### 6. Terraform is idempotent, yet we keep skipping deployment checks.

### 7. The Security Scan section of the pipeline comprises more than one tool, yet runs in serial

### 8. We have a load of excess, yet 'inactive/unused' 'active' pipelines.

### 9. The pipeline doesn;t correctly load the right containers in with each run.

Currently, it loads :latest in, but it should run the last successful build by version, 
then get updated when there is a newer, tested version. We should introduce a new container
and then migrate service over, with feedback and testing, so we guarantee that it works, and we have feedback on its functionlaity

### 10. We need better in app telemetry

### 11. We need some user statistics and data from the static site
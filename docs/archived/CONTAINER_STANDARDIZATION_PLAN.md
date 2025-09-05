# Container Standardization Implementation Plan
*September 3, 2025 - Based on Research Findings*

## Overview
Systematic implementation of container standardization with proven libraries and consistent API design, based on completed research phase.

## Research-Based Decisions ✅

### Standard Library Strategy
- **✅ ADOPT**: pydantic-settings (replace custom Config classes)
- **✅ KEEP**: secure_error_handler.py (OWASP compliant, <1hr/year maintenance)
- **✅ ADD**: tenacity (external API retry logic)
- **🔍 RESEARCH**: fastapi-utils vs custom standard_endpoints.py
- **⏳ LATER**: Python 3.12 upgrade (25% performance gain)

### API Standardization Target
```
GET  /health              # Standard health check
GET  /status              # Detailed service status  
GET  /docs                # FastAPI auto-generated docs
POST /process             # Main business logic
GET  /                    # Service info & available endpoints
```

### Container Priority Order (Based on Current Status)
1. **content-collector** - Working, needs API standardization
2. **content-processor** - Broken (404s), fix + standardize
3. **content-generator** - Working, migrate to standard APIs
4. **site-generator** - Working, migrate to standard APIs

## Implementation Phases

### Phase 1: Foundation Enhancement (Day 1)

#### Issue #1: Standard Library - pydantic-settings adoption
**Goal**: Replace custom Config classes with type-safe pydantic-settings
**Scope**: All 4 containers
**Benefit**: Type safety, validation, 50% less config code

**Tasks**:
- [ ] Install pydantic-settings in requirements
- [ ] Create standard config base class in `/libs/`  
- [ ] Update content-collector config (test case)
- [ ] Validate working in Azure deployment
- [ ] Commit and proceed to other containers

#### Issue #2: Standard Library - Add tenacity for reliability  
**Goal**: Add retry logic for external API calls (Reddit, OpenAI)
**Scope**: External API calls across containers
**Benefit**: Much better reliability for external services

**Tasks**:
- [ ] Install tenacity in requirements
- [ ] Add retry decorators to Reddit API calls
- [ ] Add retry decorators to OpenAI API calls  
- [ ] Test with simulated failures
- [ ] Document retry patterns

#### Issue #3: Research - fastapi-utils evaluation
**Goal**: Determine if fastapi-utils can replace our custom standard_endpoints.py
**Scope**: Research task, affects future endpoint development

**Tasks**:
- [ ] Install and test fastapi-utils
- [ ] Compare features vs our standard_endpoints.py
- [ ] Make adoption decision
- [ ] Document findings and recommendation

### Phase 2: Container API Standardization (Days 2-3)

#### Issue #4: content-collector API standardization
**Goal**: Replace `/api/content-womble/*` with standard `/health`, `/status`, `/docs`
**Priority**: HIGH (working container, good test case)

**Tasks**:
- [ ] Update endpoints to standard paths
- [ ] Update tests to expect standard endpoints
- [ ] Deploy to Azure and validate
- [ ] Update documentation
- [ ] Remove old service-specific paths

#### Issue #5: content-processor fix and standardization  
**Goal**: Fix broken container and implement standard APIs
**Priority**: HIGH (currently non-functional)

**Tasks**:
- [ ] Diagnose and fix 404 deployment issues
- [ ] Implement standard API endpoints
- [ ] Add comprehensive health checks
- [ ] Deploy and validate functionality
- [ ] Test processing pipeline

#### Issue #6: content-generator API migration
**Goal**: Migrate from `/api/content-generator/*` to standard endpoints
**Priority**: MEDIUM (working but inconsistent)

**Tasks**:
- [ ] Update endpoint paths to standard format
- [ ] Update any internal service calls
- [ ] Deploy and test functionality
- [ ] Update documentation

#### Issue #7: site-generator API migration
**Goal**: Migrate from `/api/site-generator/*` to standard endpoints  
**Priority**: MEDIUM (working but inconsistent)

**Tasks**:
- [ ] Update endpoint paths to standard format
- [ ] Update any internal service calls
- [ ] Deploy and test functionality
- [ ] Update documentation

### Phase 3: Integration & Validation (Day 3)

#### Issue #8: End-to-end pipeline testing
**Goal**: Validate complete Reddit → articles → website pipeline
**Priority**: HIGH (core business value validation)

**Tasks**:
- [ ] Test Reddit content collection
- [ ] Test content processing/ranking
- [ ] Test content generation  
- [ ] Test site generation and publishing
- [ ] Validate performance and costs
- [ ] Document any issues found

#### Issue #9: Documentation and API contracts
**Goal**: Update all documentation to reflect standardized APIs
**Priority**: MEDIUM (important for future development)

**Tasks**:
- [ ] Update API documentation
- [ ] Update deployment guides
- [ ] Update container README files
- [ ] Create API contract specifications
- [ ] Update agent instructions

## Success Criteria

### Technical
- [ ] All containers respond to `/health`, `/status`, `/docs` endpoints
- [ ] pydantic-settings used for all configuration
- [ ] External API calls have retry logic with tenacity
- [ ] End-to-end pipeline working: Reddit → articles → website
- [ ] All containers deploying successfully to Azure

### Operational
- [ ] Consistent API patterns across all containers  
- [ ] Clear documentation for future development
- [ ] Cost maintained at ~$30-40/month target
- [ ] No security regressions (maintain OWASP compliance)

## Risk Mitigation

### Low Risk Items (Proceed Confidently)
- pydantic-settings adoption (tested and proven)
- tenacity addition (mature library)
- API endpoint standardization (straightforward)

### Medium Risk Items (Test Thoroughly)
- content-processor fixes (currently broken)
- Azure deployment validation
- End-to-end pipeline testing

### Rollback Plan
- Maintain backward compatibility during API migration
- Keep old endpoints until new ones validated
- Commit working changes incrementally
- Use feature flags for major changes

## GitHub Issues Created ✅

### Foundation Issues
- **Issue #376**: [Standard Library: Replace Config with pydantic-settings](https://github.com/Hardcoreprawn/ai-content-farm/issues/376)
- **Issue #377**: [Standard Library: Add tenacity for external API retry logic](https://github.com/Hardcoreprawn/ai-content-farm/issues/377)  
- **Issue #378**: [Research: fastapi-utils vs custom standard_endpoints](https://github.com/Hardcoreprawn/ai-content-farm/issues/378)

### Container Standardization Issues
- **Issue #379**: [content-collector: API standardization](https://github.com/Hardcoreprawn/ai-content-farm/issues/379)
- **Issue #380**: [content-processor: Fix deployment and standardize APIs](https://github.com/Hardcoreprawn/ai-content-farm/issues/380)
- **Issue #381**: [content-generator: Migrate to standard API endpoints](https://github.com/Hardcoreprawn/ai-content-farm/issues/381)
- **Issue #382**: [site-generator: Migrate to standard API endpoints](https://github.com/Hardcoreprawn/ai-content-farm/issues/382)

### Integration Issues
- **Issue #383**: [End-to-end pipeline testing and validation](https://github.com/Hardcoreprawn/ai-content-farm/issues/383)
- **Issue #384**: [Documentation: Update API contracts and deployment guides](https://github.com/Hardcoreprawn/ai-content-farm/issues/384)

---

**Next Action**: Create GitHub issues based on this plan and begin systematic implementation.

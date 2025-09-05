# Content Pipeline Recovery Plan
*September 5, 2025 - Clear Path to Working System*

## 🎯 Current Situation

**What's Working:**
- ✅ Infrastructure: Azure Container Apps, Terraform, CI/CD pipeline
- ✅ Security: All vulnerability scans passing
- ✅ Basic containers: Building and deploying successfully
- ✅ content-processor: Mostly standardized (Phase 3 complete)

**What's Broken:**
- ❌ End-to-end pipeline: No working content flow
- ❌ API inconsistency: Mixed old/new endpoint patterns  
- ❌ Container communication: No clear data flow
- ❌ Security failures: Some Dockerfile security issues

**Root Problems:**
1. **Over-engineering**: 4 containers with unclear responsibilities
2. **Half-finished refactoring**: Mixed API patterns causing confusion
3. **No clear data flow**: Containers don't connect properly
4. **Documentation sprawl**: Too many overlapping documents

## 🚀 Recovery Strategy: "Working First, Perfect Later"

### Phase 1: Get ONE Container Fully Working (Week 1)
**Focus: content-processor as the foundation**

**Goals:**
- Fix remaining test failures (4 tests failing)
- Complete API standardization 
- Demonstrate real content processing capability
- Document the pattern for other containers

**Tasks:**
1. Fix test failures in content-processor
2. Complete security compliance (fix Dockerfile issues)
3. Test end-to-end processing with real content
4. Document the standardized pattern

### Phase 2: Simplify to 3 Working Containers (Week 2)
**Focus: Essential pipeline only**

**New Simple Architecture:**
```
Reddit/Web → content-collector → content-processor → site-generator → Website
```

**Eliminate complexity:**
- Remove content-generator (merge into content-processor)
- Remove unused base containers
- Keep only essential functionality

### Phase 3: Fix Data Flow (Week 3)
**Focus: Container communication**

**Tasks:**
1. Implement blob storage data exchange
2. Test collector → processor → generator flow
3. Verify deployed website updates
4. Add basic monitoring

## 📋 Detailed Implementation Plan

### Phase 1 Tasks (This Week)

#### Day 1: Fix content-processor Tests
```bash
# Fix the 4 failing tests:
1. Add 'uptime' field to root endpoint response
2. Add 'version' field to status endpoint  
3. Fix OpenAPI title to match test expectation
4. Ensure 404 errors include 'error_id' field
```

#### Day 2: Complete Security Compliance
```bash
# Fix Dockerfile security issues
1. Add non-root USER directive to all Dockerfiles
2. Fix any CVE vulnerabilities in base images
3. Ensure all secrets are properly handled
```

#### Day 3: Test Real Processing
```bash
# Verify content-processor works end-to-end
1. Test with real OpenAI integration
2. Verify mock mode works for development
3. Test all processing types (article, analysis, etc.)
```

### Phase 2 Tasks (Next Week)

#### Simplify Container Architecture
```bash
# Remove complexity:
1. Merge content-generator into content-processor
2. Remove unused base containers
3. Update CI/CD to only build 3 containers
4. Update infrastructure accordingly
```

#### Standardize Remaining Containers
```bash
# Apply content-processor pattern to:
1. content-collector: Standardize APIs
2. site-generator: Standardize APIs
3. Ensure consistent response formats
```

### Phase 3 Tasks (Week After)

#### Connect the Pipeline
```bash
# Implement data flow:
1. content-collector saves to blob storage
2. content-processor reads/processes/saves
3. site-generator builds and deploys website
4. Add basic error handling and retries
```

## 🛠️ Technical Standards

### API Standard (Apply to All Containers)
```
GET  /health              # Health check
GET  /status              # Detailed status  
GET  /docs                # Auto-generated docs
POST /process             # Main business logic
GET  /                    # Service info
```

### Response Standard
```json
{
  "status": "success|error",
  "message": "Human readable message",
  "data": { /* actual response data */ },
  "metadata": { /* service metadata */ }
}
```

### Error Standard (OWASP Compliant)
```json
{
  "status": "error",
  "message": "Generic error message",
  "error_id": "uuid-for-tracking",
  "errors": ["specific error details"]
}
```

## 🎯 Success Criteria

### Phase 1 Complete When:
- [ ] All content-processor tests pass (36/36)
- [ ] Security scans pass with no failures
- [ ] Real content processing works end-to-end
- [ ] API documentation is accurate

### Phase 2 Complete When:
- [ ] Only 3 containers in production
- [ ] All containers use consistent API patterns
- [ ] CI/CD builds/deploys successfully
- [ ] Infrastructure costs stay under $40/month

### Phase 3 Complete When:
- [ ] End-to-end pipeline works: Reddit → Website
- [ ] Basic monitoring shows pipeline health
- [ ] Content appears on deployed website
- [ ] Documentation updated to reflect working system

## 📚 Documentation Strategy

**Keep Only 3 Documents:**
1. `README.md` - Current state, how to use
2. `TODO.md` - Next priorities (this plan)  
3. `.github/agent-instructions.md` - AI behavior

**Archive Everything Else:**
- Move all planning docs to `docs/archived/`
- Keep implementation docs only when needed
- Focus on working code over perfect documentation

## 🚨 Anti-Patterns to Avoid

1. **Don't add new features** until basic pipeline works
2. **Don't optimize** until functionality is proven
3. **Don't refactor multiple containers** simultaneously
4. **Don't create new documentation** files
5. **Don't change infrastructure** until containers work

## 💡 Success Principles

1. **Working > Perfect**: Get basic functionality first
2. **Test-Driven**: Fix failing tests before adding features  
3. **Security-First**: All changes must pass security scans
4. **Cost-Conscious**: Keep infrastructure costs low
5. **Simple > Complex**: Reduce moving parts where possible

---

**Next Action**: Start with fixing the 4 failing content-processor tests to establish the pattern for other containers.

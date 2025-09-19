# Live Container Testing & Validation Plan

## 🎯 Objective
Test and validate each container in the production environment to observe behavior and validate the queue automation fix.

## 📋 Testing Sequence

### Phase 1: Container Health & Accessibility ✅
- [x] Content Collector: https://ai-content-prod-collector.whitecliff-6844954b.uksouth.azurecontainerapps.io
- [ ] Content Processor: https://ai-content-prod-processor.whitecliff-6844954b.uksouth.azurecontainerapps.io  
- [ ] Site Generator: https://ai-content-prod-sitegen.whitecliff-6844954b.uksouth.azurecontainerapps.io

### Phase 2: Individual Container Testing
1. **Content Collector**
   - [ ] Health endpoint test
   - [ ] Manual collection trigger  
   - [ ] Verify blob storage write
   - [ ] **KEY**: Confirm queue message sent (new fix)

2. **Content Processor** 
   - [ ] Health endpoint test
   - [ ] Queue message processing capability
   - [ ] KEDA scaling observation
   - [ ] Processing logic validation

3. **Site Generator**
   - [ ] Health endpoint test  
   - [ ] Static site generation capability
   - [ ] Output verification

### Phase 3: End-to-End Flow Testing
- [ ] Trigger collection → Observe queue message → Monitor KEDA scaling → Validate processing → Check site generation
- [ ] Test with empty collection (validates our queue fix)
- [ ] Test with content collection (once content issue resolved)

### Phase 4: Queue Infrastructure Validation
- [ ] Azure Storage Queue message inspection
- [ ] KEDA scaling events monitoring
- [ ] Container logs analysis

## 🔧 Testing Tools & Commands
- Health checks: `curl` requests
- Queue inspection: `az storage message peek`
- Container scaling: `az containerapp show`
- Logs: `az containerapp logs show`

---
**Status**: Ready to begin live testing with all changes committed to GitHub
**Latest Commit**: `a4eff40` - Queue automation fix deployed

# Clean Rebuild & Full Reprocess Plan

## Current Issues
1. Vietnamese/non-English titles in URLs (not translated)
2. Duplicate/legacy article files with wrong formats
3. Mix of old "article-" prefixed files and new date-prefixed files
4. Links not working (filename/URL mismatch)

## Solution: Clean Rebuild + Full Reprocess

### Step 1: Backup Current State (Optional)
```bash
# Download current site for comparison
az storage blob download-batch \
  --account-name aicontentprodstkwakpx \
  --source '$web' \
  --destination ./backup/current-site \
  --auth-mode login
```

### Step 2: Clear Static Site Container
```bash
# Delete ALL files from static site (clean slate)
az storage blob delete-batch \
  --account-name aicontentprodstkwakpx \
  --source '$web' \
  --pattern "articles/*" \
  --auth-mode login

az storage blob delete-batch \
  --account-name aicontentprodstkwakpx \
  --source '$web' \
  --pattern "*.html" \
  --auth-mode login
```

### Step 3: Clear Processed Content (Force Reprocess)
```bash
# Optional: Clear processed content to force full reprocessing
az storage blob delete-batch \
  --account-name aicontentprodstorage \
  --source processed-content \
  --auth-mode login
```

### Step 4: Full Reprocess - Collected Content
This will regenerate ALL articles with:
- ✅ AI-powered metadata generation (Phase 2)
- ✅ English title translation for non-English sources
- ✅ Proper YYYY-MM-DD-slug.html filenames
- ✅ URL/filename consistency (Phase 3)

```bash
# Trigger processor to reprocess ALL collected content
curl -X POST "https://ai-content-prod-processor.whitecliff-6844954b.uksouth.azurecontainerapps.io/process/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "source_container": "collected-content",
    "target_container": "processed-content",
    "force_regenerate": true,
    "limit": null
  }'
```

### Step 5: Regenerate Static Site
```bash
# Trigger site generator to rebuild entire site
curl -X POST "https://ai-content-prod-site-gen.whitecliff-6844954b.uksouth.azurecontainerapps.io/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "source_container": "processed-content",
    "force_rebuild": true
  }'
```

## Benefits

### 1. Scale Testing
- Process 577+ collected items (from pipeline diagnostics)
- Test metadata generation cost at scale
- Verify performance with large batches

### 2. Clean Data
- No legacy "article-" prefixed files
- No duplicate filenames
- All URLs match filenames exactly

### 3. AI Translation Test
- Vietnamese titles → English titles
- Japanese titles → English titles
- All other non-English content translated

### 4. Cost Analysis
Expected costs for full reprocess:
- **Metadata generation**: 577 items × $0.0001 = ~$0.058
- **Article generation**: 577 items × $0.0015 = ~$0.87
- **Total**: ~$0.93 (less than $1!)

### 5. Validation
After reprocess, verify:
```bash
# Check all new articles have proper format
az storage blob list \
  --account-name aicontentprodstkwakpx \
  --container-name '$web' \
  --prefix "articles/" \
  --auth-mode login \
  --query "[].name" -o tsv | grep -E "^articles/[0-9]{4}-[0-9]{2}-[0-9]{2}-"

# Should see ONLY files like:
# articles/2025-10-06-great-article-title.html
# articles/2025-10-05-another-article.html
```

## Execution Plan

### Quick Version (Recommended)
```bash
# 1. Clear static site
make clean-static-site  # or run az commands above

# 2. Clear processed content (force reprocess)
make clean-processed-content

# 3. Trigger full reprocess
make reprocess-all

# 4. Wait for processing (monitor logs)
make monitor-processor

# 5. Regenerate site
make regenerate-site

# 6. Verify results
make verify-site
```

### Manual Version
1. Run Step 2 commands (clear static site)
2. Run Step 3 commands (clear processed content)
3. Trigger processor via API or wait for scheduled run
4. Trigger site generator via API
5. Check results

## Monitoring

### Watch Processing Progress
```bash
# Check processor status
curl https://ai-content-prod-processor.whitecliff-6844954b.uksouth.azurecontainerapps.io/process/status | jq .

# Check site generator status
curl https://ai-content-prod-site-gen.whitecliff-6844954b.uksouth.azurecontainerapps.io/health | jq .

# Monitor logs
az containerapp logs show \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --follow
```

### Expected Timeline
- Clear containers: 2-5 minutes
- Reprocess 577 items: 30-60 minutes (depends on rate limiting)
- Regenerate site: 5-10 minutes
- **Total: ~1 hour for complete rebuild**

## Rollback Plan

If issues occur:
1. Restore from backup (Step 1)
2. Check logs for specific errors
3. Fix issues in code
4. Re-deploy and retry

## Post-Reprocess Validation

### 1. Check Filenames
```bash
# All should be YYYY-MM-DD-slug.html format
az storage blob list \
  --account-name aicontentprodstkwakpx \
  --container-name '$web' \
  --prefix "articles/" \
  --auth-mode login | jq -r '.[].name' | head -20
```

### 2. Verify No Vietnamese in URLs
```bash
# Should return 0 (no non-ASCII filenames)
az storage blob list \
  --account-name aicontentprodstkwakpx \
  --container-name '$web' \
  --prefix "articles/" \
  --auth-mode login | jq -r '.[].name' | grep -P '[^\x00-\x7F]' | wc -l
```

### 3. Test Links
```bash
# Pick random articles and verify they load
curl -I "https://aicontentprodstkwakpx.z33.web.core.windows.net/articles/2025-10-06-some-article.html"
# Should return 200 OK
```

### 4. Check Index Page
Visit: https://aicontentprodstkwakpx.z33.web.core.windows.net/
- All titles should be English
- All links should work (no 404s)
- All article URLs should match YYYY-MM-DD-slug.html format

## Next Steps After Successful Rebuild

1. **Update AGENTS.md** - Document the reprocess capability
2. **Create Makefile targets** - Add convenience commands
3. **Set up monitoring** - Track processing success rate
4. **Document costs** - Record actual costs vs estimates
5. **Schedule regular cleanups** - Prevent future legacy buildup

---

**Ready to execute?** This will give you a clean, properly formatted site with all the new metadata generation working correctly!

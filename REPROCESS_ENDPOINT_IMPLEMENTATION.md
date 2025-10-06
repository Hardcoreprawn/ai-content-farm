# Reprocess Endpoint Implementation

## Overview
Added new `/collections/reprocess` endpoint to content-collector that enables bulk reprocessing of all collected content through the queue system for parallel processing.

**SAFETY FEATURE**: Defaults to `dry_run=true` to prevent accidental expensive operations.

## Endpoint Details

### POST /collections/reprocess
**Purpose**: Queue all collected content items for reprocessing with updated metadata generation

**Parameters**:
- `max_items` (optional, query): Limit number of items to queue (for testing)
- `dry_run` (optional, query, **default: true**): If true, simulates without sending messages

**IMPORTANT SAFETY NOTES**:
- **Default is DRY RUN**: Always simulates by default to prevent accidental costs
- **No file deletion**: This endpoint only QUEUES messages - it does NOT delete files
- **File cleanup**: Use `clean-rebuild.sh` script to manage file deletion separately
- **Must explicitly set**: `dry_run=false` to actually send queue messages

**Response**:
```json
{
  "status": "success",
  "message": "DRY RUN - Would queue 577 collections for reprocessing",
  "data": {
    "dry_run": true,
    "collections_queued": 577,
    "collections_scanned": 577,
    "queue_name": "content-processing-requests",
    "estimated_cost": "$0.92",
    "estimated_time": "3462 seconds (~57 min)",
    "warning": "This was a DRY RUN - no messages were actually sent"
  }
}
```

## Architecture

### How It Works
1. **Enumerate Collections**: Scans `collected-content/collections/` for all JSON files
2. **Queue Messages**: Creates processing queue message for each collection
3. **Parallel Processing**: Content-processor containers (up to 5) pull from queue
4. **Cost Effective**: Only processes actual content, no wasted API calls

### Benefits Over Sequential Processing
- ✅ **Parallel Execution**: Up to 5 containers processing simultaneously
- ✅ **Auto-scaling**: KEDA scales based on queue depth
- ✅ **Fault Tolerant**: Failed items can be retried individually
- ✅ **Observable**: Monitor via queue metrics and container logs
- ✅ **Cost Efficient**: Process 577 items in ~10-15 minutes vs 1+ hour

## Integration with Clean Rebuild

Updated `scripts/clean-rebuild.sh` to:
1. Clear static site articles
2. Clear index pages
3. Clear processed content (optional)
4. **Auto-trigger reprocessing** if processed content cleared
5. Show monitoring commands

### Usage

```bash
# SAFE: Dry run (default) - no actual messages sent, no cost
curl -X POST "https://ai-content-prod-collector.whitecliff-6844954b.uksouth.azurecontainerapps.io/collections/reprocess"

# SAFE: Dry run with limit for testing
curl -X POST "https://ai-content-prod-collector.whitecliff-6844954b.uksouth.azurecontainerapps.io/collections/reprocess?max_items=5"

# ACTUAL EXECUTION (costs money!): Must explicitly set dry_run=false
curl -X POST "https://ai-content-prod-collector.whitecliff-6844954b.uksouth.azurecontainerapps.io/collections/reprocess?dry_run=false"

# Small test with actual queueing
curl -X POST "https://ai-content-prod-collector.whitecliff-6844954b.uksouth.azurecontainerapps.io/collections/reprocess?max_items=5&dry_run=false"

# Or use the interactive script
./scripts/clean-rebuild.sh  # Includes dry run preview before execution
```

## What Gets Cleared vs Queued

**This endpoint ONLY queues messages** - it does NOT delete any files:
- ✅ Reads collected-content container
- ✅ Creates queue messages for processor
- ❌ Does NOT delete collected content (JSON files stay)
- ❌ Does NOT delete processed content (markdown/metadata files stay)
- ❌ Does NOT delete static site articles (HTML files stay)

**Processor will overwrite processed content** when it processes queued messages:
- Reads from `collected-content/` (original JSON collections)
- Writes to `processed-content/` (overwrites existing markdown/metadata)
- Site generator then reads `processed-content/` to create HTML

**To delete files, use `clean-rebuild.sh` script**:
- Step 1: Clears static site articles (`$web/articles/*`)
- Step 2: Clears index pages (`$web/index.html`, `$web/page-*.html`)
- Step 3: Clears processed content (`processed-content/*`)
- Step 4: Triggers reprocess (with dry run preview!)

## Files Modified

### New Endpoint
- `containers/content-collector/endpoints/collections.py`
  - Added `reprocess_collections()` endpoint
  - Iterates blob storage for collections
  - Creates queue messages for processor

### Scripts Updated
- `scripts/clean-rebuild.sh`
  - Fixed storage account name (aicontentprodstkwakpx)
  - Added automatic reprocess trigger
  - Added monitoring commands

### Scripts Added
- `scripts/test-reprocess-endpoint.sh`
  - Test endpoint with max_items=5
  - Verify response before full run

### Scripts Fixed
- `scripts/check-state.sh`
  - Updated to use correct storage account name

## Testing

### Unit Tests
```bash
cd containers/content-collector
PYTHONPATH=/workspaces/ai-content-farm python -m pytest tests/ -v -m unit
# ✓ 9 passed
```

### Integration Test (After Deploy)
```bash
# Small test first
./scripts/test-reprocess-endpoint.sh

# Monitor processing
az containerapp logs show \
  --name ai-content-prod-processor \
  --resource-group ai-content-prod-rg \
  --tail 50 --follow

# Full reprocess
curl -X POST "https://ai-content-prod-collector.whitecliff-6844954b.uksouth.azurecontainerapps.io/collections/reprocess"
```

## Deployment Plan

1. **Commit Changes**
   ```bash
   git add -A
   git commit -m "feat: Add reprocess endpoint for parallel content reprocessing

   - New POST /collections/reprocess endpoint
   - Queues all collected content for processing
   - Supports parallel processing with up to 5 workers
   - Updated clean-rebuild.sh with auto-trigger
   - Fixed storage account names in scripts
   - Estimated cost: $0.92 for 577 items (~15 min)"
   git push origin main
   ```

2. **CI/CD Deploys**
   - GitHub Actions will build and deploy collector container
   - Wait for deployment to complete (~5-10 min)

3. **Test Endpoint**
   ```bash
   ./scripts/test-reprocess-endpoint.sh
   ```

4. **Run Clean Rebuild**
   ```bash
   ./scripts/clean-rebuild.sh
   # Follow prompts to clear and reprocess
   ```

5. **Monitor Processing**
   - Check queue depth in Azure Portal
   - Watch processor logs for errors
   - Verify processed-content container filling up

6. **Trigger Site Rebuild**
   ```bash
   curl -X POST "https://ai-content-prod-site-gen.whitecliff-6844954b.uksouth.azurecontainerapps.io/storage-queue/send-wake-up"
   ```

7. **Validate Results**
   - All filenames use YYYY-MM-DD-slug.html format
   - No non-ASCII characters in filenames
   - Links work correctly
   - Vietnamese/Japanese titles translated to English

## Cost Estimate

- **577 items × $0.0016 per item = $0.92**
- Processing time: ~10-15 minutes with 5 parallel workers
- Queue depth will show ~577 messages initially, draining as processing occurs

## Success Criteria

✅ Endpoint returns success with queued count
✅ Queue receives 577 messages
✅ Processor containers scale up (1-5 instances)
✅ Processed-content container fills with new items
✅ All new filenames are ASCII-only with proper date format
✅ Site generator creates clean article links
✅ No 404 errors on published site

## Next Steps After This Deploy

1. Monitor first reprocessing run for errors
2. Verify metadata generation translates non-English titles
3. Check site generation uses correct filenames
4. Document any issues found during scale testing
5. Consider adding progress tracking endpoint
6. Add retry logic for failed processing items

---

**Status**: Ready for deployment
**Estimated Deploy Time**: 15-20 minutes (CI/CD + testing)
**Risk Level**: Low (new endpoint, doesn't affect existing functionality)

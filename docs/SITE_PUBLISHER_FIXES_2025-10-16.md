# Site Publisher Fixes - October 16, 2025

## Issues Identified

### 1. Build Output Size Limit Too Restrictive (CRITICAL)
**Symptom:** `Build output too large: 120.1 MB`

**Root Cause:** The security validation in `security.py` had a hardcoded 100 MB limit that was too restrictive for sites with 4,000+ articles.

**Impact:** 
- Deployment fails validation before any files are uploaded
- Triggers unnecessary rollback operation
- Site remains unchanged, wasting compute resources

**Fix:** Increased limit from 100 MB to 200 MB in `containers/site-publisher/security.py`:
```python
max_size = 200 * 1024 * 1024  # 200 MB (increased from 100 MB)
```

### 2. Validation Happens Too Late in Pipeline
**Symptom:** Deployment attempts to upload files before validation completes

**Root Cause:** The `deploy_to_web_container()` function validates Hugo output internally, but this happens AFTER backup completes, wasting 60+ seconds.

**Impact:**
- Unnecessary backup operations when validation will fail
- Confusing logs showing successful backup followed by deployment failure
- Wasted compute time and Azure Storage API calls

**Fix:** Added early validation in `site_builder.py` before deployment:
```python
# Validate before attempting deployment
from security import validate_hugo_output
validation = validate_hugo_output(public_dir)
if not validation.is_valid:
    logger.error(f"Hugo output validation failed: {validation.errors}")
    return DeploymentResult(
        files_uploaded=0,
        duration_seconds=(datetime.now() - start_time).total_seconds(),
        errors=all_errors + validation.errors,
    )
```

### 3. Shutdown Errors During Long-Running Operations
**Symptom:** Cryptic errors logged during container shutdown:
```
AssertionError in site-publisher (e23fadb3...)
ValueError in site-publisher (fc695ece...)
ValueError in site-publisher (63564d40...)
```

**Root Cause:** Container receives SIGTERM shutdown signal while backup/rollback operations are still running (60+ seconds each for 2,166 files).

**Impact:**
- Incomplete operations when container is forcefully terminated
- Confusing error messages that don't indicate the actual problem
- Potential data inconsistency if operations are interrupted mid-stream

**Fix:** Added graceful cancellation handling in `hugo_builder.py`:
```python
except asyncio.CancelledError:
    # Gracefully handle shutdown during backup/upload/rollback
    logger.warning(f"Operation cancelled during shutdown after {completed}/{total} files")
    raise  # Re-raise to propagate cancellation
```

Also added progress logging every 500 files to track long-running operations.

## Files Modified

1. **containers/site-publisher/security.py**
   - Increased max build output size from 100 MB to 200 MB
   - Updated error message to include max size for clarity

2. **containers/site-publisher/site_builder.py**
   - Added early validation before deployment
   - Prevents wasted backup operations when validation will fail

3. **containers/site-publisher/hugo_builder.py**
   - Added `asyncio.CancelledError` handling in backup, deployment, and rollback operations
   - Added progress logging every 500 files for long-running operations
   - Better tracking of interrupted operations during shutdown

## Testing Recommendations

### Manual Testing
```bash
# Test with current site (4,000+ articles, ~120 MB output)
az containerapp logs tail \
  --name ai-content-prod-site-publisher \
  --resource-group ai-content-prod-rg \
  --follow

# Trigger a build by adding message to queue
# Should now succeed without "Build output too large" error
```

### Validation Checks
- [ ] Build completes successfully with 4,000+ articles
- [ ] No "Build output too large" error appears
- [ ] Validation happens before backup (check log timestamps)
- [ ] No cryptic errors during graceful shutdown
- [ ] Progress logging appears every 500 files during long operations

## Performance Impact

**Before:**
- Backup: ~60-70 seconds for 2,166 files
- Validation: ~1 second (but happens too late)
- Rollback: ~60-70 seconds for 2,166 files
- Total wasted time on failed build: ~130 seconds

**After:**
- Validation: ~1 second (happens early)
- No backup/rollback when validation fails
- Total time on validation failure: ~1 second
- **Time saved per failed build: ~129 seconds**

## Related Issues

These fixes address the deployment failures seen in production where:
1. Hugo successfully builds 4,017 files (120.1 MB)
2. Security validation rejects output as "too large"
3. Unnecessary backup and rollback operations execute
4. Container shutdown interrupts long-running rollback
5. Cryptic errors appear in logs during shutdown

## Future Improvements

1. **Configurable Size Limit**: Move max size to environment variable in `config.py`
   ```python
   max_build_output_mb: int = 200  # Configurable via MAX_BUILD_OUTPUT_MB env var
   ```

2. **Progress Tracking**: Add structured progress events for KEDA scaling decisions

3. **Partial Upload Resume**: Implement checkpoint/resume for interrupted operations

4. **Parallel Uploads**: Use `asyncio.gather()` with semaphore for faster deployment
   - Current: Sequential upload of 4,000+ files
   - Potential: 10-20 concurrent uploads with rate limiting

## Deployment Notes

These changes are **backward compatible** and require no infrastructure changes:
- No Terraform updates needed
- No environment variable changes required
- No breaking API changes
- Existing tests continue to pass

Deploy via standard CI/CD pipeline:
```bash
git checkout -b fix/site-publisher-validation
git add containers/site-publisher/
git commit -m "Fix site-publisher validation and shutdown handling"
git push origin fix/site-publisher-validation
# Create PR, wait for CI/CD, merge to main
```

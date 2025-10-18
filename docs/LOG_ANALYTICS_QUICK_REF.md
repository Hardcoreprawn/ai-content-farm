# Log Analytics Setup - Quick Reference

## Problem
No telemetry data in Log Analytics despite infrastructure being set up.

## Root Cause
Missing `azure-monitor-opentelemetry` dependency in container requirements.

## Solution Status
✅ **FIXED** - Changes ready for deployment

## Changes Made
1. ✅ Added `azure-monitor-opentelemetry~=1.6.4` to all 4 container requirements
2. ✅ Enhanced error logging in monitoring module
3. ✅ Created verification script

## Files Modified
```
containers/content-collector/requirements.txt
containers/content-processor/requirements.txt
containers/markdown-generator/requirements.txt
containers/site-publisher/requirements.txt
libs/monitoring/appinsights.py
scripts/verify-telemetry.sh (new)
```

## Next Steps
```bash
# Push changes to trigger CI/CD rebuild
git add -A
git commit -m "fix(telemetry): Add missing azure-monitor-opentelemetry dependency"
git push origin main

# After deployment (2-3 min), verify:
scripts/verify-telemetry.sh
```

## Expected Results
- ✅ Container logs show: "Application Insights configured..."
- ✅ Data appears in Log Analytics within 2-5 minutes
- ✅ Custom events, traces, and exceptions visible
- ✅ Can query with KQL

## Key Files
- **Analysis**: `docs/LOG_ANALYTICS_ISSUES.md`
- **Deployment Guide**: `docs/TELEMETRY_FIX_DEPLOYMENT.md`
- **Verification Script**: `scripts/verify-telemetry.sh`

## Timeline
Push → 5 min rebuild → 3 min startup → 2 min ingestion = **~10 min total**

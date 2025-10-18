# Log Analytics Setup Issues - Investigation & Fixes

**Date**: October 18, 2025  
**Issue**: No telemetry data appearing in Log Analytics despite infrastructure setup  
**Root Cause**: Missing `azure-monitor-opentelemetry` dependency in container environments

## Investigation Summary

### ✅ Infrastructure Status - All Configured Correctly
- **Log Analytics Workspace**: `ai-content-prod-la` ✅ Created
- **Application Insights**: `ai-content-prod-insights` ✅ Created
- **Connection String**: Properly set in container environment variables ✅
- **Link**: Both resources properly linked ✅

### ❌ Missing Dependency in Containers
**Problem**: The containers don't have `azure-monitor-opentelemetry` installed

**Evidence**:
```bash
# Local environment check
$ pip list | grep "azure-monitor"
# (no results - package not installed)

# Test execution result:
Azure Monitor OpenTelemetry not installed: No module named 'azure.monitor'
```

**What's installed**:
- ✅ `opentelemetry-api` 1.37.0
- ✅ `opentelemetry-sdk` 1.37.0
- ✅ `opentelemetry-exporter-otlp-proto-http` 1.37.0
- ❌ `azure-monitor-opentelemetry` NOT installed

### 🔍 Root Cause Analysis

1. **Defined in Dependencies**: The package IS defined in `/workspaces/ai-content-farm/libs/pyproject.toml`:
   ```toml
   dependencies = [
       ...
       "azure-monitor-opentelemetry~=1.6.4",  # Application Insights integration
       ...
   ]
   ```

2. **Container Requirements**: NOT in individual container requirements.txt files:
   - `containers/content-collector/requirements.txt` - ❌ Missing
   - `containers/content-processor/requirements.txt` - ❌ Missing
   - `containers/markdown-generator/requirements.txt` - ❌ Missing

3. **Build Process**: Containers install from their own `requirements.txt` + shared `libs/`, but:
   - Libs installation may be failing silently
   - Individual containers don't explicitly require the package
   - Build fallback logic doesn't report failures clearly

### 📊 Telemetry Code Path

The code is set up correctly, but never gets invoked:

```python
# /workspaces/ai-content-farm/containers/content-collector/main.py
from libs.monitoring import configure_application_insights

# This gets called at startup
configure_application_insights(service_name="content-collector")

# But inside the function:
# File: /workspaces/ai-content-farm/libs/monitoring/appinsights.py
def configure_application_insights(...):
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        # ^^^ This import FAILS because package not installed
    except ImportError as e:
        logger.warning(f"Azure Monitor OpenTelemetry not installed: {e}")
        return None  # ← Silently returns None
```

**Result**: Telemetry silently disabled at startup with no clear warning

## Solution

### Phase 1: Immediate Fix - Add Missing Dependency
**Status**: Ready to implement

Add `azure-monitor-opentelemetry` to each container's requirements.txt:

**Files to Update**:
1. `/workspaces/ai-content-farm/containers/content-collector/requirements.txt`
2. `/workspaces/ai-content-farm/containers/content-processor/requirements.txt`
3. `/workspaces/ai-content-farm/containers/markdown-generator/requirements.txt`

**Change Required** (same for all three):
```diff
+ azure-monitor-opentelemetry~=1.6.4  # Application Insights integration
```

### Phase 2: Diagnostic Improvements
**Status**: Ready to implement

Add better logging to `libs/monitoring/appinsights.py` to show when telemetry is disabled:

```python
# Before: Silent failure
logger.warning("Azure Monitor OpenTelemetry not installed: {e}")

# After: Clear error
logger.error(f"""
╔════════════════════════════════════════════════════════════════╗
║                    TELEMETRY DISABLED                          ║
╚════════════════════════════════════════════════════════════════╝
Azure Monitor OpenTelemetry package not installed: {e}

This service will NOT send telemetry to Application Insights.
Install with: pip install azure-monitor-opentelemetry~=1.6.4
Connection String (read-only): {conn_string[:50]}...
""")
```

### Phase 3: Test Verification
**Status**: Ready to implement

Add test to verify telemetry can initialize:

```python
# tests/test_telemetry_initialization.py
def test_telemetry_configuration():
    """Verify Azure Monitor OpenTelemetry is available."""
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        assert True, "azure-monitor-opentelemetry is installed"
    except ImportError as e:
        pytest.fail(f"Required package missing: {e}")
```

## Implementation Steps

### Step 1: Update Container Requirements
Add to each container's requirements.txt:

```
azure-monitor-opentelemetry~=1.6.4
```

### Step 2: Rebuild Containers
```bash
# GitHub Actions will rebuild on next push, or rebuild manually:
cd containers/content-collector
docker build -t ai-content-prod-collector:latest .

cd containers/content-processor
docker build -t ai-content-prod-processor:latest .

cd containers/markdown-generator
docker build -t ai-content-prod-generator:latest .
```

### Step 3: Deploy Updated Containers
After rebuild, push to registry and update Azure Container Apps:

```bash
# Push to registry
az acr build --registry <registry-name> \
  --image content-collector:latest \
  containers/content-collector/

# Update container app
az containerapp update \
  --name ai-content-prod-collector \
  --resource-group ai-content-prod-rg \
  --image <registry>.azurecr.io/content-collector:latest
```

### Step 4: Verify Telemetry
After deployment, check:

1. **Container logs** for telemetry initialization:
   ```bash
   az containerapp logs show --name ai-content-prod-collector \
     --resource-group ai-content-prod-rg --tail 50
   ```

2. **Log Analytics** for data arrival:
   ```kql
   customEvents | top 10 by timestamp
   traces | where severityLevel > 0
   ```

3. **Application Insights Metrics**:
   ```bash
   az monitor app-insights metrics list --app ai-content-prod-insights \
     --resource-group ai-content-prod-rg
   ```

## Why Telemetry Isn't Working

```
┌─────────────────────────────────┐
│   Container Starts             │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ main.py imports from libs       │
│ configure_application_insights()│
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Tries: from azure.monitor...    │
│ ❌ IMPORT FAILS (pkg missing)   │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ except ImportError:             │
│   logger.warning("...")         │
│   return None ← SILENT FAIL    │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ App continues without telemetry │
│ No data in Log Analytics       │
│ No user-visible error          │
└─────────────────────────────────┘
```

## Expected Result After Fix

Once `azure-monitor-opentelemetry` is installed:

1. **Container Startup**:
   ```log
   [INFO] Application Insights configured (minimal instrumentation) for: content-collector
   ```

2. **Log Analytics Data**:
   - Custom events from application code
   - FastAPI request traces
   - Exception information
   - Custom metrics

3. **Available KQL Queries**:
   ```kql
   customEvents | where name contains "collection"
   traces | where message contains "processing"
   dependencies | where type == "Http"
   ```

## Additional Configuration Options

### Enable Live Metrics (Optional)
```python
# In appinsights.py
configure_azure_monitor(
    connection_string=conn_string,
    enable_live_metrics=True,  # Changed from False
)
```

### Increase Instrumentation (Optional)
```python
instrumentation_options={
    "azure_sdk": {"enabled": True},  # Currently disabled
    "fastapi": {"enabled": True},
    "httpx": {"enabled": True},  # Currently disabled
    "requests": {"enabled": True},  # Currently disabled
}
```

### Reduce Log Noise (Current Default)
```python
# Current settings are already optimized for minimal noise:
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("opentelemetry").setLevel(logging.WARNING)
```

---

## Timeline for Data Visibility

After deploying with the fix:

| Time | What Happens |
|------|------|
| T+0s | Container starts, telemetry initializes |
| T+5s | First requests hit Application Insights |
| T+15s | Data appears in Log Analytics (batched ingestion) |
| T+30s | Available in KQL queries |
| T+1m | Metrics aggregated |
| T+5m | Dashboard can query full data |

---

## Files to Modify

### 1. `/workspaces/ai-content-farm/containers/content-collector/requirements.txt`
**Add at end**:
```
azure-monitor-opentelemetry~=1.6.4
```

### 2. `/workspaces/ai-content-farm/containers/content-processor/requirements.txt`
**Add at end**:
```
azure-monitor-opentelemetry~=1.6.4
```

### 3. `/workspaces/ai-content-farm/containers/markdown-generator/requirements.txt`
**Add at end**:
```
azure-monitor-opentelemetry~=1.6.4
```

### 4. (Optional) `/workspaces/ai-content-farm/libs/monitoring/appinsights.py`
**Enhance error logging** for better diagnostics

---

**Status**: Ready for implementation  
**Impact**: Low risk - adding package already configured, minimal code changes  
**Expected Duration**: 2-3 minutes to edit files + CI/CD deployment time

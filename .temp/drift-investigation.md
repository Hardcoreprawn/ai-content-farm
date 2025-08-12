# Infrastructure Drift Debugging - August 12, 2025

## Current Status
After deploying our infrastructure optimizations in runs #93 and #94, we're still seeing identical drift patterns, which suggests our fixes aren't working as expected.

## Observed Drift (Both Runs)
```
# Key Vault Secrets - still adding content_type and tags
+ content_type = "function-key"
+ "Environment" = "staging"
+ "ManagedBy" = "terraform"  
+ "Purpose" = "auth"

# Function App - still adding Application Insights settings
+ "APPINSIGHTS_INSTRUMENTATIONKEY" = (sensitive)
+ "APPLICATIONINSIGHTS_CONNECTION_STRING" = (sensitive)
+ "AzureWebJobsStorage" = (sensitive)

# Storage Account - still adding network_rules
+ network_rules { ... }
```

## Root Cause Analysis

### Issue 1: App Settings Not Applied
The fact that Application Insights settings show as additions suggests they're either:
- Not actually in the deployed configuration
- Stored differently in Azure than expected
- Being overwritten by Azure after deployment

### Issue 2: Lifecycle Rules Not Effective  
Our lifecycle rules are targeting properties that aren't the actual drift sources.

### Issue 3: State vs Reality Mismatch
Terraform state might not reflect what's actually deployed in Azure.

## Next Steps
1. **Verify actual deployed configuration** - Check what Azure actually has
2. **Simplify approach** - Remove complex lifecycle rules and focus on explicit definitions
3. **Test incremental changes** - One resource type at a time

## Hypothesis
The issue might be that Azure is **overwriting** our explicit settings after deployment, or there's a **timing issue** where settings get reset during the function deployment process.

---
*Investigation in progress*

# Scheduler Infrastructure Removal Plan

## Analysis Complete ✅

After thorough analysis of the codebase, the scheduler infrastructure in `infra/scheduler.tf` is **NOT being used** by the current application:

### Evidence:
- ❌ No `azurerm_logic_app` resources in current Terraform (Logic App was removed)
- ❌ Storage tables (`topicconfigurations`, `executionhistory`, `sourceanalytics`) not referenced in any container code
- ❌ Storage containers (`scheduler_logs`, `analytics_cache`) not referenced in any container code  
- ❌ No environment variables in Container Apps reference scheduler resources
- ✅ Only referenced in standalone scripts and documentation

### Security Impact:
- Storage tables and containers are creating unnecessary security alerts
- Resources consume cost and create maintenance overhead
- Violating principle of least privilege by maintaining unused resources

## Recommendation: REMOVE

The `infra/scheduler.tf` file should be removed entirely as it contains only orphaned resources.

### Before Removal:
1. Confirm no external scripts or jobs are using the storage tables
2. Backup any existing data if needed (tables appear to be empty configuration templates)
3. Update any documentation references

### Files to Update:
- Remove: `infra/scheduler.tf` 
- Update: `infra/outputs.tf` (remove scheduler outputs)
- Update documentation to reflect simplified architecture

This will resolve security alerts #146-151 by removing the unused storage resources entirely.

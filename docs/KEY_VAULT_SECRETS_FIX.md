# Key Vault Secrets Churn Fix - Summary

## Problem
Key Vault secrets were being updated on every Terraform run due to changing expiration dates caused by `timeadd(timestamp(), "8760h")`. The `timestamp()` function generates a new value on each run, causing unnecessary updates.

## Solution
Added `expiration_date` to the `ignore_changes` lifecycle rule for all Key Vault secrets.

## Changes Made

### Secrets with existing lifecycle rules (updated):
- `azurerm_key_vault_secret.reddit_client_id`
- `azurerm_key_vault_secret.reddit_client_secret` 
- `azurerm_key_vault_secret.reddit_user_agent`
- `azurerm_key_vault_secret.infracost_api_key`

**Before:**
```terraform
lifecycle {
  ignore_changes = [not_before_date, value]
}
```

**After:**
```terraform
lifecycle {
  ignore_changes = [not_before_date, value, expiration_date]
}
```

### Secrets without lifecycle rules (added):
- `azurerm_key_vault_secret.openai_endpoint`
- `azurerm_key_vault_secret.openai_chat_model`
- `azurerm_key_vault_secret.openai_embedding_model`

**Added:**
```terraform
# Prevent expiration date churn
lifecycle {
  ignore_changes = [expiration_date]
}
```

## Result
- **Before:** Plan showed "3 to add, 6 to change, 0 to destroy"
- **After:** Plan shows "3 to add, 0 to change, 0 to destroy"
- Eliminated unnecessary secret updates on every Terraform run
- Secrets still maintain their 1-year expiration policy, but don't update unless manually changed

## Benefits
1. **Reduced churn** - No more unnecessary updates to Key Vault secrets
2. **Cleaner deployments** - Terraform plans focus on actual infrastructure changes
3. **Faster execution** - Fewer resources to update
4. **Better change tracking** - Real changes are easier to spot without noise

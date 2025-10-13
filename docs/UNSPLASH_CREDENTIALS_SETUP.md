# Unsplash API Credentials Setup

**Date**: October 13, 2025  
**Status**: Infrastructure configured, ready for implementation

---

## Overview

Configured Unsplash API credentials to enable stock image fetching for article generation. Following the established pattern of syncing secrets from the core Key Vault to the production Key Vault.

---

## Infrastructure Changes

### 1. Data Sources (`infra/data_sources.tf`)

Added three data sources to read Unsplash credentials from core Key Vault:

```terraform
data "azurerm_key_vault_secret" "core_unsplash_access_key" {
  name         = "unsplash-access-key"
  key_vault_id = data.azurerm_key_vault.core.id
}

data "azurerm_key_vault_secret" "core_unsplash_application_id" {
  name         = "unsplash-application-id"
  key_vault_id = data.azurerm_key_vault.core.id
}

data "azurerm_key_vault_secret" "core_unsplash_secret_key" {
  name         = "unsplash-secret-key"
  key_vault_id = data.azurerm_key_vault.core.id
}
```

### 2. Key Vault Secrets (`infra/key_vault.tf`)

Added three secrets to production Key Vault, synced from core:

- `unsplash-access-key`: Primary API access key (Client-ID)
- `unsplash-application-id`: Application identifier
- `unsplash-secret-key`: Secret key for OAuth flows (if needed)

All follow the same pattern as Reddit credentials:
- Auto-sync from core Key Vault
- No expiration (external API credential)
- Tagged with `SyncSource = "ai-content-farm-core-kv"`

### 3. Markdown Generator Container App (`infra/container_app_markdown_generator.tf`)

Added three secrets to container app:

```terraform
secret {
  name  = "unsplash-access-key"
  value = azurerm_key_vault_secret.unsplash_access_key.value
}

secret {
  name  = "unsplash-application-id"
  value = azurerm_key_vault_secret.unsplash_application_id.value
}

secret {
  name  = "unsplash-secret-key"
  value = azurerm_key_vault_secret.unsplash_secret_key.value
}
```

And three environment variables:

```terraform
env {
  name        = "UNSPLASH_ACCESS_KEY"
  secret_name = "unsplash-access-key"
}

env {
  name        = "UNSPLASH_APPLICATION_ID"
  secret_name = "unsplash-application-id"
}

env {
  name        = "UNSPLASH_SECRET_KEY"
  secret_name = "unsplash-secret-key"
}
```

### 4. Variables Cleanup (`infra/variables.tf`)

Removed unused `unsplash_access_key` variable since we're syncing from core Key Vault.

---

## Credential Usage

### For Basic API Calls (Recommended)

Use the **Access Key** with Client-ID authentication:

```python
import os

access_key = os.getenv("UNSPLASH_ACCESS_KEY")

headers = {
    "Authorization": f"Client-ID {access_key}"
}

# Make API request
async with aiohttp.ClientSession() as session:
    async with session.get(
        "https://api.unsplash.com/search/photos",
        params={"query": "technology"},
        headers=headers
    ) as resp:
        data = await resp.json()
```

### For OAuth Flows (If Needed)

Use **Application ID** and **Secret Key** for user authentication flows. Not typically needed for server-side image fetching.

---

## Security & Compliance

### PEP 8 Standards
- Environment variable names use UPPER_SNAKE_CASE
- Secret names use kebab-case (Azure convention)

### Security Best Practices
- ✅ Secrets stored in Key Vault, not in code
- ✅ Auto-synced from core Key Vault (single source of truth)
- ✅ Secrets injected as environment variables at runtime
- ✅ No hardcoded credentials in Terraform
- ✅ Follows established pattern (Reddit credentials)

### Cost Optimization
- **Unsplash Free Tier**: 50 requests/hour
- **Expected Usage**: 10-20 articles/day = 10-20 requests/day
- **Cost Impact**: $0 (well within free tier limits)

---

## Deployment

### Prerequisites
Ensure all three secrets exist in core Key Vault:
```bash
az keyvault secret show --vault-name "ai-content-farm-core-kv" --name "unsplash-access-key"
az keyvault secret show --vault-name "ai-content-farm-core-kv" --name "unsplash-application-id"
az keyvault secret show --vault-name "ai-content-farm-core-kv" --name "unsplash-secret-key"
```

### Terraform Apply
The changes will be deployed automatically via CI/CD when merged to `main`:

1. Terraform reads secrets from core Key Vault
2. Copies them to production Key Vault
3. Injects them into markdown-generator container app
4. Environment variables available at runtime

---

## Next Steps

1. **Implement Image Service** (`containers/markdown-generator/services/image_service.py`)
   - Create `StockImageService` class
   - Use `UNSPLASH_ACCESS_KEY` for API calls
   - Implement image search and download methods

2. **Update Markdown Generator**
   - Integrate `StockImageService` into article generation
   - Add image URLs to frontmatter
   - Handle fallback when no images found

3. **Update Site Templates**
   - Add hero image display in article pages
   - Add thumbnail display in index/list pages
   - Include proper attribution links

---

## Testing

### Local Testing
```bash
# Check environment variables in container
az containerapp exec \
  --name "ai-content-prod-markdown-gen" \
  --resource-group "ai-content-prod-rg" \
  --command "env | grep UNSPLASH"
```

### Integration Testing
```python
# Test image service with real credentials
import os
from services.image_service import StockImageService

access_key = os.getenv("UNSPLASH_ACCESS_KEY")
service = StockImageService(access_key)

result = await service.search_image("artificial intelligence")
print(f"Found image: {result['url_regular']}")
```

---

## References

- **Implementation Plan**: `/docs/STOCK_IMAGES_IMPLEMENTATION.md`
- **Unsplash API Docs**: https://unsplash.com/documentation
- **Core Key Vault**: `ai-content-farm-core-kv` (not managed by Terraform)
- **Prod Key Vault**: `aicontentprodkvkwakpx` (managed by Terraform)

---

_Last updated: October 13, 2025 - Initial infrastructure setup complete_

# Azure Resource Naming Standards

This document defines the naming conventions for all Azure resources in the AI Content Farm project to ensure consistency, readability, and manageability across environments.

## Base Naming Pattern

All resources follow this pattern:
```
ai-content-{environment}-{resource-type}-{suffix}
```

## Environment Abbreviations

| Environment | Abbreviation | Example Prefix |
|-------------|-------------|----------------|
| **Production** | `prod` | `ai-content-prod` |
| **Development** | `dev` | `ai-content-dev` |
| **Ephemeral/PR** | `pr{number}` | `ai-content-pr123` |

## Resource Type Abbreviations

| Azure Resource | Abbreviation | Pattern | Example |
|---------------|-------------|---------|---------|
| **Resource Group** | `rg` | `{prefix}-rg` | `ai-content-prod-rg` |
| **Key Vault** | `kv` | `{prefix-no-hyphens}kv{random}` | `aicontentprodkv8x4k2m` |
| **Storage Account** | `st` | `{prefix-no-hyphens}st{random}` | `aicontentprodst8x4k2m` |
| **Storage Container** | `container` | `{service-name}` | `content-topics` |
| **Container Registry** | `acr` | `{prefix-no-hyphens}acr{random}` | `aicontentprodacr8x4k2m` |
| **Container Instance** | `aci` | `{prefix}-{service}-aci` | `ai-content-prod-collector-aci` |
| **Log Analytics** | `la` | `{prefix}-la` | `ai-content-prod-la` |

## Naming Rules by Resource Type

### 1. Resource Groups
```
ai-content-{environment}-rg
```
- **Production**: `ai-content-prod-rg`
- **Development**: `ai-content-dev-rg`
- **PR Environment**: `ai-content-pr123-rg`

### 2. Key Vault
```
{prefix-no-hyphens}kv{6-char-random}
```
- Remove all hyphens from prefix
- Add 6-character random suffix for uniqueness
- **Production**: `aicontentprodkv8x4k2m`
- **Development**: `aicontentdevkv7y3n1p`

### 3. Storage Account
```
{prefix-no-hyphens}st{6-char-random}
```
- Remove all hyphens from prefix
- Use 'st' for storage
- Add 6-character random suffix
- **Production**: `aicontentprodst8x4k2m`
- **Development**: `aicontentdevst7y3n1p`

### 4. Storage Containers
```
{service-purpose}
```
- Use kebab-case for container names
- Be descriptive about purpose
- **Examples**: 
  - `content-topics` (for processed content)
  - `raw-data` (for unprocessed data)
  - `enriched-content` (for AI-enhanced content)

### 5. Container Services (Future)
```
{prefix}-{service-name}-{resource-type}
```
- **Container Registry**: `ai-content-prod-acr`
- **Container Instances**: 
  - `ai-content-prod-collector-aci`
  - `ai-content-prod-enricher-aci`
  - `ai-content-prod-processor-aci`
  - `ai-content-prod-ranker-aci`
  - `ai-content-prod-scheduler-aci`
  - `ai-content-prod-ssg-aci`

## Environment-Specific Examples

### Production Environment
```bash
# Resource Group
ai-content-prod-rg

# Key Vault
aicontentprodkv8x4k2m

# Storage Account  
aicontentprodst8x4k2m

# Storage Containers
content-topics
raw-data
enriched-content

# Future Container Services
ai-content-prod-acr              # Container Registry
ai-content-prod-collector-aci     # Content Collector Container
ai-content-prod-enricher-aci      # Content Enricher Container
```

### Development Environment
```bash
# Resource Group
ai-content-dev-rg

# Key Vault
aicontentdevkv7y3n1p

# Storage Account
aicontentdevst7y3n1p

# Storage Containers
content-topics
raw-data
enriched-content
```

### Ephemeral PR Environment (PR #123)
```bash
# Resource Group
ai-content-pr123-rg

# Key Vault
aicontentpr123kv9m2x5k

# Storage Account
aicontentpr123st9m2x5k

# Storage Containers
content-topics
raw-data
```

## Terraform Implementation

### Variables
```hcl
locals {
  # Environment-based prefix
  resource_prefix = "ai-content-${var.environment}"
  
  # Clean prefix for resources that don't allow hyphens
  clean_prefix = replace(local.resource_prefix, "-", "")
  
  # Random suffix for uniqueness
  suffix = random_string.suffix.result
}
```

### Resource Naming Examples
```hcl
# Resource Group
resource "azurerm_resource_group" "main" {
  name = "${local.resource_prefix}-rg"
}

# Key Vault (no hyphens allowed)
resource "azurerm_key_vault" "main" {
  name = "${local.clean_prefix}kv${local.suffix}"
}

# Storage Account (no hyphens allowed)
resource "azurerm_storage_account" "main" {
  name = "${local.clean_prefix}st${local.suffix}"
}

# Storage Container
resource "azurerm_storage_container" "topics" {
  name = "content-topics"
}
```

## GitHub Workflow Integration

### Workflow References
Update workflows to use consistent naming:

```yaml
# Get Resource Group name
RESOURCE_GROUP_NAME="ai-content-${ENVIRONMENT}-rg"

# Get Key Vault name pattern
KEYVAULT_PATTERN="${CLEAN_PREFIX}kv*"

# Get Storage Account name pattern  
STORAGE_PATTERN="${CLEAN_PREFIX}st*"
```

## Benefits of This Standard

1. **Consistency**: All resources follow the same pattern
2. **Environment Clarity**: Easy to identify environment from name
3. **Service Identification**: Clear service purpose in container names
4. **Azure Compliance**: Follows Azure naming restrictions
5. **Automation Friendly**: Predictable patterns for scripts
6. **Cost Tracking**: Easy to group by environment/project
7. **Security**: Clear separation between environments

## Migration Notes

When migrating existing resources:
1. Update Terraform configurations to use new naming
2. Plan the migration during low-usage periods
3. Update all workflow references
4. Verify Key Vault secret access after rename
5. Test container connectivity after storage rename

## Implementation Checklist

- [ ] Update `infra/main.tf` resource names
- [ ] Update `infra/variables.tf` with clean prefix logic
- [ ] Update production/staging/dev tfvars files
- [ ] Update GitHub workflow resource group references
- [ ] Update documentation with new naming examples
- [ ] Test deployment with new naming
- [ ] Verify all secrets and connections work

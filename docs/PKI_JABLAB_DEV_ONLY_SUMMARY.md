# PKI Infrastructure Simplified - jablab.dev Only

## Changes Made

### 1. DNS Zone Simplification
- **BEFORE**: Supporting both `jablab.dev` and `jablab.com` domains
- **AFTER**: Using only `jablab.dev` domain for all services
- **Impact**: Simpler configuration, single DNS zone management

### 2. Updated Configuration Files

#### `/workspaces/ai-content-farm/infra/variables.tf`
- ✅ Removed `jablab_com_resource_group` variable
- ✅ Kept `jablab_dev_resource_group = "jabr_personal"`
- ✅ Primary domain already set to `jablab.dev`

#### `/workspaces/ai-content-farm/infra/pki_infrastructure.tf`
- ✅ Removed `data.azurerm_dns_zone.jablab_com` reference
- ✅ Updated certificate DNS names to only include `jablab.dev`
- ✅ Removed DNS A records for `jablab.com`
- ✅ Fixed certificate subject common name to use `jablab.dev`
- ✅ Fixed locals conditional type consistency

#### `/workspaces/ai-content-farm/infra/keda_dapr_integration.tf`
- ✅ Fixed certificate reference from `azurerm_key_vault_secret.service_certificates` to `azurerm_key_vault_certificate.service_certificates`
- ✅ Fixed Cosmos DB connection string reference
- ✅ Updated dependencies to use correct certificate resource

#### `/workspaces/ai-content-farm/docs/KEDA_DAPR_MTLS_IMPLEMENTATION_PLAN.md`
- ✅ Updated documentation to reflect single domain usage
- ✅ Changed DNS zone references from plural to singular

### 3. New Development Configuration
- ✅ Created `/workspaces/ai-content-farm/infra/development.tfvars` with PKI settings

## Service URLs
All services will now be available at:
- `content-collector.jablab.dev`
- `content-processor.jablab.dev` 
- `site-generator.jablab.dev`

## Certificate Configuration
- **Domain**: `jablab.dev` only
- **DNS Zone**: Existing zone in `jabr_personal` resource group
- **Certificate Authority**: Let's Encrypt via ACME
- **Challenge Type**: DNS-01 (Azure DNS integration)
- **Storage**: Azure Key Vault

## Validation Status
✅ **Terraform configuration is valid**
✅ **All reference errors fixed**
✅ **Ready for deployment**

## Next Steps
1. **Deploy PKI Infrastructure**:
   ```bash
   cd /workspaces/ai-content-farm/infra
   terraform plan -var-file="development.tfvars"
   terraform apply -var-file="development.tfvars"
   ```

2. **Verify Certificate Generation**:
   - Check Let's Encrypt certificate issuance
   - Validate DNS A records creation
   - Test certificate storage in Key Vault

3. **Test mTLS Communication**:
   - Deploy container apps with certificates
   - Validate service-to-service authentication
   - Test certificate rotation

## Cost Impact
- **No change** - still targeting ~$5/month with Cosmos DB
- **Simplified management** - single DNS zone reduces complexity
- **Faster deployment** - fewer DNS validations required

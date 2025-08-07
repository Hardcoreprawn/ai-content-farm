# Bootstrap Infrastructure

This module creates the foundational infrastructure required for the AI Content Farm project, including GitHub Actions authentication and remote state storage.

## Purpose

The bootstrap module must be deployed first as it creates:
- Azure AD Application for GitHub Actions OIDC authentication
- Federated identity credentials for secure CI/CD
- Azure Storage Account for Terraform remote state
- Service Principal with necessary permissions

## Resources Created

- `azuread_application.github_actions` - Azure AD app for GitHub Actions
- `azuread_service_principal.github_actions` - Service principal for the app
- `azuread_application_federated_identity_credential.*` - OIDC credentials for different environments/branches
- `azurerm_storage_account.tfstate` - Storage for Terraform state
- `azurerm_storage_container.tfstate` - Container for state files
- `azurerm_role_assignment.github_actions_contributor` - Subscription-level permissions

## Deployment

### Prerequisites
- Azure CLI installed and authenticated: `az login`
- Terraform >= 1.3.0 installed

### Steps

1. **Initialize Terraform:**
   ```bash
   cd bootstrap/
   terraform init
   ```

2. **Review and customize variables:**
   ```bash
   cp variables.tf.example variables.tf  # if needed
   # Edit variables or use -var flags
   ```

3. **Plan deployment:**
   ```bash
   terraform plan -var="environment=staging"
   ```

4. **Deploy:**
   ```bash
   terraform apply -var="environment=staging"
   ```

5. **Note the outputs:**
   The deployment will output important values needed for:
   - GitHub repository configuration
   - Application module backend configuration

## Outputs

- `azure_client_id` - Client ID for GitHub Actions
- `azure_tenant_id` - Azure tenant ID
- `azure_subscription_id` - Azure subscription ID
- `github_actions_object_id` - Service principal object ID
- `storage_account_name` - Storage account for remote state
- `terraform_backend_config` - Configuration for application module

## Important Notes

- This module uses **local state** (not remote state)
- Must be deployed before the application module
- Creates the storage account that the application module will use for its remote state
- The GitHub Actions service principal created here is used by CI/CD pipelines

## Security

- Uses OIDC workload identity federation (no stored secrets)
- Federated identity credentials for different GitHub environments
- Principle of least privilege access
- Service principal has Contributor role at subscription level

# Infrastructure Setup Guide

This guide explains how to set up the AI Content Farm infrastructure with proper separation between bootstrap and application layers.

## Architecture Overview

The infrastructure is split into two layers:

1. **Bootstrap Layer** (`infra/bootstrap/`): Creates foundation resources
   - Azure AD Application for GitHub Actions OIDC
   - Storage Account for Terraform remote state
   - Basic permissions and federated identity credentials

2. **Application Layer** (`infra/`): Creates the application infrastructure
   - Function Apps
   - Key Vault
   - Storage Account for content
   - Monitoring and logging

## Setup Process

### Prerequisites

1. Azure CLI installed and logged in: `az login`
2. Terraform installed (>= 1.0)
3. GitHub CLI installed (optional, for automatic variable setup): `gh auth login`

### One-Time Bootstrap Setup

Run the automated bootstrap script:

```bash
# For staging environment (default)
make bootstrap-azure

# For production environment
ENVIRONMENT=production make bootstrap-azure
```

This will:
1. Create the Azure AD application for GitHub Actions
2. Create a storage account for Terraform state
3. Configure GitHub repository variables
4. Set up remote state for the main infrastructure

### Deploy Main Infrastructure

After bootstrap is complete:

```bash
# Deploy main infrastructure
make apply

# Or run full verification first
make verify && make apply
```

## GitHub Actions Configuration

The bootstrap process automatically sets these GitHub repository variables:

- `AZURE_CLIENT_ID`: Client ID for the Azure AD application
- `AZURE_TENANT_ID`: Azure tenant ID
- `AZURE_SUBSCRIPTION_ID`: Azure subscription ID
- `TERRAFORM_STATE_STORAGE_ACCOUNT`: Storage account name for Terraform state

## State Management

Terraform state is stored remotely in Azure Storage for consistency across team members and CI/CD runs.

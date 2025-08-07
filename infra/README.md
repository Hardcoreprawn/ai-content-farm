# AI Content Farm Infrastructure

This directory contains the Infrastructure as Code (IaC) for the AI Content Farm project, organised into separate modules for clear separation of concerns.

## Directory Structure

```
infra/
├── bootstrap/          # Foundation infrastructure setup
├── application/        # Main application infrastructure
└── README.md          # This file
```

## Modules

### 1. Bootstrap (`bootstrap/`)
**Purpose**: Creates the foundational infrastructure required before deploying the main application.

**Contains**:
- GitHub Actions service principal and OIDC federated identity credentials
- Azure AD application for CI/CD authentication
- Remote state storage (Azure Storage Account)
- Role assignments for GitHub Actions

**State Management**: Uses local state (since it creates the remote state storage)

**Deploy Order**: Must be deployed FIRST

### 2. Application (`application/`)
**Purpose**: Creates the main application infrastructure including Function Apps, Key Vault, storage, and monitoring.

**Contains**:
- Azure Function Apps for the content processing pipeline
- Key Vault for secrets management
- Storage accounts for data persistence
- Application Insights and Log Analytics for monitoring
- Cost monitoring and alerting

**State Management**: Uses remote state (created by bootstrap)

**Deploy Order**: Deploy AFTER bootstrap

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

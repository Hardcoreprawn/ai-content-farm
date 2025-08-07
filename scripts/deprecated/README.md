# Deprecated Scripts

These scripts were used during the initial setup and migration process but are no longer needed:

- **setup-github-secrets.sh**: Replaced by repository variables setup (done automatically by bootstrap)
- **setup-azure-oidc.sh**: Replaced by Terraform-managed OIDC configuration in bootstrap
- **fix-oidc-environment-credentials.sh**: One-time fix script, no longer needed
- **setup-environments.sh**: Replaced by Makefile targets and Terraform workspaces

## Active Scripts (in parent directory)

- **bootstrap.sh**: Bootstrap infrastructure setup
- **setup-keyvault.sh**: Key Vault secret configuration
- **cost-calculator.py**: Cost analysis tooling
- **cost-estimate.sh**: Cost estimation pipeline integration


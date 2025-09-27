# Container Configuration Files

This directory contains configuration files that are uploaded to blob storage and used by the running containers to configure their behavior.

## Purpose

These configuration files are deployed to Azure Blob Storage via Terraform and allow containers to adjust their behavior without requiring code changes or redeployment:

- **Container targeting** - Which blob containers to read from/write to
- **Processing parameters** - Batch sizes, thresholds, timeouts
- **Service-specific settings** - Customizable per container service

## File Structure

### Service Container Configuration
- `{service-name}-containers.json` - Container targeting configuration
- `{service-name}-processing.json` - Processing parameter configuration

### Current Files
- `content-processor-containers.json` - Container names for content processor
- `content-processor-processing.json` - Processing settings for content processor

## Deployment

These files are automatically uploaded to the `collection-templates` container in blob storage under the `config/` prefix via Terraform during deployment.

## Benefits

- **No redeployment required** - Configuration changes take effect immediately
- **Environment-specific settings** - Different configs for dev/staging/prod
- **Centralized management** - All container config in one place
- **Version controlled** - Configuration changes tracked in git
- **Graceful fallback** - Services use sensible defaults if config unavailable

## Adding New Configuration

1. Create new JSON files following the naming pattern
2. Add Terraform resources to upload them to blob storage
3. Update the relevant service to load the new configuration
4. Services will automatically pick up the new config on next operation
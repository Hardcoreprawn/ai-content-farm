# Shared Container Registry Strategy

## Overview
To optimize costs, we've consolidated from per-environment container registries to a single shared Azure Container Registry. This saves **$20/month** by eliminating duplicate registries while maintaining deployment flexibility through container image tagging.

## Container Tagging Strategy

### Image Tag Conventions

| Environment | Tag Pattern | Example | Purpose |
|------------|-------------|---------|---------|
| **Development** | `latest` | `myapp:latest` | Latest development build |
| **Staging** | `staging-{version}` | `myapp:staging-v1.2.3` | Staging deployment |
| **Production** | `prod-{version}` | `myapp:prod-v1.2.3` | Production release |
| **Pull Requests** | `pr-{number}-{commit}` | `myapp:pr-123-abc1234` | Ephemeral PR environments |
| **Feature Branches** | `feature-{branch}-{commit}` | `myapp:feature-auth-def5678` | Feature development |

### Registry Details

- **Name**: `aicontentfarmacr{suffix}` (shared across all environments)
- **SKU**: Basic (cost-optimized)
- **Storage**: 10GB limit (sufficient for multiple tagged versions)
- **Authentication**: Azure AD managed identities only

## Deployment Workflow

### 1. Development
```bash
# Build and push latest
docker build -t aicontentfarmacr.azurecr.io/content-collector:latest .
docker push aicontentfarmacr.azurecr.io/content-collector:latest
```

### 2. Staging Deployment
```bash
# Tag for staging
docker tag aicontentfarmacr.azurecr.io/content-collector:latest \
    aicontentfarmacr.azurecr.io/content-collector:staging-v1.2.3
docker push aicontentfarmacr.azurecr.io/content-collector:staging-v1.2.3
```

### 3. Production Promotion
```bash
# Promote staging to production
docker tag aicontentfarmacr.azurecr.io/content-collector:staging-v1.2.3 \
    aicontentfarmacr.azurecr.io/content-collector:prod-v1.2.3
docker push aicontentfarmacr.azurecr.io/content-collector:prod-v1.2.3
```

## Container Apps Configuration

Each environment's Container Apps will reference the same registry but use different image tags:

### Development Environment
```terraform
resource "azurerm_container_app" "content_collector" {
  # ... configuration ...
  
  template {
    container {
      name   = "content-collector"
      image  = "${azurerm_container_registry.main.login_server}/content-collector:latest"
      # ... other config ...
    }
  }
}
```

### Staging Environment
```terraform
resource "azurerm_container_app" "content_collector" {
  # ... configuration ...
  
  template {
    container {
      name   = "content-collector"
      image  = "${azurerm_container_registry.main.login_server}/content-collector:staging-${var.app_version}"
      # ... other config ...
    }
  }
}
```

### Production Environment
```terraform
resource "azurerm_container_app" "content_collector" {
  # ... configuration ...
  
  template {
    container {
      name   = "content-collector"
      image  = "${azurerm_container_registry.main.login_server}/content-collector:prod-${var.app_version}"
      # ... other config ...
    }
  }
}
```

## CI/CD Integration

### GitHub Actions Workflow
```yaml
- name: Build and Push Container
  run: |
    # Determine tag based on environment
    if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
      TAG="latest"
    elif [[ "${{ github.ref }}" == "refs/heads/staging" ]]; then
      TAG="staging-${{ github.sha }}"
    elif [[ "${{ github.ref }}" == refs/pull/* ]]; then
      TAG="pr-${{ github.event.number }}-${{ github.sha }}"
    fi
    
    # Build and push
    docker build -t $ACR_LOGIN_SERVER/myapp:$TAG .
    docker push $ACR_LOGIN_SERVER/myapp:$TAG
```

## Benefits

### Cost Savings
- **$20/month saved** by eliminating duplicate registries
- **10GB shared storage** instead of 10GB per environment
- **Simplified management** with single registry

### Operational Benefits
- **Easier image promotion** between environments
- **Consistent image builds** across environments  
- **Simplified CI/CD** with single registry authentication
- **Better image reuse** and layer caching

### Security Considerations
- **Same security model** as before (Azure AD authentication)
- **Environment isolation** through tagging, not separate registries
- **Image scanning** still performed in CI/CD pipeline
- **RBAC controls** who can push/pull specific tags

## Migration Notes

### From Per-Environment Registries
1. Update all Container Apps to reference the shared registry
2. Migrate existing images with appropriate tags
3. Update CI/CD pipelines to use new tagging strategy
4. Delete old environment-specific registries after validation

### Storage Management
- Monitor registry storage usage (10GB limit on Basic SKU)
- Implement image cleanup policies for old tags
- Consider upgrading to Standard SKU if storage becomes limiting factor

## Monitoring and Maintenance

### Registry Health
- Monitor storage usage in Azure portal
- Set up alerts for approaching storage limits
- Regular cleanup of old/unused image tags

### Tag Management
```bash
# List all tags for an image
az acr repository show-tags --name aicontentfarmacr --repository content-collector

# Delete old PR tags (cleanup after PR merge)
az acr repository delete --name aicontentfarmacr --image content-collector:pr-123-abc1234
```

## Future Considerations

- **Standard SKU upgrade** if vulnerability scanning becomes required
- **Premium SKU** for geo-replication in multi-region deployments
- **Harbor or similar** for advanced image management features
- **Image signing** with Notary v2 for enhanced security

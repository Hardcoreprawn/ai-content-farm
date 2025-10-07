# Markdown Generator Deployment Plan

## Overview

Deploy the new **markdown-generator** container to Azure and deprecate the old **site-generator** container.

## Status: Ready for Deployment ✅

### Phase 1 Complete: Container Development
- ✅ FastAPI application with REST endpoints
- ✅ Jinja2 template system (3 templates)
- ✅ 25/25 tests passing (79% coverage)
- ✅ All quality checks passing (Black, Flake8, MyPy, Pylance)
- ✅ Dockerfile ready with multi-stage build
- ✅ Non-root user security
- ✅ Health checks configured

### Phase 2: Infrastructure (This Deployment)
Create Terraform resources for markdown-generator container app.

## Architecture

```
content-processor → processed_content blob → markdown_generation_requests queue
                                                        ↓
                                                  KEDA triggers
                                                        ↓
                                              markdown-generator
                                                        ↓
                                            markdown_content blob
```

## Infrastructure Changes Required

### 1. New Storage Queue

**File**: `infra/storage.tf`

Add new queue for markdown generation requests:

```terraform
resource "azurerm_storage_queue" "markdown_generation_requests" {
  name                 = "markdown-generation-requests"
  storage_account_name = azurerm_storage_account.main.name

  metadata = {
    purpose     = "markdown-generator-keda-scaling"
    description = "Triggers markdown-generator to convert processed JSON to markdown"
  }
}
```

### 2. New Container App

**File**: `infra/container_app_markdown_generator.tf` (NEW)

```terraform
resource "azurerm_container_app" "markdown_generator" {
  name                         = "${local.resource_prefix}-markdown-gen"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  lifecycle {
    ignore_changes = [
      template[0].custom_scale_rule[0].authentication,
      template[0].container[0].image
    ]
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.containers.id]
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    ip_security_restriction {
      action           = "Allow"
      ip_address_range = "81.2.90.47/32"
      name             = "AllowStaticIP"
    }

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    container {
      name   = "markdown-generator"
      image  = local.container_images["markdown-generator"]
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.containers.client_id
      }

      env {
        name  = "AZURE_STORAGE_ACCOUNT_NAME"
        value = azurerm_storage_account.main.name
      }

      env {
        name  = "AZURE_TENANT_ID"
        value = data.azurerm_client_config.current.tenant_id
      }

      env {
        name  = "AZURE_SUBSCRIPTION_ID"
        value = data.azurerm_client_config.current.subscription_id
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      env {
        name  = "INPUT_CONTAINER"
        value = "processed-content"
      }

      env {
        name  = "OUTPUT_CONTAINER"
        value = "markdown-content"
      }
    }

    min_replicas = 0
    max_replicas = 5

    # Responsive KEDA scaling - process individual items immediately
    custom_scale_rule {
      name             = "markdown-queue-scaler"
      custom_rule_type = "azure-queue"
      metadata = {
        queueName   = azurerm_storage_queue.markdown_generation_requests.name
        accountName = azurerm_storage_account.main.name
        queueLength = "1"  # Scale immediately for each item
        cloud       = "AzurePublicCloud"
      }
    }
  }

  tags = local.common_tags

  depends_on = [
    azurerm_storage_container.processed_content,
    azurerm_storage_container.markdown_content,
    azurerm_storage_queue.markdown_generation_requests,
    azurerm_role_assignment.containers_storage_blob_data_contributor
  ]
}
```

### 3. Update Container Discovery

**File**: `infra/container_discovery.tf`

The dynamic container discovery will automatically detect `containers/markdown-generator/Dockerfile` and add it to the deployment.

### 4. Deprecate site-generator

**Option A**: Comment out (Recommended for safe rollback)
```terraform
# Deprecated - replaced by markdown-generator + site-builder split
# resource "azurerm_container_app" "site_generator" {
#   ...
# }
```

**Option B**: Remove entirely (After validation markdown-generator works)

## Deployment Process

### Step 1: Create Feature Branch

```bash
git checkout -b feature/deploy-markdown-generator
```

### Step 2: Create Terraform Files

```bash
# Create container app configuration
cat > infra/container_app_markdown_generator.tf << 'EOF'
# [Content from above]
EOF

# Add storage queue to storage.tf
# (append to existing file)
```

### Step 3: Update Dockerfile (if needed)

Ensure `containers/markdown-generator/Dockerfile` exists and is properly configured.

### Step 4: Commit and Push

```bash
git add containers/markdown-generator/
git add infra/container_app_markdown_generator.tf
git add infra/storage.tf
git add docs/MARKDOWN_GENERATOR_DEPLOYMENT.md

git commit -m "feat: add markdown-generator container with Jinja2 templates

- Add markdown-generator FastAPI container
- Jinja2 template system (default, with-toc, minimal)
- 25/25 tests passing, 79% coverage
- KEDA queue scaling (queueLength=1)
- Terraform infrastructure for Container App
- Add markdown-generation-requests queue
- Ready to replace site-generator markdown generation

Closes #596"

git push origin feature/deploy-markdown-generator
```

### Step 5: Create Pull Request

GitHub PR will trigger CI/CD pipeline:
1. ✅ Security scans (Checkov, Trivy, Terrascan)
2. ✅ Test containers (pytest)
3. ✅ Terraform validation
4. ✅ Cost analysis (Infracost)
5. ✅ Build container image
6. ⏸️  Wait for approval
7. 🚀 Deploy to production (after merge to main)

### Step 6: Monitor Deployment

```bash
# Watch GitHub Actions
# https://github.com/Hardcoreprawn/ai-content-farm/actions

# After deployment, verify health
curl https://ai-content-prod-markdown-gen.azurecontainerapps.io/health

# Check KEDA scaling
az containerapp show \
  --name ai-content-prod-markdown-gen \
  --resource-group ai-content-prod-rg \
  --query "properties.template.scale"
```

### Step 7: Test End-to-End

```bash
# Manually trigger processing to create markdown
curl -X POST https://ai-content-prod-markdown-gen.azurecontainerapps.io/api/markdown/generate \
  -H "Content-Type: application/json" \
  -d '{
    "blob_name": "test-article.json",
    "output_container": "markdown-content"
  }'

# Verify markdown was created
az storage blob list \
  --container-name markdown-content \
  --account-name aicontentprodstkwakpx \
  --auth-mode login
```

## Rollback Plan

If issues occur:

1. **Revert PR**: Close and revert the merged PR
2. **Terraform Rollback**: 
   ```bash
   cd infra
   terraform plan -destroy -target=azurerm_container_app.markdown_generator
   terraform apply -destroy -target=azurerm_container_app.markdown_generator
   ```
3. **Re-enable site-generator**: Uncomment the old container app configuration

## Cost Estimate

**Markdown-Generator Container**:
- CPU: 0.25 cores
- Memory: 0.5Gi
- Min replicas: 0 (scale-to-zero)
- Max replicas: 5
- Queue length: 1 (responsive scaling)

**Expected Cost**: ~$1-2/month (scales to zero when idle)

## Success Criteria

- ✅ Container deploys successfully
- ✅ Health endpoint returns 200 OK
- ✅ KEDA scaling triggers on queue messages
- ✅ Markdown files created in `markdown-content` container
- ✅ Jinja2 templates render correctly
- ✅ No errors in Application Insights logs
- ✅ Cost remains under $3/month

## Timeline

- **Phase 1** (Complete): Container development and testing
- **Phase 2** (This PR): Infrastructure deployment
- **Phase 3** (Next): Integrate with content-processor to send queue messages
- **Phase 4** (Future): Build site-builder container for static site generation

---

**Status**: Ready for deployment via CI/CD pipeline ✅  
**Last Updated**: October 7, 2025

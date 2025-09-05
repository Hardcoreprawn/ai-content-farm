# GitHub Actions Multi-Tier Container Strategy

## Overview
The CI/CD pipeline has been restructured to support our multi-tier container strategy using reusable GitHub Actions.

## New Action Structure

### 1. Build Base Images Action
**Location**: `.github/actions/build-base-images/action.yml`

**Purpose**: Builds the multi-tier base images in correct dependency order
- foundation → common-deps → web-services → data-processing → scheduler

**Inputs**:
- `registry` (optional): Container registry to tag images for

**Outputs**:
- `base-images-built`: Comma-separated list of built base images

**Usage**:
```yaml
- uses: ./.github/actions/build-base-images
  with:
    registry: ${{ secrets.ACR_LOGIN_SERVER }}
```

### 2. Build Service Containers Action
**Location**: `.github/actions/build-service-containers/action.yml`

**Purpose**: Builds service containers using the multi-tier base images

**Inputs**:
- `registry` (optional): Container registry to tag images for
- `containers` (optional): Specific containers to build (default: all)

**Outputs**:
- `containers-built`: Comma-separated list of built containers
- `build-summary`: Build statistics and success rate

**Usage**:
```yaml
- uses: ./.github/actions/build-service-containers
  with:
    containers: "content-processor,site-generator"
    registry: ${{ secrets.ACR_LOGIN_SERVER }}
```

### 3. Deploy to Azure Action
**Location**: `.github/actions/deploy-to-azure/action.yml`

**Purpose**: Complete deployment pipeline for Azure Container Apps

**Inputs**:
- `azure-credentials`: Azure service principal credentials
- `resource-group`: Azure resource group name
- `acr-name`: Azure Container Registry name
- `environment`: Environment to deploy to
- `containers`: Containers to deploy (default: all)

**Outputs**:
- `deployment-url`: URL of deployed application
- `deployed-containers`: List of deployed containers

**Usage**:
```yaml
- uses: ./.github/actions/deploy-to-azure
  with:
    azure-credentials: ${{ secrets.AZURE_CREDENTIALS }}
    resource-group: 'ai-content-farm-core-rg'
    acr-name: 'aicontentfarm76ko2hacr'
    environment: 'production'
```

## Updated Workflows

### Main CI/CD Pipeline
**File**: `.github/workflows/cicd-pipeline.yml`

**Changes**:
1. `container-build-validation` job now uses reusable actions
2. `production-deployment` job uses the deploy action
3. Outputs are properly structured for downstream jobs

### Test Workflow
**File**: `.github/workflows/test-container-actions.yml`

**Purpose**: Validate actions work correctly before full pipeline runs
- Can be triggered manually via workflow_dispatch
- Tests specific containers or all containers
- Optional deployment testing

## Benefits

### ✅ Maintainability
- Container build logic centralized in reusable actions
- Easy to update build process across all workflows
- Clear separation of concerns

### ✅ Testability
- Actions can be tested independently
- Dry-run capabilities for deployment validation
- Selective container building and deployment

### ✅ Flexibility
- Can build specific containers vs all containers
- Support for different environments (staging/production)
- Configurable registry targeting

### ✅ Observability
- Structured outputs for build summaries
- Clear success/failure reporting
- Deployment URL and container tracking

## Testing the New Structure

### Quick Test (Local Simulation)
```bash
# Test the build logic locally
cd /workspaces/ai-content-farm

# Build base images
docker build -f containers/base/Dockerfile.multitier -t ai-content-farm-base:web-services --target web-services .

# Build a service container
docker build -f containers/content-processor/Dockerfile -t content-processor:latest .
```

### GitHub Actions Test
1. Go to Actions tab in GitHub
2. Run "Test Multi-Tier Container Actions" workflow
3. Specify containers to test (or use default)
4. Monitor build results and outputs

### Full Pipeline Test
1. Push changes to trigger main CI/CD pipeline
2. Monitor container-build-validation job
3. Check production deployment (if all quality gates pass)

## Migration Benefits Realized

### Before Multi-Tier Strategy:
- 38 dependency PRs per update cycle
- 8 separate container builds
- Complex Dockerfile maintenance
- Inconsistent base configurations

### After Multi-Tier Strategy:
- ~8-10 dependency PRs per update cycle (75% reduction)
- Shared base layers with layer caching
- Simplified service Dockerfiles
- Consistent foundation across all services
- Structured, testable CI/CD pipeline

## Next Steps

1. **Validate Actions**: Run test workflow to ensure actions work correctly
2. **Expand Container Apps**: Add remaining 7 container apps to Terraform
3. **Environment Parity**: Ensure staging environment matches production structure
4. **Monitoring**: Add deployment health checks and rollback capabilities

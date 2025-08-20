# GitHub Actions Containerization Consistency

## Overview
Updated GitHub Actions to be consistent with the Makefile's containerized approach, ensuring tools run in containers wherever possible.

## Changes Made

### ✅ Already Containerized (Consistent)
- **Trivy**: `aquasec/trivy:latest` (infrastructure & container scanning)
- **Semgrep**: `returntocorp/semgrep:latest` (SAST scanning)
- **Checkov**: `bridgecrew/checkov:latest` (IaC validation)
- **Syft**: `anchore/syft:latest` (SBOM generation)
- **Infracost**: `infracost/infracost:latest` (cost analysis)
- **Terraform**: `hashicorp/terraform:latest` (infrastructure deployment)
- **Azure CLI**: `mcr.microsoft.com/azure-cli:latest` (cloud operations)

### 🔄 Updated to Containerized
- **yamllint**: Changed from `pip install yamllint` → `cytopia/yamllint:latest`
- **actionlint**: Changed from direct download → `rhymond/actionlint:latest`
- **Safety**: Changed from `pip install safety` → `pyupio/safety:latest` (matches Makefile)

### ⚠️ Kept as Direct Install (No Official Container)
- **Bandit**: No official containerized version available, kept as `pip install bandit`

## Benefits

### 1. **Environment Consistency**
- Same tool versions between local development (Makefile) and CI/CD (GitHub Actions)
- Eliminates "works on my machine" issues

### 2. **Isolation & Security**
- Tools run in isolated containers
- No system-wide installations that could conflict
- Predictable environment per tool

### 3. **Reproducibility**
- Exact same container images used across environments
- Version pinning through container tags
- Easy rollback to previous tool versions

### 4. **Maintenance**
- No need to manage tool installations in runners
- Container images are pre-built and cached
- Faster execution due to no installation overhead

## Tool Comparison: Before vs After

| Tool | Before | After | Consistency |
|------|--------|-------|-------------|
| yamllint | `pip install` | `cytopia/yamllint:latest` | ✅ Containerized |
| actionlint | `curl + install` | `rhymond/actionlint:latest` | ✅ Containerized |
| Safety | `pip install` | `pyupio/safety:latest` | ✅ Matches Makefile |
| Bandit | `pip install` | `pip install` | ⚠️ No container available |
| Trivy | `aquasec/trivy:latest` | `aquasec/trivy:latest` | ✅ Already consistent |
| Semgrep | `returntocorp/semgrep:latest` | `returntocorp/semgrep:latest` | ✅ Already consistent |
| Checkov | `bridgecrew/checkov:latest` | `bridgecrew/checkov:latest` | ✅ Already consistent |

## Container Image Sources

All containers are pulled from official/trusted sources:
- **Trivy**: Official Aqua Security image
- **Semgrep**: Official Semgrep (r2c) image  
- **Checkov**: Official Bridgecrew/Prisma Cloud image
- **yamllint**: Community-maintained, well-established
- **actionlint**: Official rhymond image
- **Safety**: Official PyUp.io image
- **Syft**: Official Anchore image
- **Infracost**: Official Infracost image

## Performance Impact
- **Positive**: No installation time for most tools
- **Container Pulls**: First run pulls images, subsequent runs use cache
- **Network**: Minimal additional bandwidth for container pulls
- **Execution**: Faster startup after initial pull

## Future Improvements
- [ ] Monitor for official Bandit container image
- [ ] Consider custom multi-tool container for related tools
- [ ] Implement container image vulnerability scanning
- [ ] Add container image version pinning strategy

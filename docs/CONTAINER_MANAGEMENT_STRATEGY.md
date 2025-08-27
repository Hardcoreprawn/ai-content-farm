# Simple Container Management Strategy

## Overview

A single, smart deployment action that automatically chooses between fast container updates and full Terraform deployment based on what files changed.

## Problem Solved

- **State Lock Conflicts**: Multiple concurrent dependency updates competing for Terraform state
- **Slow Deployments**: Every dependency change requiring full infrastructure deployment  
- **Complex Workflows**: Multiple workflow files that are hard to maintain

## Simple Solution: Smart Deploy Action

**One action (`smart-deploy`) that analyzes changes and chooses the appropriate deployment method:**

### Fast Path: Container Updates Only
**Triggers**: When ONLY these files change:
- `containers/**` (container code)
- `libs/**` (shared libraries)  
- `requirements*.txt` (dependencies)
- `pyproject.toml` (Python config)

**Method**: Direct `az containerapp update` calls
**Duration**: ~2-3 minutes
**No Terraform state lock required**

### Slow Path: Full Infrastructure Deployment  
**Triggers**: When ANY of these change:
- `infra/**` (Terraform files)
- Mixed changes (containers + infrastructure)
- Any other files not in the fast path

**Method**: Full Terraform deployment with state management
**Duration**: ~8-12 minutes
**Uses existing state lock mechanism**

## Implementation

### Single Workflow
- **Maintains all existing safety checks** (security scanning, testing, code quality)
- **Preserves all permissions and environments**
- **Simply replaces the deployment step** with smart-deploy action

### Smart Deploy Action
```yaml
- name: Smart Deploy to Azure
  uses: ./.github/actions/smart-deploy
  # Automatically chooses deployment method
```

**Change Detection Logic**:
```bash
if: only containers/libs/requirements changed
  → Fast container updates (no Terraform)
else:
  → Full Terraform deployment
```

## Benefits

### Performance
- **Dependency updates**: 75% faster (2-3 min vs 8-12 min)
- **Container fixes**: Same performance improvement
- **Infrastructure changes**: No performance impact (uses existing path)

### Simplicity  
- **Single workflow file** to maintain
- **All safety checks preserved** 
- **Automatic routing** - no manual intervention
- **Backward compatible** - infrastructure changes work exactly as before

### Reliability
- **No state lock conflicts** for dependency updates
- **Reduced deployment queue backup**
- **Same permissions and security** as existing workflow

## Examples

**Dependabot updates fastapi**:
```
requirements.txt changed → Fast path (2-3 min)
No Terraform state lock conflicts
```

**Developer fixes container bug**:
```  
containers/site-generator/main.py changed → Fast path (2-3 min)
Single container updated directly
```

**Infrastructure change**:
```
infra/variables.tf changed → Slow path (8-12 min)
Full Terraform deployment with state management
```

## Migration Impact

### Immediate
- **Zero changes** to existing workflow structure
- **All existing safety checks maintained**
- **Dependabot PRs stop failing** due to state locks

### Long-term
- **Simplified maintenance** - single workflow to manage
- **Faster developer feedback** for container changes
- **Improved CI/CD reliability**

This approach gives you **maximum benefit with minimum complexity** - just one smart action that makes the right choice automatically!

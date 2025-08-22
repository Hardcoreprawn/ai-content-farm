# Workflow Validation & Pre-commit Hooks

## Overview

This document describes the automated workflow validation system that ensures GitHub Actions workflows and action files are always syntactically correct and secure.

## Components

### 1. Pre-commit Hook (`scripts/pre-commit-hook.sh`)

**Purpose**: Automatically validates workflow files before they're committed to prevent broken workflows from reaching the repository.

**Triggered when**: Any files in `.github/workflows/` or `.github/actions/` are staged for commit.

**What it does**:
- Runs `make lint-workflows` to validate YAML syntax and GitHub Actions semantics
- Runs `make scan-semgrep` to check for security vulnerabilities 
- Blocks commits if validation fails
- Shows exactly which files changed and why validation is running

**Setup**: Run `./scripts/setup-git-hooks.sh` once per developer machine.

### 2. CI Workflow Validation (`workflow-validation` job)

**Purpose**: Validates all workflows in CI/CD pipeline as the first step, failing fast if there are issues.

**When it runs**: On every push and pull request.

**What it validates**:
- YAML syntax (yamllint)
- GitHub Actions semantics (actionlint) 
- Emoji usage policy compliance
- Security patterns via semgrep

### 3. Makefile Targets

**`make lint-workflows`**: Runs all workflow validation tools
- `make yamllint`: YAML syntax validation
- `make actionlint`: GitHub Actions specific validation  
- `make emoji-check`: Ensures compliant emoji usage

## Why This Matters

### Before This System
```bash
# Developer commits workflow changes
git add .github/workflows/cicd-pipeline.yml
git commit -m "Update workflow"
git push

# 5 minutes later... 
❌ CI/CD Pipeline failed - YAML syntax error on line 82
# All other developers' PRs are now blocked
# Wasted CI/CD resources and developer time
```

### After This System  
```bash
# Developer commits workflow changes
git add .github/workflows/cicd-pipeline.yml  
git commit -m "Update workflow"

🔍 Workflow files changed, running workflow linting...
Changed files:
  - .github/workflows/cicd-pipeline.yml
❌ Workflow linting failed!
Please run 'make lint-workflows' to see the issues and fix them.

# Developer fixes issues locally, then:
git add .github/workflows/cicd-pipeline.yml
git commit -m "Update workflow"
✅ Workflow linting passed!

git push
# CI/CD runs successfully, no wasted time
```

## Developer Workflow

### First Time Setup
```bash
./scripts/setup-git-hooks.sh
```

### Daily Usage
The system works automatically! When you modify workflow files:

1. **Local validation**: Pre-commit hook runs automatically
2. **Fix issues**: If validation fails, run `make lint-workflows` to see details
3. **CI validation**: Workflows are validated again in CI for safety

### Bypassing (Emergency Only)
```bash
# Skip pre-commit hooks (not recommended)
git commit --no-verify

# Skip specific checks in CI
git commit -m "feat: emergency fix [skip lint]"
```

## Files Changed

- `.git/hooks/pre-commit`: Local Git hook (auto-installed)
- `scripts/pre-commit-hook.sh`: Shared hook logic (version controlled)
- `scripts/setup-git-hooks.sh`: One-time setup script
- `.github/actions/lint-workflows/action.yml`: Enhanced to show changed files
- `.github/workflows/cicd-pipeline.yml`: Workflow validation as first step

## Benefits

✅ **Fast feedback**: Catch issues in ~5 seconds locally vs ~5 minutes in CI  
✅ **No broken main**: Invalid workflows never reach the repository  
✅ **Developer productivity**: No waiting for CI to fail on syntax errors  
✅ **Resource efficiency**: Avoid wasted CI/CD runner time  
✅ **Security**: Automatic scanning for script injection vulnerabilities  
✅ **Team coordination**: Clear error messages and fix guidance  

## Troubleshooting

### Pre-commit hook not working
```bash
# Check if hook is installed and executable
ls -la .git/hooks/pre-commit

# Reinstall if needed
./scripts/setup-git-hooks.sh
```

### Linting tools not found
```bash
# Install linting dependencies
make setup-lint-tools
```

### Emergency bypass
```bash
# If you absolutely must bypass validation
git commit --no-verify -m "Emergency fix - will fix linting in follow-up"
```

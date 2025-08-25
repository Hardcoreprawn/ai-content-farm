# Pre-commit Setup Instructions

This repository uses pre-commit hooks to ensure code quality and consistency. The hooks use the same scripts and tools as our CI/CD pipeline to guarantee alignment between local development and automated checks.

## Installation

1. **Install pre-commit** (if not already installed):
   ```bash
   pip install pre-commit
   ```

2. **Install the pre-commit hooks**:
   ```bash
   pre-commit install
   ```

## What Gets Checked

Our pre-commit configuration runs the following checks:

### Code Quality (Python)
- **Black** - Code formatting
- **isort** - Import sorting  
- **flake8** - Code linting and style checking
- Uses the same `./scripts/code-quality.sh` script as CI/CD

### File Quality
- Trailing whitespace removal
- End-of-file fixing
- Large file detection (>1MB)
- Merge conflict detection
- Debug statement detection

### Configuration Files
- **YAML linting** - Using yamllint with relaxed rules
- **GitHub Actions linting** - Using actionlint for workflow validation

### Security
- **Secret detection** - Using detect-secrets to prevent credential commits

## Manual Execution

You can run pre-commit checks manually:

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run python-code-quality
pre-commit run actionlint

# Run only on staged files (default behavior)
pre-commit run
```

## Integration with Makefile

The pre-commit hooks use the same underlying scripts as our Makefile targets:

```bash
# These use the same ./scripts/code-quality.sh script:
make lint-python        # Same as pre-commit python-code-quality hook
make flake8            # Individual tool from the script
make format-python     # Auto-fix version
```

## Bypassing Hooks (Not Recommended)

In exceptional cases, you can bypass pre-commit hooks:

```bash
git commit --no-verify -m "Emergency commit message"
```

However, this is discouraged as it breaks the consistency between local and CI checks.

## Troubleshooting

### Hook Installation Issues
```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install

# Update hooks to latest versions
pre-commit autoupdate
```

### Code Quality Failures
```bash
# Auto-fix formatting issues
make format-python

# Check specific issues
./scripts/code-quality.sh --linting  # Just flake8
./scripts/code-quality.sh --all      # All checks including types
```

### Actionlint Issues
```bash
# Check GitHub Actions workflows specifically
make lint-workflows
```

## CI/CD Alignment

The pre-commit configuration ensures that the same quality checks run locally as in our GitHub Actions:

- ✅ **Python Code Quality**: Uses `./scripts/code-quality.sh` (same as CI)
- ✅ **GitHub Actions Linting**: Uses `actionlint` (same as CI) 
- ✅ **YAML Validation**: Uses `yamllint` (same as CI)
- ✅ **Security Scanning**: Uses `detect-secrets` (same as CI)

This guarantees that commits passing local pre-commit checks will also pass CI/CD pipeline validation.

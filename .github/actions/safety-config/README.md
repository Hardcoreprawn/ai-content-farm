# Centralized Safety Configuration

This directory contains the centralized Safety configuration system that ensures consistent Python security scanning across all parts of the project.

## Overview

Previously, Safety was configured in multiple places with potentially different versions and settings:
- Individual GitHub Actions
- Makefile 
- Requirements files
- Docker containers

This led to configuration drift and made it hard to update Safety consistently.

## Solution

The centralized approach provides:

1. **Single Source of Truth**: `config/shared-versions.toml` defines the Safety version
2. **Reusable Action**: `.github/actions/safety-config/action.yml` handles all Safety operations
3. **Automatic Sync**: `scripts/sync_security_versions.py` syncs versions across all files

## Usage

### In GitHub Actions

Use the centralized Safety action instead of direct Safety commands:

```yaml
- name: Run Safety Scan
  uses: ./.github/actions/safety-config
  with:
    mode: 'scan'                    # install, scan, or check-results
    output-format: 'both'           # json, text, or both
    output-dir: 'security-results'  # where to store results
    requirements-files: ''          # optional: specific files to scan
    container-name: ''              # optional: for single container scans
```

### Modes

- **install**: Only install Safety (useful when you need Safety available for later steps)
- **scan**: Install Safety and run scans on all found requirements.txt files
- **check-results**: Analyze existing Safety scan results and report summary

### Output Formats

- **json**: Produces machine-readable `.json` files for CI/CD processing
- **text**: Produces human-readable `.txt` files for developers
- **both**: Produces both formats (recommended for most use cases)

## Configuration Management

### Updating Safety Version

1. Edit `config/shared-versions.toml`:
   ```toml
   [security]
   safety = "~=3.2.8"  # New version
   ```

2. Run the sync script:
   ```bash
   python3 scripts/sync_security_versions.py
   ```

3. The script will update:
   - `requirements-dev.txt`
   - `requirements.txt` (if it exists)
   - GitHub Actions files with hardcoded versions
   - `Makefile` safety commands

### Verification

Check that all Safety configurations are in sync:
```bash
# Search for any hardcoded Safety versions
grep -r "safety.*=" . --include="*.yml" --include="*.yaml" --include="*.txt" --include="Makefile"
```

## Migration Benefits

### Before (Problems)
- Safety configured in 6+ different places
- Version inconsistencies between environments
- Hard to update Safety across the entire project
- Duplicate configuration logic in multiple actions

### After (Solutions)
- ✅ Single centralized Safety configuration action
- ✅ Consistent Safety version from `shared-versions.toml`
- ✅ Easy updates via sync script
- ✅ Reduced code duplication
- ✅ Better maintainability

### Files Updated

#### New Files Created
- `.github/actions/safety-config/action.yml` - Centralized Safety configuration
- `scripts/sync_security_versions.py` - Version synchronization script
- `config/shared-versions.toml` - Added `[security]` section

#### Files Modified to Use Centralized Config
- `.github/actions/dependency-analysis/action.yml`
- `.github/actions/security-scan/action.yml` 
- `.github/actions/security-python/action.yml`
- `Makefile` - Updated to prefer native Safety over Docker when available

## Outputs

The safety-config action provides useful outputs:

- `safety-version`: The version of Safety that was installed/used
- `scan-results`: JSON array of scan results for each file scanned
- `vulnerabilities-found`: Total number of vulnerabilities found across all scans

These can be used in subsequent workflow steps:

```yaml
- name: Run Safety Scan
  id: safety
  uses: ./.github/actions/safety-config
  with:
    mode: 'scan'

- name: Check Results
  run: |
    echo "Safety version: ${{ steps.safety.outputs.safety-version }}"
    echo "Vulnerabilities found: ${{ steps.safety.outputs.vulnerabilities-found }}"
    if [ "${{ steps.safety.outputs.vulnerabilities-found }}" -gt 0 ]; then
      echo "Security review required!"
    fi
```

## Best Practices

1. **Always use the centralized action** instead of direct Safety commands
2. **Update versions via shared-versions.toml** and run the sync script
3. **Use 'both' output format** for maximum flexibility
4. **Check outputs** to make decisions in your workflows
5. **Run sync script** after any Safety version changes

## Troubleshooting

### Action not found
Ensure you're using the correct path: `./.github/actions/safety-config`

### Permission errors
The action needs to install packages and write files. Ensure proper permissions in your workflow.

### Version conflicts
If you see version conflicts, run `scripts/sync_security_versions.py` to ensure all configurations match `shared-versions.toml`.

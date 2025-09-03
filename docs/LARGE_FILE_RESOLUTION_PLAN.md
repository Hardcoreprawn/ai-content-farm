# Large File Issues Resolution Plan

## Current Situation
- **172 total large-file issues** (before cleanup)
- **~145 unique large files** identified
- **Multiple duplicates** for each file (5-6 issues per file)
- **26 duplicate sprint summary issues**

## Problem Analysis
The Large File Detector workflow had two main issues:
1. **Faulty duplicate detection** - Regex pattern matching wasn't working correctly
2. **No protection against duplicate sprint summaries** - Created new ones on every run

## Solution Implemented

### 1. Fixed Workflow (`/.github/workflows/large-file-detector.yml`)
- **Improved duplicate detection** with proper regex and Set-based checking
- **Added sprint summary deduplication** - only creates new ones if none exist in last 7 days
- **Added path filters** - doesn't run on docs/markdown changes to reduce noise
- **Added weekly schedule** - runs Monday mornings for regular monitoring

### 2. Cleanup Scripts

#### `./scripts/simple-cleanup-duplicates.sh`
- Safely closes duplicate issues while keeping the most recent for each file
- Preserves one sprint summary issue
- Provides detailed progress reporting

#### `./scripts/analyze-large-file-priorities.sh`
- Analyzes remaining backlog by priority (Critical > Warning > Large)
- Groups by file type and container service
- Provides actionable recommendations

## File Priority Classification

### 🔴 CRITICAL (>1000 lines) - 5 unique files
1. `.secrets.baseline` (1307 lines) - Security baseline file
2. `Makefile` (881 lines) - Build automation

### 🟡 WARNING (600-1000 lines) - ~20 unique files
- `infra/container_apps.tf` (749 lines) - Infrastructure
- `containers/site-generator/service_logic.py` (720 lines) - Service logic
- Various container main.py files (600-700 lines)

### 🟠 LARGE (500-600 lines) - ~120 unique files
- Multiple Python service files
- Documentation files
- YAML workflows
- Test files

## Immediate Action Plan

### Phase 1: Cleanup (Ready to Execute)
```bash
# 1. Clean up duplicates
cd /workspaces/ai-content-farm
./scripts/simple-cleanup-duplicates.sh

# 2. Analyze priorities
./scripts/analyze-large-file-priorities.sh
```

### Phase 2: Strategic Refactoring

#### Priority Order:
1. **`.secrets.baseline`** - Can be split into multiple baseline files
2. **`Makefile`** - Break into modular makefiles and include them
3. **Container service main.py files** - Apply microservice refactoring patterns
4. **Infrastructure Terraform** - Modularize into separate components
5. **Documentation files** - Split into focused topic areas

#### Refactoring Approach:
```bash
# For each file, create a feature branch
git checkout -b refactor/secrets-baseline
# ... make changes
# ... test thoroughly
git commit -m "refactor: split .secrets.baseline into modular files"
# ... create PR
```

### Phase 3: Prevention
- **Workflow improvements** are already implemented
- **Regular monitoring** via weekly runs
- **Path filters** prevent noise from documentation changes

## Container Services Strategy

### Most Impacted Services:
1. **content-collector** (25 files) - Highest priority for refactoring
2. **site-generator** (14 files) - Second priority
3. **markdown-generator** (12 files) - Third priority

### Refactoring Pattern:
1. **Extract business logic** into separate modules
2. **Separate configuration** into config files
3. **Split large functions** into focused methods
4. **Move utilities** to shared libraries
5. **Preserve API compatibility** during transitions

## Quick Start Commands

```bash
# Run cleanup (closes ~140+ duplicate issues)
./scripts/simple-cleanup-duplicates.sh

# Analyze remaining work
./scripts/analyze-large-file-priorities.sh

# Test current state
make test

# Start with highest priority file
git checkout -b refactor/secrets-baseline
# Edit .secrets.baseline
# Test changes
# Commit and create PR
```

## Success Metrics
- **Target**: All files under 500 lines
- **Current**: 145 files over 500 lines
- **Estimated effort**: ~30 weeks (1 file per day, 5 files per week)
- **Impact**: ~50% reduction in total lines for large files

## Next Steps
1. **Execute cleanup scripts** to resolve duplicates
2. **Start with Critical files** (`.secrets.baseline`, `Makefile`)
3. **Focus on container services** next
4. **Maintain test coverage** throughout
5. **Document refactoring patterns** for team consistency

# Dependabot Auto-Merge Configuration Guide

## Current Issue
Dependabot PRs are blocked because the repository requires manual reviews before merging, even though the main branch shows as "not protected" in the API.

## Solution: Configure Branch Protection + Dependabot Auto-Merge

### Step 1: Enable Auto-Merge in Repository Settings

```bash
# Enable auto-merge feature for the repository
gh api repos/Hardcoreprawn/ai-content-farm --method PATCH --field allow_auto_merge=true
```

### Step 2: Configure Branch Protection Rules

Create optimal branch protection that allows Dependabot to auto-merge while maintaining security:

```bash
# Set up branch protection with Dependabot-friendly rules
gh api repos/Hardcoreprawn/ai-content-farm/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["CI/CD Pipeline / Validate Workflows","CI/CD Pipeline / Code Quality"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"required_approving_review_count":0,"dismiss_stale_reviews":true,"require_code_owner_reviews":false}' \
  --field restrictions=null \
  --field allow_auto_merge=true
```

### Step 3: Configure Dependabot Auto-Merge Workflow

Update `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    # Enable auto-merge for patch and minor updates
    open-pull-requests-limit: 10
    # Allow Dependabot to auto-merge
    auto-merge:
      - dependency-type: "direct"
        update-type: "security"
      - dependency-type: "direct" 
        update-type: "version-update:semver-patch"
      - dependency-type: "direct"
        update-type: "version-update:semver-minor"
```

### Step 4: Enhanced Auto-Merge GitHub Action

Create `.github/workflows/dependabot-auto-merge.yml`:

```yaml
name: Dependabot Auto-Merge
on: pull_request

permissions:
  contents: write
  pull-requests: write
  checks: read

jobs:
  dependabot-auto-merge:
    runs-on: ubuntu-latest
    if: github.actor == 'dependabot[bot]'
    steps:
      - name: Dependabot metadata
        id: metadata
        uses: dependabot/fetch-metadata@v1
        with:
          github-token: "${{ secrets.GITHUB_TOKEN }}"

      - name: Auto-approve Dependabot PRs
        if: steps.metadata.outputs.update-type == 'version-update:semver-patch' || steps.metadata.outputs.update-type == 'version-update:semver-minor' || steps.metadata.outputs.update-type == 'version-update:semver-security'
        run: |
          gh pr review --approve "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Enable auto-merge for Dependabot PRs
        if: steps.metadata.outputs.update-type == 'version-update:semver-patch' || steps.metadata.outputs.update-type == 'version-update:semver-minor' || steps.metadata.outputs.update-type == 'version-update:semver-security'
        run: |
          gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Step 5: Alternative - Use GitHub App Token

For more robust permissions, create a GitHub App or use a personal access token:

```yaml
# In the workflow, use a token with broader permissions
- name: Auto-merge with app token
  run: |
    gh pr merge --auto --squash "$PR_URL"
  env:
    PR_URL: ${{ github.event.pull_request.html_url }}
    GITHUB_TOKEN: ${{ secrets.DEPENDABOT_AUTO_MERGE_TOKEN }}
```

## Quick Implementation Commands

### Option 1: Minimal Protection (Recommended for rapid development)
```bash
# Remove review requirement but keep CI checks
gh api repos/Hardcoreprawn/ai-content-farm/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["CI/CD Pipeline / Code Quality","CI/CD Pipeline / Container Test Summary"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews=null \
  --field restrictions=null

# Enable auto-merge
gh api repos/Hardcoreprawn/ai-content-farm --method PATCH --field allow_auto_merge=true
```

### Option 2: Smart Protection (Production-ready)
```bash
# Require CI but auto-approve Dependabot
gh api repos/Hardcoreprawn/ai-content-farm/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["CI/CD Pipeline / Code Quality","CI/CD Pipeline / Container Test Summary"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":false}' \
  --field restrictions=null

# Then use the GitHub Action above to auto-approve Dependabot PRs
```

## Benefits After Implementation

✅ **Automated Security Updates**: Critical security patches merge automatically  
✅ **Reduced Maintenance**: No manual review needed for minor dependency updates  
✅ **CI/CD Validation**: All changes still go through full test suite  
✅ **Selective Automation**: Only patch/minor updates auto-merge, major updates require review  
✅ **Audit Trail**: All changes logged and traceable  

## Current Status

- ✅ **Completed**: Manual merge of 18 pending Dependabot PRs  
- ⏳ **Next**: Implement branch protection configuration  
- ⏳ **Future**: Monitor and fine-tune auto-merge rules  

## Testing the Setup

After configuration, test with:
```bash
# Trigger a Dependabot update manually
gh api repos/Hardcoreprawn/ai-content-farm/dependency-graph/vulnerabilities \
  --method POST \
  --field ecosystem=pip
```

This setup will eliminate the manual PR management overhead while maintaining code quality and security standards.

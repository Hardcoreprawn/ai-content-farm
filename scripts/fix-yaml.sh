#!/bin/bash
# Quick fix for YAML formatting issues
# Remove trailing spaces and fix long lines

cd /workspaces/ai-content-farm

# Remove trailing spaces
sed -i 's/[[:space:]]*$//' .github/workflows/optimized-cicd.yml

# Fix long lines by breaking them appropriately
# This is a simplified version that meets YAML standards

cat > .github/workflows/optimized-cicd.yml << 'EOF'
---
name: Optimized CI/CD Pipeline

'on':
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
    paths-ignore:
      - '**.md'
      - 'docs/**'

permissions:
  contents: read
  security-events: write
  pull-requests: write
  packages: write
  id-token: write

env:
  DOCKER_BUILDKIT: 1
  REGISTRY: ghcr.io
  REPOSITORY: hardcoreprawn/ai-content-farm

jobs:
  detect-changes:
    name: Detect Changes
    runs-on: ubuntu-latest
    if: github.actor != 'dependabot[bot]'
    outputs:
      containers: ${{ steps.changes.outputs.containers }}
      infrastructure: ${{ steps.changes.outputs.infrastructure }}
      deploy-method: ${{ steps.changes.outputs.deploy-method }}
    steps:
      - name: Checkout
        uses: actions/checkout@v5
        with:
          fetch-depth: 2

      - name: Detect Changes
        id: changes
        run: |
          changed_files=$(git diff --name-only HEAD~1 HEAD || echo "")
          containers="[]"
          infrastructure="false"
          deploy_method="skip"
          container_list=()

          while IFS= read -r file; do
            case "$file" in
              containers/*/*)
                container=$(echo "$file" | cut -d/ -f2)
                if [[ -f "containers/$container/Dockerfile" ]]; then
                  container_list+=("$container")
                fi
                ;;
              libs/*|requirements*.txt|pyproject.toml)
                for dir in containers/*/; do
                  container=$(basename "$dir")
                  if [[ -f "$dir/Dockerfile" ]]; then
                    container_list+=("$container")
                  fi
                done
                ;;
              infra/*|*.tf|*.tfvars)
                infrastructure="true"
                ;;
            esac
          done <<< "$changed_files"

          if [[ ${#container_list[@]} -gt 0 ]]; then
            containers=$(printf '%s\n' "${container_list[@]}" | \
                        sort -u | jq -R . | jq -s .)
          fi

          if [[ "$infrastructure" == "true" ]]; then
            deploy_method="terraform"
          elif [[ "$containers" != "[]" ]]; then
            deploy_method="containers"
          fi

          echo "containers=$containers" >> "$GITHUB_OUTPUT"
          echo "infrastructure=$infrastructure" >> "$GITHUB_OUTPUT"
          echo "deploy-method=$deploy_method" >> "$GITHUB_OUTPUT"

  quality-checks:
    name: Quality Checks
    runs-on: ubuntu-latest
    needs: detect-changes
    if: needs.detect-changes.outputs.deploy-method != 'skip'
    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Lint Workflows
        uses: ./.github/actions/lint-workflows

      - name: Security Scan
        uses: ./.github/actions/security-scan
        with:
          fail-on-critical: 'false'

      - name: Code Quality
        if: needs.detect-changes.outputs.containers != '[]'
        uses: ./.github/actions/code-quality

  terraform-checks:
    name: Terraform Checks
    runs-on: ubuntu-latest
    needs: detect-changes
    if: needs.detect-changes.outputs.infrastructure == 'true'
    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Terraform Quality
        uses: ./.github/actions/infrastructure-quality

      - name: Cost Analysis
        uses: ./.github/actions/cost-analysis
        with:
          infracost-api-key: ${{ secrets.INFRACOST_API_KEY }}

  test-containers:
    name: Test ${{ matrix.container }}
    runs-on: ubuntu-latest
    needs: [detect-changes, quality-checks]
    if: needs.detect-changes.outputs.containers != '[]'
    strategy:
      matrix:
        container: ${{ fromJson(needs.detect-changes.outputs.containers) }}
      fail-fast: false
    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Test Container
        uses: ./.github/actions/test-single-container
        with:
          container-name: ${{ matrix.container }}

  build-containers:
    name: Build ${{ matrix.container }}
    runs-on: ubuntu-latest
    needs: [detect-changes, test-containers]
    if: |
      always() &&
      needs.detect-changes.outputs.containers != '[]' &&
      needs.test-containers.result == 'success'
    strategy:
      matrix:
        container: ${{ fromJson(needs.detect-changes.outputs.containers) }}
      fail-fast: false
    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and Push
        uses: ./.github/actions/build-and-push-container
        with:
          container-name: ${{ matrix.container }}
          registry: ${{ env.REGISTRY }}
          repository: ${{ env.REPOSITORY }}
          tag: ${{ github.sha }}

  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    needs: [detect-changes, build-containers, terraform-checks]
    if: |
      always() &&
      github.ref == 'refs/heads/main' &&
      needs.detect-changes.outputs.deploy-method != 'skip' &&
      (needs.build-containers.result == 'success' ||
       needs.build-containers.result == 'skipped') &&
      (needs.terraform-checks.result == 'success' ||
       needs.terraform-checks.result == 'skipped')
    environment: production
    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Azure Login
        uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - name: Deploy
        uses: ./.github/actions/smart-deploy-optimized
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
          environment: production
          deployment-method: ${{ needs.detect-changes.outputs.deploy-method }}
          terraform-storage-account: ${{ vars.TERRAFORM_STATE_STORAGE_ACCOUNT_PROD }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          image-tag: ${{ github.sha }}

  summary:
    name: Summary
    runs-on: ubuntu-latest
    needs: [detect-changes, quality-checks, terraform-checks,
            test-containers, build-containers, deploy]
    if: always()
    steps:
      - name: Generate Summary
        run: |
          echo "# Pipeline Summary" >> $GITHUB_STEP_SUMMARY
          echo "Deploy method: ${{ needs.detect-changes.outputs.deploy-method }}" >> $GITHUB_STEP_SUMMARY
          echo "Containers: ${{ needs.detect-changes.outputs.containers }}" >> $GITHUB_STEP_SUMMARY
EOF

echo "Pipeline YAML fixed!"

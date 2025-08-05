#!/bin/bash

# Script to configure GitHub environment protection rules
# This ensures no deployments happen without proper approvals

set -e

REPO="Hardcoreprawn/ai-content-farm"

echo "🔧 Configuring GitHub environment protection rules..."

# Create staging environment with protection rules
gh api \
  --method PUT \
  "/repos/$REPO/environments/staging" \
  --field "wait_timer=0" \
  --field "prevent_self_review=true" \
  --field "reviewers[0][type]=Team" \
  --field "reviewers[0][id]=maintainers" || echo "Staging environment already exists"

# Create production environment with stricter protection
gh api \
  --method PUT \
  "/repos/$REPO/environments/production" \
  --field "wait_timer=300" \
  --field "prevent_self_review=true" \
  --field "reviewers[0][type]=Team" \
  --field "reviewers[0][id]=maintainers" \
  --field "deployment_branch_policy[protected_branches]=true" \
  --field "deployment_branch_policy[custom_branch_policies]=false" || echo "Production environment already exists"

# Create approval-required environment for manual reviews
gh api \
  --method PUT \
  "/repos/$REPO/environments/approval-required" \
  --field "wait_timer=0" \
  --field "prevent_self_review=true" \
  --field "reviewers[0][type]=User" \
  --field "reviewers[0][id]=$(gh api user --jq .id)" || echo "Approval environment already exists"

echo "✅ Environment protection rules configured"
echo ""
echo "Environments created:"
echo "  🟡 staging - No manual approval for develop branch"
echo "  🔴 production - Requires approval + 5min wait timer + protected branches only"
echo "  ⚠️  approval-required - Manual approval for security/cost warnings"
echo ""
echo "To complete setup, ensure you have:"
echo "  1. Repository settings > Environments configured"
echo "  2. Branch protection rules on main/develop"
echo "  3. Required status checks enabled"

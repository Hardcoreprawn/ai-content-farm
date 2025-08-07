#!/bin/bash

# Get the repository and user information
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
USER_ID=$(gh api user | jq -r .id)

echo "🔧 Configuring GitHub environment protection rules..."

# Create approval-required environment for manual reviews  
echo "Setting up 'approval-required' environment..."
cat << EOF | gh api repos/$REPO/environments/approval-required --method PUT --input -
{
  "wait_timer": 0,
  "prevent_self_review": true,
  "reviewers": [{"type": "User", "id": $USER_ID}],
  "deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": false}
}
EOF
echo "Approval environment configured"

# Create staging environment with basic protection
echo "Setting up 'staging' environment..."
cat << EOF | gh api repos/$REPO/environments/staging --method PUT --input -
{
  "wait_timer": 0,
  "prevent_self_review": false,
  "deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": false}
}
EOF
echo "Staging environment configured"

# Create production environment with stricter protection
echo "Setting up 'production' environment..."
cat << EOF | gh api repos/$REPO/environments/production --method PUT --input -
{
  "wait_timer": 300,
  "prevent_self_review": true,
  "reviewers": [{"type": "User", "id": $USER_ID}],
  "deployment_branch_policy": {"protected_branches": true, "custom_branch_policies": false}
}
EOF
echo "Production environment configured"

echo "✅ Environment protection rules configured"

echo ""
echo "Environments created:"
echo "  ⚠️  approval-required - Manual approval for security/cost warnings"
echo "  🟡 staging - Basic protection for develop branch"
echo "  🔴 production - Requires approval + 5min wait timer + protected branches only"
echo ""
echo "To approve deployments:"
echo "  1. Go to: https://github.com/$REPO/actions"
echo "  2. Click on the workflow run"
echo "  3. Click 'Review deployments' when prompted"
echo "  4. Select environment and click 'Approve and deploy'"

#!/bin/bash
# GitHub Actions Cleanup Script
# Identifies unused actions and workflows for removal

set -euo pipefail

cd /workspaces/ai-content-farm

echo "🧹 GitHub Actions Cleanup Analysis"
echo "=================================="
echo

# Find actions used in current workflows
echo "📋 Actions currently used in workflows:"
echo "--------------------------------------"
used_actions=()
for workflow in .github/workflows/*.yml; do
    if [[ "$workflow" != *".disabled" && "$workflow" != *".backup" ]]; then
        echo "Checking $workflow..."
        while IFS= read -r action; do
            if [[ -n "$action" ]]; then
                used_actions+=("$action")
                echo "  ✓ $action"
            fi
        done < <(grep -o "\./.github/actions/[^'\" ]*" "$workflow" 2>/dev/null || true)
    fi
done

echo
echo "📦 All existing actions:"
echo "----------------------"
all_actions=()
while IFS= read -r action_dir; do
    action_name=$(basename "$action_dir")
    all_actions+=("./.github/actions/$action_name")
    echo "  • ./.github/actions/$action_name"
done < <(find .github/actions -name "action.yml" -exec dirname {} \; | sort)

echo
echo "🗑️  Actions marked for removal (unused):"
echo "----------------------------------------"
unused_actions=()
for action in "${all_actions[@]}"; do
    if [[ ! " ${used_actions[*]} " =~ " ${action} " ]]; then
        unused_actions+=("$action")
        echo "  ❌ $action"
    fi
done

echo
echo "📊 Summary:"
echo "----------"
echo "Total actions: ${#all_actions[@]}"
echo "Used actions: ${#used_actions[@]}"
echo "Unused actions: ${#unused_actions[@]}"
echo "Cleanup ratio: $((${#unused_actions[@]} * 100 / ${#all_actions[@]}))% can be removed"

# Check for disabled workflows
echo
echo "📁 Disabled/backup workflows:"
echo "----------------------------"
for file in .github/workflows/*.disabled .github/workflows/*.backup; do
    if [[ -f "$file" ]]; then
        echo "  🗂️  $file"
    fi
done

# Generate cleanup commands
if [[ ${#unused_actions[@]} -gt 0 ]]; then
    echo
    echo "🚀 Cleanup commands to run:"
    echo "---------------------------"
    echo "# Remove unused actions:"
    for action in "${unused_actions[@]}"; do
        action_path="${action#./}"
        echo "rm -rf \"$action_path\""
    done

    echo
    echo "# Remove disabled workflows:"
    echo "rm -f .github/workflows/*.disabled .github/workflows/*.backup"

    echo
    echo "# Remove optimized pipeline (now replaced):"
    echo "rm -f .github/workflows/optimized-cicd.yml"

    echo
    echo "# Remove temporary smart-deploy-optimized:"
    echo "rm -rf .github/actions/smart-deploy-optimized"
fi

echo
echo "⚠️  Review these actions before removal - some may be needed for other workflows!"
echo "Run the commands manually after verification."

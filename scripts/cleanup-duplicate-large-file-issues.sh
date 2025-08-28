#!/bin/bash

# Cleanup script for duplicate large-file issues
# This script will close duplicate issues, keeping only the most recent one for each file

set -e

echo "🧹 Cleaning up duplicate large file issues..."

# Function to close an issue
close_issue() {
    local issue_number=$1
    local reason="$2"

    echo "  Closing issue #$issue_number: $reason"
    gh issue close "$issue_number" --comment "**🤖 Automated Cleanup**

This issue is a duplicate and has been automatically closed to reduce noise.

$reason

The most recent issue for this file remains open for tracking purposes."
}

# 1. Clean up duplicate individual file issues
echo
echo "📁 Step 1: Cleaning up duplicate individual file issues..."

# Get all large-file issues that are individual file issues (not sprint summaries)
issues_json=$(gh issue list --label "large-file" --state open --limit 200 --json number,title,createdAt \
    | jq '[.[] | select(.title | startswith("Refactor large file:"))]')

# Group by file path and keep only the most recent for each file
files_to_clean=$(echo "$issues_json" | jq -r '
  group_by(.title | capture("Refactor large file: `(?<path>[^`]+)`").path)
  | map(select(length > 1))
  | map(sort_by(.createdAt) | reverse)
  | .[]
  | .[1:][]
  | "\(.number)|\(.title)"')

duplicate_count=0
while IFS='|' read -r issue_number title; do
    if [[ -n "$issue_number" ]]; then
        file_path=$(echo "$title" | sed -n 's/Refactor large file: `\([^`]*\)`.*/\1/p')
        close_issue "$issue_number" "Duplicate issue for file: \`$file_path\`"
        ((duplicate_count++))
    fi
done <<< "$files_to_clean"

echo "✅ Closed $duplicate_count duplicate individual file issues"

# 2. Clean up duplicate sprint summary issues
echo
echo "📊 Step 2: Cleaning up duplicate sprint summary issues..."

# Get all sprint summary issues
sprint_issues=$(gh issue list --label "large-file" --state open --limit 200 --json number,title,createdAt \
    | jq '[.[] | select(.title | contains("Large File Refactoring Sprint:"))] | sort_by(.createdAt) | reverse')

sprint_count=$(echo "$sprint_issues" | jq 'length')

if [[ $sprint_count -gt 1 ]]; then
    # Keep the most recent sprint summary, close the rest
    echo "$sprint_issues" | jq -r '.[1:][] | "\(.number)|\(.title)"' | while IFS='|' read -r issue_number title; do
        if [[ -n "$issue_number" ]]; then
            close_issue "$issue_number" "Duplicate sprint summary issue"
        fi
    done

    closed_sprint_count=$((sprint_count - 1))
    echo "✅ Closed $closed_sprint_count duplicate sprint summary issues"

    # Update the remaining sprint summary with current stats
    remaining_issue=$(echo "$sprint_issues" | jq -r '.[0].number')
    if [[ -n "$remaining_issue" ]]; then
        echo "  Updating remaining sprint summary issue #$remaining_issue with current stats..."

        # Get current file count
        current_files=$(gh issue list --label "large-file" --state open --limit 200 --json title \
            | jq '[.[] | select(.title | startswith("Refactor large file:"))] | length')

        gh issue comment "$remaining_issue" --body "**🔄 Updated Status ($(date +%Y-%m-%d))**

After cleanup:
- **Active individual file issues**: $current_files
- **Duplicate issues closed**: $duplicate_count
- **Duplicate sprint summaries closed**: $closed_sprint_count

The backlog has been cleaned up and is ready for systematic refactoring work."
    fi
else
    echo "✅ No duplicate sprint summary issues found"
fi

# 3. Summary report
echo
echo "📈 Step 3: Generating cleanup summary..."

remaining_individual=$(gh issue list --label "large-file" --state open --limit 200 --json title \
    | jq '[.[] | select(.title | startswith("Refactor large file:"))] | length')

remaining_sprints=$(gh issue list --label "large-file" --state open --limit 200 --json title \
    | jq '[.[] | select(.title | contains("Large File Refactoring Sprint:"))] | length')

echo
echo "🎉 Cleanup Complete!"
echo "===================="
echo "• Closed duplicate individual issues: $duplicate_count"
echo "• Closed duplicate sprint summaries: $((sprint_count > 1 ? sprint_count - 1 : 0))"
echo "• Remaining individual file issues: $remaining_individual"
echo "• Remaining sprint summaries: $remaining_sprints"
echo "• Total remaining large-file issues: $((remaining_individual + remaining_sprints))"
echo
echo "Next steps:"
echo "1. Review the remaining $remaining_individual file issues"
echo "2. Prioritize based on file size and criticality"
echo "3. Start refactoring with the largest/most critical files"
echo "4. The improved workflow will prevent future duplicates"

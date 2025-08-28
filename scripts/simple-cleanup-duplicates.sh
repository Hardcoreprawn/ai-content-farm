#!/bin/bash

# Simple cleanup script for duplicate large-file issues
# Closes duplicates while keeping the most recent one for each file

set -e

echo "🧹 Large File Issues Cleanup - Safe Mode"
echo "========================================"

# Step 1: Get all large-file issues
echo "📊 Analyzing current issues..."

total_issues=$(gh issue list --label "large-file" --state open --limit 300 | wc -l)
echo "Total large-file issues: $total_issues"

# Step 2: Find and close duplicate individual file issues
echo
echo "🔍 Finding duplicates..."

# Create a temporary file to track unique files
temp_file=$(mktemp)
duplicate_count=0

# Get all individual file issues, sorted by creation date (newest first)
gh issue list --label "large-file" --state open --limit 300 --json number,title,createdAt \
  | jq -r '.[] | select(.title | startswith("Refactor large file:")) | "\(.createdAt)|\(.number)|\(.title)"' \
  | sort -r | while IFS='|' read -r created_at number title; do

  # Extract file path from title
  file_path=$(echo "$title" | sed -n 's/Refactor large file: `\([^`]*\)`.*/\1/p')

  if [[ -n "$file_path" ]]; then
    # Check if we've seen this file before
    if grep -q "^$file_path$" "$temp_file" 2>/dev/null; then
      echo "  🗑️  Closing duplicate: #$number ($file_path)"
      gh issue close "$number" --comment "🤖 **Automated Cleanup**

This is a duplicate issue for file \`$file_path\`.

A more recent issue for this file already exists and remains open for tracking. Closing this duplicate to reduce noise in the backlog.

*Closed by automated cleanup script*" || echo "    ❌ Failed to close #$number"
      ((duplicate_count++))
    else
      echo "  ✅ Keeping: #$number ($file_path)"
      echo "$file_path" >> "$temp_file"
    fi
  fi
done

# Step 3: Clean up duplicate sprint summaries (keep only the most recent)
echo
echo "📋 Cleaning up sprint summaries..."

sprint_issues=$(gh issue list --label "large-file" --state open --limit 100 --json number,title,createdAt \
  | jq -r '.[] | select(.title | contains("Large File Refactoring Sprint:")) | "\(.createdAt)|\(.number)|\(.title)"' \
  | sort -r)

sprint_count=$(echo "$sprint_issues" | wc -l)

if [[ $sprint_count -gt 1 ]]; then
  echo "  Found $sprint_count sprint summaries, keeping the most recent..."

  # Keep the first (most recent), close the rest
  echo "$sprint_issues" | tail -n +2 | while IFS='|' read -r created_at number title; do
    echo "  🗑️  Closing duplicate sprint: #$number"
    gh issue close "$number" --comment "🤖 **Automated Cleanup**

This is a duplicate sprint summary issue.

A more recent sprint summary already exists and remains open. Closing this duplicate to reduce noise in the backlog.

*Closed by automated cleanup script*" || echo "    ❌ Failed to close #$number"
  done

  closed_sprint_count=$((sprint_count - 1))
else
  closed_sprint_count=0
fi

# Step 4: Final report
echo
echo "🎉 Cleanup Complete!"
echo "===================="

remaining_individual=$(gh issue list --label "large-file" --state open --limit 300 --json title \
  | jq '[.[] | select(.title | startswith("Refactor large file:"))] | length')

remaining_sprints=$(gh issue list --label "large-file" --state open --limit 100 --json title \
  | jq '[.[] | select(.title | contains("Large File Refactoring Sprint:"))] | length')

echo "📊 Results:"
echo "• Duplicate individual issues closed: $duplicate_count"
echo "• Duplicate sprint summaries closed: $closed_sprint_count"
echo "• Remaining individual file issues: $remaining_individual"
echo "• Remaining sprint summaries: $remaining_sprints"
echo "• Total remaining large-file issues: $((remaining_individual + remaining_sprints))"

# Cleanup
rm -f "$temp_file"

echo
echo "✅ Ready for systematic refactoring!"
echo "Next: Run './scripts/analyze-large-file-priorities.sh' to plan your work"

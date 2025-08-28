#!/bin/bash

# Batch cleanup of duplicate large-file issues
# Process in smaller batches to avoid API limits

set -e

echo "🧹 Batch Cleanup of Large File Duplicates"
echo "========================================"

# Get unique file paths and their most recent issue numbers
echo "📊 Finding duplicates..."

gh issue list --label "large-file" --state open --limit 200 --json number,title,createdAt \
  | jq -r '.[] | select(.title | startswith("Refactor large file:")) | "\(.createdAt)|\(.number)|\(.title)"' \
  | sort -r > /tmp/all_issues.txt

# Extract unique files and their most recent issues
awk -F'|' '{
    file = $3
    gsub(/Refactor large file: `([^`]*)`.*/, "\\1", file)
    gsub(/Refactor large file: `/, "", file)
    gsub(/`.*/, "", file)

    if (!seen[file]) {
        seen[file] = 1
        print "KEEP|" $2 "|" file
    } else {
        print "CLOSE|" $2 "|" file
    }
}' /tmp/all_issues.txt > /tmp/cleanup_plan.txt

keep_count=$(grep "^KEEP" /tmp/cleanup_plan.txt | wc -l)
close_count=$(grep "^CLOSE" /tmp/cleanup_plan.txt | wc -l)

echo "📋 Cleanup Plan:"
echo "• Files to keep (most recent): $keep_count"
echo "• Duplicates to close: $close_count"

echo
echo "🗑️  Closing duplicates in batches..."

batch_num=1
grep "^CLOSE" /tmp/cleanup_plan.txt | while read -r line; do
    action=$(echo "$line" | cut -d'|' -f1)
    issue_num=$(echo "$line" | cut -d'|' -f2)
    file_path=$(echo "$line" | cut -d'|' -f3)

    echo "  Batch $batch_num: Closing #$issue_num ($file_path)"

    gh issue close "$issue_num" --comment "🤖 **Automated Cleanup**

This is a duplicate issue for file \`$file_path\`.

A more recent issue for this file already exists and remains open for tracking. Closing this duplicate to reduce noise in the backlog.

*Closed by batch cleanup process*" && echo "    ✅ Closed" || echo "    ❌ Failed"

    ((batch_num++))

    # Small delay to avoid rate limits
    sleep 0.5
done

echo
echo "🧹 Cleaning up sprint summaries..."

# Close all but the most recent sprint summary
gh issue list --label "large-file" --state open --limit 100 --json number,title,createdAt \
  | jq -r '.[] | select(.title | contains("Large File Refactoring Sprint:")) | "\(.createdAt)|\(.number)"' \
  | sort -r | tail -n +2 | while IFS='|' read -r created_at number; do
    echo "  Closing sprint summary #$number"
    gh issue close "$number" --comment "🤖 **Automated Cleanup**

This is a duplicate sprint summary issue. A more recent sprint summary already exists and remains open.

*Closed by automated cleanup script*" && echo "    ✅ Closed" || echo "    ❌ Failed"
done

# Final report
echo
echo "🎉 Cleanup Complete!"
echo "===================="

remaining_files=$(gh issue list --label "large-file" --state open --limit 200 --json title \
  | jq '[.[] | select(.title | startswith("Refactor large file:"))] | length')

remaining_sprints=$(gh issue list --label "large-file" --state open --limit 100 --json title \
  | jq '[.[] | select(.title | contains("Large File Refactoring Sprint:"))] | length')

echo "📊 Final Status:"
echo "• Remaining individual file issues: $remaining_files"
echo "• Remaining sprint summaries: $remaining_sprints"
echo "• Total remaining large-file issues: $((remaining_files + remaining_sprints))"

# Cleanup temp files
rm -f /tmp/all_issues.txt /tmp/cleanup_plan.txt

echo
echo "✅ Ready for systematic refactoring!"

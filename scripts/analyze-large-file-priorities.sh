#!/bin/bash

# Analyze and prioritize large file refactoring backlog
# This script helps identify which files to tackle first

set -e

echo "📊 Large File Refactoring Priority Analysis"
echo "==========================================="

# Get all current large file issues
echo "📁 Analyzing current backlog..."

issues_data=$(gh issue list --label "large-file" --state open --limit 200 --json number,title,labels \
    | jq '[.[] | select(.title | startswith("Refactor large file:"))]')

if [[ $(echo "$issues_data" | jq 'length') -eq 0 ]]; then
    echo "✅ No large file issues found!"
    exit 0
fi

echo
echo "🎯 Priority Breakdown:"
echo "====================="

# Extract and categorize files by size
critical_files=$(echo "$issues_data" | jq -r '.[] | select(.title | contains("lines)")) | .title' \
    | sed -n 's/Refactor large file: `\([^`]*\)` (\([0-9]*\) lines)/\2:\1/p' \
    | awk -F: '$1 > 1000 {print $0}' | sort -nr)

warning_files=$(echo "$issues_data" | jq -r '.[] | select(.title | contains("lines)")) | .title' \
    | sed -n 's/Refactor large file: `\([^`]*\)` (\([0-9]*\) lines)/\2:\1/p' \
    | awk -F: '$1 > 600 && $1 <= 1000 {print $0}' | sort -nr)

large_files=$(echo "$issues_data" | jq -r '.[] | select(.title | contains("lines)")) | .title' \
    | sed -n 's/Refactor large file: `\([^`]*\)` (\([0-9]*\) lines)/\2:\1/p' \
    | awk -F: '$1 > 500 && $1 <= 600 {print $0}' | sort -nr)

# Count by category
critical_count=$(echo "$critical_files" | grep -c . || echo "0")
warning_count=$(echo "$warning_files" | grep -c . || echo "0")
large_count=$(echo "$large_files" | grep -c . || echo "0")
total_count=$((critical_count + warning_count + large_count))

echo "🔴 CRITICAL (>1000 lines): $critical_count files"
echo "🟡 WARNING (600-1000 lines): $warning_count files"
echo "🟠 LARGE (500-600 lines): $large_count files"
echo "📊 TOTAL: $total_count files"

echo
echo "🚨 CRITICAL Priority Files (Start Here!):"
echo "========================================="
if [[ $critical_count -gt 0 ]]; then
    echo "$critical_files" | while IFS=':' read -r lines file; do
        echo "• $file ($lines lines)"
    done
else
    echo "✅ No critical files!"
fi

echo
echo "⚠️  WARNING Priority Files:"
echo "==========================="
if [[ $warning_count -gt 0 ]]; then
    echo "$warning_files" | head -10 | while IFS=':' read -r lines file; do
        echo "• $file ($lines lines)"
    done
    if [[ $warning_count -gt 10 ]]; then
        echo "... and $((warning_count - 10)) more"
    fi
else
    echo "✅ No warning files!"
fi

echo
echo "📈 File Type Analysis:"
echo "====================="

# Analyze by file type
echo "$issues_data" | jq -r '.[] | .title' | sed -n 's/Refactor large file: `\([^`]*\)` .*/\1/p' | while read -r file; do
    echo "${file##*.}"
done | sort | uniq -c | sort -nr | head -10 | while read -r count ext; do
    echo "• .$ext files: $count"
done

echo
echo "📁 Container Service Analysis:"
echo "============================="

container_files=$(echo "$issues_data" | jq -r '.[] | .title' | sed -n 's/Refactor large file: `\([^`]*\)` .*/\1/p' | grep "^containers/" || echo "")

if [[ -n "$container_files" ]]; then
    echo "$container_files" | cut -d'/' -f2 | sort | uniq -c | sort -nr | while read -r count service; do
        echo "• $service: $count files"
    done
else
    echo "✅ No container service files!"
fi

echo
echo "🎯 Recommended Action Plan:"
echo "=========================="
echo "1. **Start with CRITICAL files** (>1000 lines) - highest impact"
echo "2. **Focus on container services** - affects system architecture"
echo "3. **Tackle Python files first** - likely to have the most refactoring opportunities"
echo "4. **Break down by service** - work on one microservice at a time"
echo "5. **Update tests last** - ensure functionality is preserved first"

echo
echo "⚡ Quick Wins (Files to tackle first):"
echo "====================================="

# Find the top 5 most critical files that are likely quick wins
echo "$critical_files" | head -5 | while IFS=':' read -r lines file; do
    case "$file" in
        *.py)
            echo "🐍 $file ($lines lines) - Python refactoring tools available"
            ;;
        *.yml|*.yaml)
            echo "📝 $file ($lines lines) - YAML can be split into multiple files"
            ;;
        *.md)
            echo "📖 $file ($lines lines) - Documentation can be reorganized"
            ;;
        *)
            echo "📄 $file ($lines lines) - Consider modularization"
            ;;
    esac
done

echo
echo "📋 Next Steps:"
echo "=============="
echo "1. Run: make test  # Ensure all tests pass before refactoring"
echo "2. Pick the top critical file and create a refactoring plan"
echo "3. Use git feature branches for each refactoring"
echo "4. Maintain backward compatibility"
echo "5. Update documentation as you go"

total_lines=$(echo "$critical_files $warning_files $large_files" | tr ' ' '\n' | cut -d':' -f1 | paste -sd+ | bc)
target_reduction=$((total_lines - (total_count * 500)))

echo
echo "📊 Impact Metrics:"
echo "=================="
echo "• Total lines in large files: $total_lines"
echo "• Target after refactoring: $((total_count * 500)) lines (500 per file)"
echo "• Lines to reduce: $target_reduction ($(((target_reduction * 100) / total_lines))% reduction)"
echo "• Estimated effort: $((total_count / 5)) weeks (assuming 1 file per day)"

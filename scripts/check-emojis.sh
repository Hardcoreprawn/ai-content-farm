#!/bin/bash

# Script to check for emojis in YAML files
# Emojis cause encoding issues in CI/CD pipelines and should be avoided

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check for emojis in a file
check_file_for_emojis() {
    local file="$1"
    local found_emojis=0

    # Check for common emojis that might appear in CI/CD scripts
    # This regex catches most Unicode emoji ranges
    if grep -P '[\x{1F300}-\x{1F5FF}\x{1F600}-\x{1F64F}\x{1F680}-\x{1F6FF}\x{1F700}-\x{1F77F}\x{1F780}-\x{1F7FF}\x{1F800}-\x{1F8FF}\x{1F900}-\x{1F9FF}\x{1FA00}-\x{1FA6F}\x{1FA70}-\x{1FAFF}\x{2600}-\x{26FF}\x{2700}-\x{27BF}]' "$file" > /dev/null 2>&1; then
        echo -e "${RED}FAIL${NC}: Found emojis in $file"

        # Show the lines with emojis
        while IFS= read -r line_info; do
            local line_num=$(echo "$line_info" | cut -d: -f1)
            local line_content=$(echo "$line_info" | cut -d: -f2-)
            echo "  Line $line_num: $line_content"
        done < <(grep -nP '[\x{1F300}-\x{1F5FF}\x{1F600}-\x{1F64F}\x{1F680}-\x{1F6FF}\x{1F700}-\x{1F77F}\x{1F780}-\x{1F7FF}\x{1F800}-\x{1F8FF}\x{1F900}-\x{1F9FF}\x{1FA00}-\x{1FA6F}\x{1FA70}-\x{1FAFF}\x{2600}-\x{26FF}\x{2700}-\x{27BF}]' "$file")

        found_emojis=1
    fi

    return $found_emojis
}

# Main function
main() {
    local exit_code=0
    local total_files=0
    local files_with_emojis=0

    echo "Checking YAML files for emojis..."
    echo "Emojis cause encoding issues in CI/CD pipelines and should be avoided."
    echo ""

    # Find all YAML files in .github directory
    if [ -d ".github" ]; then
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                total_files=$((total_files + 1))

                if ! check_file_for_emojis "$file"; then
                    files_with_emojis=$((files_with_emojis + 1))
                    exit_code=1
                fi
            fi
        done < <(find .github -type f \( -name "*.yml" -o -name "*.yaml" \))
    else
        echo "Warning: .github directory not found"
    fi

    echo ""
    echo "Summary:"
    echo "  Total YAML files checked: $total_files"
    echo "  Files with emojis: $files_with_emojis"

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}PASS${NC}: No emojis found in YAML files"
    else
        echo -e "${RED}FAIL${NC}: Found emojis in $files_with_emojis file(s)"
        echo ""
        echo "To fix these issues:"
        echo "1. Replace emojis with descriptive text like [PASS], [FAIL], [WARN]"
        echo "2. Use plain text descriptions instead of emojis"
        echo "3. Consider using status indicators like ✓/✗ only in markdown files"
        echo ""
        echo "Example replacements:"
        echo "  🔍 -> [SCAN]"
        echo "  ✅ -> [PASS]"
        echo "  ❌ -> [FAIL]"
        echo "  ⚠️ -> [WARN]"
        echo "  🐳 -> [CONTAINER]"
        echo "  📊 -> [STATS]"
    fi

    exit $exit_code
}

# Run main function
main "$@"

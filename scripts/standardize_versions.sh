#!/bin/bash
# Script to standardize dependency versions across all containers
# DEPRECATED: Use standardize_versions.py with shared-versions.toml instead

set -e

echo "⚠️  DEPRECATED: This script uses the old shared-versions.txt format"
echo "📝 Please use: python scripts/standardize_versions.py"
echo "🔧 Which uses: shared-versions.toml"
echo ""
echo "🚫 Exiting..."
exit 1

CONTAINER_DIR="containers"
SHARED_VERSIONS_FILE="shared-versions.toml"

# Read shared versions into associative array
declare -A SHARED_VERSIONS
while IFS='=' read -r package version || [[ -n "$package" ]]; do
    # Skip empty lines and comments
    if [[ -z "$package" ]] || [[ "$package" =~ ^#.* ]] || [[ -z "$version" ]]; then
        continue
    fi

    # Clean up whitespace
    package=$(echo "$package" | xargs)
    version=$(echo "$version" | xargs)

    SHARED_VERSIONS["$package"]="$version"
done < "$SHARED_VERSIONS_FILE"

echo "📋 Loaded ${#SHARED_VERSIONS[@]} shared versions"

standardize_file() {
    local file="$1"
    local temp_file=$(mktemp)
    local changed=false

    while IFS= read -r line; do
        # Skip empty lines and comments
        if [[ -z "$line" ]] || [[ "$line" =~ ^#.* ]]; then
            echo "$line" >> "$temp_file"
            continue
        fi

        # Extract package name (handle ~ and == patterns)
        package=""
        if [[ "$line" =~ ^([a-zA-Z0-9_\[\]-]+)[~=] ]]; then
            package="${BASH_REMATCH[1]}"
        fi

        # Check if we have a shared version for this package
        if [[ -n "$package" ]] && [[ -n "${SHARED_VERSIONS[$package]:-}" ]]; then
            new_line="${package}~=${SHARED_VERSIONS[$package]}"
            if [[ "$line" != "$new_line" ]]; then
                echo "  📝 $package: $line → $new_line"
                changed=true
            fi
            echo "$new_line" >> "$temp_file"
        else
            echo "$line" >> "$temp_file"
        fi
    done < "$file"

    if [[ "$changed" == true ]]; then
        mv "$temp_file" "$file"
        return 0
    else
        rm "$temp_file"
        return 1
    fi
}

standardize_container() {
    local container_name="$1"
    local container_path="${CONTAINER_DIR}/${container_name}"

    echo "🔄 Standardizing $container_name..."

    local files_changed=0

    # Check production requirements
    if [[ -f "${container_path}/requirements-prod.txt" ]]; then
        if standardize_file "${container_path}/requirements-prod.txt"; then
            ((files_changed++))
        fi
    fi

    # Check test requirements
    if [[ -f "${container_path}/requirements-test.txt" ]]; then
        if standardize_file "${container_path}/requirements-test.txt"; then
            ((files_changed++))
        fi
    fi

    # Check legacy requirements.txt
    if [[ -f "${container_path}/requirements.txt" ]]; then
        if standardize_file "${container_path}/requirements.txt"; then
            ((files_changed++))
        fi
    fi

    if [[ $files_changed -eq 0 ]]; then
        echo "  ✅ No changes needed"
    else
        echo "  ✅ Updated $files_changed file(s)"
    fi
}

# Main execution
echo "🚀 Standardizing dependency versions across all containers..."
echo ""

for container_dir in ${CONTAINER_DIR}/*/; do
    if [[ -d "$container_dir" ]]; then
        container_name=$(basename "$container_dir")
        if [[ "$container_name" != "base" ]]; then
            standardize_container "$container_name"
        fi
    fi
done

echo ""
echo "🎉 Version standardization complete!"
echo ""
echo "📋 Summary of shared versions applied:"
for package in "${!SHARED_VERSIONS[@]}"; do
    echo "  $package == ${SHARED_VERSIONS[$package]}"
done | sort

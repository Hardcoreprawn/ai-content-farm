#!/bin/bash
# DEPRECATED: Script to split requirements.txt into production and test dependencies
# Use standardize_versions.py with shared-versions.toml instead

set -e

echo "⚠️  DEPRECATED: This script is no longer needed"
echo "📝 Use: python scripts/standardize_versions.py"
echo "🔧 Which uses: shared-versions.toml for version management"
echo ""
echo "🚫 Exiting..."
exit 1

CONTAINER_DIR="containers"
SHARED_VERSIONS_FILE="shared-versions.toml"

# Test dependencies to move to requirements-test.txt
TEST_DEPS=(
    "pytest"
    "pytest-asyncio"
    "pytest-cov"
    "pytest-xdist"
    "black"
    "isort"
    "mypy"
    "types-"
    "coverage"
)

split_requirements() {
    local container_name=$1
    local req_file="${CONTAINER_DIR}/${container_name}/requirements.txt"
    local prod_file="${CONTAINER_DIR}/${container_name}/requirements-prod.txt"
    local test_file="${CONTAINER_DIR}/${container_name}/requirements-test.txt"

    if [[ ! -f "$req_file" ]]; then
        echo "❌ No requirements.txt found for $container_name"
        return 1
    fi

    echo "📦 Processing $container_name..."

    # Create production requirements (exclude test dependencies)
    echo "# Production dependencies for $container_name" > "$prod_file"
    echo "# Auto-generated from requirements.txt - do not edit manually" >> "$prod_file"
    echo "" >> "$prod_file"

    # Create test requirements
    echo "# Test dependencies for $container_name" > "$test_file"
    echo "# Auto-generated from requirements.txt - do not edit manually" >> "$test_file"
    echo "" >> "$test_file"

    # Process each line in requirements.txt
    while IFS= read -r line; do
        # Skip empty lines and comments
        if [[ -z "$line" ]] || [[ "$line" =~ ^#.* ]]; then
            continue
        fi

        # Check if this is a test dependency
        is_test_dep=false
        for test_dep in "${TEST_DEPS[@]}"; do
            if [[ "$line" =~ ^${test_dep} ]]; then
                echo "$line" >> "$test_file"
                is_test_dep=true
                break
            fi
        done

        # If not a test dependency, add to production
        if [[ "$is_test_dep" == false ]]; then
            echo "$line" >> "$prod_file"
        fi

    done < "$req_file"

    echo "✅ Created $prod_file and $test_file"
}

update_dockerfile() {
    local container_name=$1
    local dockerfile="${CONTAINER_DIR}/${container_name}/Dockerfile"

    if [[ ! -f "$dockerfile" ]]; then
        echo "❌ No Dockerfile found for $container_name"
        return 1
    fi

    # Update Dockerfile to use requirements-prod.txt instead of requirements.txt
    if grep -q "requirements\.txt" "$dockerfile"; then
        echo "🐳 Updating Dockerfile for $container_name..."
        sed -i 's/requirements\.txt/requirements-prod.txt/g' "$dockerfile"
        echo "✅ Updated $dockerfile"
    fi
}

# Main execution
if [[ $# -eq 0 ]]; then
    echo "🚀 Processing all containers..."
    for container_dir in ${CONTAINER_DIR}/*/; do
        if [[ -d "$container_dir" ]]; then
            container_name=$(basename "$container_dir")
            if [[ "$container_name" != "base" ]]; then
                split_requirements "$container_name"
                update_dockerfile "$container_name"
                echo ""
            fi
        fi
    done
else
    container_name=$1
    split_requirements "$container_name"
    update_dockerfile "$container_name"
fi

echo "🎉 Requirements splitting complete!"
echo ""
echo "📋 Next steps:"
echo "1. Review the generated requirements-prod.txt and requirements-test.txt files"
echo "2. Test that containers build successfully with new requirements"
echo "3. Update version inconsistencies using containers/shared-versions.txt as reference"
echo "4. Commit the changes"

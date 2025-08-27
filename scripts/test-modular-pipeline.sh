#!/bin/bash
set -e

echo "🧪 Testing Modular CI/CD Pipeline"
echo "=================================="

# Function to create a test commit and push
create_test_commit() {
    local test_type="$1"
    local test_description="$2"
    shift 2
    local files=("$@")

    echo ""
    echo "📝 Test: $test_type"
    echo "Description: $test_description"
    echo "Files to modify: ${files[*]}"

    # Create or modify test files
    for file in "${files[@]}"; do
        if [[ "$file" == *.md ]]; then
            echo "<!-- Test change $(date) -->" >> "$file"
        elif [[ "$file" == *.py ]]; then
            echo "# Test change $(date)" >> "$file"
        elif [[ "$file" == *.yml ]] || [[ "$file" == *.yaml ]]; then
            echo "# Test change $(date)" >> "$file"
        elif [[ "$file" == *.tf ]]; then
            echo "# Test change $(date)" >> "$file"
        else
            echo "Test change $(date)" >> "$file"
        fi
        echo "  ✓ Modified $file"
    done

    # Commit and push
    git add "${files[@]}"
    git commit -m "test($test_type): $test_description

This is a test commit to validate the modular CI/CD pipeline behavior
for $test_type changes. Expected pipeline behavior:

$(case "$test_type" in
    "docs-only") echo "- Skip deployment completely
- Only run workflow validation" ;;
    "container-single") echo "- Test only changed container
- Build only changed container
- Fast deployment via Azure CLI" ;;
    "container-multiple") echo "- Test changed containers in parallel
- Build changed containers in parallel
- Fast deployment via Azure CLI" ;;
    "infrastructure") echo "- Run full quality checks
- Full Terraform deployment
- Complete validation suite" ;;
    "mixed") echo "- Test changed containers
- Run infrastructure quality checks
- Full Terraform deployment" ;;
esac)"

    echo "  ✓ Committed changes"

    # Ask user if they want to push
    read -p "Push this commit to trigger the pipeline? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin main
        echo "  ✅ Pushed to trigger pipeline"
        echo "  🔗 Monitor at: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\([^.]*\).*/\1/')/actions"

        # Wait for user to check results
        read -p "Press Enter after checking the pipeline results..." -r
    else
        echo "  ⏸️ Skipped push - commit is staged for later testing"
    fi
}

# Test scenarios
echo "🔍 Available test scenarios:"
echo "1. Documentation-only changes (should skip deployment)"
echo "2. Single container change (should use fast path)"
echo "3. Multiple container changes (should test/build in parallel)"
echo "4. Infrastructure-only changes (should use Terraform path)"
echo "5. Mixed changes (should use Terraform path)"
echo "6. Library changes (should affect all containers)"

read -p "Which test would you like to run? (1-6): " test_choice

case $test_choice in
    1)
        create_test_commit "docs-only" "documentation update to test skip deployment" \
            "docs/README.md" "README.md"
        ;;
    2)
        echo "Available containers:"
        echo "- content-collector"
        echo "- content-enricher"
        echo "- content-generator"
        echo "- content-processor"
        echo "- content-ranker"
        echo "- markdown-generator"
        echo "- site-generator"
        echo "- collector-scheduler"

        read -p "Which container to modify? " container_name

        if [[ -d "containers/$container_name" ]]; then
            create_test_commit "container-single" "single container update for $container_name" \
                "containers/$container_name/main.py"
        else
            echo "❌ Container not found: $container_name"
            exit 1
        fi
        ;;
    3)
        create_test_commit "container-multiple" "multiple container updates to test parallel execution" \
            "containers/content-collector/main.py" \
            "containers/content-enricher/main.py"
        ;;
    4)
        create_test_commit "infrastructure" "infrastructure change to test Terraform path" \
            "infra/variables.tf"
        ;;
    5)
        create_test_commit "mixed" "mixed container and infrastructure changes" \
            "containers/content-collector/main.py" \
            "infra/container_apps.tf"
        ;;
    6)
        create_test_commit "library" "library change affecting all containers" \
            "libs/blob_storage.py"
        ;;
    *)
        echo "❌ Invalid choice: $test_choice"
        exit 1
        ;;
esac

echo ""
echo "🎉 Test scenario completed!"
echo ""
echo "📊 Expected Pipeline Behavior:"
case $test_choice in
    1) echo "- ⏭️ Skip deployment (docs-only changes)"
       echo "- ✅ Only workflow validation should run" ;;
    2) echo "- 🎯 Test single container: $container_name"
       echo "- 🏗️ Build single container: $container_name"
       echo "- ⚡ Fast deployment via Azure CLI (2-3 minutes)" ;;
    3) echo "- 🎯 Test multiple containers in parallel"
       echo "- 🏗️ Build multiple containers in parallel"
       echo "- ⚡ Fast deployment via Azure CLI (2-3 minutes)" ;;
    4) echo "- 🔒 Infrastructure quality checks"
       echo "- 🏗️ Full Terraform deployment (6-8 minutes)"
       echo "- 📋 Complete validation suite" ;;
    5) echo "- 🎯 Test changed containers"
       echo "- 🔒 Infrastructure quality checks"
       echo "- 🏗️ Full Terraform deployment (6-8 minutes)" ;;
    6) echo "- 🎯 Test ALL containers (library affects all)"
       echo "- 🏗️ Build ALL containers"
       echo "- ⚡ Fast deployment via Azure CLI" ;;
esac

echo ""
echo "🔍 Monitor the pipeline to verify:"
echo "- Correct jobs are triggered/skipped"
echo "- Matrix execution for changed containers only"
echo "- Appropriate deployment method is used"
echo "- Execution time matches expectations"

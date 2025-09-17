#!/bin/bash
#
# Terraform Container Image Discovery with Fallback
#
# This script discovers containers and returns image URLs with fallback logic.
# For commit hash tags, it falls back to a stable tag (latest/main).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINERS_SCRIPT="$SCRIPT_DIR/discover-containers.sh"
IMAGE_CHECK_SCRIPT="$SCRIPT_DIR/check-container-image.sh"

# Parse JSON input from Terraform (external data source query)
if [[ $# -eq 0 ]]; then
    # Read from stdin when called by Terraform
    input=$(cat)
    IMAGE_TAG=$(echo "$input" | jq -r '.image_tag // "latest"')
    FALLBACK_STRATEGY=$(echo "$input" | jq -r '.image_fallback_strategy // "latest"')
else
    # Allow command line usage for testing
    IMAGE_TAG="${1:-latest}"
    FALLBACK_STRATEGY="${2:-latest}"
fi

# Get containers as JSON array (suppress stderr to avoid Terraform warnings)
containers_json=$("$CONTAINERS_SCRIPT" --json 2>/dev/null)

# Parse containers
containers=$(echo "$containers_json" | jq -r '.[]')

# Build result object
result="{"
first=true

for container in $containers; do
    if [[ "$first" == "true" ]]; then
        first=false
    else
        result+=","
    fi

    # Check image and get fallback URL (suppress stderr)
    image_result=$("$IMAGE_CHECK_SCRIPT" "$container" "$IMAGE_TAG" "$FALLBACK_STRATEGY" 2>/dev/null || echo "{\"image_url\": \"ghcr.io/hardcoreprawn/ai-content-farm/${container}:${IMAGE_TAG}\"}")
    image_url=$(echo "$image_result" | jq -r '.image_url')

    result+="\"${container}\": \"${image_url}\""
done

result+="}"

echo "$result"

#!/bin/bash
#
# Terraform Container Discovery Wrapper
#
# This script provides container discovery in the format expected by Terraform's external data source.
# The external data source expects a JSON object with string values only.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINERS_SCRIPT="$SCRIPT_DIR/discover-containers.sh"

# Get containers as JSON array (suppress stderr to avoid Terraform warnings)
containers_json=$("$CONTAINERS_SCRIPT" --json 2>/dev/null)

# Convert JSON array to comma-separated string and create JSON object with string values
containers_string=$(echo "$containers_json" | jq -r 'join(",")')

# Output JSON object with string values only
echo "{\"containers\": \"$containers_string\"}"

#!/bin/bash
#
# Container Discovery Script
#
# Dynamically discovers all valid container directories in the project.
# Used by CI/CD pipelines to ensure we only test containers that actually exist.
#
# Usage:
#   ./scripts/discover-containers.sh [--json|--list|--count]
#
# Options:
#   --json    Output as JSON array (default)
#   --list    Output as space-separated list
#   --count   Output just the count
#   --help    Show this help

set -euo pipefail

# Default output format
OUTPUT_FORMAT="json"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONTAINERS_DIR="$PROJECT_ROOT/containers"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --json)
      OUTPUT_FORMAT="json"
      shift
      ;;
    --list)
      OUTPUT_FORMAT="list"
      shift
      ;;
    --count)
      OUTPUT_FORMAT="count"
      shift
      ;;
    --help)
      echo "Container Discovery Script"
      echo ""
      echo "Usage: $0 [--json|--list|--count|--help]"
      echo ""
      echo "Options:"
      echo "  --json    Output as JSON array (default)"
      echo "  --list    Output as space-separated list"
      echo "  --count   Output just the count"
      echo "  --help    Show this help"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Use --help for usage information" >&2
      exit 1
      ;;
  esac
done

# Function to discover containers
discover_containers() {
  local containers=()

  if [[ ! -d "$CONTAINERS_DIR" ]]; then
    echo "Error: Containers directory '$CONTAINERS_DIR' not found" >&2
    exit 1
  fi

  # Find all directories with Dockerfiles
  while IFS= read -r -d '' container_dir; do
    container_name="$(basename "$container_dir")"

    # Skip special directories
    if [[ "$container_name" == "base" ||
          "$container_name" == "__pycache__" ||
          "$container_name" == "." ||
          "$container_name" == ".." ]]; then
      continue
    fi

    # Verify it has a Dockerfile
    if [[ -f "$container_dir/Dockerfile" ]]; then
      containers+=("$container_name")
      echo "[DISCOVERY] Found container: $container_name" >&2
    else
      echo "[WARNING] Skipping $container_name: No Dockerfile found" >&2
    fi
  done < <(find "$CONTAINERS_DIR" -mindepth 1 -maxdepth 1 -type d -print0)

  # Sort containers for consistent output
  IFS=$'\n' containers=($(sort <<<"${containers[*]}"))
  unset IFS

  echo "${containers[@]}"
}

# Discover containers
containers=($(discover_containers))
container_count=${#containers[@]}

echo "[INFO] Discovered $container_count containers: ${containers[*]}" >&2

# Output in requested format
case $OUTPUT_FORMAT in
  json)
    printf '%s\n' "${containers[@]}" | jq -R . | jq -s .
    ;;
  list)
    printf '%s\n' "${containers[*]}"
    ;;
  count)
    printf '%d\n' "$container_count"
    ;;
esac

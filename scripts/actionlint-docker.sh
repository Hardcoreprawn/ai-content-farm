#!/bin/bash
# Run actionlint using Docker for pre-commit hooks

set -e

echo "🔍 Running actionlint via Docker..."

# Run actionlint in Docker container
docker run --rm -v "${PWD}:/repo" -w /repo rhysd/actionlint:latest -color "$@"

echo "✅ actionlint completed successfully"

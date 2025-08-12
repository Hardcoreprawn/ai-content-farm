#!/bin/bash
set -euo pipefail

# Create standardized blob container structure
# Usage: ./create-blob-containers.sh <storage-account-name>

STORAGE_ACCOUNT=${1:-"hottopicsstoraget0t36m"}

echo "Creating standardized blob container structure in: $STORAGE_ACCOUNT"

# Core processing containers
containers=(
    "topic-collection-queue"
    "topic-collection-complete"
    "content-ranking-queue"
    "content-ranking-complete"
    "content-enrichment-queue"
    "content-enrichment-complete"
    "content-publishing-queue"
    "published-articles"
    "job-status"
    "processing-errors"
    "dead-letter-queue"
)

for container in "${containers[@]}"; do
    echo "Creating container: $container"
    az storage container create \
        --name "$container" \
        --account-name "$STORAGE_ACCOUNT" \
        --auth-mode login \
        --public-access off
done

echo "✅ Container structure created successfully"
echo ""
echo "Created containers:"
az storage container list \
    --account-name "$STORAGE_ACCOUNT" \
    --auth-mode login \
    --query "[].name" \
    --output table

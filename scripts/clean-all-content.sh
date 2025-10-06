#!/bin/bash
set -e

# Clean All Generated Content
# Removes all processed content and static site files for a clean rebuild

STORAGE_ACCOUNT="aicontentprodstkwakpx"
RESOURCE_GROUP="ai-content-prod-rg"

echo "⚠️  WARNING: This will DELETE all processed content and static site files!"
echo ""
echo "This includes:"
echo "  - All processed-content blobs (~3,348 items)"
echo "  - All static site files in \$web container (~344 items)"
echo ""
echo "Collected content (raw) will NOT be deleted."
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Cancelled"
    exit 1
fi

echo ""
echo "🔑 Getting storage connection string..."
CONN_STRING=$(az storage account show-connection-string \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --query connectionString -o tsv)

echo ""
echo "🗑️  Deleting processed-content blobs..."
PROCESSED_COUNT=$(az storage blob list \
    --container-name processed-content \
    --connection-string "$CONN_STRING" \
    --query "length(@)" -o tsv)

echo "Found $PROCESSED_COUNT blobs to delete..."

if [ "$PROCESSED_COUNT" -gt 0 ]; then
    # Delete in batches using batch delete for efficiency
    az storage blob delete-batch \
        --source processed-content \
        --connection-string "$CONN_STRING" \
        --pattern "*" \
        --output none
    echo "✅ Deleted processed-content blobs"
else
    echo "✅ No processed-content blobs to delete"
fi

echo ""
echo "🗑️  Deleting static site files..."
WEB_COUNT=$(az storage blob list \
    --container-name '$web' \
    --connection-string "$CONN_STRING" \
    --query "length(@)" -o tsv)

echo "Found $WEB_COUNT files to delete..."

if [ "$WEB_COUNT" -gt 0 ]; then
    az storage blob delete-batch \
        --source '$web' \
        --connection-string "$CONN_STRING" \
        --pattern "*" \
        --output none
    echo "✅ Deleted static site files"
else
    echo "✅ No static site files to delete"
fi

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Next steps:"
echo "1. Trigger reprocessing: curl -X POST https://ai-content-prod-collector.whitecliff-6844954b.uksouth.azurecontainerapps.io/reprocess -H 'Content-Type: application/json' -d '{\"dry_run\": false}'"
echo "2. Monitor progress with ./scripts/monitor-reprocessing.sh"
echo "3. Wait for site generation to complete"

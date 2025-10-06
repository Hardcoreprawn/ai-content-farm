#!/bin/bash
# Clean rebuild script for AI Content Farm
# This script clears all static site content and processed articles for a fresh rebuild

set -e  # Exit on error

echo "🧹 AI Content Farm - Clean Rebuild Script"
echo "=========================================="
echo ""

# Configuration
STATIC_STORAGE_ACCOUNT="aicontentprodstkwakpx"
CONTENT_STORAGE_ACCOUNT="aicontentprodstkwakpx"
STATIC_CONTAINER='$web'
PROCESSED_CONTAINER="processed-content"
COLLECTOR_ENDPOINT="https://ai-content-prod-collector.whitecliff-6844954b.uksouth.azurecontainerapps.io"
SITEGEN_ENDPOINT="https://ai-content-prod-site-gen.whitecliff-6844954b.uksouth.azurecontainerapps.io"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to prompt for confirmation
confirm() {
    local prompt="$1"
    local response

    while true; do
        read -p "$prompt (yes/no): " response
        case "$response" in
            [Yy]|[Yy][Ee][Ss])
                return 0
                ;;
            [Nn]|[Nn][Oo])
                return 1
                ;;
            *)
                echo "Please answer yes or no."
                ;;
        esac
    done
}

# Step 1: Clear static site articles
echo -e "${YELLOW}Step 1: Clear Static Site Articles${NC}"
echo "This will delete ALL article HTML files from the static site."
echo "Container: $STATIC_CONTAINER"
echo ""

if confirm "Delete all articles from static site?"; then
    echo "Deleting articles..."
    az storage blob delete-batch \
        --account-name "$STATIC_STORAGE_ACCOUNT" \
        --source "$STATIC_CONTAINER" \
        --pattern "articles/*" \
        --auth-mode login \
        2>&1 | grep -v "WARNING" || true

    echo -e "${GREEN}✓ Static site articles cleared${NC}"
else
    echo -e "${YELLOW}⊘ Skipped static site cleanup${NC}"
fi

echo ""

# Step 2: Clear index pages
echo -e "${YELLOW}Step 2: Clear Index Pages${NC}"
echo "This will delete index.html and paginated pages."
echo ""

if confirm "Delete index pages from static site?"; then
    echo "Deleting index pages..."
    az storage blob delete-batch \
        --account-name "$STATIC_STORAGE_ACCOUNT" \
        --source "$STATIC_CONTAINER" \
        --pattern "index.html" \
        --auth-mode login \
        2>&1 | grep -v "WARNING" || true

    az storage blob delete-batch \
        --account-name "$STATIC_STORAGE_ACCOUNT" \
        --source "$STATIC_CONTAINER" \
        --pattern "page-*.html" \
        --auth-mode login \
        2>&1 | grep -v "WARNING" || true

    echo -e "${GREEN}✓ Index pages cleared${NC}"
else
    echo -e "${YELLOW}⊘ Skipped index page cleanup${NC}"
fi

echo ""

# Step 3: Clear processed content (optional - forces reprocess)
echo -e "${YELLOW}Step 3: Clear Processed Content (OPTIONAL)${NC}"
echo "This will delete ALL processed articles, forcing full reprocessing."
echo "This means ALL collected content will be regenerated with new metadata."
echo "Container: $PROCESSED_CONTAINER"
echo ""
echo -e "${RED}WARNING: This will trigger reprocessing of ALL content!${NC}"
echo "Cost estimate: 577 items × $0.0016 ≈ $0.93"
echo ""

if confirm "Clear processed content and force full reprocess?"; then
    echo "Deleting processed content..."
    az storage blob delete-batch \
        --account-name "$CONTENT_STORAGE_ACCOUNT" \
        --source "$PROCESSED_CONTAINER" \
        --auth-mode login \
        2>&1 | grep -v "WARNING" || true

    # Mark that reprocessing is needed
    touch /tmp/reprocess_needed

    echo -e "${GREEN}✓ Processed content cleared - full reprocess will occur${NC}"
else
    echo -e "${YELLOW}⊘ Skipped processed content cleanup - will use existing articles${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✓ Cleanup complete!${NC}"
echo ""

# Step 4: Trigger reprocessing (if processed content was cleared)
if [ -f /tmp/reprocess_needed ]; then
    echo -e "${YELLOW}Step 4: Trigger Reprocessing${NC}"
    echo "Queuing all 577 collected items for reprocessing..."
    echo ""

    # First show dry run
    echo "Running DRY RUN to estimate impact..."
    DRY_RESPONSE=$(curl -X POST "$COLLECTOR_ENDPOINT/reprocess" \
        -H "Content-Type: application/json" \
        -d '{"dry_run": true}' \
        -s)

    TOTAL=$(echo "$DRY_RESPONSE" | jq -r '.data.collections_queued // 0')
    COST=$(echo "$DRY_RESPONSE" | jq -r '.data.estimated_cost // "unknown"')
    TIME=$(echo "$DRY_RESPONSE" | jq -r '.data.estimated_time // "unknown"')

    echo "  Collections to process: $TOTAL"
    echo "  Estimated cost: $COST"
    echo "  Estimated time: $TIME"
    echo ""
    echo -e "${RED}⚠️  WARNING: This will actually send queue messages and cost money!${NC}"
    echo ""

    if confirm "Queue all collections for reprocessing now?"; then
        echo "Triggering ACTUAL reprocess (dry_run=false)..."

        RESPONSE=$(curl -X POST "$COLLECTOR_ENDPOINT/reprocess" \
            -H "Content-Type: application/json" \
            -d '{"dry_run": false}' \
            -s)

        # Parse response
        QUEUED=$(echo "$RESPONSE" | jq -r '.data.collections_queued // 0')
        ACTUAL_COST=$(echo "$RESPONSE" | jq -r '.data.estimated_cost // "unknown"')

        echo -e "${GREEN}✓ Queued $QUEUED collections for reprocessing${NC}"
        echo "  Actual cost: $ACTUAL_COST"
        echo ""
        echo "Monitor processing at:"
        echo "  Azure Portal → Container Apps → content-processor → Log Stream"
        rm /tmp/reprocess_needed
    else
        echo -e "${YELLOW}⊘ Skipped automatic reprocessing${NC}"
        echo "You can trigger it manually later with:"
        echo "  curl -X POST \"$COLLECTOR_ENDPOINT/reprocess\" -H 'Content-Type: application/json' -d '{\"dry_run\": false}'"
    fi
    echo ""
fi

echo "Next steps:"
if [ ! -f /tmp/reprocess_needed ]; then
    echo "1. Wait for reprocessing to complete (~1 hour for 577 items)"
    echo "2. Trigger site generator to rebuild HTML pages"
else
    echo "1. Trigger reprocessing manually (see command above)"
    echo "2. Wait for processing to complete"
    echo "3. Trigger site generator"
fi
echo "3. Verify results at: https://aicontentprodstkwakpx.z33.web.core.windows.net/"
echo ""
echo "Commands:"
echo "  # Check processing status:"
echo "  az containerapp logs show --name ai-content-prod-processor --resource-group ai-content-prod-rg --tail 50"
echo ""
echo "  # Trigger site rebuild (after processing completes):"
echo "  curl -X POST $SITEGEN_ENDPOINT/storage-queue/send-wake-up"
echo ""

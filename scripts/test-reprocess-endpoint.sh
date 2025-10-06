#!/bin/bash
# Test the reprocess endpoint locally before deploying

set -e

echo "🧪 Testing Reprocess Endpoint"
echo "=============================="
echo ""

COLLECTOR_ENDPOINT="${COLLECTOR_ENDPOINT:-https://ai-content-prod-collector.whitecliff-6844954b.uksouth.azurecontainerapps.io}"

# Test 1: Dry run with 5 items (default behavior - SAFE)
echo "Test 1: DRY RUN with max_items=5 (simulates without queueing)"
echo "This is SAFE and won't queue any messages or cost money"
echo ""

curl -X POST "$COLLECTOR_ENDPOINT/reprocess" \
    -H "Content-Type: application/json" \
    -d '{"dry_run": true, "max_items": 5}' \
    -s | jq .

echo ""
echo "------------------------------------------------------------"
echo ""

# Test 2: Show what full dry run would look like
echo "Test 2: DRY RUN of ALL collections (still safe)"
echo ""

curl -X POST "$COLLECTOR_ENDPOINT/reprocess" \
    -H "Content-Type: application/json" \
    -d '{"dry_run": true}' \
    -s | jq .

echo ""
echo "=============================="
echo "✓ Tests complete"
echo ""
echo "Results show:"
echo "  - dry_run: true (no actual messages sent)"
echo "  - collections_queued: N (would be queued)"
echo "  - estimated_cost and estimated_time"
echo ""
echo "To ACTUALLY queue messages (costs money!):"
echo "  curl -X POST \"$COLLECTOR_ENDPOINT/reprocess\" -H 'Content-Type: application/json' -d '{\"dry_run\": false}'"
echo ""
echo "Or with limited items for testing:"
echo "  curl -X POST \"$COLLECTOR_ENDPOINT/reprocess\" -H 'Content-Type: application/json' -d '{\"dry_run\": false, \"max_items\": 5}'"
echo ""

#!/bin/bash
# Monitor reprocessing pipeline performance and scaling

set -e

echo "📊 AI Content Farm - Reprocessing Monitor"
echo "=========================================="
echo ""

COLLECTOR_ENDPOINT="${COLLECTOR_ENDPOINT:-https://ai-content-prod-collector.whitecliff-6844954b.uksouth.azurecontainerapps.io}"
PROCESSOR_ENDPOINT="${PROCESSOR_ENDPOINT:-https://ai-content-prod-processor.whitecliff-6844954b.uksouth.azurecontainerapps.io}"
SITEGEN_ENDPOINT="${SITEGEN_ENDPOINT:-https://ai-content-prod-site-gen.whitecliff-6844954b.uksouth.azurecontainerapps.io}"

# Function to get current timestamp
timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# Function to get queue depth from reprocess status
get_queue_depth() {
    curl -s "$COLLECTOR_ENDPOINT/reprocess/status" | jq -r '.data.queue_depth // 0'
}

# Function to get container replica counts
get_replica_count() {
    local app_name=$1
    az containerapp replica list \
        --name "$app_name" \
        --resource-group ai-content-prod-rg \
        --query "length([])" -o tsv 2>/dev/null || echo "0"
}

# Function to get processed count
get_processed_count() {
    curl -s "$COLLECTOR_ENDPOINT/reprocess/status" | jq -r '.data.processed_items // 0'
}

# Check if monitoring should run continuously
CONTINUOUS="${1:-false}"
INTERVAL="${2:-10}"

if [ "$CONTINUOUS" = "true" ] || [ "$CONTINUOUS" = "-c" ] || [ "$CONTINUOUS" = "--continuous" ]; then
    echo "📡 Starting continuous monitoring (Ctrl+C to stop)"
    echo "Interval: ${INTERVAL}s"
    echo ""
    echo "Time              | Queue | Processor | Site Gen | Processed | Rate"
    echo "------------------|-------|-----------|----------|-----------|----------"

    LAST_PROCESSED=0
    LAST_TIME=$(date +%s)

    while true; do
        CURRENT_TIME=$(date +%s)
        QUEUE_DEPTH=$(get_queue_depth)
        PROCESSOR_REPLICAS=$(get_replica_count "ai-content-prod-processor")
        SITEGEN_REPLICAS=$(get_replica_count "ai-content-prod-site-gen")
        PROCESSED_COUNT=$(get_processed_count)

        # Calculate processing rate (items/min)
        TIME_DIFF=$((CURRENT_TIME - LAST_TIME))
        if [ $TIME_DIFF -gt 0 ]; then
            ITEM_DIFF=$((PROCESSED_COUNT - LAST_PROCESSED))
            RATE=$(echo "scale=1; ($ITEM_DIFF * 60) / $TIME_DIFF" | bc)
        else
            RATE="0.0"
        fi

        printf "%-17s | %5s | %9s | %8s | %9s | %s items/min\n" \
            "$(timestamp)" \
            "$QUEUE_DEPTH" \
            "$PROCESSOR_REPLICAS" \
            "$SITEGEN_REPLICAS" \
            "$PROCESSED_COUNT" \
            "$RATE"

        LAST_PROCESSED=$PROCESSED_COUNT
        LAST_TIME=$CURRENT_TIME

        sleep "$INTERVAL"
    done
else
    # Single snapshot
    echo "📸 Single Snapshot"
    echo ""

    echo "🔄 Processing Queue:"
    QUEUE_DEPTH=$(get_queue_depth)
    echo "  Queue depth: $QUEUE_DEPTH messages"
    echo ""

    echo "📦 Container Replicas:"
    COLLECTOR_REPLICAS=$(get_replica_count "ai-content-prod-collector")
    PROCESSOR_REPLICAS=$(get_replica_count "ai-content-prod-processor")
    SITEGEN_REPLICAS=$(get_replica_count "ai-content-prod-site-gen")
    echo "  Collector:  $COLLECTOR_REPLICAS replicas"
    echo "  Processor:  $PROCESSOR_REPLICAS replicas (max: 3)"
    echo "  Site Gen:   $SITEGEN_REPLICAS replicas"
    echo ""

    echo "📊 Content Statistics:"
    STATUS=$(curl -s "$COLLECTOR_ENDPOINT/reprocess/status")
    COLLECTED=$(echo "$STATUS" | jq -r '.data.collected_items // 0')
    PROCESSED=$(echo "$STATUS" | jq -r '.data.processed_items // 0')
    echo "  Collected:  $COLLECTED items"
    echo "  Processed:  $PROCESSED items"
    echo ""

    if [ "$QUEUE_DEPTH" -gt 0 ]; then
        echo "⏱️  Estimated completion:"
        # Assume ~6 seconds per item with current replicas
        SECONDS_PER_ITEM=6
        if [ "$PROCESSOR_REPLICAS" -gt 0 ]; then
            EFFECTIVE_RATE=$(echo "scale=0; $PROCESSOR_REPLICAS * (60 / $SECONDS_PER_ITEM)" | bc)
            MINUTES=$(echo "scale=1; $QUEUE_DEPTH / $EFFECTIVE_RATE" | bc)
            echo "  ~$MINUTES minutes at current scale ($PROCESSOR_REPLICAS replicas)"
            echo "  Processing rate: ~$EFFECTIVE_RATE items/min"
        else
            echo "  Waiting for processors to scale up..."
        fi
        echo ""
    fi

    echo "=========================================="
    echo ""
    echo "Commands:"
    echo "  Continuous monitoring:"
    echo "    $0 --continuous [interval_seconds]"
    echo ""
    echo "  Azure portal metrics:"
    echo "    https://portal.azure.com/#@/resource/subscriptions/.../resourceGroups/ai-content-prod-rg/overview"
    echo ""
    echo "  Live logs (processor):"
    echo "    az containerapp logs show --name ai-content-prod-processor --resource-group ai-content-prod-rg --tail 50 --follow"
    echo ""
    echo "  Queue metrics:"
    echo "    az storage queue stats --account-name aicontentprodstkwakpx --name content-processing-requests"
    echo ""
fi

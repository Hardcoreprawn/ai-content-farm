#!/bin/bash
# Cron-Aware Pipeline Monitor
# Tracks pipeline execution windows, not idle state
# Usage: ./monitor-cron-pipeline.sh [--window HOURS] [--export CSV_FILE]

set -euo pipefail

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-ai-content-prod-rg}"
CRON_INTERVAL_HOURS=8  # Pipeline runs every 8 hours
EXECUTION_WINDOW_MINUTES=30  # Expected max execution time
POLL_INTERVAL=10  # Check every 10 seconds during execution
EXPORT_FILE=""

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --window)
      EXECUTION_WINDOW_MINUTES="$2"
      shift 2
      ;;
    --export)
      EXPORT_FILE="$2"
      shift 2
      ;;
    --interval)
      CRON_INTERVAL_HOURS="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--window MINUTES] [--interval HOURS] [--export CSV_FILE]"
      exit 1
      ;;
  esac
done

# Get storage account connection string for queue access
get_storage_connection_string() {
    local storage_account=$(az storage account list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[0].name" -o tsv 2>/dev/null)

    if [[ -z "$storage_account" ]]; then
        echo -e "${RED}❌ Could not find storage account${NC}" >&2
        return 1
    fi

    # Try to get connection string
    az storage account show-connection-string \
        --name "$storage_account" \
        --resource-group "$RESOURCE_GROUP" \
        --query "connectionString" -o tsv 2>/dev/null
}

# Get queue depth with proper authentication
get_queue_depth() {
    local queue_name=$1
    local conn_str=$2

    if [[ -z "$conn_str" ]]; then
        echo "0"
        return
    fi

    # Get approximate message count
    local count=$(az storage queue metadata show \
        --name "$queue_name" \
        --connection-string "$conn_str" \
        --query "approximateMessageCount" -o tsv 2>/dev/null || echo "0")

    echo "$count"
}

# Check if any containers are running (execution window active)
is_execution_window_active() {
    local running_count=$(az containerapp list \
        --resource-group "$RESOURCE_GROUP" \
        --query "length([?properties.runningStatus=='Running'])" -o tsv 2>/dev/null || echo "0")

    [[ "$running_count" -gt 0 ]]
}

# Get container replica counts
get_container_status() {
    az containerapp list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[].{name:name, replicas:properties.template.scale.currentReplicas, status:properties.runningStatus}" \
        -o json 2>/dev/null || echo "[]"
}

# Get all queue depths
get_all_queue_depths() {
    local conn_str=$1

    local collector=$(get_queue_depth "content-collection-requests" "$conn_str")
    local processor=$(get_queue_depth "content-processing-requests" "$conn_str")
    local markdown=$(get_queue_depth "markdown-generation-requests" "$conn_str")
    local publisher=$(get_queue_depth "site-publishing-requests" "$conn_str")

    echo "$collector|$processor|$markdown|$publisher"
}

# Calculate time until next expected execution
time_until_next_execution() {
    # Get last execution time from Application Insights or logs
    # For now, estimate based on cron interval
    # This would need proper implementation with actual timestamps
    echo "Unknown - check cron schedule"
}

# Monitor execution window
monitor_execution_window() {
    local start_time=$(date +%s)
    local conn_str=$(get_storage_connection_string)

    if [[ -z "$conn_str" ]]; then
        echo -e "${YELLOW}⚠️  No storage connection string - queue depths unavailable${NC}"
        echo -e "${YELLOW}⚠️  Grant 'Storage Queue Data Reader' role or use access key${NC}"
    fi

    echo -e "${GREEN}🚀 Execution window detected! Monitoring...${NC}"
    echo ""

    local iteration=0
    local max_iterations=$((EXECUTION_WINDOW_MINUTES * 60 / POLL_INTERVAL))

    # CSV header
    if [[ -n "$EXPORT_FILE" ]]; then
        echo "timestamp,collector_queue,processor_queue,markdown_queue,publisher_queue,collector_replicas,processor_replicas,markdown_replicas,publisher_replicas" > "$EXPORT_FILE"
    fi

    while [[ $iteration -lt $max_iterations ]]; do
        local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

        # Get queue depths
        IFS='|' read -r collector_q processor_q markdown_q publisher_q <<< "$(get_all_queue_depths "$conn_str")"

        # Get container status
        local container_status=$(get_container_status)
        local collector_r=$(echo "$container_status" | jq -r '.[] | select(.name | contains("collector")) | .replicas // 0')
        local processor_r=$(echo "$container_status" | jq -r '.[] | select(.name | contains("processor")) | .replicas // 0')
        local markdown_r=$(echo "$container_status" | jq -r '.[] | select(.name | contains("markdown")) | .replicas // 0')
        local publisher_r=$(echo "$container_status" | jq -r '.[] | select(.name | contains("publisher")) | .replicas // 0')

        # Display status
        echo -e "${CYAN}[$timestamp]${NC}"
        echo -e "  Queue Depths: collector=${YELLOW}$collector_q${NC} processor=${YELLOW}$processor_q${NC} markdown=${YELLOW}$markdown_q${NC} publisher=${YELLOW}$publisher_q${NC}"
        echo -e "  Replicas: collector=${GREEN}$collector_r${NC} processor=${GREEN}$processor_r${NC} markdown=${GREEN}$markdown_r${NC} publisher=${GREEN}$publisher_r${NC}"

        # Export to CSV
        if [[ -n "$EXPORT_FILE" ]]; then
            echo "$timestamp,$collector_q,$processor_q,$markdown_q,$publisher_q,$collector_r,$processor_r,$markdown_r,$publisher_r" >> "$EXPORT_FILE"
        fi

        # Check if execution window still active
        if ! is_execution_window_active && [[ $iteration -gt 5 ]]; then
            echo -e "${GREEN}✅ Execution window completed${NC}"
            break
        fi

        # Warning if queues growing
        if [[ $processor_q -gt 20 ]] || [[ $markdown_q -gt 20 ]]; then
            echo -e "  ${RED}⚠️  WARNING: Queue depth growing! Check for processing issues${NC}"
        fi

        # Warning if site-publisher not triggered
        if [[ $markdown_q -eq 0 ]] && [[ $publisher_q -eq 0 ]] && [[ $markdown_r -eq 0 ]] && [[ $processor_r -eq 0 ]]; then
            echo -e "  ${YELLOW}⚠️  NOTICE: Pipeline may be complete - verify site published${NC}"
        fi

        echo ""

        sleep $POLL_INTERVAL
        ((iteration++))
    done

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo ""
    echo -e "${GREEN}📊 Execution Window Summary${NC}"
    echo -e "  Duration: ${duration}s ($((duration / 60))m)"
    echo -e "  Final Queue Depths: collector=$collector_q processor=$processor_q markdown=$markdown_q publisher=$publisher_q"

    if [[ -n "$EXPORT_FILE" ]]; then
        echo -e "  Data exported to: ${CYAN}$EXPORT_FILE${NC}"
    fi
}

# Wait for next execution window
wait_for_execution_window() {
    echo -e "${BLUE}⏰ Waiting for next execution window (cron: every ${CRON_INTERVAL_HOURS}h)${NC}"
    echo -e "${BLUE}   Pipeline is expected to be idle between executions${NC}"
    echo ""

    local wait_count=0
    while true; do
        if is_execution_window_active; then
            return 0
        fi

        if [[ $((wait_count % 30)) -eq 0 ]]; then
            echo -e "${BLUE}⏳ Still waiting... (checked $wait_count times)${NC}"
        fi

        sleep 60  # Check every minute
        ((wait_count++))
    done
}

# Main execution
main() {
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  Cron-Aware Pipeline Monitor                          ║${NC}"
    echo -e "${CYAN}║  Resource Group: ${RESOURCE_GROUP}${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Check current status
    if is_execution_window_active; then
        monitor_execution_window
    else
        echo -e "${BLUE}💤 Pipeline is idle (expected for cron-based execution)${NC}"
        echo -e "${BLUE}   Containers scale to zero between cron runs${NC}"
        echo ""

        # Show next expected execution time
        echo -e "${BLUE}⏰ Next execution expected in ~${CRON_INTERVAL_HOURS}h (based on cron schedule)${NC}"
        echo ""

        read -p "Wait for next execution window? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            wait_for_execution_window
            monitor_execution_window
        fi
    fi
}

main "$@"

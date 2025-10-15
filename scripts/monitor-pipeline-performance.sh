#!/bin/bash
# Pipeline Performance Monitor
# Tracks queue depths, container scaling, and flow-through metrics for all four container apps
# Usage: ./monitor-pipeline-performance.sh [--interval SECONDS] [--duration MINUTES] [--export CSV_FILE]

set -euo pipefail

# Configuration
INTERVAL=10  # Default polling interval in seconds
DURATION=0   # 0 = run indefinitely
EXPORT_FILE=""
RESOURCE_GROUP="${RESOURCE_GROUP:-ai-content-prod-rg}"
STORAGE_ACCOUNT=""
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ANSI colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --interval)
      INTERVAL="$2"
      shift 2
      ;;
    --duration)
      DURATION="$2"
      shift 2
      ;;
    --export)
      EXPORT_FILE="$2"
      shift 2
      ;;
    --resource-group)
      RESOURCE_GROUP="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--interval SECONDS] [--duration MINUTES] [--export CSV_FILE] [--resource-group RG_NAME]"
      exit 1
      ;;
  esac
done

# Validate Azure CLI and login
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI not found. Please install it first.${NC}"
    exit 1
fi

if ! az account show &> /dev/null; then
    echo -e "${YELLOW}Not logged in to Azure. Running 'az login'...${NC}"
    az login
fi

# Get storage account name
echo -e "${CYAN}Discovering storage account...${NC}"
STORAGE_ACCOUNT=$(az storage account list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)
if [ -z "$STORAGE_ACCOUNT" ]; then
    echo -e "${RED}Error: No storage account found in resource group $RESOURCE_GROUP${NC}"
    exit 1
fi

# Get container app names
COLLECTOR_APP=$(az containerapp list --resource-group "$RESOURCE_GROUP" --query "[?contains(name, 'collector')].name" -o tsv | head -n 1)
PROCESSOR_APP=$(az containerapp list --resource-group "$RESOURCE_GROUP" --query "[?contains(name, 'processor')].name" -o tsv | head -n 1)
MARKDOWN_APP=$(az containerapp list --resource-group "$RESOURCE_GROUP" --query "[?contains(name, 'markdown')].name" -o tsv | head -n 1)
PUBLISHER_APP=$(az containerapp list --resource-group "$RESOURCE_GROUP" --query "[?contains(name, 'publisher')].name" -o tsv | head -n 1)

echo -e "${GREEN}Found container apps:${NC}"
echo -e "  Collector:  ${BLUE}$COLLECTOR_APP${NC}"
echo -e "  Processor:  ${BLUE}$PROCESSOR_APP${NC}"
echo -e "  Markdown:   ${BLUE}$MARKDOWN_APP${NC}"
echo -e "  Publisher:  ${BLUE}$PUBLISHER_APP${NC}"
echo ""

# Initialize CSV export if requested
if [ -n "$EXPORT_FILE" ]; then
    echo "timestamp,collection_queue,processing_queue,markdown_queue,publish_queue,collector_replicas,processor_replicas,markdown_replicas,publisher_replicas,collector_cpu,processor_cpu,markdown_cpu,publisher_cpu,collector_mem,processor_mem,markdown_mem,publisher_mem" > "$EXPORT_FILE"
    echo -e "${GREEN}Exporting metrics to: $EXPORT_FILE${NC}"
fi

# Function to get queue depth
get_queue_depth() {
    local queue_name=$1
    local depth=$(az storage queue stats --name "$queue_name" \
        --account-name "$STORAGE_ACCOUNT" \
        --auth-mode login \
        --query "approximateMessageCount" -o tsv 2>/dev/null || echo "0")
    echo "${depth:-0}"
}

# Function to get container replica count
get_replica_count() {
    local app_name=$1
    local replicas=$(az containerapp replica list \
        --name "$app_name" \
        --resource-group "$RESOURCE_GROUP" \
        --query "length(@)" -o tsv 2>/dev/null || echo "0")
    echo "${replicas:-0}"
}

# Function to get container resource metrics
get_container_metrics() {
    local app_name=$1
    # Get actual CPU/memory from replicas
    local metrics=$(az containerapp replica list \
        --name "$app_name" \
        --resource-group "$RESOURCE_GROUP" \
        --query "[].{cpu:properties.runningState,mem:properties.runningState}" -o json 2>/dev/null || echo "[]")

    # For now, return placeholder - will integrate with Log Analytics for actual metrics
    echo "0.0,0.0"
}

# Function to display dashboard
display_dashboard() {
    local collection_q=$1
    local processing_q=$2
    local markdown_q=$3
    local publish_q=$4
    local collector_r=$5
    local processor_r=$6
    local markdown_r=$7
    local publisher_r=$8
    local timestamp=$9

    clear
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}          ${GREEN}AI Content Farm - Pipeline Performance Monitor${NC}              ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BLUE}Timestamp:${NC} $timestamp"
    echo -e "  ${BLUE}Resource Group:${NC} $RESOURCE_GROUP"
    echo -e "  ${BLUE}Update Interval:${NC} ${INTERVAL}s"
    echo ""

    echo -e "${CYAN}┌─────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│${NC} ${YELLOW}Queue Depths${NC}                                                          ${CYAN}│${NC}"
    echo -e "${CYAN}├─────────────────────────────────────────────────────────────────────────┤${NC}"
    printf "${CYAN}│${NC}   Collection Queue:       ${GREEN}%6s${NC} messages                             ${CYAN}│${NC}\n" "$collection_q"
    printf "${CYAN}│${NC}   Processing Queue:       ${GREEN}%6s${NC} messages                             ${CYAN}│${NC}\n" "$processing_q"
    printf "${CYAN}│${NC}   Markdown Queue:         ${GREEN}%6s${NC} messages                             ${CYAN}│${NC}\n" "$markdown_q"
    printf "${CYAN}│${NC}   Publishing Queue:       ${GREEN}%6s${NC} messages                             ${CYAN}│${NC}\n" "$publish_q"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""

    echo -e "${CYAN}┌─────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│${NC} ${YELLOW}Container Replicas${NC}                                                    ${CYAN}│${NC}"
    echo -e "${CYAN}├─────────────────────────────────────────────────────────────────────────┤${NC}"
    printf "${CYAN}│${NC}   Collector:              ${BLUE}%3s${NC} / 1 replicas (KEDA: manual)       ${CYAN}│${NC}\n" "$collector_r"
    printf "${CYAN}│${NC}   Processor:              ${BLUE}%3s${NC} / 6 replicas (KEDA: queueLength=8)${CYAN}│${NC}\n" "$processor_r"
    printf "${CYAN}│${NC}   Markdown Generator:     ${BLUE}%3s${NC} / 1 replicas (KEDA: queueLength=1)${CYAN}│${NC}\n" "$markdown_r"
    printf "${CYAN}│${NC}   Site Publisher:         ${BLUE}%3s${NC} / 1 replicas (KEDA: queueLength=1)${CYAN}│${NC}\n" "$publisher_r"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""

    echo -e "${CYAN}┌─────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│${NC} ${YELLOW}Pipeline Flow Analysis${NC}                                                ${CYAN}│${NC}"
    echo -e "${CYAN}├─────────────────────────────────────────────────────────────────────────┤${NC}"

    # Analyze bottlenecks
    if [ "$collection_q" -gt 0 ] && [ "$collector_r" -eq 0 ]; then
        echo -e "${CYAN}│${NC}   ${RED}⚠ BOTTLENECK:${NC} Collector scaled to zero with pending work       ${CYAN}│${NC}"
    fi

    if [ "$processing_q" -gt 50 ] && [ "$processor_r" -lt 3 ]; then
        echo -e "${CYAN}│${NC}   ${YELLOW}⚠ SLOW:${NC} Processing queue growing faster than consumption     ${CYAN}│${NC}"
    elif [ "$processing_q" -gt 100 ]; then
        echo -e "${CYAN}│${NC}   ${RED}⚠ BOTTLENECK:${NC} Large processing queue - may need more replicas ${CYAN}│${NC}"
    fi

    if [ "$markdown_q" -gt 20 ] && [ "$markdown_r" -eq 0 ]; then
        echo -e "${CYAN}│${NC}   ${YELLOW}⚠ SLOW:${NC} Markdown queue backing up - KEDA may need tuning    ${CYAN}│${NC}"
    fi

    if [ "$publish_q" -gt 5 ] && [ "$publisher_r" -eq 0 ]; then
        echo -e "${CYAN}│${NC}   ${YELLOW}⚠ INFO:${NC} Publishing queue has work - waiting for activation   ${CYAN}│${NC}"
    fi

    # Show healthy state
    if [ "$collection_q" -eq 0 ] && [ "$processing_q" -eq 0 ] && [ "$markdown_q" -eq 0 ] && [ "$publish_q" -eq 0 ]; then
        echo -e "${CYAN}│${NC}   ${GREEN}✓ Pipeline idle - all queues empty${NC}                           ${CYAN}│${NC}"
    elif [ "$processing_q" -lt 20 ] && [ "$markdown_q" -lt 10 ]; then
        echo -e "${CYAN}│${NC}   ${GREEN}✓ Pipeline healthy - steady processing rate${NC}                  ${CYAN}│${NC}"
    fi

    echo -e "${CYAN}└─────────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop monitoring${NC}"
}

# Main monitoring loop
echo -e "${GREEN}Starting pipeline monitor...${NC}"
echo ""

start_time=$(date +%s)
iteration=0

while true; do
    iteration=$((iteration + 1))
    current_time=$(date +%s)

    # Check duration limit
    if [ "$DURATION" -gt 0 ]; then
        elapsed=$((current_time - start_time))
        if [ $elapsed -ge $((DURATION * 60)) ]; then
            echo -e "\n${GREEN}Monitoring duration completed.${NC}"
            break
        fi
    fi

    # Collect metrics
    timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    collection_queue=$(get_queue_depth "content-collection-requests")
    processing_queue=$(get_queue_depth "content-processing-requests")
    markdown_queue=$(get_queue_depth "markdown-generation-requests")
    publish_queue=$(get_queue_depth "site-publishing-requests")

    collector_replicas=$(get_replica_count "$COLLECTOR_APP")
    processor_replicas=$(get_replica_count "$PROCESSOR_APP")
    markdown_replicas=$(get_replica_count "$MARKDOWN_APP")
    publisher_replicas=$(get_replica_count "$PUBLISHER_APP")

    # Display dashboard
    display_dashboard \
        "$collection_queue" \
        "$processing_queue" \
        "$markdown_queue" \
        "$publish_queue" \
        "$collector_replicas" \
        "$processor_replicas" \
        "$markdown_replicas" \
        "$publisher_replicas" \
        "$timestamp"

    # Export to CSV if requested
    if [ -n "$EXPORT_FILE" ]; then
        echo "$timestamp,$collection_queue,$processing_queue,$markdown_queue,$publish_queue,$collector_replicas,$processor_replicas,$markdown_replicas,$publisher_replicas,0,0,0,0,0,0,0,0" >> "$EXPORT_FILE"
    fi

    sleep "$INTERVAL"
done

echo -e "${GREEN}Monitoring stopped.${NC}"
if [ -n "$EXPORT_FILE" ]; then
    echo -e "${GREEN}Metrics exported to: $EXPORT_FILE${NC}"
fi

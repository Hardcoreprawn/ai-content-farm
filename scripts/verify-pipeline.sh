#!/bin/bash
# Pipeline Verification Script - Azure Production Testing
# Aligned with project philosophy: "Direct Azure Development"

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="ai-content-prod-rg"
STORAGE_ACCOUNT="aicontentprodstorage"
INSIGHTS_APP="ai-content-prod-insights"

# Container names
COLLECTOR="ai-content-prod-collector"
PROCESSOR="ai-content-prod-processor"
MARKDOWN_GEN="ai-content-prod-markdown-gen"
SITE_GEN="ai-content-prod-site-generator"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_azure_login() {
    log_info "Checking Azure login status..."
    if ! az account show &> /dev/null; then
        log_error "Not logged into Azure. Please run: az login"
        exit 1
    fi
    log_success "Azure login verified"
}

check_container_status() {
    local container=$1
    log_info "Checking status of $container..."

    local status=$(az containerapp show \
        --name "$container" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.runningStatus" \
        --output tsv 2>/dev/null || echo "NOT_FOUND")

    if [ "$status" == "Running" ]; then
        log_success "$container is running"
        return 0
    else
        log_error "$container status: $status"
        return 1
    fi
}

check_queue_depth() {
    local queue_name=$1
    log_info "Checking queue: $queue_name..."

    local count=$(az storage queue show \
        --name "$queue_name" \
        --account-name "$STORAGE_ACCOUNT" \
        --auth-mode login \
        --query "approximateMessageCount" \
        --output tsv 2>/dev/null || echo "0")

    echo "$count"
}

get_replica_count() {
    local container=$1
    local count=$(az containerapp replica list \
        --name "$container" \
        --resource-group "$RESOURCE_GROUP" \
        --query "length(@)" \
        --output tsv 2>/dev/null || echo "0")
    echo "$count"
}

stream_logs() {
    local container=$1
    local tail=${2:-50}

    log_info "Streaming logs for $container (last $tail lines)..."
    az containerapp logs show \
        --name "$container" \
        --resource-group "$RESOURCE_GROUP" \
        --follow \
        --tail "$tail"
}

list_recent_blobs() {
    local container=$1
    local prefix=$2

    log_info "Listing blobs in $container with prefix: $prefix"
    az storage blob list \
        --account-name "$STORAGE_ACCOUNT" \
        --container-name "$container" \
        --prefix "$prefix" \
        --auth-mode login \
        --query "[].{Name:name, Created:properties.creationTime, Size:properties.contentLength}" \
        --output table
}

trigger_collection() {
    log_info "Triggering manual collection..."

    local collector_url=$(az containerapp show \
        --name "$COLLECTOR" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.configuration.ingress.fqdn" \
        --output tsv)

    if [ -z "$collector_url" ]; then
        log_error "Could not get collector URL"
        return 1
    fi

    log_info "Collector URL: https://${collector_url}"

    curl -X POST "https://${collector_url}/collect" \
        -H "Content-Type: application/json" \
        -d '{
            "template": "tech-news",
            "max_topics": 5
        }'

    log_success "Collection triggered"
}

show_pipeline_status() {
    echo ""
    echo "============================================"
    echo "        PIPELINE STATUS OVERVIEW"
    echo "============================================"
    echo ""

    # Container status
    echo "--- Container Status ---"
    check_container_status "$COLLECTOR" && echo "✅ Collector" || echo "❌ Collector"
    check_container_status "$PROCESSOR" && echo "✅ Processor" || echo "❌ Processor"
    check_container_status "$MARKDOWN_GEN" && echo "✅ Markdown Generator" || echo "❌ Markdown Generator"
    check_container_status "$SITE_GEN" && echo "✅ Site Generator" || echo "❌ Site Generator"
    echo ""

    # Replica counts
    echo "--- Current Replicas (KEDA Scaling) ---"
    echo "Collector: $(get_replica_count $COLLECTOR)"
    echo "Processor: $(get_replica_count $PROCESSOR)"
    echo "Markdown Gen: $(get_replica_count $MARKDOWN_GEN)"
    echo "Site Gen: $(get_replica_count $SITE_GEN)"
    echo ""

    # Queue depths
    echo "--- Queue Depths ---"
    echo "process-topic: $(check_queue_depth 'process-topic')"
    echo "generate-markdown: $(check_queue_depth 'generate-markdown')"
    echo "publish-site: $(check_queue_depth 'publish-site')"
    echo ""

    # Recent content
    echo "--- Recent Content (Today) ---"
    TODAY=$(date +%Y/%m/%d)
    echo "Collections:"
    az storage blob list \
        --account-name "$STORAGE_ACCOUNT" \
        --container-name "collected-content" \
        --prefix "collections/$TODAY" \
        --auth-mode login \
        --query "length(@)" \
        --output tsv 2>/dev/null || echo "0"

    echo "Processed:"
    az storage blob list \
        --account-name "$STORAGE_ACCOUNT" \
        --container-name "processed-content" \
        --prefix "$TODAY" \
        --auth-mode login \
        --query "length(@)" \
        --output tsv 2>/dev/null || echo "0"

    echo "Markdown:"
    az storage blob list \
        --account-name "$STORAGE_ACCOUNT" \
        --container-name "markdown-content" \
        --prefix "articles/$TODAY" \
        --auth-mode login \
        --query "length(@)" \
        --output tsv 2>/dev/null || echo "0"
    echo ""
}

watch_keda_scaling() {
    log_info "Watching KEDA scaling behavior (Ctrl+C to stop)..."
    echo ""

    while true; do
        clear
        echo "=== KEDA Scaling Monitor ==="
        echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
        echo ""

        echo "Container            | Replicas | Queue Depth"
        echo "-------------------- | -------- | -----------"
        printf "%-20s | %8s | %s\n" "Collector" "$(get_replica_count $COLLECTOR)" "N/A (cron)"
        printf "%-20s | %8s | %s\n" "Processor" "$(get_replica_count $PROCESSOR)" "$(check_queue_depth 'process-topic')"
        printf "%-20s | %8s | %s\n" "Markdown Gen" "$(get_replica_count $MARKDOWN_GEN)" "$(check_queue_depth 'generate-markdown')"
        printf "%-20s | %8s | %s\n" "Site Generator" "$(get_replica_count $SITE_GEN)" "$(check_queue_depth 'publish-site')"

        echo ""
        echo "Refreshing in 10 seconds... (Ctrl+C to stop)"
        sleep 10
    done
}

check_site_gen_errors() {
    log_info "Checking site-generator for post-refactor errors..."

    # Check recent logs for errors
    local errors=$(az containerapp logs show \
        --name "$SITE_GEN" \
        --resource-group "$RESOURCE_GROUP" \
        --tail 200 \
        2>/dev/null | grep -E "ERROR|Exception|Traceback|AttributeError|TypeError" || echo "")

    if [ -z "$errors" ]; then
        log_success "No errors found in site-generator logs"
    else
        log_error "Errors found in site-generator:"
        echo "$errors"
    fi

    # Check Application Insights
    log_info "Checking Application Insights for exceptions..."
    az monitor app-insights query \
        --app "$INSIGHTS_APP" \
        --resource-group "$RESOURCE_GROUP" \
        --analytics-query "
            exceptions
            | where timestamp > ago(1h)
            | where cloud_RoleName == '$SITE_GEN'
            | project timestamp, type, outerMessage
            | order by timestamp desc
            | take 10
        " \
        --output table 2>/dev/null || log_warning "Could not query Application Insights"
}

# Main menu
show_menu() {
    echo ""
    echo "============================================"
    echo "   Pipeline Verification Tool (Azure)"
    echo "============================================"
    echo ""
    echo "1) Show pipeline status overview"
    echo "2) Trigger manual collection"
    echo "3) Watch KEDA scaling in real-time"
    echo "4) Stream collector logs"
    echo "5) Stream processor logs"
    echo "6) Stream markdown-gen logs"
    echo "7) Stream site-generator logs"
    echo "8) Check site-generator for refactor errors"
    echo "9) List recent collections"
    echo "10) List processed content"
    echo "11) List markdown articles"
    echo "12) Check queue depths"
    echo "13) Full verification (interactive)"
    echo "0) Exit"
    echo ""
}

full_verification() {
    log_info "Starting full pipeline verification..."
    echo ""

    # Pre-checks
    log_info "Step 1: Pre-verification checks"
    show_pipeline_status
    read -p "Press Enter to continue or Ctrl+C to abort..."

    # Trigger collection
    log_info "Step 2: Triggering collection"
    trigger_collection
    echo ""
    read -p "Press Enter to stream collector logs or 's' to skip: " choice
    if [ "$choice" != "s" ]; then
        stream_logs "$COLLECTOR" 100
    fi

    # Wait for processing
    log_info "Step 3: Waiting for processing to start..."
    echo "Monitoring processor scaling..."
    for i in {1..30}; do
        replicas=$(get_replica_count "$PROCESSOR")
        if [ "$replicas" -gt 0 ]; then
            log_success "Processor scaled to $replicas replicas!"
            break
        fi
        echo -n "."
        sleep 2
    done
    echo ""

    read -p "Press Enter to stream processor logs or 's' to skip: " choice
    if [ "$choice" != "s" ]; then
        stream_logs "$PROCESSOR" 100
    fi

    # Check markdown generation
    log_info "Step 4: Checking markdown generation"
    read -p "Press Enter to stream markdown-gen logs or 's' to skip: " choice
    if [ "$choice" != "s" ]; then
        stream_logs "$MARKDOWN_GEN" 100
    fi

    # Check site generation (critical - post refactor)
    log_info "Step 5: Verifying site-generator (REFACTORED)"
    check_site_gen_errors
    echo ""
    read -p "Press Enter to stream site-generator logs or 's' to skip: " choice
    if [ "$choice" != "s" ]; then
        stream_logs "$SITE_GEN" 100
    fi

    # Final status
    log_info "Step 6: Final status check"
    show_pipeline_status

    log_success "Full verification complete!"
}

# Main script
main() {
    check_azure_login

    while true; do
        show_menu
        read -p "Select option: " choice

        case $choice in
            1) show_pipeline_status ;;
            2) trigger_collection ;;
            3) watch_keda_scaling ;;
            4) stream_logs "$COLLECTOR" 100 ;;
            5) stream_logs "$PROCESSOR" 100 ;;
            6) stream_logs "$MARKDOWN_GEN" 100 ;;
            7) stream_logs "$SITE_GEN" 100 ;;
            8) check_site_gen_errors ;;
            9) list_recent_blobs "collected-content" "collections/$(date +%Y/%m/%d)" ;;
            10) list_recent_blobs "processed-content" "$(date +%Y/%m/%d)" ;;
            11) list_recent_blobs "markdown-content" "articles/$(date +%Y/%m/%d)" ;;
            12)
                echo "process-topic: $(check_queue_depth 'process-topic')"
                echo "generate-markdown: $(check_queue_depth 'generate-markdown')"
                echo "publish-site: $(check_queue_depth 'publish-site')"
                ;;
            13) full_verification ;;
            0) log_info "Exiting..."; exit 0 ;;
            *) log_error "Invalid option" ;;
        esac

        if [ "$choice" != "3" ] && [ "$choice" != "13" ]; then
            read -p "Press Enter to continue..."
        fi
    done
}

# Run main
main

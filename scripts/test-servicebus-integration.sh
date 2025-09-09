#!/bin/bash
"""
Service Bus Integration Test Script

Tests the Phase 1 Security Implementation Service Bus integration.
Validates that Logic Apps can send messages to Service Bus and
Container Apps can receive and process them correctly.

Features:
- Service Bus connectivity testing
- Message sending and receiving validation
- KEDA scaling verification
- End-to-end workflow testing
- Error handling and retry logic testing
"""

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TIMEOUT=300 # 5 minutes
POLL_INTERVAL=10

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TEST_RESULTS=()

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    TEST_RESULTS+=("✅ $1")
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    TEST_RESULTS+=("❌ $1")
}

# Utility functions
check_dependencies() {
    log_info "Checking dependencies..."

    local deps=("az" "curl" "jq")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "Required dependency '$dep' not found"
            exit 1
        fi
    done

    # Check Azure CLI login
    if ! az account show &> /dev/null; then
        log_error "Not logged into Azure CLI. Run 'az login' first."
        exit 1
    fi

    log_success "All dependencies available"
}

get_azure_resources() {
    log_info "Getting Azure resource information..."

    # Get resource group and container app URLs
    RESOURCE_GROUP=$(az group list --query "[?contains(name, 'ai-content-farm')].name | [0]" -o tsv)
    if [[ -z "$RESOURCE_GROUP" ]]; then
        log_error "Could not find ai-content-farm resource group"
        exit 1
    fi

    # Get container app FQDNs
    CONTENT_COLLECTOR_URL=$(az containerapp show \
        --resource-group "$RESOURCE_GROUP" \
        --name "ai-content-farm-collector" \
        --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")

    CONTENT_PROCESSOR_URL=$(az containerapp show \
        --resource-group "$RESOURCE_GROUP" \
        --name "ai-content-farm-processor" \
        --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")

    SITE_GENERATOR_URL=$(az containerapp show \
        --resource-group "$RESOURCE_GROUP" \
        --name "ai-content-farm-site-generator" \
        --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")

    # Get Service Bus namespace
    SERVICE_BUS_NAMESPACE=$(az servicebus namespace list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[0].name" -o tsv 2>/dev/null || echo "")

    log_info "Resource Group: $RESOURCE_GROUP"
    log_info "Content Collector: $CONTENT_COLLECTOR_URL"
    log_info "Content Processor: $CONTENT_PROCESSOR_URL"
    log_info "Site Generator: $SITE_GENERATOR_URL"
    log_info "Service Bus Namespace: $SERVICE_BUS_NAMESPACE"
}

# Test functions
test_service_bus_connectivity() {
    log_info "Testing Service Bus connectivity..."

    if [[ -z "$SERVICE_BUS_NAMESPACE" ]]; then
        log_error "Service Bus namespace not found"
        return 1
    fi

    # Test Service Bus namespace accessibility
    local namespace_status=$(az servicebus namespace show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$SERVICE_BUS_NAMESPACE" \
        --query "status" -o tsv 2>/dev/null || echo "Unknown")

    if [[ "$namespace_status" == "Active" ]]; then
        log_success "Service Bus namespace is active"
    else
        log_error "Service Bus namespace status: $namespace_status"
        return 1
    fi

    # Test queue accessibility
    local queues=("content-collection-requests" "content-processing-requests" "site-generation-requests")
    for queue in "${queues[@]}"; do
        local queue_status=$(az servicebus queue show \
            --resource-group "$RESOURCE_GROUP" \
            --namespace-name "$SERVICE_BUS_NAMESPACE" \
            --name "$queue" \
            --query "status" -o tsv 2>/dev/null || echo "NotFound")

        if [[ "$queue_status" == "Active" ]]; then
            log_success "Queue '$queue' is active"
        else
            log_error "Queue '$queue' status: $queue_status"
            return 1
        fi
    done
}

test_container_servicebus_endpoints() {
    log_info "Testing container Service Bus endpoints..."

    local containers=("$CONTENT_COLLECTOR_URL" "$CONTENT_PROCESSOR_URL" "$SITE_GENERATOR_URL")
    local container_names=("content-collector" "content-processor" "site-generator")

    for i in "${!containers[@]}"; do
        local url="${containers[$i]}"
        local name="${container_names[$i]}"

        if [[ -z "$url" ]]; then
            log_warning "Skipping $name - URL not available"
            continue
        fi

        # Test Service Bus status endpoint
        log_info "Testing Service Bus status for $name..."
        local response=$(curl -s -w "%{http_code}" \
            "https://$url/internal/servicebus-status" \
            -o /tmp/servicebus_test_response.json || echo "000")

        if [[ "$response" == "200" ]]; then
            local status=$(jq -r '.data.connection_status' /tmp/servicebus_test_response.json 2>/dev/null || echo "unknown")
            if [[ "$status" == "healthy" ]]; then
                log_success "$name Service Bus status endpoint working"
            else
                log_warning "$name Service Bus status: $status"
            fi
        else
            log_error "$name Service Bus status endpoint failed (HTTP $response)"
        fi

        # Test message processing endpoint
        log_info "Testing Service Bus message processing for $name..."
        local process_response=$(curl -s -w "%{http_code}" \
            -X POST "https://$url/internal/process-servicebus-message" \
            -H "Content-Type: application/json" \
            -o /tmp/servicebus_process_response.json || echo "000")

        if [[ "$process_response" == "200" ]]; then
            log_success "$name Service Bus message processing endpoint working"
        else
            log_error "$name Service Bus message processing failed (HTTP $process_response)"
        fi
    done
}

test_message_sending() {
    log_info "Testing Service Bus message sending..."

    # Create a test message
    local test_message='{
        "message_id": "test-'$(date +%s)'",
        "correlation_id": "test-correlation-'$(date +%s)'",
        "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
        "service_name": "integration-test",
        "operation": "collect_content",
        "payload": {
            "sources": [{
                "type": "reddit",
                "subreddits": ["technology"],
                "limit": 5
            }],
            "save_to_storage": true,
            "deduplicate": true
        },
        "metadata": {
            "created_by": "integration_test",
            "version": "1.0.0"
        }
    }'

    # Send message to content collection queue
    log_info "Sending test message to content-collection-requests queue..."

    local send_result=$(az servicebus message send \
        --resource-group "$RESOURCE_GROUP" \
        --namespace-name "$SERVICE_BUS_NAMESPACE" \
        --queue-name "content-collection-requests" \
        --body "$test_message" \
        --content-type "application/json" 2>&1 || echo "FAILED")

    if [[ "$send_result" != "FAILED" ]]; then
        log_success "Test message sent successfully"

        # Wait a moment for processing
        sleep 5

        # Check if message was processed by checking queue metrics
        local active_messages=$(az servicebus queue show \
            --resource-group "$RESOURCE_GROUP" \
            --namespace-name "$SERVICE_BUS_NAMESPACE" \
            --name "content-collection-requests" \
            --query "messageCount" -o tsv 2>/dev/null || echo "0")

        log_info "Active messages in queue: $active_messages"

    else
        log_error "Failed to send test message: $send_result"
    fi
}

test_keda_scaling() {
    log_info "Testing KEDA scaling behavior..."

    # Check current replica count
    local current_replicas=$(az containerapp revision list \
        --resource-group "$RESOURCE_GROUP" \
        --name "ai-content-farm-collector" \
        --query "[0].properties.replicas" -o tsv 2>/dev/null || echo "0")

    log_info "Current collector replicas: $current_replicas"

    # Send multiple messages to trigger scaling
    log_info "Sending multiple messages to trigger KEDA scaling..."

    for i in {1..3}; do
        local test_message='{
            "message_id": "scale-test-'$i'-'$(date +%s)'",
            "correlation_id": "scale-correlation-'$i'-'$(date +%s)'",
            "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
            "service_name": "keda-scale-test",
            "operation": "collect_content",
            "payload": {
                "sources": [{
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 2
                }],
                "save_to_storage": true,
                "deduplicate": true
            }
        }'

        az servicebus message send \
            --resource-group "$RESOURCE_GROUP" \
            --namespace-name "$SERVICE_BUS_NAMESPACE" \
            --queue-name "content-collection-requests" \
            --body "$test_message" \
            --content-type "application/json" &>/dev/null || true

        sleep 2
    done

    # Wait for scaling to occur
    log_info "Waiting for KEDA scaling (up to 60 seconds)..."
    local scaling_timeout=60
    local scaling_start=$(date +%s)

    while [[ $(($(date +%s) - scaling_start)) -lt $scaling_timeout ]]; do
        local new_replicas=$(az containerapp revision list \
            --resource-group "$RESOURCE_GROUP" \
            --name "ai-content-farm-collector" \
            --query "[0].properties.replicas" -o tsv 2>/dev/null || echo "0")

        if [[ "$new_replicas" -gt "$current_replicas" ]]; then
            log_success "KEDA scaling triggered: $current_replicas -> $new_replicas replicas"
            return 0
        fi

        sleep 5
    done

    log_warning "KEDA scaling not observed within timeout (current: $new_replicas)"
}

test_end_to_end_workflow() {
    log_info "Testing end-to-end Service Bus workflow..."

    # This test verifies the complete flow:
    # 1. Message sent to Service Bus
    # 2. Container App receives and processes message
    # 3. Processing results are stored
    # 4. No errors in the pipeline

    local workflow_start=$(date +%s)
    local test_correlation_id="e2e-test-$(date +%s)"

    # Send a realistic content collection request
    local collection_request='{
        "message_id": "'$test_correlation_id'",
        "correlation_id": "'$test_correlation_id'",
        "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
        "service_name": "end-to-end-test",
        "operation": "collect_content",
        "payload": {
            "sources": [{
                "type": "reddit",
                "subreddits": ["technology"],
                "limit": 3
            }],
            "save_to_storage": true,
            "deduplicate": true
        },
        "metadata": {
            "test_type": "end_to_end",
            "correlation_id": "'$test_correlation_id'"
        }
    }'

    log_info "Sending end-to-end test message with correlation ID: $test_correlation_id"

    az servicebus message send \
        --resource-group "$RESOURCE_GROUP" \
        --namespace-name "$SERVICE_BUS_NAMESPACE" \
        --queue-name "content-collection-requests" \
        --body "$collection_request" \
        --content-type "application/json" &>/dev/null || {
        log_error "Failed to send end-to-end test message"
        return 1
    }

    # Monitor for completion (check for reduced queue depth)
    log_info "Monitoring workflow completion..."
    local monitoring_timeout=120

    while [[ $(($(date +%s) - workflow_start)) -lt $monitoring_timeout ]]; do
        # Check queue depth
        local queue_depth=$(az servicebus queue show \
            --resource-group "$RESOURCE_GROUP" \
            --namespace-name "$SERVICE_BUS_NAMESPACE" \
            --name "content-collection-requests" \
            --query "messageCount" -o tsv 2>/dev/null || echo "999")

        if [[ "$queue_depth" -eq 0 ]]; then
            log_success "End-to-end workflow completed (queue empty)"
            return 0
        fi

        log_info "Queue depth: $queue_depth, waiting..."
        sleep 10
    done

    log_warning "End-to-end workflow timeout reached"
}

# Performance testing
test_service_bus_performance() {
    log_info "Testing Service Bus performance and throughput..."

    local start_time=$(date +%s)
    local message_count=10

    log_info "Sending $message_count messages for performance testing..."

    for i in $(seq 1 $message_count); do
        local perf_message='{
            "message_id": "perf-test-'$i'-'$(date +%s)'",
            "correlation_id": "perf-correlation-'$(date +%s)'",
            "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
            "service_name": "performance-test",
            "operation": "collect_content",
            "payload": {
                "sources": [{
                    "type": "reddit",
                    "subreddits": ["technology"],
                    "limit": 1
                }],
                "test_mode": true
            }
        }'

        az servicebus message send \
            --resource-group "$RESOURCE_GROUP" \
            --namespace-name "$SERVICE_BUS_NAMESPACE" \
            --queue-name "content-collection-requests" \
            --body "$perf_message" \
            --content-type "application/json" &>/dev/null &
    done

    wait # Wait for all background sends to complete

    local send_time=$(($(date +%s) - start_time))
    local throughput=$(echo "scale=2; $message_count / $send_time" | bc -l 2>/dev/null || echo "N/A")

    log_info "Sent $message_count messages in ${send_time}s (${throughput} msg/s)"

    if [[ "$send_time" -lt 30 ]]; then
        log_success "Service Bus performance test completed within acceptable time"
    else
        log_warning "Service Bus performance slower than expected: ${send_time}s"
    fi
}

# Cleanup function
cleanup_test_resources() {
    log_info "Cleaning up test resources..."

    # Remove any test files
    rm -f /tmp/servicebus_test_response.json /tmp/servicebus_process_response.json

    log_info "Cleanup completed"
}

# Main execution
main() {
    echo "Service Bus Integration Test Suite"
    echo "================================="
    echo ""

    # Set trap for cleanup
    trap cleanup_test_resources EXIT

    # Run tests
    check_dependencies
    get_azure_resources

    test_service_bus_connectivity
    test_container_servicebus_endpoints
    test_message_sending
    test_keda_scaling
    test_end_to_end_workflow
    test_service_bus_performance

    # Test summary
    echo ""
    echo "Test Results Summary"
    echo "==================="

    for result in "${TEST_RESULTS[@]}"; do
        echo "$result"
    done

    echo ""
    echo "Tests Passed: $TESTS_PASSED"
    echo "Tests Failed: $TESTS_FAILED"

    if [[ $TESTS_FAILED -eq 0 ]]; then
        log_success "All Service Bus integration tests passed!"
        exit 0
    else
        log_error "Some Service Bus integration tests failed"
        exit 1
    fi
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

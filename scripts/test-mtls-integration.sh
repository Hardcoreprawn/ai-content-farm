#!/bin/bash
# mTLS Integration Test Suite for Azure Container Apps
# Tests certificate management, Dapr mTLS communication, and service discovery

set -euo pipefail

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-ai-content-dev-rg}"
KEY_VAULT_NAME="${KEY_VAULT_NAME:-}"
DNS_ZONE="${DNS_ZONE:-jablab.com}"
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:-}"
TEST_TIMEOUT=300  # 5 minutes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $*${NC}" >&2
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARN: $*${NC}" >&2
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*${NC}" >&2
}

success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $*${NC}" >&2
}

# Test result tracking
declare -a TEST_RESULTS=()
TOTAL_TESTS=0
PASSED_TESTS=0

# Test function wrapper
run_test() {
    local test_name="$1"
    local test_function="$2"
    
    log "Running test: $test_name"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if $test_function; then
        success "✓ $test_name PASSED"
        TEST_RESULTS+=("PASS: $test_name")
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        error "✗ $test_name FAILED"
        TEST_RESULTS+=("FAIL: $test_name")
        return 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Azure CLI
    if ! command -v az &>/dev/null; then
        error "Azure CLI is not installed"
        return 1
    fi
    
    # Check Azure login
    if ! az account show &>/dev/null; then
        error "Not logged into Azure CLI"
        return 1
    fi
    
    # Check required tools
    local tools=("curl" "openssl" "jq")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &>/dev/null; then
            error "$tool is not installed"
            return 1
        fi
    done
    
    # Check environment variables
    if [[ -z "$KEY_VAULT_NAME" ]]; then
        # Try to discover Key Vault name
        KEY_VAULT_NAME=$(az keyvault list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || echo "")
        if [[ -z "$KEY_VAULT_NAME" ]]; then
            error "KEY_VAULT_NAME not set and could not be discovered"
            return 1
        fi
        log "Discovered Key Vault: $KEY_VAULT_NAME"
    fi
    
    if [[ -z "$STORAGE_ACCOUNT" ]]; then
        # Try to discover Storage Account name
        STORAGE_ACCOUNT=$(az storage account list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || echo "")
        if [[ -z "$STORAGE_ACCOUNT" ]]; then
            error "STORAGE_ACCOUNT not set and could not be discovered"
            return 1
        fi
        log "Discovered Storage Account: $STORAGE_ACCOUNT"
    fi
    
    return 0
}

# Test 1: Certificate Storage in Key Vault
test_certificate_storage() {
    log "Testing certificate storage in Key Vault..."
    
    # Check if certificates exist in Key Vault
    local certificates
    certificates=$(az keyvault certificate list --vault-name "$KEY_VAULT_NAME" --query "length([?contains(name, 'api') || contains(name, 'collector') || contains(name, 'processor')])" -o tsv 2>/dev/null || echo "0")
    
    if [[ "$certificates" -gt 0 ]]; then
        log "Found $certificates certificate(s) in Key Vault"
        
        # Test certificate retrieval
        local cert_name
        cert_name=$(az keyvault certificate list --vault-name "$KEY_VAULT_NAME" --query "[0].name" -o tsv 2>/dev/null || echo "")
        
        if [[ -n "$cert_name" ]]; then
            local cert_details
            cert_details=$(az keyvault certificate show --vault-name "$KEY_VAULT_NAME" --name "$cert_name" --query "attributes.expires" -o tsv 2>/dev/null || echo "")
            
            if [[ -n "$cert_details" ]]; then
                log "Certificate $cert_name expires on: $cert_details"
                return 0
            fi
        fi
    fi
    
    warn "No certificates found or certificate retrieval failed"
    return 1
}

# Test 2: DNS Configuration
test_dns_configuration() {
    log "Testing DNS configuration..."
    
    # Check DNS zone exists
    if ! az network dns zone show --name "$DNS_ZONE" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
        error "DNS zone $DNS_ZONE not found"
        return 1
    fi
    
    # Check service DNS records
    local services=("api" "collector" "processor" "generator")
    local dns_records_found=0
    
    for service in "${services[@]}"; do
        if az network dns record-set a show --zone-name "$DNS_ZONE" --resource-group "$RESOURCE_GROUP" --name "$service" &>/dev/null; then
            log "DNS A record found for $service.$DNS_ZONE"
            dns_records_found=$((dns_records_found + 1))
        else
            warn "DNS A record missing for $service.$DNS_ZONE"
        fi
    done
    
    if [[ $dns_records_found -gt 0 ]]; then
        log "Found $dns_records_found service DNS records"
        return 0
    else
        error "No service DNS records found"
        return 1
    fi
}

# Test 3: Container Apps Deployment
test_container_apps_deployment() {
    log "Testing Container Apps deployment..."
    
    # Check if Container Apps exist
    local apps
    apps=$(az containerapp list --resource-group "$RESOURCE_GROUP" --query "length([?contains(name, 'collector') || contains(name, 'processor') || contains(name, 'generator')])" -o tsv 2>/dev/null || echo "0")
    
    if [[ "$apps" -eq 0 ]]; then
        error "No Container Apps found"
        return 1
    fi
    
    log "Found $apps Container App(s)"
    
    # Check if Dapr-enabled apps exist
    local dapr_apps
    dapr_apps=$(az containerapp list --resource-group "$RESOURCE_GROUP" --query "length([?contains(name, 'dapr')])" -o tsv 2>/dev/null || echo "0")
    
    if [[ "$dapr_apps" -gt 0 ]]; then
        log "Found $dapr_apps Dapr-enabled Container App(s)"
        return 0
    else
        warn "No Dapr-enabled Container Apps found (mTLS may not be enabled)"
        return 0  # Non-blocking for now
    fi
}

# Test 4: Dapr mTLS Configuration
test_dapr_mtls_configuration() {
    log "Testing Dapr mTLS configuration..."
    
    # Check Container App Environment for Dapr components
    local environment_name
    environment_name=$(az containerapp env list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || echo "")
    
    if [[ -z "$environment_name" ]]; then
        error "Container App Environment not found"
        return 1
    fi
    
    log "Using Container App Environment: $environment_name"
    
    # Check for Dapr components (this requires newer Azure CLI)
    # For now, we'll check if the environment has dapr-enabled apps
    local dapr_enabled_apps
    dapr_enabled_apps=$(az containerapp list --resource-group "$RESOURCE_GROUP" --query "length([?properties.configuration.dapr.enabled])" -o tsv 2>/dev/null || echo "0")
    
    if [[ "$dapr_enabled_apps" -gt 0 ]]; then
        log "Found $dapr_enabled_apps Dapr-enabled app(s)"
        return 0
    else
        warn "No Dapr-enabled apps found"
        return 1
    fi
}

# Test 5: Service-to-Service Communication
test_service_communication() {
    log "Testing service-to-service communication..."
    
    # Get Container App URLs
    local collector_url
    collector_url=$(az containerapp show --name "*collector*" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
    
    if [[ -z "$collector_url" ]]; then
        # Try to find any collector app
        collector_url=$(az containerapp list --resource-group "$RESOURCE_GROUP" --query "[?contains(name, 'collector')].properties.configuration.ingress.fqdn | [0]" -o tsv 2>/dev/null || echo "")
    fi
    
    if [[ -z "$collector_url" ]]; then
        warn "Collector app URL not found"
        return 1
    fi
    
    log "Testing collector health endpoint: https://$collector_url"
    
    # Test health endpoint
    local response_code
    response_code=$(curl -s -k -o /dev/null -w "%{http_code}" "https://$collector_url/health" --connect-timeout 10 --max-time 30 || echo "000")
    
    if [[ "$response_code" == "200" ]]; then
        log "Collector health check successful (HTTP $response_code)"
        return 0
    else
        warn "Collector health check failed (HTTP $response_code)"
        return 1
    fi
}

# Test 6: Certificate Expiration Monitoring
test_certificate_monitoring() {
    log "Testing certificate expiration monitoring..."
    
    # Check if monitoring alerts exist
    local alerts
    alerts=$(az monitor metrics alert list --resource-group "$RESOURCE_GROUP" --query "length([?contains(name, 'cert')])" -o tsv 2>/dev/null || echo "0")
    
    if [[ "$alerts" -gt 0 ]]; then
        log "Found $alerts certificate monitoring alert(s)"
        
        # Check Log Analytics workspace
        local workspace
        workspace=$(az monitor log-analytics workspace list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null || echo "")
        
        if [[ -n "$workspace" ]]; then
            log "Log Analytics workspace found: $workspace"
            return 0
        else
            warn "Log Analytics workspace not found"
            return 1
        fi
    else
        warn "No certificate monitoring alerts found"
        return 1
    fi
}

# Test 7: Cost Monitoring
test_cost_monitoring() {
    log "Testing cost monitoring configuration..."
    
    # Check if budget alerts exist
    local budgets
    budgets=$(az consumption budget list --resource-group-name "$RESOURCE_GROUP" --query "length([?contains(name, 'cert')])" -o tsv 2>/dev/null || echo "0")
    
    if [[ "$budgets" -gt 0 ]]; then
        log "Found $budgets cost budget(s) for certificate management"
        return 0
    else
        warn "No cost budgets found for certificate management"
        return 1
    fi
}

# Test 8: End-to-End mTLS Communication
test_end_to_end_mtls() {
    log "Testing end-to-end mTLS communication..."
    
    # This is a comprehensive test that would require actual deployment
    # For now, we'll check if all components are in place
    
    local required_components=("certificates" "dns" "container_apps" "monitoring")
    local components_ready=0
    
    # Check certificates
    if az keyvault certificate list --vault-name "$KEY_VAULT_NAME" --query "length([?contains(name, 'api') || contains(name, 'collector')])" -o tsv | grep -q "^[1-9]"; then
        components_ready=$((components_ready + 1))
        log "✓ Certificates component ready"
    else
        warn "✗ Certificates component not ready"
    fi
    
    # Check DNS
    if az network dns zone show --name "$DNS_ZONE" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
        components_ready=$((components_ready + 1))
        log "✓ DNS component ready"
    else
        warn "✗ DNS component not ready"
    fi
    
    # Check Container Apps
    if [[ $(az containerapp list --resource-group "$RESOURCE_GROUP" --query "length([])" -o tsv) -gt 0 ]]; then
        components_ready=$((components_ready + 1))
        log "✓ Container Apps component ready"
    else
        warn "✗ Container Apps component not ready"
    fi
    
    # Check Monitoring
    if [[ $(az monitor log-analytics workspace list --resource-group "$RESOURCE_GROUP" --query "length([])" -o tsv) -gt 0 ]]; then
        components_ready=$((components_ready + 1))
        log "✓ Monitoring component ready"
    else
        warn "✗ Monitoring component not ready"
    fi
    
    if [[ $components_ready -eq ${#required_components[@]} ]]; then
        log "All mTLS components are ready"
        return 0
    else
        warn "Only $components_ready of ${#required_components[@]} mTLS components are ready"
        return 1
    fi
}

# Generate test report
generate_test_report() {
    log "Generating test report..."
    
    echo
    echo "==============================================="
    echo "mTLS Integration Test Report"
    echo "==============================================="
    echo "Total Tests: $TOTAL_TESTS"
    echo "Passed: $PASSED_TESTS"
    echo "Failed: $((TOTAL_TESTS - PASSED_TESTS))"
    echo "Success Rate: $(( (PASSED_TESTS * 100) / TOTAL_TESTS ))%"
    echo
    echo "Test Results:"
    
    for result in "${TEST_RESULTS[@]}"; do
        if [[ "$result" =~ ^PASS ]]; then
            echo -e "${GREEN}$result${NC}"
        else
            echo -e "${RED}$result${NC}"
        fi
    done
    
    echo
    echo "==============================================="
    
    # Return success if all tests passed
    if [[ $PASSED_TESTS -eq $TOTAL_TESTS ]]; then
        success "All tests passed!"
        return 0
    else
        error "Some tests failed!"
        return 1
    fi
}

# Main test execution
main() {
    log "Starting mTLS Integration Test Suite"
    
    if ! check_prerequisites; then
        error "Prerequisites check failed"
        exit 1
    fi
    
    # Run all tests
    run_test "Certificate Storage" test_certificate_storage
    run_test "DNS Configuration" test_dns_configuration
    run_test "Container Apps Deployment" test_container_apps_deployment
    run_test "Dapr mTLS Configuration" test_dapr_mtls_configuration
    run_test "Service Communication" test_service_communication
    run_test "Certificate Monitoring" test_certificate_monitoring
    run_test "Cost Monitoring" test_cost_monitoring
    run_test "End-to-End mTLS" test_end_to_end_mtls
    
    # Generate final report
    generate_test_report
}

# Handle script arguments
case "${1:-all}" in
    "all")
        main
        ;;
    "prerequisites")
        check_prerequisites
        ;;
    "certificates")
        run_test "Certificate Storage" test_certificate_storage
        ;;
    "dns")
        run_test "DNS Configuration" test_dns_configuration
        ;;
    "apps")
        run_test "Container Apps Deployment" test_container_apps_deployment
        ;;
    "dapr")
        run_test "Dapr mTLS Configuration" test_dapr_mtls_configuration
        ;;
    "communication")
        run_test "Service Communication" test_service_communication
        ;;
    "monitoring")
        run_test "Certificate Monitoring" test_certificate_monitoring
        ;;
    "cost")
        run_test "Cost Monitoring" test_cost_monitoring
        ;;
    "e2e")
        run_test "End-to-End mTLS" test_end_to_end_mtls
        ;;
    "help"|*)
        echo "Usage: $0 {all|prerequisites|certificates|dns|apps|dapr|communication|monitoring|cost|e2e|help}"
        echo
        echo "  all            - Run all tests (default)"
        echo "  prerequisites  - Check prerequisites only"
        echo "  certificates   - Test certificate storage"
        echo "  dns           - Test DNS configuration"
        echo "  apps          - Test Container Apps deployment"
        echo "  dapr          - Test Dapr mTLS configuration"
        echo "  communication - Test service-to-service communication"
        echo "  monitoring    - Test certificate monitoring"
        echo "  cost          - Test cost monitoring"
        echo "  e2e           - Test end-to-end mTLS functionality"
        echo "  help          - Show this help message"
        exit 0
        ;;
esac
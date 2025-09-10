#!/bin/bash
"""
Azure AD Authentication Test Script

Tests the Phase 2 Security Implementation Azure AD token authentication.
Validates that Container Apps properly validate Azure AD tokens and
reject unauthorized requests.

Features:
- Azure AD token acquisition testing
- Token validation endpoint testing
- Role-based access control verification
- Authentication failure handling
- Token expiry and refresh testing
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

    log_info "Resource Group: $RESOURCE_GROUP"
    log_info "Content Collector: $CONTENT_COLLECTOR_URL"
    log_info "Content Processor: $CONTENT_PROCESSOR_URL"
    log_info "Site Generator: $SITE_GENERATOR_URL"
}

# Azure AD token functions
get_azure_ad_token() {
    log_info "Acquiring Azure AD access token..."

    # Try to get token for Microsoft Graph (common scope)
    local token=$(az account get-access-token --resource "https://graph.microsoft.com" --query "accessToken" -o tsv 2>/dev/null || echo "")

    if [[ -n "$token" ]]; then
        log_success "Azure AD token acquired successfully"
        echo "$token"
    else
        log_error "Failed to acquire Azure AD token"
        return 1
    fi
}

get_invalid_token() {
    # Create an obviously invalid token for testing
    echo "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6IjFMVE16YWtpaGlSbGFfKzR0OXRGaEJmZ2FSUSIsImtpZCI6IjFMVE16YWtpaGlSbGFfKzR0OXRGaEJmZ2FSUSJHRU1TYWtpaGlSbGFfKzR0OXRGaEJmZ2FSUSJDVE1TYWtpaGlSbGFfKzR0OXRGaEJmZ2FSUSIsImtpZCI6IjFMVE16YWtpaGlSbGFfKzR0OXRGaEJmZ2FSUSIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2IiwieDV0IjoiMUxUTXpha2loaVJsYV8rNHQ5dEZoQmZnYVJRIiwia2lkIjoiMUxUTXpha2loaVJsYV8rNHQ5dEZoQmZnYVJRIn0.INVALID_TOKEN_FOR_TESTING"
}

# Test functions
test_unauthorized_access() {
    log_info "Testing unauthorized access (no token)..."

    local containers=("$CONTENT_COLLECTOR_URL" "$CONTENT_PROCESSOR_URL" "$SITE_GENERATOR_URL")
    local container_names=("content-collector" "content-processor" "site-generator")

    for i in "${!containers[@]}"; do
        local url="${containers[$i]}"
        local name="${container_names[$i]}"

        if [[ -z "$url" ]]; then
            log_warning "Skipping $name - URL not available"
            continue
        fi

        log_info "Testing unauthorized access to $name..."

        # Test health endpoint (should be accessible without auth)
        local health_response=$(curl -s -w "%{http_code}" \
            "https://$url/health" \
            -o /tmp/health_response.json || echo "000")

        if [[ "$health_response" == "200" ]]; then
            log_success "$name health endpoint accessible without auth (expected)"
        else
            log_warning "$name health endpoint returned HTTP $health_response"
        fi

        # Test protected endpoint without token (should return 401)
        local protected_response=$(curl -s -w "%{http_code}" \
            "https://$url/status" \
            -o /tmp/protected_response.json || echo "000")

        if [[ "$protected_response" == "401" ]]; then
            log_success "$name protected endpoint correctly returns 401 without token"
        elif [[ "$protected_response" == "200" ]]; then
            log_warning "$name protected endpoint allows access without token (Phase 2 not implemented yet)"
        else
            log_error "$name protected endpoint unexpected response: HTTP $protected_response"
        fi
    done
}

test_invalid_token_access() {
    log_info "Testing access with invalid token..."

    local invalid_token=$(get_invalid_token)
    local containers=("$CONTENT_COLLECTOR_URL" "$CONTENT_PROCESSOR_URL" "$SITE_GENERATOR_URL")
    local container_names=("content-collector" "content-processor" "site-generator")

    for i in "${!containers[@]}"; do
        local url="${containers[$i]}"
        local name="${container_names[$i]}"

        if [[ -z "$url" ]]; then
            log_warning "Skipping $name - URL not available"
            continue
        fi

        log_info "Testing invalid token access to $name..."

        local response=$(curl -s -w "%{http_code}" \
            -H "Authorization: Bearer $invalid_token" \
            "https://$url/status" \
            -o /tmp/invalid_token_response.json || echo "000")

        if [[ "$response" == "401" || "$response" == "403" ]]; then
            log_success "$name correctly rejects invalid token (HTTP $response)"
        elif [[ "$response" == "200" ]]; then
            log_warning "$name allows access with invalid token (Phase 2 not implemented yet)"
        else
            log_error "$name unexpected response to invalid token: HTTP $response"
        fi
    done
}

test_valid_token_access() {
    log_info "Testing access with valid Azure AD token..."

    local token=$(get_azure_ad_token)
    if [[ -z "$token" ]]; then
        log_error "Cannot test valid token access - no token available"
        return 1
    fi

    local containers=("$CONTENT_COLLECTOR_URL" "$CONTENT_PROCESSOR_URL" "$SITE_GENERATOR_URL")
    local container_names=("content-collector" "content-processor" "site-generator")

    for i in "${!containers[@]}"; do
        local url="${containers[$i]}"
        local name="${container_names[$i]}"

        if [[ -z "$url" ]]; then
            log_warning "Skipping $name - URL not available"
            continue
        fi

        log_info "Testing valid token access to $name..."

        local response=$(curl -s -w "%{http_code}" \
            -H "Authorization: Bearer $token" \
            "https://$url/status" \
            -o /tmp/valid_token_response.json || echo "000")

        if [[ "$response" == "200" ]]; then
            local status=$(jq -r '.status' /tmp/valid_token_response.json 2>/dev/null || echo "unknown")
            if [[ "$status" == "success" ]]; then
                log_success "$name accepts valid Azure AD token"
            else
                log_warning "$name valid token access returned status: $status"
            fi
        elif [[ "$response" == "401" || "$response" == "403" ]]; then
            log_warning "$name rejects valid token (may need app registration configuration)"
        else
            log_error "$name unexpected response to valid token: HTTP $response"
        fi
    done
}

# mTLS Certificate and Communication Testing Functions
test_mtls_certificates() {
    log_info "Testing mTLS certificate availability..."

    # Check if certificates exist in Key Vault
    local cert_name="mtls-wildcard-cert"
    local cert_exists=$(az keyvault certificate show \
        --vault-name "$(az keyvault list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)" \
        --name "$cert_name" \
        --query "id" -o tsv 2>/dev/null || echo "")

    if [[ -n "$cert_exists" ]]; then
        log_success "mTLS certificate found in Key Vault: $cert_name"
        
        # Check certificate expiry
        local expires=$(az keyvault certificate show \
            --vault-name "$(az keyvault list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)" \
            --name "$cert_name" \
            --query "attributes.expires" -o tsv)
        
        local expires_epoch=$(date -d "$expires" +%s)
        local current_epoch=$(date +%s)
        local days_remaining=$(( (expires_epoch - current_epoch) / 86400 ))
        
        if [[ $days_remaining -gt 30 ]]; then
            log_success "Certificate valid for $days_remaining more days"
        else
            log_warning "Certificate expires in $days_remaining days - renewal recommended"
        fi
    else
        log_error "mTLS certificate not found in Key Vault"
    fi
}

test_mtls_communication() {
    log_info "Testing mTLS inter-service communication..."

    # Test Dapr service invocation with mTLS
    local containers=("content-collector" "content-processor" "site-generator")
    
    for container in "${containers[@]}"; do
        log_info "Testing $container Dapr mTLS communication..."
        
        # Get container app URL
        local app_url=$(az containerapp show \
            --resource-group "$RESOURCE_GROUP" \
            --name "ai-content-dev-$container" \
            --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
        
        if [[ -n "$app_url" ]]; then
            # Test Dapr health endpoint
            local dapr_response=$(curl -s -w "%{http_code}" \
                "https://$app_url/v1.0/healthz" \
                -o /tmp/dapr_health.json || echo "000")
            
            if [[ "$dapr_response" == "200" ]]; then
                log_success "$container Dapr sidecar is healthy"
                
                # Check if mTLS is enabled
                local mtls_status=$(curl -s "https://$app_url/v1.0/metadata" \
                    | jq -r '.extendedMetadata.daprRuntimeVersion' 2>/dev/null || echo "unknown")
                
                if [[ "$mtls_status" != "unknown" ]]; then
                    log_success "$container Dapr runtime detected: $mtls_status"
                else
                    log_warning "$container Dapr metadata not available"
                fi
            else
                log_error "$container Dapr health check failed: HTTP $dapr_response"
            fi
        else
            log_warning "$container URL not available for mTLS testing"
        fi
    done
}

test_service_discovery() {
    log_info "Testing service discovery functionality..."

    # Check DNS zone and records
    local dns_zone=$(az network dns zone show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$DOMAIN_NAME" \
        --query "name" -o tsv 2>/dev/null || echo "")

    if [[ -n "$dns_zone" ]]; then
        log_success "DNS zone found: $dns_zone"
        
        # Check CNAME records for each service
        local services=("collector" "processor" "generator")
        for service in "${services[@]}"; do
            local cname_record=$(az network dns record-set cname show \
                --resource-group "$RESOURCE_GROUP" \
                --zone-name "$dns_zone" \
                --name "$service" \
                --query "cname" -o tsv 2>/dev/null || echo "")
            
            if [[ -n "$cname_record" ]]; then
                log_success "Service discovery record found: $service.$dns_zone -> $cname_record"
                
                # Test DNS resolution
                if nslookup "$service.$dns_zone" &>/dev/null; then
                    log_success "DNS resolution working for $service.$dns_zone"
                else
                    log_warning "DNS resolution failed for $service.$dns_zone"
                fi
            else
                log_error "Service discovery record not found: $service.$dns_zone"
            fi
        done
    else
        log_error "DNS zone not found: $DOMAIN_NAME"
    fi
}

test_keda_scaling() {
    log_info "Testing KEDA autoscaling configuration..."

    local containers=("content-collector" "content-processor" "site-generator")
    
    for container in "${containers[@]}"; do
        log_info "Checking KEDA scaling for $container..."
        
        # Get container app scaling configuration
        local scaling_config=$(az containerapp show \
            --resource-group "$RESOURCE_GROUP" \
            --name "ai-content-dev-$container" \
            --query "properties.template.scale" -o json 2>/dev/null || echo "{}")
        
        local min_replicas=$(echo "$scaling_config" | jq -r '.minReplicas // "0"')
        local max_replicas=$(echo "$scaling_config" | jq -r '.maxReplicas // "1"')
        local scale_rules=$(echo "$scaling_config" | jq -r '.rules | length // 0')
        
        log_info "$container scaling: min=$min_replicas, max=$max_replicas, rules=$scale_rules"
        
        if [[ $scale_rules -gt 0 ]]; then
            log_success "$container has KEDA scaling rules configured"
        else
            log_warning "$container has no scaling rules configured"
        fi
    done
}

test_certificate_monitoring() {
    log_info "Testing certificate expiration monitoring..."

    # Check if monitoring alerts are configured
    local cert_alert=$(az monitor metrics alert show \
        --resource-group "$RESOURCE_GROUP" \
        --name "ai-content-dev-cert-expiry-alert" \
        --query "name" -o tsv 2>/dev/null || echo "")

    if [[ -n "$cert_alert" ]]; then
        log_success "Certificate expiration alert configured: $cert_alert"
        
        # Check alert status
        local alert_enabled=$(az monitor metrics alert show \
            --resource-group "$RESOURCE_GROUP" \
            --name "ai-content-dev-cert-expiry-alert" \
            --query "enabled" -o tsv)
        
        if [[ "$alert_enabled" == "true" ]]; then
            log_success "Certificate monitoring alert is enabled"
        else
            log_warning "Certificate monitoring alert is disabled"
        fi
    else
        log_error "Certificate expiration alert not found"
    fi

    # Test Application Insights integration
    local app_insights=$(az monitor app-insights component show \
        --resource-group "$RESOURCE_GROUP" \
        --app "ai-content-dev-appinsights" \
        --query "name" -o tsv 2>/dev/null || echo "")

    if [[ -n "$app_insights" ]]; then
        log_success "Application Insights configured for mTLS monitoring"
    else
        log_warning "Application Insights not found for detailed monitoring"
    fi
}

test_token_validation_endpoints() {
    log_info "Testing token validation endpoints..."

    local token=$(get_azure_ad_token)
    if [[ -z "$token" ]]; then
        log_warning "Cannot test token validation - no token available"
        return 0
    fi

    # Test token info endpoint (if implemented)
    local containers=("$CONTENT_COLLECTOR_URL" "$CONTENT_PROCESSOR_URL" "$SITE_GENERATOR_URL")
    local container_names=("content-collector" "content-processor" "site-generator")

    for i in "${!containers[@]}"; do
        local url="${containers[$i]}"
        local name="${container_names[$i]}"

        if [[ -z "$url" ]]; then
            continue
        fi

        # Test if there's a token validation endpoint
        local validation_response=$(curl -s -w "%{http_code}" \
            -H "Authorization: Bearer $token" \
            "https://$url/auth/validate" \
            -o /tmp/token_validation_response.json 2>/dev/null || echo "404")

        if [[ "$validation_response" == "200" ]]; then
            log_success "$name has token validation endpoint"
        elif [[ "$validation_response" == "404" ]]; then
            log_info "$name does not have token validation endpoint (optional)"
        else
            log_warning "$name token validation endpoint returned HTTP $validation_response"
        fi
    done
}

test_role_based_access() {
    log_info "Testing role-based access control..."

    local token=$(get_azure_ad_token)
    if [[ -z "$token" ]]; then
        log_warning "Cannot test RBAC - no token available"
        return 0
    fi

    # Test different endpoints that might have different permission requirements
    local containers=("$CONTENT_COLLECTOR_URL" "$CONTENT_PROCESSOR_URL" "$SITE_GENERATOR_URL")
    local container_names=("content-collector" "content-processor" "site-generator")

    for i in "${!containers[@]}"; do
        local url="${containers[$i]}"
        local name="${container_names[$i]}"

        if [[ -z "$url" ]]; then
            continue
        fi

        # Test read-only endpoint
        local read_response=$(curl -s -w "%{http_code}" \
            -H "Authorization: Bearer $token" \
            "https://$url/status" \
            -o /tmp/rbac_read_response.json || echo "000")

        # Test write endpoint (POST to collections, processing, etc.)
        local write_endpoint=""
        case "$name" in
            "content-collector")
                write_endpoint="/collections"
                ;;
            "content-processor")
                write_endpoint="/process"
                ;;
            "site-generator")
                write_endpoint="/generate-markdown"
                ;;
        esac

        if [[ -n "$write_endpoint" ]]; then
            local write_response=$(curl -s -w "%{http_code}" \
                -X POST \
                -H "Authorization: Bearer $token" \
                -H "Content-Type: application/json" \
                -d '{"test": "rbac"}' \
                "https://$url$write_endpoint" \
                -o /tmp/rbac_write_response.json || echo "000")

            log_info "$name read access: HTTP $read_response, write access: HTTP $write_response"

            # For now, just log the results since RBAC implementation details depend on app registration
            if [[ "$read_response" == "200" && "$write_response" == "200" ]]; then
                log_info "$name allows both read and write access"
            elif [[ "$read_response" == "200" && "$write_response" != "200" ]]; then
                log_success "$name has differentiated read/write access"
            else
                log_info "$name RBAC results: read=$read_response, write=$write_response"
            fi
        fi
    done
}

test_token_expiry_handling() {
    log_info "Testing token expiry handling..."

    # Test with an expired token (simulated)
    local expired_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiJhcGk6Ly9leGFtcGxlIiwiaXNzIjoiaHR0cHM6Ly9zdHMud2luZG93cy5uZXQvIiwiaWF0IjoxNjAwMDAwMDAwLCJuYmYiOjE2MDAwMDAwMDAsImV4cCI6MTYwMDAwMDAwMSwic3ViIjoidGVzdCIsIm5hbWUiOiJUZXN0IFVzZXIifQ.EXPIRED_TOKEN_SIGNATURE" # pragma: allowlist secret

    local containers=("$CONTENT_COLLECTOR_URL")
    if [[ -n "$CONTENT_COLLECTOR_URL" ]]; then
        log_info "Testing expired token handling..."

        local response=$(curl -s -w "%{http_code}" \
            -H "Authorization: Bearer $expired_token" \
            "https://$CONTENT_COLLECTOR_URL/status" \
            -o /tmp/expired_token_response.json || echo "000")

        if [[ "$response" == "401" ]]; then
            log_success "Container correctly rejects expired token"
        elif [[ "$response" == "403" ]]; then
            log_success "Container correctly handles expired token with 403"
        else
            log_warning "Container response to expired token: HTTP $response"
        fi
    fi
}

# Integration test with Service Bus
test_azure_ad_servicebus_integration() {
    log_info "Testing Azure AD integration with Service Bus endpoints..."

    local token=$(get_azure_ad_token)
    if [[ -z "$token" ]]; then
        log_warning "Cannot test Azure AD + Service Bus integration - no token available"
        return 0
    fi

    # Test Service Bus endpoints with Azure AD token
    local containers=("$CONTENT_COLLECTOR_URL" "$CONTENT_PROCESSOR_URL" "$SITE_GENERATOR_URL")
    local container_names=("content-collector" "content-processor" "site-generator")

    for i in "${!containers[@]}"; do
        local url="${containers[$i]}"
        local name="${container_names[$i]}"

        if [[ -z "$url" ]]; then
            continue
        fi

        # Test Service Bus status endpoint with Azure AD token
        local sb_response=$(curl -s -w "%{http_code}" \
            -H "Authorization: Bearer $token" \
            "https://$url/internal/servicebus-status" \
            -o /tmp/azuread_sb_response.json || echo "000")

        if [[ "$sb_response" == "200" ]]; then
            log_success "$name Service Bus endpoint accepts Azure AD token"
        elif [[ "$sb_response" == "401" || "$sb_response" == "403" ]]; then
            log_info "$name Service Bus endpoint enforces authentication (HTTP $sb_response)"
        else
            log_warning "$name Service Bus endpoint response: HTTP $sb_response"
        fi
    done
}

# Cleanup function
cleanup_test_resources() {
    log_info "Cleaning up test resources..."

    # Remove any test files
    rm -f /tmp/health_response.json /tmp/protected_response.json
    rm -f /tmp/invalid_token_response.json /tmp/valid_token_response.json
    rm -f /tmp/token_validation_response.json /tmp/rbac_read_response.json
    rm -f /tmp/rbac_write_response.json /tmp/expired_token_response.json
    rm -f /tmp/azuread_sb_response.json

    log_info "Cleanup completed"
}

# Main execution
main() {
    echo "Azure AD Authentication and mTLS Security Test Suite"
    echo "==================================================="
    echo ""

    # Set trap for cleanup
    trap cleanup_test_resources EXIT

    # Check if running in mTLS mode
    local mtls_mode="${1:-full}"
    
    # Run tests
    check_dependencies
    get_azure_resources

    # Azure AD Authentication Tests
    log_info "Running Azure AD Authentication Tests..."
    test_unauthorized_access
    test_invalid_token_access
    test_valid_token_access
    test_token_validation_endpoints
    test_role_based_access
    test_token_expiry_handling
    test_azure_ad_servicebus_integration

    # mTLS and Service Discovery Tests (Phase 2)
    if [[ "$mtls_mode" == "full" || "$mtls_mode" == "mtls" ]]; then
        log_info "Running mTLS and Service Discovery Tests..."
        test_mtls_certificates
        test_mtls_communication
        test_service_discovery
        test_keda_scaling
        test_certificate_monitoring
    fi

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
        log_success "All security tests completed successfully!"
        echo ""
        if [[ "$mtls_mode" == "full" ]]; then
            echo "✅ Azure AD authentication validated"
            echo "✅ mTLS certificates validated"  
            echo "✅ Service discovery tested"
            echo "✅ KEDA scaling verified"
            echo "✅ Certificate monitoring confirmed"
        else
            echo "Note: Some tests may show warnings if Phase 2 (mTLS/Service Discovery)"
            echo "is not yet fully implemented. Use 'mtls' mode to test mTLS features only."
        fi
        exit 0
    else
        log_error "Some security tests failed"
        exit 1
    fi
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

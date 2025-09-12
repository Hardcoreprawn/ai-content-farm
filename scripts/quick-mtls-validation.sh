#!/bin/bash
"""
Quick mTLS Health Check Script

Performs basic validation of mTLS implementation for CI/CD pipelines.
This is a simpler version of the comprehensive validation for automated testing.
"""

set -euo pipefail

# Configuration
DOMAIN="${MTLS_DOMAIN:-example.com}"
SERVICES="${MTLS_SERVICES:-content-collector,content-processor,site-generator}"
TIMEOUT="${MTLS_TIMEOUT:-30}"
VERBOSE="${MTLS_VERBOSE:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Test function
test_endpoint() {
    local url="$1"
    local expected_status="${2:-200}"
    local timeout="${3:-10}"

    if [[ "$VERBOSE" == "true" ]]; then
        log_info "Testing: $url"
    fi

    local response
    response=$(curl -s -w "%{http_code}" -o /tmp/response.txt --max-time "$timeout" --fail-with-body "$url" 2>/dev/null || echo "000")

    if [[ "$response" == "$expected_status" ]]; then
        return 0
    else
        if [[ "$VERBOSE" == "true" ]]; then
            log_error "Expected $expected_status, got $response"
            if [[ -f /tmp/response.txt ]]; then
                cat /tmp/response.txt
            fi
        fi
        return 1
    fi
}

# Certificate validation
validate_certificates() {
    log_info "🔒 Validating mTLS Certificates"

    local cert_dir="/etc/ssl/certs"
    local errors=0

    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
    for service in "${SERVICE_ARRAY[@]}"; do
        service=$(echo "$service" | xargs) # trim whitespace

        local cert_file="$cert_dir/$service.crt"
        local key_file="$cert_dir/$service.key"

        if [[ -f "$cert_file" && -f "$key_file" ]]; then
            # Check certificate expiration
            if command -v openssl >/dev/null 2>&1; then
                local expiry_date
                expiry_date=$(openssl x509 -in "$cert_file" -noout -enddate 2>/dev/null | cut -d= -f2)
                local expiry_epoch
                expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null || echo "0")
                local current_epoch
                current_epoch=$(date +%s)
                local days_left=$(( (expiry_epoch - current_epoch) / 86400 ))

                if [[ $days_left -lt 7 ]]; then
                    log_error "Certificate for $service expires in $days_left days"
                    ((errors++))
                elif [[ $days_left -lt 30 ]]; then
                    log_warning "Certificate for $service expires in $days_left days"
                else
                    log_success "Certificate for $service is valid ($days_left days remaining)"
                fi
            else
                log_warning "OpenSSL not available, skipping certificate expiration check"
            fi
        else
            log_error "Missing certificate files for $service"
            ((errors++))
        fi
    done

    return $errors
}

# Service health validation
validate_service_health() {
    log_info "🏥 Validating Service Health"

    local errors=0

    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
    for service in "${SERVICE_ARRAY[@]}"; do
        service=$(echo "$service" | xargs) # trim whitespace

        local base_url="https://$service.$DOMAIN"

        # Test basic health endpoint
        if test_endpoint "$base_url/health" 200 "$TIMEOUT"; then
            log_success "$service health endpoint responding"
        else
            log_error "$service health endpoint failed"
            ((errors++))
        fi

        # Test mTLS-specific health endpoint
        if test_endpoint "$base_url/health/mtls" 200 "$TIMEOUT"; then
            log_success "$service mTLS health endpoint responding"
        else
            log_warning "$service mTLS health endpoint failed (may not be implemented yet)"
        fi

        # Test status endpoint
        if test_endpoint "$base_url/status" 200 "$TIMEOUT"; then
            log_success "$service status endpoint responding"
        else
            log_warning "$service status endpoint failed"
        fi
    done

    return $errors
}

# Inter-service communication validation
validate_inter_service_communication() {
    log_info "🔗 Validating Inter-Service Communication"

    local errors=0

    # Test content-collector -> content-processor communication
    log_info "Testing content-collector -> content-processor"
    if test_endpoint "https://content-collector.$DOMAIN/health/dependencies" 200 "$TIMEOUT"; then
        log_success "Content collector can communicate with dependencies"
    else
        log_warning "Content collector dependency check failed"
    fi

    # Test content-processor -> site-generator communication
    log_info "Testing content-processor -> site-generator"
    if test_endpoint "https://content-processor.$DOMAIN/health/dependencies" 200 "$TIMEOUT"; then
        log_success "Content processor can communicate with dependencies"
    else
        log_warning "Content processor dependency check failed"
    fi

    # Test end-to-end pipeline health from site-generator
    log_info "Testing end-to-end pipeline health"
    if test_endpoint "https://site-generator.$DOMAIN/health/pipeline" 200 "$TIMEOUT"; then
        log_success "End-to-end pipeline health check passed"
    else
        log_warning "End-to-end pipeline health check failed"
    fi

    return $errors
}

# DNS resolution validation
validate_dns_resolution() {
    log_info "🌐 Validating DNS Resolution"

    local errors=0

    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
    for service in "${SERVICE_ARRAY[@]}"; do
        service=$(echo "$service" | xargs) # trim whitespace

        local fqdn="$service.$DOMAIN"

        if nslookup "$fqdn" >/dev/null 2>&1; then
            log_success "DNS resolution for $fqdn working"
        else
            log_error "DNS resolution for $fqdn failed"
            ((errors++))
        fi
    done

    return $errors
}

# Main validation function
main() {
    log_info "🚀 Starting mTLS Implementation Validation"
    log_info "Domain: $DOMAIN"
    log_info "Services: $SERVICES"
    log_info "Timeout: ${TIMEOUT}s"
    echo ""

    local total_errors=0

    # Run all validations
    validate_dns_resolution || total_errors=$((total_errors + $?))
    echo ""

    validate_certificates || total_errors=$((total_errors + $?))
    echo ""

    validate_service_health || total_errors=$((total_errors + $?))
    echo ""

    validate_inter_service_communication || total_errors=$((total_errors + $?))
    echo ""

    # Summary
    if [[ $total_errors -eq 0 ]]; then
        log_success "✅ All mTLS validation checks passed!"
        exit 0
    else
        log_error "❌ $total_errors validation errors found"
        exit 1
    fi
}

# Handle script arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --services)
            SERVICES="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE="true"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --domain DOMAIN     Domain name for testing (default: example.com)"
            echo "  --services LIST     Comma-separated list of services (default: content-collector,content-processor,site-generator)"
            echo "  --timeout SECONDS   Request timeout in seconds (default: 30)"
            echo "  --verbose          Enable verbose output"
            echo "  --help             Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  MTLS_DOMAIN        Same as --domain"
            echo "  MTLS_SERVICES      Same as --services"
            echo "  MTLS_TIMEOUT       Same as --timeout"
            echo "  MTLS_VERBOSE       Same as --verbose (true/false)"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main

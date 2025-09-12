#!/bin/bash
"""
Azure PKI Certificate Management Script

Handles certificate provisioning, renewal, and deployment for mTLS infrastructure.
Integrates with Azure Key Vault and Let's Encrypt via ACME.
"""

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOMAIN="${MTLS_DOMAIN:-jablab.dev}"
KEY_VAULT_NAME="${AZURE_KEY_VAULT_NAME:-}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-}"
SERVICES="${CERTIFICATE_SERVICES:-content-collector,content-processor,site-generator}"

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

# Check prerequisites
check_prerequisites() {
    log_info "🔍 Checking prerequisites..."

    # Check Azure CLI
    if ! command -v az >/dev/null 2>&1; then
        log_error "Azure CLI not found. Please install Azure CLI."
        exit 1
    fi

    # Check if logged in
    if ! az account show >/dev/null 2>&1; then
        log_error "Not logged into Azure. Please run 'az login'"
        exit 1
    fi

    # Check terraform
    if ! command -v terraform >/dev/null 2>&1; then
        log_error "Terraform not found. Please install Terraform."
        exit 1
    fi

    # Check required variables
    if [[ -z "$KEY_VAULT_NAME" ]]; then
        log_error "AZURE_KEY_VAULT_NAME environment variable not set"
        exit 1
    fi

    if [[ -z "$RESOURCE_GROUP" ]]; then
        log_error "AZURE_RESOURCE_GROUP environment variable not set"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Deploy PKI infrastructure
deploy_pki_infrastructure() {
    log_info "🏗️ Deploying PKI infrastructure..."

    cd "$PROJECT_ROOT/infra"

    # Initialize terraform if needed
    if [[ ! -f ".terraform.lock.hcl" ]]; then
        terraform init
    fi

    # Plan with PKI enabled
    terraform plan \
        -var="enable_pki=true" \
        -var="primary_domain=$DOMAIN" \
        -var="certificate_email=${CERTIFICATE_EMAIL:-admin@${DOMAIN}}" \
        -out=pki.tfplan

    # Apply the plan
    log_info "Applying PKI infrastructure changes..."
    terraform apply pki.tfplan

    # Clean up plan file
    rm -f pki.tfplan

    log_success "PKI infrastructure deployed"
}

# Check certificate status
check_certificate_status() {
    local service="$1"

    log_info "📋 Checking certificate status for $service..."

    # Check if certificate exists in Key Vault
    local cert_name="${service}-certificate"

    if az keyvault certificate show \
        --vault-name "$KEY_VAULT_NAME" \
        --name "$cert_name" \
        --output none 2>/dev/null; then

        # Get certificate details
        local cert_info
        cert_info=$(az keyvault certificate show \
            --vault-name "$KEY_VAULT_NAME" \
            --name "$cert_name" \
            --output json)

        local expires_on
        expires_on=$(echo "$cert_info" | jq -r '.attributes.expires')

        local expiry_date
        expiry_date=$(date -d "@$expires_on" +"%Y-%m-%d %H:%M:%S")

        local days_until_expiry
        days_until_expiry=$(( (expires_on - $(date +%s)) / 86400 ))

        if [[ $days_until_expiry -lt 7 ]]; then
            log_error "Certificate for $service expires in $days_until_expiry days ($expiry_date)"
            return 2
        elif [[ $days_until_expiry -lt 30 ]]; then
            log_warning "Certificate for $service expires in $days_until_expiry days ($expiry_date)"
            return 1
        else
            log_success "Certificate for $service is valid (expires in $days_until_expiry days)"
            return 0
        fi
    else
        log_warning "Certificate for $service not found in Key Vault"
        return 1
    fi
}

# Renew certificates
renew_certificates() {
    log_info "🔄 Renewing certificates..."

    local needs_renewal=false

    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
    for service in "${SERVICE_ARRAY[@]}"; do
        service=$(echo "$service" | xargs) # trim whitespace

        if ! check_certificate_status "$service"; then
            needs_renewal=true
        fi
    done

    if [[ "$needs_renewal" == "true" ]]; then
        log_info "Some certificates need renewal. Re-running Terraform..."

        cd "$PROJECT_ROOT/infra"

        # Force renewal by tainting the certificate resources
        IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
        for service in "${SERVICE_ARRAY[@]}"; do
            service=$(echo "$service" | xargs)
            terraform taint "acme_certificate.service_certificates[\"$service\"]" 2>/dev/null || true
        done

        # Apply changes
        terraform apply \
            -var="enable_pki=true" \
            -var="primary_domain=$DOMAIN" \
            -var="certificate_email=${CERTIFICATE_EMAIL:-admin@${DOMAIN}}" \
            -auto-approve

        log_success "Certificate renewal completed"
    else
        log_success "All certificates are valid"
    fi
}

# Deploy certificates to Container Apps
deploy_certificates_to_containers() {
    log_info "🚀 Deploying certificates to Container Apps..."

    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
    for service in "${SERVICE_ARRAY[@]}"; do
        service=$(echo "$service" | xargs)

        local cert_name="${service}-certificate"
        local key_name="${service}-private-key"

        log_info "Deploying certificate for $service..."

        # Get certificate and key from Key Vault
        local cert_content
        cert_content=$(az keyvault certificate download \
            --vault-name "$KEY_VAULT_NAME" \
            --name "$cert_name" \
            --file /tmp/"$cert_name".pem \
            --encoding PEM 2>/dev/null && cat /tmp/"$cert_name".pem)

        local key_content
        key_content=$(az keyvault secret show \
            --vault-name "$KEY_VAULT_NAME" \
            --name "$key_name" \
            --query value \
            --output tsv)

        # Create Kubernetes secrets for Container Apps
        # Note: This assumes you have kubectl configured for the Container Apps environment
        if command -v kubectl >/dev/null 2>&1; then
            kubectl create secret tls "${service}-tls" \
                --cert=<(echo "$cert_content") \
                --key=<(echo "$key_content") \
                --dry-run=client -o yaml | kubectl apply -f -

            log_success "Certificate deployed for $service"
        else
            log_warning "kubectl not available. Certificates available in Key Vault for manual deployment."
        fi

        # Clean up temp files
        rm -f /tmp/"$cert_name".pem
    done
}

# Update DNS records
update_dns_records() {
    log_info "🌐 Updating DNS records..."

    # Get Container Apps environment IP
    local container_app_ip
    container_app_ip=$(az containerapp env show \
        --name "${RESOURCE_GROUP}-containerapp-env" \
        --resource-group "$RESOURCE_GROUP" \
        --query properties.staticIp \
        --output tsv 2>/dev/null || echo "")

    if [[ -z "$container_app_ip" ]]; then
        log_warning "Could not get Container Apps IP. Using placeholder."
        container_app_ip="20.108.146.58"
    fi

    log_info "Using IP address: $container_app_ip"

    # Update DNS A records for each service
    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
    for service in "${SERVICE_ARRAY[@]}"; do
        service=$(echo "$service" | xargs)

        # Update jablab.dev record
        az network dns record-set a add-record \
            --resource-group "$RESOURCE_GROUP" \
            --zone-name "jablab.dev" \
            --record-set-name "$service" \
            --ipv4-address "$container_app_ip" \
            --output none 2>/dev/null || {

            # Create the record if it doesn't exist
            az network dns record-set a create \
                --resource-group "$RESOURCE_GROUP" \
                --zone-name "jablab.dev" \
                --name "$service" \
                --ttl 300 \
                --output none

            az network dns record-set a add-record \
                --resource-group "$RESOURCE_GROUP" \
                --zone-name "jablab.dev" \
                --record-set-name "$service" \
                --ipv4-address "$container_app_ip" \
                --output none
        }

        # Update jablab.com record
        az network dns record-set a add-record \
            --resource-group "$RESOURCE_GROUP" \
            --zone-name "jablab.com" \
            --record-set-name "$service" \
            --ipv4-address "$container_app_ip" \
            --output none 2>/dev/null || {

            # Create the record if it doesn't exist
            az network dns record-set a create \
                --resource-group "$RESOURCE_GROUP" \
                --zone-name "jablab.com" \
                --name "$service" \
                --ttl 300 \
                --output none

            az network dns record-set a add-record \
                --resource-group "$RESOURCE_GROUP" \
                --zone-name "jablab.com" \
                --record-set-name "$service" \
                --ipv4-address "$container_app_ip" \
                --output none
        }

        log_success "DNS records updated for $service"
    done
}

# Validate deployment
validate_deployment() {
    log_info "✅ Validating certificate deployment..."

    local validation_failed=false

    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
    for service in "${SERVICE_ARRAY[@]}"; do
        service=$(echo "$service" | xargs)

        # Test DNS resolution
        if nslookup "${service}.${DOMAIN}" >/dev/null 2>&1; then
            log_success "DNS resolution working for ${service}.${DOMAIN}"
        else
            log_error "DNS resolution failed for ${service}.${DOMAIN}"
            validation_failed=true
        fi

        # Test HTTPS connectivity (basic check)
        if curl -k --connect-timeout 10 "https://${service}.${DOMAIN}/health" >/dev/null 2>&1; then
            log_success "HTTPS connectivity working for ${service}.${DOMAIN}"
        else
            log_warning "HTTPS connectivity test failed for ${service}.${DOMAIN} (may be normal if service not deployed)"
        fi
    done

    if [[ "$validation_failed" == "true" ]]; then
        log_error "Some validation checks failed"
        return 1
    else
        log_success "All validation checks passed"
        return 0
    fi
}

# Show certificate status
show_status() {
    log_info "📊 Certificate Status Report"
    echo ""

    echo "Domain: $DOMAIN"
    echo "Key Vault: $KEY_VAULT_NAME"
    echo "Resource Group: $RESOURCE_GROUP"
    echo "Services: $SERVICES"
    echo ""

    IFS=',' read -ra SERVICE_ARRAY <<< "$SERVICES"
    for service in "${SERVICE_ARRAY[@]}"; do
        service=$(echo "$service" | xargs)
        echo "=== $service ==="
        check_certificate_status "$service" || true
        echo ""
    done
}

# Main command handling
main() {
    local command="${1:-help}"

    case "$command" in
        "deploy")
            check_prerequisites
            deploy_pki_infrastructure
            update_dns_records
            deploy_certificates_to_containers
            validate_deployment
            ;;
        "renew")
            check_prerequisites
            renew_certificates
            deploy_certificates_to_containers
            ;;
        "status")
            check_prerequisites
            show_status
            ;;
        "validate")
            check_prerequisites
            validate_deployment
            ;;
        "dns")
            check_prerequisites
            update_dns_records
            ;;
        "help"|*)
            echo "Azure PKI Certificate Management"
            echo ""
            echo "Usage: $0 <command>"
            echo ""
            echo "Commands:"
            echo "  deploy    - Deploy complete PKI infrastructure and certificates"
            echo "  renew     - Renew expiring certificates"
            echo "  status    - Show certificate status"
            echo "  validate  - Validate certificate deployment"
            echo "  dns       - Update DNS records"
            echo "  help      - Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  MTLS_DOMAIN           - Primary domain (default: jablab.dev)"
            echo "  AZURE_KEY_VAULT_NAME  - Key Vault name (required)"
            echo "  AZURE_RESOURCE_GROUP  - Resource group name (required)"
            echo "  CERTIFICATE_SERVICES  - Comma-separated list of services"
            echo "  CERTIFICATE_EMAIL     - Email for Let's Encrypt registration"
            echo ""
            exit 0
            ;;
    esac
}

# Run main function
main "$@"

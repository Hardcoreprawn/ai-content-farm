#!/bin/bash
"""
Let's Encrypt Certificate Management with DNS-01 Challenge
Automates certificate issuance, renewal, and storage in Azure Key Vault

Features:
- Let's Encrypt certificate issuance with DNS-01 challenge
- Azure DNS zone management for domain validation
- Certificate storage in Azure Key Vault
- Automated renewal with expiration monitoring
- mTLS certificate deployment to Container Apps
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
DOMAIN_NAME="${DOMAIN_NAME:-ai-content-farm.local}"
RESOURCE_GROUP="${RESOURCE_GROUP:-}"
KEY_VAULT_NAME="${KEY_VAULT_NAME:-}"
DNS_ZONE_NAME="${DNS_ZONE_NAME:-$DOMAIN_NAME}"

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

# Utility functions
check_dependencies() {
    log_info "Checking dependencies..."

    local deps=("az" "certbot" "jq")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "Required dependency '$dep' not found"
            if [[ "$dep" == "certbot" ]]; then
                log_info "Installing certbot..."
                sudo apt-get update && sudo apt-get install -y certbot python3-certbot-dns-azure
            else
                exit 1
            fi
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

    if [[ -z "$RESOURCE_GROUP" ]]; then
        RESOURCE_GROUP=$(az group list --query "[?contains(name, 'ai-content-farm')].name | [0]" -o tsv)
        if [[ -z "$RESOURCE_GROUP" ]]; then
            log_error "Could not find ai-content-farm resource group"
            exit 1
        fi
    fi

    if [[ -z "$KEY_VAULT_NAME" ]]; then
        KEY_VAULT_NAME=$(az keyvault list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)
        if [[ -z "$KEY_VAULT_NAME" ]]; then
            log_error "Could not find Key Vault in resource group $RESOURCE_GROUP"
            exit 1
        fi
    fi

    log_success "Found resources: RG=$RESOURCE_GROUP, KV=$KEY_VAULT_NAME"
}

# Certificate management functions
issue_certificate() {
    local domain="$1"
    log_info "Issuing Let's Encrypt certificate for $domain..."

    # Create temporary directory for certificate files
    local cert_dir="/tmp/letsencrypt-$domain"
    mkdir -p "$cert_dir"

    # Use Azure DNS plugin for DNS-01 challenge
    certbot certonly \
        --dns-azure \
        --dns-azure-config /tmp/azure-dns-config.ini \
        --email "admin@$domain" \
        --agree-tos \
        --non-interactive \
        --domains "$domain,*.$domain" \
        --cert-path "$cert_dir/cert.pem" \
        --key-path "$cert_dir/privkey.pem" \
        --fullchain-path "$cert_dir/fullchain.pem"

    if [[ -f "$cert_dir/fullchain.pem" && -f "$cert_dir/privkey.pem" ]]; then
        log_success "Certificate issued successfully for $domain"
        echo "$cert_dir"
    else
        log_error "Failed to issue certificate for $domain"
        exit 1
    fi
}

create_azure_dns_config() {
    log_info "Creating Azure DNS configuration for certbot..."

    # Get current subscription and tenant
    local subscription_id=$(az account show --query "id" -o tsv)
    local tenant_id=$(az account show --query "tenantId" -o tsv)

    # Create temporary config file for Azure DNS
    cat > /tmp/azure-dns-config.ini << EOF
[default]
dns_azure_subscription_id = $subscription_id
dns_azure_resource_group = $RESOURCE_GROUP
dns_azure_zone = $DNS_ZONE_NAME
dns_azure_tenant_id = $tenant_id
dns_azure_use_msi = true
EOF

    log_success "Azure DNS configuration created"
}

store_certificate_in_keyvault() {
    local cert_dir="$1"
    local cert_name="$2"
    
    log_info "Storing certificate in Azure Key Vault..."

    # Create PKCS12 certificate bundle
    local p12_file="/tmp/${cert_name}.p12"
    openssl pkcs12 -export \
        -out "$p12_file" \
        -inkey "$cert_dir/privkey.pem" \
        -in "$cert_dir/fullchain.pem" \
        -passout pass:

    # Store in Key Vault
    az keyvault certificate import \
        --vault-name "$KEY_VAULT_NAME" \
        --name "$cert_name" \
        --file "$p12_file"

    # Store individual components as secrets
    az keyvault secret set \
        --vault-name "$KEY_VAULT_NAME" \
        --name "${cert_name}-private-key" \
        --file "$cert_dir/privkey.pem"

    az keyvault secret set \
        --vault-name "$KEY_VAULT_NAME" \
        --name "${cert_name}-certificate" \
        --file "$cert_dir/fullchain.pem"

    # Clean up temporary files
    rm -f "$p12_file"
    rm -rf "$cert_dir"

    log_success "Certificate stored in Key Vault: $cert_name"
}

check_certificate_expiry() {
    local cert_name="$1"
    log_info "Checking certificate expiry for $cert_name..."

    local cert_info=$(az keyvault certificate show \
        --vault-name "$KEY_VAULT_NAME" \
        --name "$cert_name" \
        --query "attributes.expires" -o tsv 2>/dev/null || echo "")

    if [[ -n "$cert_info" ]]; then
        local expires_epoch=$(date -d "$cert_info" +%s)
        local current_epoch=$(date +%s)
        local days_remaining=$(( (expires_epoch - current_epoch) / 86400 ))

        if [[ $days_remaining -lt 30 ]]; then
            log_warning "Certificate $cert_name expires in $days_remaining days - renewal recommended"
            return 1
        else
            log_success "Certificate $cert_name valid for $days_remaining more days"
            return 0
        fi
    else
        log_warning "Certificate $cert_name not found in Key Vault"
        return 1
    fi
}

deploy_certificates_to_containers() {
    log_info "Deploying certificates to Container Apps..."

    # Update Container Apps with certificate references
    local containers=("content-collector" "content-processor" "site-generator")
    
    for container in "${containers[@]}"; do
        log_info "Updating $container with certificate configuration..."
        
        # Add certificate environment variables
        az containerapp update \
            --name "ai-content-dev-$container" \
            --resource-group "$RESOURCE_GROUP" \
            --set-env-vars \
                "CERT_SECRET_NAME=mtls-wildcard-cert" \
                "KEY_VAULT_NAME=$KEY_VAULT_NAME" \
                "MTLS_ENABLED=true"
    done

    log_success "Certificates deployed to all Container Apps"
}

# Main certificate management workflow
main() {
    log_info "Starting Let's Encrypt certificate management..."

    check_dependencies
    get_azure_resources
    create_azure_dns_config

    local cert_name="mtls-wildcard-cert"
    
    # Check if certificate exists and is valid
    if ! check_certificate_expiry "$cert_name"; then
        log_info "Certificate renewal required"
        
        # Issue new certificate
        local cert_dir=$(issue_certificate "$DOMAIN_NAME")
        
        # Store in Key Vault
        store_certificate_in_keyvault "$cert_dir" "$cert_name"
        
        # Deploy to containers
        deploy_certificates_to_containers
        
        log_success "Certificate renewal completed successfully"
    else
        log_success "Certificate is valid, no renewal needed"
    fi

    # Clean up
    rm -f /tmp/azure-dns-config.ini

    log_success "Certificate management completed"
}

# Script execution
case "${1:-main}" in
    "check")
        check_dependencies
        get_azure_resources
        check_certificate_expiry "mtls-wildcard-cert"
        ;;
    "renew")
        main
        ;;
    "deploy")
        check_dependencies
        get_azure_resources
        deploy_certificates_to_containers
        ;;
    *)
        main
        ;;
esac
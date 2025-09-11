#!/bin/bash
# Certificate Management and Renewal Script for Azure Container Apps mTLS
# Uses Certbot with DNS-01 challenges for Let's Encrypt certificates

set -euo pipefail

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-ai-content-dev-rg}"
KEY_VAULT_NAME="${KEY_VAULT_NAME:-}"
DNS_ZONE="${DNS_ZONE:-jablab.com}"
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:-}"
CERTIFICATE_EMAIL="${CERTIFICATE_EMAIL:-admin@jablab.com}"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >&2
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Check required environment variables
check_requirements() {
    local missing_vars=()
    
    [[ -z "$KEY_VAULT_NAME" ]] && missing_vars+=("KEY_VAULT_NAME")
    [[ -z "$STORAGE_ACCOUNT" ]] && missing_vars+=("STORAGE_ACCOUNT")
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        error_exit "Missing required environment variables: ${missing_vars[*]}"
    fi
    
    # Check if Azure CLI is logged in
    if ! az account show &>/dev/null; then
        error_exit "Azure CLI not logged in. Run 'az login' first."
    fi
    
    # Check if certbot is installed
    if ! command -v certbot &>/dev/null; then
        log "Installing certbot..."
        if command -v apt-get &>/dev/null; then
            sudo apt-get update && sudo apt-get install -y certbot python3-certbot-dns-azure
        elif command -v yum &>/dev/null; then
            sudo yum install -y certbot python3-certbot-dns-azure
        else
            error_exit "Please install certbot manually"
        fi
    fi
}

# Setup Azure DNS plugin for Certbot
setup_dns_plugin() {
    local config_file="/tmp/azure-credentials.ini"
    
    log "Setting up Azure DNS plugin for Certbot..."
    
    # Get Azure subscription and tenant info
    local subscription_id
    local tenant_id
    subscription_id=$(az account show --query id -o tsv)
    tenant_id=$(az account show --query tenantId -o tsv)
    
    # Create Azure credentials file for Certbot DNS plugin
    cat > "$config_file" <<EOF
# Azure credentials for Certbot DNS plugin
dns_azure_subscription_id = $subscription_id
dns_azure_resource_group = $RESOURCE_GROUP
dns_azure_tenant_id = $tenant_id

# Use managed identity for authentication (when running in Azure)
dns_azure_msi_client_id = \${AZURE_CLIENT_ID}
dns_azure_msi_resource_id = \${AZURE_CLIENT_ID}
EOF
    
    chmod 600 "$config_file"
    echo "$config_file"
}

# Request new certificate using DNS-01 challenge
request_certificate() {
    local domain="$1"
    local config_file="$2"
    
    log "Requesting certificate for domain: $domain"
    
    # Define certificate paths
    local cert_dir="/etc/letsencrypt/live/$domain"
    local cert_path="$cert_dir/fullchain.pem"
    local key_path="$cert_dir/privkey.pem"
    
    # Request certificate using DNS-01 challenge
    certbot certonly \
        --dns-azure \
        --dns-azure-credentials "$config_file" \
        --dns-azure-propagation-seconds 60 \
        --email "$CERTIFICATE_EMAIL" \
        --agree-tos \
        --non-interactive \
        --domains "$domain" \
        --cert-name "$domain" || error_exit "Failed to request certificate for $domain"
    
    log "Certificate requested successfully for $domain"
    
    # Upload certificate to Key Vault
    upload_certificate_to_keyvault "$domain" "$cert_path" "$key_path"
}

# Upload certificate and private key to Azure Key Vault
upload_certificate_to_keyvault() {
    local domain="$1"
    local cert_path="$2"
    local key_path="$3"
    
    log "Uploading certificate for $domain to Key Vault: $KEY_VAULT_NAME"
    
    # Sanitize domain name for Key Vault (replace dots with hyphens)
    local cert_name
    cert_name=$(echo "$domain" | sed 's/\./-/g')
    
    # Create PEM bundle for Key Vault
    local bundle_path="/tmp/${cert_name}-bundle.pem"
    cat "$cert_path" "$key_path" > "$bundle_path"
    
    # Import certificate to Key Vault
    az keyvault certificate import \
        --vault-name "$KEY_VAULT_NAME" \
        --name "$cert_name" \
        --file "$bundle_path" \
        --policy "$(generate_certificate_policy)" || error_exit "Failed to upload certificate to Key Vault"
    
    # Store certificate metadata
    store_certificate_metadata "$domain" "$cert_name"
    
    # Cleanup temporary files
    rm -f "$bundle_path"
    
    log "Certificate uploaded to Key Vault successfully"
}

# Generate certificate policy for Key Vault
generate_certificate_policy() {
    cat <<EOF
{
  "issuerParameters": {
    "name": "Unknown"
  },
  "keyProperties": {
    "exportable": true,
    "keySize": 2048,
    "keyType": "RSA",
    "reuseKey": false
  },
  "secretProperties": {
    "contentType": "application/x-pkcs12"
  },
  "x509CertificateProperties": {
    "keyUsage": [
      "cRLSign",
      "dataEncipherment",
      "digitalSignature",
      "keyEncipherment",
      "keyAgreement",
      "keyCertSign"
    ],
    "subject": "CN=$domain",
    "validityInMonths": 3
  }
}
EOF
}

# Store certificate metadata in Azure Storage
store_certificate_metadata() {
    local domain="$1"
    local cert_name="$2"
    
    log "Storing certificate metadata for $domain"
    
    # Get certificate expiration date
    local expiry_date
    expiry_date=$(openssl x509 -in "/etc/letsencrypt/live/$domain/cert.pem" -noout -enddate | cut -d= -f2)
    
    # Create metadata JSON
    local metadata_file="/tmp/${cert_name}-metadata.json"
    cat > "$metadata_file" <<EOF
{
  "domain": "$domain",
  "certificateName": "$cert_name",
  "issuer": "Let's Encrypt",
  "issuedDate": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "expiryDate": "$expiry_date",
  "keyVaultName": "$KEY_VAULT_NAME",
  "lastRenewal": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "renewalStatus": "success"
}
EOF
    
    # Upload metadata to storage
    az storage blob upload \
        --account-name "$STORAGE_ACCOUNT" \
        --container-name "certificate-metadata" \
        --name "${cert_name}-metadata.json" \
        --file "$metadata_file" \
        --auth-mode login \
        --overwrite || log "Warning: Failed to upload certificate metadata"
    
    rm -f "$metadata_file"
}

# Check certificate expiration and renew if needed
check_and_renew_certificates() {
    log "Checking certificates for renewal..."
    
    # List all certificates in Key Vault
    local certificates
    certificates=$(az keyvault certificate list --vault-name "$KEY_VAULT_NAME" --query "[].name" -o tsv)
    
    while IFS= read -r cert_name; do
        [[ -z "$cert_name" ]] && continue
        
        log "Checking certificate: $cert_name"
        
        # Get certificate details
        local expiry_date
        expiry_date=$(az keyvault certificate show \
            --vault-name "$KEY_VAULT_NAME" \
            --name "$cert_name" \
            --query "attributes.expires" -o tsv)
        
        # Check if renewal is needed (30 days before expiry)
        local renewal_threshold
        renewal_threshold=$(date -d "+30 days" +%s)
        local cert_expiry
        cert_expiry=$(date -d "$expiry_date" +%s)
        
        if [[ $cert_expiry -lt $renewal_threshold ]]; then
            log "Certificate $cert_name expires soon ($expiry_date), renewing..."
            
            # Extract domain from certificate name
            local domain
            domain=$(echo "$cert_name" | sed 's/-/./g')
            
            # Renew certificate
            renew_certificate "$domain"
        else
            log "Certificate $cert_name is valid until $expiry_date"
        fi
    done <<< "$certificates"
}

# Renew specific certificate
renew_certificate() {
    local domain="$1"
    local config_file
    config_file=$(setup_dns_plugin)
    
    log "Renewing certificate for domain: $domain"
    
    # Force renewal using certbot
    certbot renew \
        --dns-azure \
        --dns-azure-credentials "$config_file" \
        --cert-name "$domain" \
        --force-renewal || error_exit "Failed to renew certificate for $domain"
    
    # Re-upload to Key Vault
    local cert_path="/etc/letsencrypt/live/$domain/fullchain.pem"
    local key_path="/etc/letsencrypt/live/$domain/privkey.pem"
    
    upload_certificate_to_keyvault "$domain" "$cert_path" "$key_path"
    
    # Cleanup
    rm -f "$config_file"
    
    log "Certificate renewed successfully for $domain"
}

# Generate certificates for service domains
generate_service_certificates() {
    local config_file
    config_file=$(setup_dns_plugin)
    
    # List of service domains
    local domains=(
        "api.$DNS_ZONE"
        "collector.$DNS_ZONE"
        "processor.$DNS_ZONE"
        "generator.$DNS_ZONE"
        "admin.$DNS_ZONE"
    )
    
    for domain in "${domains[@]}"; do
        log "Generating certificate for service domain: $domain"
        request_certificate "$domain" "$config_file"
    done
    
    # Cleanup
    rm -f "$config_file"
}

# Main function
main() {
    case "${1:-help}" in
        "help"|*)
            echo "Usage: $0 {generate|renew|check}"
            echo "  generate - Generate certificates for all service domains"
            echo "  renew    - Check and renew expiring certificates"
            echo "  check    - Check certificate status (alias for renew)"
            exit 0
            ;;
    esac
    
    log "Starting certificate management for Azure Container Apps mTLS"
    
    check_requirements
    
    case "${1:-help}" in
        "generate")
            generate_service_certificates
            ;;
        "renew")
            check_and_renew_certificates
            ;;
        "check")
            check_and_renew_certificates
            ;;
    esac
    
    log "Certificate management completed successfully"
}

# Run main function
main "$@"
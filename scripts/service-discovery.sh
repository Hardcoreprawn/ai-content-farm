#!/bin/bash
"""
Service Discovery and KEDA Scaling Automation

Manages dynamic service discovery with Azure DNS updates during
Container App scaling events triggered by KEDA.

Features:
- Automatic DNS record updates when containers scale
- Service health monitoring and DNS cleanup
- Integration with Azure Container Apps and KEDA
- mTLS-aware service discovery
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

# Get Azure resources
get_azure_resources() {
    log_info "Getting Azure resource information..."

    if [[ -z "$RESOURCE_GROUP" ]]; then
        RESOURCE_GROUP=$(az group list --query "[?contains(name, 'ai-content-farm')].name | [0]" -o tsv)
        if [[ -z "$RESOURCE_GROUP" ]]; then
            log_error "Could not find ai-content-farm resource group"
            exit 1
        fi
    fi

    log_success "Found resource group: $RESOURCE_GROUP"
}

# Container discovery functions
get_container_apps() {
    log_info "Discovering Container Apps..."

    local container_apps=$(az containerapp list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[].{name:name, fqdn:properties.configuration.ingress.fqdn, replicas:properties.template.scale.maxReplicas}" \
        -o json)

    echo "$container_apps"
}

get_container_app_instances() {
    local app_name="$1"
    log_info "Getting active instances for $app_name..."

    # Get current revision and replica count
    local revision_info=$(az containerapp revision list \
        --name "$app_name" \
        --resource-group "$RESOURCE_GROUP" \
        --query "[?properties.active].{name:name, replicas:properties.replicas, trafficWeight:properties.trafficWeight}" \
        -o json)

    echo "$revision_info"
}

# DNS management functions
update_dns_records() {
    local service_name="$1"
    local target_fqdn="$2"
    local action="${3:-create}" # create, update, delete

    log_info "Updating DNS record: $service_name.$DNS_ZONE_NAME -> $target_fqdn ($action)"

    case "$action" in
        "create"|"update")
            # Create or update CNAME record
            az network dns record-set cname set-record \
                --resource-group "$RESOURCE_GROUP" \
                --zone-name "$DNS_ZONE_NAME" \
                --record-set-name "$service_name" \
                --cname "$target_fqdn" \
                --ttl 300 >/dev/null

            log_success "DNS record updated: $service_name.$DNS_ZONE_NAME"
            ;;
        "delete")
            # Delete CNAME record
            az network dns record-set cname delete \
                --resource-group "$RESOURCE_GROUP" \
                --zone-name "$DNS_ZONE_NAME" \
                --name "$service_name" \
                --yes >/dev/null 2>&1 || true

            log_success "DNS record deleted: $service_name.$DNS_ZONE_NAME"
            ;;
    esac
}

create_service_records() {
    local app_name="$1"
    local app_fqdn="$2"

    # Extract service name from app name
    local service_name=$(echo "$app_name" | sed 's/ai-content-dev-//' | sed 's/-/_/g')

    # Create main service record
    update_dns_records "$service_name" "$app_fqdn" "create"

    # Create additional mTLS-specific records
    update_dns_records "${service_name}_mtls" "$app_fqdn" "create"
    
    # Create load balancer record for multiple instances
    update_dns_records "${service_name}_lb" "$app_fqdn" "create"
}

# Health monitoring functions
check_service_health() {
    local service_fqdn="$1"
    local timeout="${2:-10}"

    log_info "Checking health of $service_fqdn..."

    # Test HTTP health endpoint
    local http_status=$(curl -s -w "%{http_code}" \
        --max-time "$timeout" \
        "https://$service_fqdn/health" \
        -o /dev/null || echo "000")

    if [[ "$http_status" == "200" ]]; then
        log_success "$service_fqdn is healthy"
        return 0
    else
        log_warning "$service_fqdn health check failed (HTTP $http_status)"
        return 1
    fi
}

check_mtls_connectivity() {
    local service_fqdn="$1"
    
    log_info "Checking mTLS connectivity to $service_fqdn..."

    # Test Dapr health endpoint
    local dapr_status=$(curl -s -w "%{http_code}" \
        --max-time 10 \
        "https://$service_fqdn/v1.0/healthz" \
        -o /dev/null || echo "000")

    if [[ "$dapr_status" == "200" ]]; then
        log_success "$service_fqdn Dapr/mTLS is healthy"
        return 0
    else
        log_warning "$service_fqdn Dapr/mTLS check failed (HTTP $dapr_status)"
        return 1
    fi
}

# KEDA scaling monitoring
monitor_scaling_events() {
    log_info "Monitoring KEDA scaling events..."

    # Get container apps
    local container_apps=$(get_container_apps)
    local app_count=$(echo "$container_apps" | jq '. | length')

    log_info "Monitoring $app_count container apps for scaling events"

    # Monitor each app
    echo "$container_apps" | jq -c '.[]' | while read -r app; do
        local app_name=$(echo "$app" | jq -r '.name')
        local app_fqdn=$(echo "$app" | jq -r '.fqdn // empty')
        local max_replicas=$(echo "$app" | jq -r '.replicas // 1')

        if [[ -n "$app_fqdn" ]]; then
            log_info "Monitoring $app_name (max replicas: $max_replicas)"
            
            # Check current health
            check_service_health "$app_fqdn" 5
            check_mtls_connectivity "$app_fqdn"
            
            # Update DNS records to ensure they're current
            create_service_records "$app_name" "$app_fqdn"
        else
            log_warning "$app_name has no external FQDN"
        fi
    done
}

# Service cleanup for unhealthy instances
cleanup_unhealthy_services() {
    log_info "Cleaning up DNS records for unhealthy services..."

    # Get all DNS CNAME records in our zone
    local dns_records=$(az network dns record-set cname list \
        --resource-group "$RESOURCE_GROUP" \
        --zone-name "$DNS_ZONE_NAME" \
        --query "[].{name:name, target:cname}" \
        -o json)

    echo "$dns_records" | jq -c '.[]' | while read -r record; do
        local record_name=$(echo "$record" | jq -r '.name')
        local record_target=$(echo "$record" | jq -r '.target')

        # Skip system records
        if [[ "$record_name" =~ ^(www|mail|mx|ns|txt)$ ]]; then
            continue
        fi

        log_info "Checking DNS record: $record_name -> $record_target"

        # Test if target is healthy
        if ! check_service_health "$record_target" 5; then
            log_warning "Service $record_target is unhealthy, considering cleanup"
            
            # Additional checks before cleanup
            local retries=3
            local healthy=false
            
            for ((i=1; i<=retries; i++)); do
                log_info "Retry $i/$retries for $record_target..."
                if check_service_health "$record_target" 10; then
                    healthy=true
                    break
                fi
                sleep 30
            done

            if [[ "$healthy" == "false" ]]; then
                log_warning "Service $record_target failed all health checks - removing DNS record"
                update_dns_records "$record_name" "$record_target" "delete"
            fi
        fi
    done
}

# Main service discovery workflow
main() {
    local action="${1:-monitor}"
    
    log_info "Starting service discovery automation (action: $action)..."

    # Check dependencies
    local deps=("az" "jq" "curl")
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

    get_azure_resources

    case "$action" in
        "monitor")
            monitor_scaling_events
            ;;
        "cleanup")
            cleanup_unhealthy_services
            ;;
        "update")
            log_info "Updating all service DNS records..."
            monitor_scaling_events
            ;;
        "health")
            log_info "Checking health of all services..."
            local container_apps=$(get_container_apps)
            echo "$container_apps" | jq -c '.[]' | while read -r app; do
                local app_fqdn=$(echo "$app" | jq -r '.fqdn // empty')
                if [[ -n "$app_fqdn" ]]; then
                    check_service_health "$app_fqdn"
                    check_mtls_connectivity "$app_fqdn"
                fi
            done
            ;;
        *)
            log_error "Unknown action: $action"
            echo "Usage: $0 [monitor|cleanup|update|health]"
            exit 1
            ;;
    esac

    log_success "Service discovery automation completed"
}

# Script execution
main "$@"
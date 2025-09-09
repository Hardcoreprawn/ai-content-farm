#!/bin/bash
# Configure initial topic configurations for the content scheduler
# This script sets up the Technology topic in Key Vault for the Logic App scheduler

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-ai-content-dev-rg}"
KEY_VAULT_NAME="${KEY_VAULT_NAME:-ai-content-dev-kv}"
STORAGE_ACCOUNT="${STORAGE_ACCOUNT:-aicontentdev}"

echo -e "${GREEN}🚀 Configuring scheduler topics...${NC}"

# Function to check if Azure CLI is logged in
check_azure_login() {
    if ! az account show >/dev/null 2>&1; then
        echo -e "${RED}❌ Not logged into Azure. Please run 'az login' first.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Azure CLI authenticated${NC}"
}

# Function to get Key Vault name dynamically
get_key_vault_name() {
    local kv_name
    kv_name=$(az keyvault list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null)
    if [[ -n "$kv_name" ]]; then
        KEY_VAULT_NAME="$kv_name"
        echo -e "${GREEN}✅ Found Key Vault: $KEY_VAULT_NAME${NC}"
    else
        echo -e "${YELLOW}⚠️  Using default Key Vault name: $KEY_VAULT_NAME${NC}"
    fi
}

# Function to get Storage Account name dynamically
get_storage_account_name() {
    local storage_name
    storage_name=$(az storage account list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null)
    if [[ -n "$storage_name" ]]; then
        STORAGE_ACCOUNT="$storage_name"
        echo -e "${GREEN}✅ Found Storage Account: $STORAGE_ACCOUNT${NC}"
    else
        echo -e "${YELLOW}⚠️  Using default Storage Account name: $STORAGE_ACCOUNT${NC}"
    fi
}

# Create initial topic configuration JSON
create_topic_config() {
    cat << 'EOF'
{
  "content_collector_url": "https://content-collector.placeholder.azurecontainerapps.io",
  "content_processor_url": "https://content-processor.placeholder.azurecontainerapps.io",
  "initial_topics": {
    "technology": {
      "display_name": "Technology",
      "schedule": {
        "frequency_hours": 6,
        "priority": "high",
        "active_hours": "0-23"
      },
      "sources": {
        "reddit": {
          "subreddits": ["technology", "programming", "MachineLearning", "artificial"],
          "limit": 20,
          "sort": "hot"
        }
      },
      "criteria": {
        "min_score": 50,
        "min_comments": 10,
        "include_keywords": ["AI", "machine learning", "automation", "tech"]
      },
      "analytics": {
        "last_run": null,
        "success_rate": 0.0,
        "avg_quality_score": 0.0,
        "content_generated": 0
      }
    },
    "programming": {
      "display_name": "Programming",
      "schedule": {
        "frequency_hours": 6,
        "priority": "medium",
        "active_hours": "0-23"
      },
      "sources": {
        "reddit": {
          "subreddits": ["programming", "webdev", "javascript", "python"],
          "limit": 15,
          "sort": "hot"
        }
      },
      "criteria": {
        "min_score": 30,
        "min_comments": 5,
        "include_keywords": ["code", "development", "framework", "library"]
      },
      "analytics": {
        "last_run": null,
        "success_rate": 0.0,
        "avg_quality_score": 0.0,
        "content_generated": 0
      }
    },
    "science": {
      "display_name": "Science",
      "schedule": {
        "frequency_hours": 8,
        "priority": "medium",
        "active_hours": "0-23"
      },
      "sources": {
        "reddit": {
          "subreddits": ["science", "Futurology", "datascience"],
          "limit": 15,
          "sort": "hot"
        }
      },
      "criteria": {
        "min_score": 40,
        "min_comments": 8,
        "include_keywords": ["research", "study", "discovery", "innovation"]
      },
      "analytics": {
        "last_run": null,
        "success_rate": 0.0,
        "avg_quality_score": 0.0,
        "content_generated": 0
      }
    }
  }
}
EOF
}

# Function to update Container App URLs in the configuration
update_container_urls() {
    local config="$1"

    # Get Container App URLs dynamically
    local collector_url processor_url
    collector_url=$(az containerapp show --name "ai-content-dev-content-collector" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
    processor_url=$(az containerapp show --name "ai-content-dev-content-processor" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")

    if [[ -n "$collector_url" ]]; then
        collector_url="https://$collector_url"
        config=$(echo "$config" | jq --arg url "$collector_url" '.content_collector_url = $url')
        echo -e "${GREEN}✅ Updated content-collector URL: $collector_url${NC}"
    else
        echo -e "${YELLOW}⚠️  Could not find content-collector URL, using placeholder${NC}"
    fi

    if [[ -n "$processor_url" ]]; then
        processor_url="https://$processor_url"
        config=$(echo "$config" | jq --arg url "$processor_url" '.content_processor_url = $url')
        echo -e "${GREEN}✅ Updated content-processor URL: $processor_url${NC}"
    else
        echo -e "${YELLOW}⚠️  Could not find content-processor URL, using placeholder${NC}"
    fi

    echo "$config"
}

# Main execution
main() {
    echo -e "${GREEN}🔧 Setting up scheduler topic configuration...${NC}"

    # Verify prerequisites
    check_azure_login
    get_key_vault_name
    get_storage_account_name

    # Create topic configuration
    echo -e "${GREEN}📝 Creating topic configuration...${NC}"
    local config
    config=$(create_topic_config)

    # Update URLs with actual Container App endpoints
    config=$(update_container_urls "$config")

    # Store configuration in Key Vault
    echo -e "${GREEN}🔐 Storing configuration in Key Vault...${NC}"
    if az keyvault secret set \
        --vault-name "$KEY_VAULT_NAME" \
        --name "scheduler-config" \
        --value "$config" \
        --description "Scheduler topic configuration for Logic App" >/dev/null; then
        echo -e "${GREEN}✅ Successfully stored scheduler-config in Key Vault${NC}"
    else
        echo -e "${RED}❌ Failed to store configuration in Key Vault${NC}"
        exit 1
    fi

    # Initialize Azure Table Storage tables (if they don't exist)
    echo -e "${GREEN}📊 Initializing storage tables...${NC}"

    # Get storage account key
    local storage_key
    storage_key=$(az storage account keys list --account-name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" --query "[0].value" -o tsv)

    # Create tables if they don't exist
    for table in "topicconfigurations" "executionhistory" "sourceanalytics"; do
        if az storage table create \
            --name "$table" \
            --account-name "$STORAGE_ACCOUNT" \
            --account-key "$storage_key" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Created/verified table: $table${NC}"
        else
            echo -e "${YELLOW}⚠️  Table $table already exists or creation failed${NC}"
        fi
    done

    # Display summary
    echo -e "${GREEN}"
    echo "🎉 Topic configuration setup complete!"
    echo "   ├── Key Vault: $KEY_VAULT_NAME"
    echo "   ├── Secret: scheduler-config"
    echo "   ├── Storage Account: $STORAGE_ACCOUNT"
    echo "   └── Tables: topicconfigurations, executionhistory, sourceanalytics"
    echo -e "${NC}"

    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Deploy the Logic App with Terraform"
    echo "2. Test the scheduler workflow"
    echo "3. Monitor execution in Azure Portal"
}

# Run main function
main "$@"

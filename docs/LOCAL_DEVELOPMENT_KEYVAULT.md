# Local Development with Azure Key Vault Integration

This guide explains how to set up local development that uses **Azurite for storage** and **Azure Key Vault for secrets**, providing a hybrid approach that mirrors production security practices.

## 🏗️ Architecture Overview

### Local Development Stack
```
┌─────────────────────────────────────────────────────────────┐
│                    Local Development                        │
├─────────────────────────────────────────────────────────────┤
│  🐳 Docker Containers (Local)                              │
│  ├── Content Collector ──┐                                 │
│  ├── Content Processor   │                                 │
│  ├── Content Enricher    │                                 │
│  ├── Content Ranker      │                                 │
│  └── Azurite (Storage)   │                                 │
│                           │                                 │
│  🔗 Connects to Cloud     │                                 │
│  └─────────────────────────┘                               │
├─────────────────────────────────────────────────────────────┤
│                    Azure Cloud                             │
│  ☁️  Azure Key Vault (Production/Staging)                  │
│  ├── reddit-client-id                                      │
│  ├── reddit-client-secret                                  │
│  └── reddit-user-agent                                     │
└─────────────────────────────────────────────────────────────┘
```

### Benefits of This Approach
- **🔒 Production-like Security**: Use real Azure Key Vault for secrets
- **⚡ Fast Local Storage**: Azurite provides immediate storage emulation
- **🔄 Credential Sync**: Same secrets as production/staging environments
- **📋 Fallback Options**: Environment variables as backup
- **✅ Easy Testing**: Test Key Vault integration locally

## 🚀 Quick Setup

### Option 1: Interactive Setup (Recommended)
```bash
# Run the interactive setup script
./setup-local-dev.sh
```

### Option 2: Manual Configuration
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your values
vim .env
```

## 🔑 Azure Key Vault Configuration

### 1. Create Key Vault (if needed)
```bash
# Create resource group
az group create --name ai-content-farm-dev --location eastus

# Create Key Vault
az keyvault create \
  --name your-keyvault-name \
  --resource-group ai-content-farm-dev \
  --location eastus
```

### 2. Add Reddit Secrets to Key Vault
```bash
# Set Reddit API credentials
az keyvault secret set --vault-name your-keyvault-name \
  --name reddit-client-id --value "your-reddit-client-id"

az keyvault secret set --vault-name your-keyvault-name \
  --name reddit-client-secret --value "your-reddit-client-secret"

az keyvault secret set --vault-name your-keyvault-name \
  --name reddit-user-agent --value "ai-content-farm:v1.0"
```

### 3. Setup Authentication

#### Option A: Azure CLI (Easiest for Development)
```bash
# Login to Azure
az login

# Set your subscription
az account set --subscription "your-subscription-id"
```

#### Option B: Service Principal (More Production-like)
```bash
# Create service principal
az ad sp create-for-rbac --name ai-content-farm-local \
  --role "Key Vault Secrets User" \
  --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.KeyVault/vaults/{vault-name}

# Use the output to set these in .env:
# AZURE_CLIENT_ID=<appId>
# AZURE_CLIENT_SECRET=<password>
# AZURE_TENANT_ID=<tenant>
```

## 📝 Environment Configuration

### Required Variables (.env file)
```bash
# Azure Key Vault
AZURE_KEY_VAULT_URL=https://your-keyvault.vault.azure.net/

# Authentication (choose one method)
# Method 1: Service Principal
AZURE_CLIENT_ID=your-service-principal-id
AZURE_CLIENT_SECRET=your-service-principal-secret
AZURE_TENANT_ID=your-tenant-id

# Method 2: Use Azure CLI (no additional vars needed after 'az login')

# Fallback Reddit Credentials (optional)
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-client-secret
REDDIT_USER_AGENT=ai-content-farm-local/1.0
```

## 🐳 Docker Compose Integration

The `docker-compose.yml` automatically:
- Loads variables from `.env` file
- Connects to Azurite for storage emulation
- Connects to Azure Key Vault for secrets
- Provides fallback to environment variables

### Start Services
```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs content-collector
```

## 🔍 Testing the Integration

### 1. Health Check
```bash
# Check overall health
curl -s http://localhost:8001/health | jq .

# Check Key Vault status specifically
curl -s http://localhost:8001/health | jq '.environment_info.key_vault'

# Check credential validation
curl -s http://localhost:8001/health | jq '.environment_info.config_validation'
```

### 2. Test Content Collection
```bash
# Test Reddit collection (requires credentials)
curl -X POST http://localhost:8001/collect \
  -H "Content-Type: application/json" \
  -d '{
    "sources": [
      {
        "type": "reddit",
        "subreddits": ["technology"],
        "limit": 5
      }
    ]
  }' | jq .
```

## 🔧 Troubleshooting

### Key Vault Issues

#### "Key Vault URL not configured"
```bash
# Check .env file
grep AZURE_KEY_VAULT_URL .env

# Should output: AZURE_KEY_VAULT_URL=https://your-keyvault.vault.azure.net/
```

#### "Authentication failed"
```bash
# Test Azure CLI login
az account show

# Test Key Vault access
az keyvault secret show --vault-name your-keyvault-name --name reddit-client-id
```

#### "Secret not found"
```bash
# List all secrets
az keyvault secret list --vault-name your-keyvault-name

# Check specific secret
az keyvault secret show --vault-name your-keyvault-name --name reddit-client-id
```

### Container Issues

#### Check container logs
```bash
# Content collector logs
docker logs ai-content-farm-collector

# All services logs
docker-compose logs
```

#### Restart services
```bash
# Restart content collector
docker-compose restart content-collector

# Rebuild and restart
docker-compose build content-collector
docker-compose up -d content-collector
```

## 🔄 Credential Fallback Strategy

The system uses a hierarchical approach:

1. **Primary**: Azure Key Vault secrets
   - `reddit-client-id`
   - `reddit-client-secret`
   - `reddit-user-agent`

2. **Fallback**: Environment variables
   - `REDDIT_CLIENT_ID`
   - `REDDIT_CLIENT_SECRET`
   - `REDDIT_USER_AGENT`

3. **Default**: Public APIs with rate limits

### Example Health Response
```json
{
  "status": "healthy",
  "environment_info": {
    "key_vault": {
      "status": "healthy",
      "key_vault_url": "https://your-keyvault.vault.azure.net/",
      "client_available": true
    },
    "config_validation": {
      "valid": true,
      "issues": []
    },
    "source_statuses": {
      "reddit": {
        "authentication": true,
        "authentication_message": "Reddit API credentials valid (retrieved from Key Vault or environment)"
      }
    }
  }
}
```

## 🎯 Production Readiness

This local setup prepares you for production by:

- **✅ Same Secret Store**: Using Azure Key Vault like production
- **✅ Authentication Patterns**: Testing Azure identity integration
- **✅ Error Handling**: Validating fallback mechanisms
- **✅ Monitoring**: Health checks include Key Vault status
- **✅ Security**: No secrets in code or containers

## 📚 Next Steps

1. **Test the Pipeline**: Run `python test_mock_pipeline.py`
2. **Add More Secrets**: Store OpenAI API key in Key Vault
3. **Deploy to Azure**: Use same Key Vault for staging/production
4. **Monitor Usage**: Check Key Vault access logs in Azure portal

---

**🔗 Related Files:**
- `.env.example` - Environment template
- `setup-local-dev.sh` - Interactive setup script
- `docker-compose.yml` - Container orchestration
- `containers/content-collector/keyvault_client.py` - Key Vault integration

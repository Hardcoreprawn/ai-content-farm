# Womble Function Testing Guide

**Created:** August 5, 2025  
**Last Updated:** August 5, 2025

This guide covers testing the HTTP-triggered Womble functions for Reddit hot topic collection, including Key Vault integration and various configuration options.

## 🧪 Test Overview

The Summary Womble function provides an HTTP API for on-demand topic collection, making it easier to test and validate the system without waiting for timer-based triggers.

### Function Endpoints
- **Staging**: `https://ai-content-staging-func.azurewebsites.net/api/SummaryWomble`
- **Production**: `https://ai-content-prod-func.azurewebsites.net/api/SummaryWomble`
- **Local**: `http://localhost:7071/api/SummaryWomble`

## 🔧 Test Configurations

### Basic Test (Technology Topics)
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "source": "reddit",
    "topics": ["technology"],
    "limit": 5,
    "credentials": {
      "source": "keyvault"
    }
  }' \
  "https://ai-content-staging-func.azurewebsites.net/api/SummaryWomble"
```

### Multi-Topic Test
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "source": "reddit", 
    "topics": ["technology", "programming", "MachineLearning"],
    "limit": 3,
    "credentials": {
      "source": "keyvault"
    }
  }' \
  "https://ai-content-staging-func.azurewebsites.net/api/SummaryWomble"
```

### Custom Storage Test
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "source": "reddit",
    "topics": ["gadgets"],
    "limit": 5,
    "credentials": {
      "source": "keyvault"
    },
    "storage": {
      "account_name": "your-storage-account",
      "container_name": "hot-topics"
    }
  }' \
  "https://ai-content-staging-func.azurewebsites.net/api/SummaryWomble"
```

### Local Development Test
```bash
# Start Azure Functions locally
cd functions
func start

# Test local endpoint
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "source": "reddit",
    "topics": ["technology"],
    "limit": 2,
    "credentials": {
      "source": "environment"
    }
  }' \
  "http://localhost:7071/api/SummaryWomble"
```

## 📋 Request Parameters

### Required Parameters
- **source**: Data source (`"reddit"` currently supported)
- **topics**: Array of subreddit names to collect from
- **credentials**: Authentication configuration

### Optional Parameters
- **limit**: Number of posts per topic (default: 10)
- **storage**: Custom storage configuration
- **timeframe**: Time period for hot topics (`"day"`, `"week"`, `"month"`)

### Credentials Configuration

#### Key Vault (Recommended)
```json
{
  "credentials": {
    "source": "keyvault"
  }
}
```

#### Environment Variables (Local Development)
```json
{
  "credentials": {
    "source": "environment"
  }
}
```

#### Direct Credentials (Testing Only)
```json
{
  "credentials": {
    "source": "direct",
    "client_id": "your-reddit-client-id",
    "client_secret": "your-reddit-client-secret",
    "user_agent": "your-user-agent"
  }
}
```

## 📊 Response Format

### Successful Response
```json
{
  "status": "success",
  "timestamp": "2025-08-05T10:30:00Z",
  "source": "reddit",
  "topics_collected": 3,
  "total_posts": 15,
  "storage_location": "hot-topics/2025/08/05/hot-topics-10-30-00.json",
  "execution_time_ms": 2450,
  "topics": {
    "technology": {
      "posts_collected": 5,
      "top_score": 3250,
      "subreddit": "technology"
    },
    "programming": {
      "posts_collected": 5,
      "top_score": 1890,
      "subreddit": "programming"
    },
    "MachineLearning": {
      "posts_collected": 5,
      "top_score": 1456,
      "subreddit": "MachineLearning"
    }
  }
}
```

### Error Response
```json
{
  "status": "error",
  "error_type": "authentication_failed",
  "message": "Failed to retrieve Reddit credentials from Key Vault",
  "timestamp": "2025-08-05T10:30:00Z",
  "request_id": "abc123-def456-ghi789"
}
```

## 🔍 Testing Scenarios

### 1. Authentication Testing

#### Key Vault Integration Test
```bash
# Test Key Vault credential retrieval
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "source": "reddit",
    "topics": ["test"],
    "limit": 1,
    "credentials": {"source": "keyvault"}
  }' \
  "https://ai-content-staging-func.azurewebsites.net/api/SummaryWomble"
```

Expected: Successful authentication and data collection

#### Authentication Failure Test
```bash
# Test with invalid credentials source
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "source": "reddit",
    "topics": ["test"],
    "credentials": {"source": "invalid"}
  }' \
  "https://ai-content-staging-func.azurewebsites.net/api/SummaryWomble"
```

Expected: Authentication error response

### 2. Data Collection Testing

#### Popular Subreddits Test
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "source": "reddit",
    "topics": ["news", "worldnews", "science"],
    "limit": 3,
    "credentials": {"source": "keyvault"}
  }' \
  "https://ai-content-staging-func.azurewebsites.net/api/SummaryWomble"
```

#### Niche Subreddits Test
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "source": "reddit",
    "topics": ["DevOps", "kubernetes", "Terraform"],
    "limit": 2,
    "credentials": {"source": "keyvault"}
  }' \
  "https://ai-content-staging-func.azurewebsites.net/api/SummaryWomble"
```

### 3. Performance Testing

#### Large Request Test
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "source": "reddit",
    "topics": ["technology", "programming", "MachineLearning", "DevOps", "cloud", "Azure", "aws", "docker"],
    "limit": 10,
    "credentials": {"source": "keyvault"}
  }' \
  "https://ai-content-staging-func.azurewebsites.net/api/SummaryWomble"
```

#### Rate Limiting Test
```bash
# Sequential requests to test rate limiting
for i in {1..5}; do
  echo "Request $i:"
  curl -X POST \
    -H "Content-Type: application/json" \
    -d '{
      "source": "reddit",
      "topics": ["technology"],
      "limit": 1,
      "credentials": {"source": "keyvault"}
    }' \
    "https://ai-content-staging-func.azurewebsites.net/api/SummaryWomble"
  echo -e "\n---\n"
  sleep 2
done
```

### 4. Error Handling Testing

#### Invalid Subreddit Test
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "source": "reddit",
    "topics": ["nonexistentsubreddit123456"],
    "limit": 5,
    "credentials": {"source": "keyvault"}
  }' \
  "https://ai-content-staging-func.azurewebsites.net/api/SummaryWomble"
```

#### Malformed Request Test
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "invalid": "request"
  }' \
  "https://ai-content-staging-func.azurewebsites.net/api/SummaryWomble"
```

## 🛠️ Local Testing Setup

### Prerequisites
```bash
# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4

# Install Python dependencies
cd functions
pip install -r requirements.txt

# Set local environment variables
export REDDIT_CLIENT_ID="your-client-id"
export REDDIT_CLIENT_SECRET="your-client-secret"
export REDDIT_USER_AGENT="your-user-agent"
```

### Local Function Execution
```bash
# Start local function host
cd functions
func start --verbose

# Test in another terminal
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "source": "reddit",
    "topics": ["technology"],
    "limit": 2,
    "credentials": {"source": "environment"}
  }' \
  "http://localhost:7071/api/SummaryWomble"
```

## 📈 Monitoring & Debugging

### Function Logs (Azure)
```bash
# Stream live logs
az functionapp log tail \
  --name "ai-content-staging-func" \
  --resource-group "ai-content-staging"

# Get recent logs
az functionapp log download \
  --name "ai-content-staging-func" \
  --resource-group "ai-content-staging"
```

### Application Insights Queries
```kusto
// Function execution traces
traces
| where cloud_RoleName == "ai-content-staging-func"
| where operation_Name == "SummaryWomble"
| order by timestamp desc
| take 100

// Error analysis
exceptions
| where cloud_RoleName == "ai-content-staging-func"
| where operation_Name == "SummaryWomble"
| summarize count() by problemId, outerMessage
```

### Key Vault Access Monitoring
```kusto
// Key Vault access logs
KeyVaultData
| where ResourceProvider == "MICROSOFT.KEYVAULT"
| where OperationName == "SecretGet"
| where ResultSignature == "OK"
| project TimeGenerated, CallerIpAddress, ResourceId, OperationName
| order by TimeGenerated desc
```

## 🔄 Automated Testing

### GitHub Actions Test
Create a workflow to test function endpoints:

```yaml
name: Function Integration Test
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  test-functions:
    runs-on: ubuntu-latest
    steps:
      - name: Test Staging Function
        run: |
          response=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -d '{
              "source": "reddit",
              "topics": ["technology"],
              "limit": 1,
              "credentials": {"source": "keyvault"}
            }' \
            "https://ai-content-staging-func.azurewebsites.net/api/SummaryWomble")
          
          echo "$response" | jq '.status' | grep -q "success" || exit 1
```

### Test Results Analysis
- **Success Rate**: Monitor successful vs failed requests
- **Response Time**: Track function execution performance
- **Data Quality**: Validate collected data structure and content
- **Error Patterns**: Identify common failure modes

This comprehensive testing guide ensures reliable function operation and helps identify issues before they impact production.

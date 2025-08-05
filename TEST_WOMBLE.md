# Summary Womble HTTP API Testing

## Test Configurations

### Basic Test (Technology only)
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
  "https://hot-topics-func.azurewebsites.net/api/SummaryWomble"
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
  "https://hot-topics-func.azurewebsites.net/api/SummaryWomble"
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
      "account_name": "hottopicsstorageib91ea",
      "container_name": "hot-topics"
    }
  }' \
  "https://hot-topics-func.azurewebsites.net/api/SummaryWomble"
```

### Direct Credentials Test (for development)
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "source": "reddit",
    "topics": ["technology"],
    "limit": 2,
    "credentials": {
      "source": "direct",
      "client_id": "your-client-id",
      "client_secret": "your-client-secret"
    }
  }' \
  "https://hot-topics-func.azurewebsites.net/api/SummaryWomble"
```

## Expected Response Format

```json
{
  "status": "completed",
  "timestamp": "20250805_105000",
  "source": "reddit",
  "total_topics": 15,
  "total_subreddits": 3,
  "results": [
    {
      "subreddit": "technology",
      "topics_count": 5,
      "blob_name": "20250805_105000_reddit_technology.json",
      "status": "success"
    },
    {
      "subreddit": "programming", 
      "topics_count": 5,
      "blob_name": "20250805_105000_reddit_programming.json",
      "status": "success"
    },
    {
      "subreddit": "MachineLearning",
      "topics_count": 5,
      "blob_name": "20250805_105000_reddit_MachineLearning.json", 
      "status": "success"
    }
  ]
}
```

## Quick Makefile Commands

```bash
# Test with a single subreddit
make test-womble

# Test with verbose output
make test-womble-verbose
```

## Parameter Reference

### Required Parameters
- `source`: Currently only "reddit" is supported

### Optional Parameters
- `topics`: Array of subreddit names (default: technology, programming, etc.)
- `limit`: Number of posts per subreddit (default: 10)
- `credentials`: Credential configuration object
- `storage`: Storage configuration object

### Credentials Object
- `source`: "keyvault" (default) or "direct"
- For keyvault source:
  - `vault_url`: Key Vault URL (optional, defaults to project vault)
  - `client_id_secret`: Secret name for client ID (default: "reddit-client-id")
  - `client_secret_secret`: Secret name for client secret (default: "reddit-client-secret")
- For direct source:
  - `client_id`: Reddit client ID
  - `client_secret`: Reddit client secret

### Storage Object
- `account_name`: Storage account name (optional, uses environment default)
- `container_name`: Container name (optional, defaults to "hot-topics")

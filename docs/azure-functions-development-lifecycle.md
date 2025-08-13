# Azure Functions Development Lifecycle

## Overview

This document outlines the development lifecycle for Azure Functions in the AI Content Farm project, including local development, testing, and deployment processes.

## Architecture

- **Programming Model**: Azure Functions v4 with Python 3.11
- **Function App Structure**: Single `function_app.py` file with `@app.route` decorators
- **Business Logic**: Extracted into separate modules (e.g., `ranker_core.py`)
- **Deployment**: Terraform-managed infrastructure with zip deployment

## Development Environment

### Prerequisites

The following tools should be available in the development environment:

1. **Python 3.11** - Runtime environment
2. **Azure Functions Core Tools** - For local development and testing
3. **Azure CLI** - For authentication and resource management
4. **Terraform** - For infrastructure deployment

### DevContainer Requirements

The devcontainer should include:
```dockerfile
# Add Azure Functions Core Tools
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg && \
    sudo mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg && \
    sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/microsoft-ubuntu-$(lsb_release -cs)-prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/dotnetdev.list' && \
    sudo apt-get update && \
    sudo apt-get install -y azure-functions-core-tools-4
```

## Local Development Workflow

### 1. Function Structure

All functions are defined in `/functions/function_app.py` using the v4 programming model:

```python
import azure.functions as func

app = func.FunctionApp()

@app.route(route="function_name", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def function_name(req: func.HttpRequest) -> func.HttpResponse:
    # Function implementation
    return func.HttpResponse("Response", status_code=200)
```

### 2. Business Logic Separation

Complex business logic should be extracted into separate modules:

- Keep HTTP handling in `function_app.py`
- Extract core logic into dedicated modules (e.g., `ranker_core.py`)
- Use functional programming patterns for testability

### 3. Local Testing

```bash
# Start local development server
cd functions
func start

# Test functions locally
curl -X POST http://localhost:7071/api/function_name \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### 4. Unit Testing

```bash
# Run unit tests
make test-unit

# Run with coverage
make test-coverage

# Watch mode for development
make test-watch
```

## Deployment Process

### Method 1: CI/CD Pipeline (Preferred)

1. **Commit Changes**: Push to develop branch
2. **Automatic Deployment**: GitHub Actions handles deployment to staging
3. **Manual Promotion**: Deploy to production when ready

### Method 2: Manual Terraform Deployment

For immediate deployment or when CI/CD is unavailable:

```bash
# Deploy application infrastructure (includes functions)
make deploy ENVIRONMENT=staging

# For new environments, use full setup
make staging  # Creates entire staging environment
```

### Method 3: Direct Function Deployment (Not Recommended)

Only use in emergency situations due to permissions complexity:

```bash
# Deploy functions directly (may have permission issues)
make deploy-functions ENVIRONMENT=staging
```

## Key Points

### ✅ Correct Deployment Approach

- **Use Terraform**: The `make deploy` command handles function packaging and deployment
- **Infrastructure as Code**: All resources managed through Terraform
- **Zip Deployment**: Functions are packaged and deployed via `zip_deploy_file`

### ❌ Common Pitfalls

- **Don't use Azure Functions CLI directly** for production deployments
- **Don't mix programming models** - stick to v4 model exclusively
- **Don't deploy without testing locally** first

### 🔧 Troubleshooting

#### 503 Site Unavailable Errors
- Usually caused by programming model conflicts
- Ensure all functions use v4 model (`@app.route` decorators)
- Check `host.json` configuration

#### Permission Issues with `func azure functionapp publish`
- This bypasses Terraform-managed permissions
- Use `make deploy` instead for proper infrastructure alignment

#### Local Function Not Loading
- Check `func start` output for syntax errors
- Ensure all dependencies in `requirements.txt`
- Verify function signatures match v4 model

## File Structure

```
functions/
├── function_app.py          # Main Azure Functions app (v4 model)
├── requirements.txt         # Python dependencies
├── host.json               # Function runtime configuration
├── ranker_core.py          # Business logic modules
├── .old_functions/         # Legacy functions (moved during migration)
└── __pycache__/           # Python cache (excluded from deployment)
```

## Migration Notes

When migrating from v1 to v4 programming model:

1. **Preserve Business Logic**: Extract to separate modules
2. **Update Function Signatures**: Use `@app.route` decorators
3. **Standardize Responses**: Implement consistent response format
4. **Move Legacy Code**: Keep old functions in `.old_functions/` during transition
5. **Test Thoroughly**: Verify both local and deployed behavior

## Environment Variables

Functions access configuration through app settings managed by Terraform:

- **Storage**: `AzureWebJobsStorage`, `OUTPUT_CONTAINER`
- **Authentication**: Key Vault references for secrets
- **Monitoring**: Application Insights connection strings

## Security Considerations

- **Function-level Authentication**: Use `auth_level=func.AuthLevel.FUNCTION`
- **Key Vault Integration**: Store secrets in Azure Key Vault
- **Managed Identity**: Functions use system-assigned identity for Azure resource access
- **HTTPS Only**: All function endpoints enforce HTTPS

## Future Improvements

1. **Add Azure Functions Core Tools to DevContainer**
2. **Implement automated testing in CI/CD**
3. **Create function-specific deployment targets**
4. **Add monitoring and alerting for function health**

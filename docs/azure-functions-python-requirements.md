# Azure Functions Python Requirements Research

**Date**: 2025-08-13  
**Issue**: GitHub #2 - Azure Functions 503 errors after Terraform deployment  
**Status**: Functions deploy successfully but return 503 Site Unavailable

## Azure Functions Python Runtime Architecture

### Core Requirements

Azure Functions Python runtime has very specific requirements that differ from typical Python applications:

#### 1. **Azure Functions Core Dependencies**
```txt
azure-functions>=1.0.0
```
This is the **ONLY** mandatory dependency. The Azure Functions runtime provides:
- Function triggers and bindings
- HTTP request/response handling  
- Logging integration
- Application Insights integration

#### 2. **What NOT to Include**
❌ **azure-functions-worker** - This is part of the runtime, not a dependency
❌ **grpcio/grpcio-tools** - Can cause compilation conflicts
❌ **azure-cli** packages - Heavy and unnecessary for runtime

#### 3. **Runtime Environment**
- **Python Version**: 3.11 (as configured)
- **Functions Runtime**: ~4 (extension bundle 4.x)
- **Host**: Linux consumption plan
- **Package Method**: ZIP deployment via Terraform

## Current Configuration Analysis

### ✅ Correct Configuration
```json
// host.json
{
  "version": "2.0",
  "functionTimeout": "00:05:00",
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle", 
    "version": "[4.*, 5.0.0)"
  }
}
```

### ✅ Minimal Requirements
```txt
// functions/requirements.txt
azure-functions
azure-storage-blob
azure-identity
azure-keyvault-secrets
requests
praw
```

### ❓ Potential Issues

#### 1. **Package Structure Validation**
Terraform's `data.archive_file` creates ZIP from `/functions` directory:
```hcl
data "archive_file" "function_package" {
  type        = "zip"
  source_dir  = "${path.module}/../../functions"
  output_path = "${path.module}/function-package.zip"
  excludes    = ["__pycache__", "*.pyc", "tests", ".pytest_cache"]
}
```

**Required Structure**:
```
functions/
├── host.json                    ✅
├── requirements.txt            ✅
├── ContentRanker/
│   ├── __init__.py            ✅
│   ├── function.json          ✅
│   └── ...
└── SummaryWomble/
    ├── __init__.py            ✅
    ├── function.json          ✅
    └── ...
```

#### 2. **Python Import Issues**
Each function's `__init__.py` must have:
```python
import azure.functions as func
import logging

def main(req: func.HttpRequest) -> func.HttpResponse:
    # Function logic
    pass
```

#### 3. **Function Binding Configuration**
Each `function.json` must have valid trigger configuration:
```json
{
    "bindings": [
        {
            "authLevel": "function",
            "type": "httpTrigger", 
            "direction": "in",
            "name": "req",
            "methods": ["post"]
        },
        {
            "type": "http",
            "direction": "out", 
            "name": "$return"
        }
    ]
}
```

## Diagnostic Approach

### Phase 1: Runtime Validation
1. **Check function entry points** - Verify `main()` function signature
2. **Validate imports** - Ensure no circular imports or missing modules
3. **Test minimal function** - Deploy single "hello world" function

### Phase 2: Deployment Analysis  
1. **ZIP package inspection** - Verify all files included correctly
2. **App Settings verification** - Check environment variables
3. **Connection string validation** - Verify Key Vault references

### Phase 3: Logging Investigation
1. **Application Insights query** - Check for startup errors
2. **Function invocation logs** - Verify trigger registration
3. **Host startup logs** - Check Python runtime initialization

## Recommended Fixes

### Option 1: Minimal Function Test
Create minimal test function to isolate runtime issues:
```python
# TestFunction/__init__.py
import azure.functions as func
import logging

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Test function processed a request.')
    return func.HttpResponse("Hello World", status_code=200)
```

### Option 2: Package Validation
```bash
# Manually test ZIP package creation
cd functions/
zip -r test-package.zip . -x "__pycache__/*" "*.pyc" "tests/*"
unzip -l test-package.zip  # Verify structure
```

### Option 3: Dependency Minimization
```txt
# Minimal requirements.txt for testing
azure-functions>=1.18.0
```

## References

- [Azure Functions Python Developer Guide](https://docs.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- [Azure Functions Host Runtime](https://github.com/Azure/azure-functions-host)
- [Python Function Structure](https://docs.microsoft.com/en-us/azure/azure-functions/functions-reference-python#folder-structure)

## Next Actions

1. Test with minimal function first
2. Validate ZIP package structure 
3. Check Application Insights for detailed error logs
4. Consider CLI deployment for comparison testing

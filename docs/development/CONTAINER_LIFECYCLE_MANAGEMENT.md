# Container Lifecycle Management

## Overview

This document describes the environment-based container lifecycle control system implemented across all Azure Container Apps in the AI Content Farm project. This system provides flexible control over container shutdown behavior to balance debugging needs with production cost efficiency.

## Problem Statement

**The Challenge**: Container apps in Azure need different lifecycle behaviors for different purposes:
- **Production**: Containers should shut down quickly after completing work to minimize costs
- **Development/Debugging**: Containers need to stay alive long enough for investigation and testing

**Previous Behavior**: All containers automatically shut down 2 seconds after completing their work, making debugging and investigation very difficult.

## Solution: Environment-Based Lifecycle Control

### Environment Variable: `DISABLE_AUTO_SHUTDOWN`

All containers now check the `DISABLE_AUTO_SHUTDOWN` environment variable:

- **`DISABLE_AUTO_SHUTDOWN=false`** (default): Production behavior - containers shut down after work
- **`DISABLE_AUTO_SHUTDOWN=true`**: Development behavior - containers stay alive, let KEDA handle scaling

### Container Behaviors

#### Content Collector (`content-collector`)
```python
# After scheduled collection completion
if disable_auto_shutdown:
    logger.info("Collection completed - container will remain active (DISABLE_AUTO_SHUTDOWN=true)")
else:
    logger.info("Collection completed - scheduling graceful shutdown")
    asyncio.create_task(graceful_shutdown())
```

#### Content Processor (`content-processor`)  
```python
# After startup queue processing
if processed_count > 0:
    if disable_auto_shutdown:
        logger.info("Messages processed - container will remain active (DISABLE_AUTO_SHUTDOWN=true)")
    else:
        logger.info("Messages processed - scheduling graceful shutdown")
        asyncio.create_task(graceful_shutdown())
```

#### Site Generator (`site-generator`)
```python
# After site generation processing  
if processed_count > 0:
    if disable_auto_shutdown:
        logger.info("Site generation completed - container will remain active (DISABLE_AUTO_SHUTDOWN=true)")
    else:
        logger.info("Site generation completed - scheduling graceful shutdown")
        asyncio.create_task(graceful_shutdown())
```

## Terraform Configuration

The environment variable is configured in `infra/container_apps.tf` for all three containers:

```hcl
# Content Collector
resource "azurerm_container_app" "content_collector" {
  # ... other configuration ...
  
  template {
    container {
      # ... other env vars ...
      
      # Disable auto-shutdown for debugging (set to false for production efficiency)
      env {
        name  = "DISABLE_AUTO_SHUTDOWN"
        value = "true"  # Currently set for debugging
      }
    }
  }
}

# Content Processor
resource "azurerm_container_app" "content_processor" {
  # ... same pattern ...
}

# Site Generator  
resource "azurerm_container_app" "site_generator" {
  # ... same pattern ...
}
```

## Shared Library: `libs/container_lifecycle.py`

A shared library has been created to standardize lifecycle management across containers:

```python
from libs.container_lifecycle import create_lifecycle_manager

# In container main.py
lifecycle_manager = create_lifecycle_manager("service-name")

# Handle work completion
await lifecycle_manager.handle_work_completion("Task description", success=True)

# Handle startup queue processing
await lifecycle_manager.handle_startup_queue_processing(
    process_messages_func, 
    "queue-name", 
    max_messages=32
)
```

### ContainerLifecycleManager Class

The lifecycle manager provides:
- **Environment-based shutdown control**: Automatic detection of `DISABLE_AUTO_SHUTDOWN`
- **Consistent logging**: Standardized log messages across all containers
- **Graceful shutdown**: Proper cleanup with configurable delay
- **Work completion handling**: Success/failure lifecycle decisions
- **Queue processing integration**: Standardized startup queue handling

## Operational Usage

### For Development/Debugging

**Current Setting**: `DISABLE_AUTO_SHUTDOWN=true` in Terraform

**Benefits**:
- Containers stay alive for investigation
- Can test API endpoints without premature shutdowns  
- Easier debugging of processing pipelines
- KEDA still handles scaling after 5-minute idle timeout

**Usage**:
```bash
# Test container APIs while they're alive
curl https://ai-content-prod-processor.whitecliff-6844954b.uksouth.azurecontainerapps.io/health

# Check processing status
curl https://ai-content-prod-processor.whitecliff-6844954b.uksouth.azurecontainerapps.io/status
```

### For Production Efficiency

**Production Setting**: Change to `DISABLE_AUTO_SHUTDOWN=false` in Terraform

**Benefits**:
- Containers shut down quickly after work completion
- Minimizes Azure Container Apps compute costs
- Maintains responsive scaling for incoming work
- KEDA scales up containers when needed

**Deployment**:
```bash
# Update Terraform configuration
# Set value = "false" for all containers in infra/container_apps.tf

# Deploy changes
make deploy-production
```

## Migration Status

### ✅ Completed
- Environment variable support in all three containers
- Terraform configuration with debugging enabled
- Shared library `libs/container_lifecycle.py` created
- Content processor partially migrated to shared library

### 🚧 In Progress  
- Complete migration of all containers to use shared lifecycle library
- Testing with fixed API contracts and stable containers

### 📋 Future Tasks
- Set `DISABLE_AUTO_SHUTDOWN=false` for production efficiency
- Add container lifecycle metrics and monitoring
- Document best practices for container lifecycle debugging

## Best Practices

### Development
1. **Keep debugging enabled** during active development and testing
2. **Monitor container uptime** to understand behavior patterns
3. **Test both shutdown modes** to ensure proper production behavior
4. **Use shared library** for consistent lifecycle management

### Production
1. **Enable auto-shutdown** for cost efficiency
2. **Monitor scaling patterns** to optimize KEDA configuration  
3. **Set appropriate KEDA idle timeouts** for workload patterns
4. **Track container costs** and adjust shutdown timing if needed

### Debugging Container Issues
1. **Check container logs** for shutdown/lifecycle messages
2. **Test API endpoints** while containers are alive
3. **Verify environment variable** is properly set in Azure
4. **Monitor KEDA scaling** behavior and queue processing

## Related Documentation

- [`CONTAINER_MANAGEMENT_STRATEGY.md`](CONTAINER_MANAGEMENT_STRATEGY.md) - Deployment and update strategies
- [`SYSTEM_ARCHITECTURE.md`](SYSTEM_ARCHITECTURE.md) - Overall system design
- [`content-collector-api.md`](content-collector-api.md) - Content collector API specification

## Troubleshooting

### Containers Still Shutting Down Immediately
- Verify `DISABLE_AUTO_SHUTDOWN=true` in Azure Container App environment variables
- Check container logs for lifecycle manager messages
- Ensure latest container images are deployed with environment variable support

### Containers Not Processing Work
- Check KEDA scaling configuration and queue message presence
- Verify queue names match between containers and infrastructure
- Test container API endpoints manually while containers are alive

### High Container Costs
- Switch to `DISABLE_AUTO_SHUTDOWN=false` for production
- Review KEDA idle timeout settings
- Monitor container usage patterns and optimize shutdown timing

---

*Last updated: September 26, 2025*  
*Author: AI Content Farm Development Team*
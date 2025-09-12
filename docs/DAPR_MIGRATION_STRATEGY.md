# Dapr Service Mesh Migration Strategy

## Current State: Service Bus Architecture

```
[Logic Apps] → [Service Bus Queue] → [KEDA Scaler] → [Container App]
                      ↓
              [Dead Letter Queue]
                      ↓
              [Manual Recovery]
```

**Problems:**
- High costs (~$200-600/month for Service Bus Premium)
- Complex KEDA scaling configuration
- Network restrictions and firewall rules
- Dead letter queue management complexity
- Authentication token management

## Target State: Dapr Service Mesh

```
[Container A] ←--mTLS--> [Dapr Sidecar] ←--Service Invocation--> [Dapr Sidecar] ←--mTLS--> [Container B]
      ↑                        ↑                                         ↑                        ↑
 Standard HTTP           Certificate Auth                    Certificate Auth            Standard HTTP
    Calls                 + Load Balancing                  + Circuit Breaker              Calls
```

## Migration Benefits

### 1. **Cost Reduction**
- **Service Bus Premium**: $600/month → **$0/month**
- **Service Bus Standard**: $200/month → **$0/month**
- **Certificate management**: Automated via Let's Encrypt (free)
- **Total savings**: $200-600/month

### 2. **Simplified Architecture**
- **No more queues**: Direct service-to-service calls
- **No KEDA scaling**: Native Container Apps horizontal scaling
- **No message routing**: Direct API calls with retry logic
- **No dead letter queues**: Circuit breaker patterns handle failures

### 3. **Better Performance**
- **Lower latency**: Direct calls vs queue → process → call
- **Real-time processing**: No polling delays
- **Better error handling**: Immediate failure detection

## Implementation Phases

### Phase 1: Add Dapr Service Invocation (Parallel with Service Bus)
- Enable Dapr sidecars on all Container Apps
- Add direct service-to-service endpoints
- Keep Service Bus running for safety

### Phase 2: Implement mTLS Authentication
- Deploy PKI infrastructure
- Configure certificate-based authentication
- Update health endpoints with mTLS validation

### Phase 3: Switch Traffic to Dapr
- Update Logic Apps to call services directly
- Remove KEDA scaling rules
- Keep Service Bus as backup

### Phase 4: Remove Service Bus Infrastructure
- Delete Service Bus queues and namespace
- Remove Service Bus client code
- Update monitoring and alerting

## Implementation Details

### Direct Service Communication Pattern

**Before (Service Bus):**
```python
# Content Collector → Content Processor
message = ServiceBusMessageModel(
    service_name="content-collector",
    operation="process",
    payload={"content": content_data}
)
await service_bus_client.send_message(queue="content-processing-requests", message=message)
```

**After (Dapr Service Invocation):**
```python
# Content Collector → Content Processor
async with aiohttp.ClientSession() as session:
    async with session.post(
        "http://localhost:3500/v1.0/invoke/content-processor/method/process-content",
        json={"content": content_data},
        ssl=ssl_context  # mTLS authentication
    ) as response:
        result = await response.json()
```

### Auto-scaling Pattern

**Before (KEDA + Service Bus):**
```terraform
azure_queue_scale_rule {
  name         = "servicebus-queue-scaler"
  queue_name   = azurerm_servicebus_queue.content_processing_requests.name
  queue_length = 1
}
```

**After (HTTP-based scaling):**
```terraform
http_scale_rule {
  name                = "http-requests-scaler"
  concurrent_requests = 10
}
```

## Risk Mitigation

### 1. **Gradual Migration**
- Run both systems in parallel initially
- Feature flags to switch between Service Bus and Dapr
- Rollback capability at each phase

### 2. **Circuit Breaker Pattern**
```python
from libs.resilience import CircuitBreaker

@CircuitBreaker(failure_threshold=5, recovery_timeout=60)
async def call_content_processor(data):
    # Direct Dapr service call with automatic retry/fallback
    return await dapr_client.invoke_method(
        app_id="content-processor",
        method_name="process-content",
        data=data
    )
```

### 3. **Health Monitoring**
- Enhanced health endpoints validate mTLS connectivity
- Real-time service discovery via Dapr
- Automatic certificate rotation monitoring

## Timeline

- **Week 1**: Implement Dapr service invocation endpoints
- **Week 2**: Deploy PKI infrastructure and mTLS
- **Week 3**: Parallel testing with Service Bus backup
- **Week 4**: Switch Logic Apps to direct calls
- **Week 5**: Remove Service Bus infrastructure

This migration eliminates your Service Bus costs while providing better performance and security!

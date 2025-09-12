# mTLS Health Endpoint Integration Guide

This guide shows how to integrate the enhanced mTLS health endpoints into existing containers.

## Quick Integration

### 1. Content Collector Integration

Add to your existing `main.py` or `app.py`:

```python
# Import the enhanced health endpoint
from enhanced_health import add_enhanced_health_endpoint

# After creating your FastAPI app
app = FastAPI(title="Content Collector")

# Add your existing endpoints...

# Add enhanced health endpoints
add_enhanced_health_endpoint(app)
```

### 2. Content Processor Integration

Similar integration for content processor:

```python
from enhanced_health import add_enhanced_health_endpoint

app = FastAPI(title="Content Processor")

# Add your existing endpoints...

# Add enhanced health endpoints
add_enhanced_health_endpoint(app)
```

### 3. Site Generator Integration

For site generator:

```python
from enhanced_health import add_enhanced_health_endpoint

app = FastAPI(title="Site Generator")

# Add your existing endpoints...

# Add enhanced health endpoints
add_enhanced_health_endpoint(app)
```

## New Endpoints Available

After integration, each service will have these new endpoints:

### Enhanced Health Endpoints

1. **`GET /health/detailed`** - Comprehensive health with mTLS validation
2. **`GET /health/mtls`** - mTLS-specific health information
3. **`GET /health/dependencies`** - Dependency connectivity testing

### Response Format

```json
{
  "service": "content-collector",
  "timestamp": "2025-09-12T10:30:00Z",
  "status": "healthy|warning|unhealthy",
  "checks": {
    "reddit_api": {
      "status": "healthy",
      "details": {...}
    },
    "blob_storage": {
      "status": "healthy", 
      "details": {...}
    },
    "mtls": {
      "overall_status": "healthy",
      "components": {
        "certificate": {...},
        "dapr_sidecar": {...},
        "dependencies": {...}
      }
    }
  }
}
```

## Testing the Integration

### 1. Basic Health Test
```bash
curl https://content-collector.yourdomain.com/health/detailed
```

### 2. mTLS-Specific Test
```bash
curl https://content-collector.yourdomain.com/health/mtls
```

### 3. Dependency Test
```bash
curl https://content-collector.yourdomain.com/health/dependencies
```

### 4. Automated Validation
```bash
# Quick validation
./scripts/quick-mtls-validation.sh --domain yourdomain.com --verbose

# Comprehensive validation
python scripts/validate-mtls-implementation.py --domain yourdomain.com --verbose
```

## Monitoring Integration

### Prometheus Metrics

The enhanced health endpoints can be scraped by Prometheus:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'ai-content-farm-mtls'
    static_configs:
      - targets: ['collector.yourdomain.com', 'processor.yourdomain.com', 'site-gen.yourdomain.com']
    metrics_path: '/health/mtls'
    scrape_interval: 30s
```

### Azure Application Insights

Health data is automatically logged to Application Insights when using the enhanced endpoints.

### Alerting Rules

Set up alerts based on health status:

```yaml
# Alert when mTLS health is unhealthy
- alert: MTLSHealthUnhealthy
  expr: mtls_health_status{status="unhealthy"} == 1
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "mTLS health check failing for {{ $labels.service }}"
```

## Container-Specific Customization

### Content Collector Specific Checks
- Reddit API connectivity
- Collection queue status
- Rate limiting status

### Content Processor Specific Checks  
- Azure OpenAI connectivity
- Processing queue backlog
- AI model availability

### Site Generator Specific Checks
- Static Web Apps deployment status
- Template engine health
- Content processing status

## Troubleshooting

### Common Issues

1. **Certificate Not Found**
   - Check `/etc/ssl/certs/` for service certificates
   - Verify Azure Key Vault access

2. **Dapr Sidecar Not Responding**
   - Check Dapr sidecar logs
   - Verify mTLS configuration

3. **Dependency Connectivity Issues**
   - Test DNS resolution
   - Check certificate trust chain
   - Verify firewall rules

### Debug Commands

```bash
# Check certificate expiration
openssl x509 -in /etc/ssl/certs/content-collector.crt -noout -enddate

# Test Dapr sidecar
curl http://localhost:3500/v1.0/healthz

# Check DNS resolution
nslookup content-processor.yourdomain.com

# Test mTLS connectivity
curl --cert /etc/ssl/certs/content-collector.crt --key /etc/ssl/certs/content-collector.key https://content-processor.yourdomain.com/health
```

## Performance Considerations

- Health checks run asynchronously to minimize impact
- Caching implemented for expensive checks
- Timeouts configured to prevent hanging
- Circuit breaker pattern for external dependencies

## Security Notes

- Health endpoints don't expose sensitive information
- Certificate details are sanitized in responses
- Authentication maintained for internal communication
- Audit logging enabled for all health checks

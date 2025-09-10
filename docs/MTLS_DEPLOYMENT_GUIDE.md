# mTLS Implementation Deployment Guide

This guide provides step-by-step instructions for deploying the automated mTLS setup for the AI Content Farm project.

## Prerequisites

1. **Azure CLI** - Ensure you're logged in with appropriate permissions
2. **Terraform** - Version 1.0 or later
3. **Domain ownership** - Control over the DNS zone for certificate validation
4. **Azure subscription** - With sufficient permissions to create resources

## Deployment Steps

### Phase 1: Infrastructure Setup

1. **Clone and navigate to the project**:
   ```bash
   git clone <repository-url>
   cd ai-content-farm/infra
   ```

2. **Configure Terraform variables**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your specific values
   ```

   Required variables:
   ```hcl
   certificate_email = "admin@yourdomain.com"
   enable_mtls = true
   dns_zone = "yourdomain.com"
   ```

3. **Initialize and plan Terraform**:
   ```bash
   terraform init
   terraform plan
   ```

4. **Deploy infrastructure**:
   ```bash
   terraform apply
   ```

### Phase 2: Certificate Generation

1. **Set environment variables**:
   ```bash
   export RESOURCE_GROUP="<your-resource-group>"
   export KEY_VAULT_NAME="<your-key-vault-name>"
   export DNS_ZONE="<your-domain>"
   export STORAGE_ACCOUNT="<your-storage-account>"
   ```

2. **Generate initial certificates**:
   ```bash
   cd ../scripts
   ./certificate-management.sh generate
   ```

3. **Verify certificate installation**:
   ```bash
   az keyvault certificate list --vault-name $KEY_VAULT_NAME
   ```

### Phase 3: Service Deployment

1. **Deploy mTLS-enabled Container Apps**:
   ```bash
   cd ../infra
   terraform apply -var="enable_mtls=true"
   ```

2. **Verify Dapr mTLS configuration**:
   ```bash
   az containerapp list --resource-group $RESOURCE_GROUP --query "[?properties.configuration.dapr.enabled]"
   ```

### Phase 4: Testing and Validation

1. **Run integration tests**:
   ```bash
   cd ../scripts
   ./test-mtls-integration.sh all
   ```

2. **Test individual components**:
   ```bash
   ./test-mtls-integration.sh certificates
   ./test-mtls-integration.sh dns
   ./test-mtls-integration.sh apps
   ./test-mtls-integration.sh dapr
   ```

3. **Verify service communication**:
   ```bash
   ./test-mtls-integration.sh communication
   ```

### Phase 5: Monitoring Setup

1. **Configure certificate monitoring**:
   - Alerts are automatically configured during Terraform deployment
   - Check Azure Monitor for certificate expiration alerts

2. **Set up cost monitoring**:
   - Budget alerts are configured automatically
   - Review cost estimates in Azure portal

3. **Enable Application Insights**:
   - mTLS communication logs are automatically collected
   - Access dashboard through Azure portal

## Post-Deployment Configuration

### Certificate Renewal

The system automatically checks for certificate renewal daily at 2 AM UTC. To manually trigger renewal:

```bash
./certificate-management.sh renew
```

### DNS Management

Service discovery is handled automatically. To manually update DNS records:

```bash
az network dns record-set a update \
  --resource-group $RESOURCE_GROUP \
  --zone-name $DNS_ZONE \
  --name api \
  --target-resource "<container-app-resource-id>"
```

### Monitoring and Alerts

- **Certificate Expiration**: Alerts sent 30 days before expiration
- **mTLS Handshake Failures**: Alerts when failure rate exceeds threshold
- **Container Health**: Alerts for container startup failures
- **Cost Monitoring**: Budget alerts for certificate management costs

## Troubleshooting

### Common Issues

1. **Certificate generation fails**:
   - Verify DNS zone permissions
   - Check Azure CLI authentication
   - Ensure Certbot is properly installed

2. **mTLS handshake failures**:
   - Verify certificates are uploaded to Key Vault
   - Check Dapr configuration
   - Review container logs

3. **Service discovery issues**:
   - Verify DNS records are created
   - Check Container App ingress configuration
   - Validate network connectivity

### Debug Commands

```bash
# Check certificate status
az keyvault certificate show --vault-name $KEY_VAULT_NAME --name <cert-name>

# View container logs
az containerapp logs show --name <app-name> --resource-group $RESOURCE_GROUP

# Test service endpoints
curl -k https://api.yourdomain.com/health

# Check Dapr configuration
az containerapp env dapr-component list --name <environment-name> --resource-group $RESOURCE_GROUP
```

## Cost Optimization

Expected monthly costs for small-scale deployment:

- **Azure Key Vault**: $5-10 (certificate operations)
- **Azure DNS**: $5-15 (hosted zone + queries)  
- **Azure Monitor**: $20-50 (logs and metrics)
- **Container Apps**: $10-30 (mTLS-enabled containers)
- **Total**: ~$40-105/month

### Cost Reduction Tips

1. Use shared Log Analytics workspace
2. Configure log retention policies
3. Optimize certificate renewal frequency
4. Monitor unused resources

## Security Considerations

1. **Certificate Storage**: All certificates stored encrypted in Key Vault
2. **Access Control**: Managed identities used for service authentication
3. **Network Security**: mTLS enforced for all inter-service communication
4. **Monitoring**: Comprehensive logging and alerting for security events

## Maintenance

### Regular Tasks

1. **Weekly**: Review certificate expiration alerts
2. **Monthly**: Check cost monitoring reports
3. **Quarterly**: Update container images and dependencies
4. **Annually**: Review and rotate access keys

### Automated Tasks

- Daily certificate renewal checks
- Automated DNS updates during scaling
- Continuous monitoring and alerting
- Automatic cost tracking and reporting

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review Azure Monitor logs and alerts
3. Run integration tests to identify specific issues
4. Consult Azure documentation for service-specific problems

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Let's Encrypt  │    │   Azure DNS     │    │   Azure Key     │
│   (Certificates)│◄───┤   (Discovery)   │◄───┤   Vault (Storage)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                Container Apps Environment                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Collector   │  │ Processor   │  │ Generator   │            │
│  │ + Dapr      │◄─┤ + Dapr      │◄─┤ + Dapr      │            │
│  │ (mTLS)      │  │ (mTLS)      │  │ (mTLS)      │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                Azure Monitor + Application Insights              │
│           (Certificate Lifecycle + mTLS Health)                  │
└─────────────────────────────────────────────────────────────────┘
```

This implementation provides automated, secure, and cost-effective mTLS for Azure Container Apps with comprehensive monitoring and certificate lifecycle management.
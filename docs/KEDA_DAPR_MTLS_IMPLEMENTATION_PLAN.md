# KEDA + Dapr + mTLS Architecture Implementation Plan
**Date: September 12, 2025**

## 🎯 **Project Goals**
- **Maintain scale-to-zero** capabilities (essential for cost control)
- **Replace Service Bus** with direct mTLS communication
- **Achieve 90% cost reduction** ($60/month → $5/month)
- **Implement production-grade security** with certificate-based authentication

## 🏗️ **Architecture Overview**

### Current State (Service Bus + KEDA)
```
[Logic App] → [Service Bus Queue] → [KEDA Scaler] → [Container Apps]
Cost: ~$60/month | Security: Shared keys | Latency: 2-hop routing
```

### Target State (KEDA + Dapr + mTLS)
```
[HTTP Trigger] → [Cosmos Work Queue] → [KEDA Scaler] → [Container Apps] ←--mTLS--> [Other Services]
Cost: ~$5/month | Security: Certificate-based | Latency: Direct P2P
```

## 📊 **Cost Analysis**

| Component | Current | New | Savings |
|-----------|---------|-----|---------|
| **Message Queue** | Service Bus: $50/month | Cosmos DB: $5/month | $45/month |
| **Network** | Egress: $10/month | Direct: $0/month | $10/month |
| **Management** | High overhead | Automated | Operational savings |
| **Total** | **$60/month** | **$5/month** | **$55/month (90%)** |

## 🔐 **Security Architecture**

### mTLS Implementation
- **Certificate Authority**: Let's Encrypt (free, automated)
- **Certificate Storage**: Azure Key Vault (secure, managed)
- **DNS Validation**: Azure DNS zone (jablab.dev)
- **Automatic Renewal**: ACME protocol + Logic Apps monitoring
- **Service Identity**: Each service gets unique certificate

### Certificate Lifecycle
```
1. Terraform → ACME → Let's Encrypt → Certificate issued
2. Certificate → Azure Key Vault → Secure storage
3. Container Apps → Managed Identity → Certificate access
4. Dapr Sidecar → mTLS handshake → Service communication
5. Logic Apps → Monitor expiry → Auto-renewal (30 days)
```

## 🚀 **KEDA Scaling Strategy**

### Work Queue Scaling (Replaces Service Bus)
```python
# Cosmos DB Query for KEDA scaling
SELECT VALUE COUNT(1) FROM c 
WHERE c.service_name = 'content-collector' 
AND c.status = 'pending'

# Scale trigger: targetValue = 1
# Scale from 0 → N when work items pending
```

### Service Configuration
| Service | Min Replicas | Max Replicas | Scale Trigger | Operations |
|---------|--------------|--------------|---------------|------------|
| **content-collector** | 0 | 3 | 1 pending item | collect_content, process_reddit |
| **content-processor** | 0 | 5 | 1 pending item | process_content, analyze_content |
| **site-generator** | 0 | 2 | 1 pending item | generate_site, publish_changes |

## 🛠️ **Implementation Phases**

### Phase 1: PKI Infrastructure (Day 1) ✅
- [x] Design PKI architecture
- [x] Use existing Azure DNS zone (jablab.dev)
- [x] Implement ACME/Let's Encrypt integration
- [x] Set up Azure Key Vault for certificates
- [x] Create certificate automation scripts
- [ ] **Deploy PKI infrastructure**
- [ ] **Test certificate issuance**

### Phase 2: mTLS Integration (Day 1-2)
- [x] Create mTLS validation library
- [x] Design health endpoints with certificate checking
- [x] Implement Dapr sidecar integration
- [ ] **Deploy mTLS certificates**
- [ ] **Test service-to-service authentication**
- [ ] **Validate certificate rotation**

### Phase 3: KEDA + Cosmos DB (Day 2-3)
- [x] Design Cosmos DB work queue schema
- [x] Create KEDA work queue manager
- [x] Implement Dapr service caller
- [ ] **Deploy Cosmos DB (budget optimized)**
- [ ] **Test KEDA scaling with work queue**
- [ ] **Validate scale-to-zero behavior**

### Phase 4: Service Migration (Day 3-4)
- [x] Create container migration examples
- [x] Design Service Bus compatibility layer
- [x] Plan gradual migration strategy
- [ ] **Deploy new container versions**
- [ ] **Run parallel systems**
- [ ] **Migrate traffic gradually**

### Phase 5: Decommission & Optimize (Day 4-5)
- [ ] **Monitor cost reduction**
- [ ] **Validate performance improvements**
- [ ] **Decommission Service Bus**
- [ ] **Document final architecture**

## 📁 **File Structure Created**

```
/workspaces/ai-content-farm/
├── infra/
│   ├── pki_infrastructure.tf          # Azure PKI with Let's Encrypt
│   └── keda_dapr_integration.tf       # KEDA + Cosmos DB scaling
├── libs/
│   ├── mtls_integration.py            # mTLS validation library
│   ├── keda_dapr_integration.py       # Work queue + service caller
│   └── servicebus_migration.py       # Migration helper tools
├── scripts/
│   └── pki-certificate-manager.sh    # Certificate automation
└── containers/content-collector/endpoints/
    └── keda_router.py                 # Example KEDA integration
```

## 🎯 **Key Technical Decisions**

### Cosmos DB Optimization (Budget-Friendly)
- **Throughput**: 400 RU/s (minimum for shared)
- **Consistency**: Session (cheapest, sufficient for work queue)
- **TTL**: 1 hour (automatic cleanup of completed work)
- **Partitioning**: By service_name (optimal for KEDA queries)
- **Expected Cost**: $5-10/month vs $50+ for Service Bus

### KEDA Scaling Triggers
- **Custom Scaler**: Cosmos DB document count
- **HTTP Scaler**: Direct request-based scaling
- **Scale-to-zero**: Maintained with work queue pattern
- **Batch Processing**: 5-10 items per scaling event

### Service Communication
- **Synchronous**: Direct Dapr invocation (replaces HTTP calls)
- **Asynchronous**: Work queue items (replaces Service Bus messages)
- **Security**: mTLS for all inter-service communication
- **Service Discovery**: Dapr service mesh automatic routing

## 🔧 **Environment Variables**

### PKI Configuration
```bash
AZURE_KEY_VAULT_NAME="ai-content-farm-certs-kv"
AZURE_RESOURCE_GROUP="ai-content-farm-rg"
MTLS_DOMAIN="jablab.dev"
CERTIFICATE_EMAIL="admin@jablab.dev"
CERTIFICATE_SERVICES="content-collector,content-processor,site-generator"
```

### KEDA + Dapr Configuration
```bash
DAPR_HTTP_PORT="3500"
DAPR_GRPC_PORT="50001"
DAPR_MTLS_ENABLED="true"
KEDA_STATE_STORE="keda-work-queue"
COSMOS_DB_ENDPOINT="https://ai-content-farm-keda-state.documents.azure.com:443/"
```

## 📈 **Success Metrics**

### Performance Targets
- **Scale-up time**: < 30 seconds (from 0 to 1 replica)
- **Inter-service latency**: < 100ms (direct vs 200ms+ via Service Bus)
- **Certificate validation**: < 10ms per request
- **Work queue processing**: 10+ items/second per replica

### Cost Targets
- **Monthly Azure costs**: < $10/month (from $60+/month)
- **Certificate management**: $0/month (Let's Encrypt free)
- **Network costs**: Minimal (direct communication)

### Security Targets
- **Zero shared secrets** in production
- **Certificate rotation**: Fully automated
- **mTLS coverage**: 100% inter-service communication
- **Security alerts**: < 5 minutes to notification

## 🚨 **Risk Mitigation**

### Migration Risks
- **Parallel deployment**: Run both systems during transition
- **Gradual traffic migration**: 10% → 50% → 100%
- **Rollback plan**: Keep Service Bus until proven stable
- **Monitoring**: Enhanced observability during migration

### Technical Risks
- **Certificate failures**: Automated monitoring and alerts
- **Cosmos DB limits**: RU/s monitoring and auto-scaling
- **KEDA scaling**: Detailed metrics and debugging
- **Service discovery**: Dapr health checks and fallbacks

## 📋 **Next Steps (Today)**

1. **Deploy PKI Infrastructure** (30 minutes)
   ```bash
   cd /workspaces/ai-content-farm/infra
   terraform plan -var="enable_pki=true" -var="primary_domain=jablab.dev"
   terraform apply
   ```

2. **Test Certificate Issuance** (15 minutes)
   ```bash
   ./scripts/pki-certificate-manager.sh deploy
   ./scripts/pki-certificate-manager.sh status
   ```

3. **Deploy Cosmos DB for KEDA** (20 minutes)
   ```bash
   terraform plan -var="enable_mtls=true"
   terraform apply
   ```

4. **Test KEDA Scaling** (30 minutes)
   - Deploy test container with Cosmos DB scaler
   - Add work items and verify scale-up
   - Confirm scale-to-zero behavior

## 💡 **Innovation Highlights**

This architecture combines cutting-edge cloud-native patterns:
- **GitOps**: Infrastructure as Code with Terraform
- **Zero Trust**: Certificate-based service identity
- **FinOps**: Aggressive cost optimization with scale-to-zero
- **Event-Driven**: KEDA scaling based on business logic
- **Service Mesh**: Dapr for communication and observability
- **Automation**: Full certificate lifecycle management

**Expected Outcome**: Production-grade, secure, cost-optimized microservices platform with 90% cost reduction and enterprise security posture.

---
*This document represents the complete architectural vision and implementation plan. All components have been designed and are ready for deployment.*

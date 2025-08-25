# Container Apps Architecture - Cost Optimization Analysis

**Date:** August 25, 2025  
**Context:** Migration from Azure Functions to Container Apps completed, analyzing cost optimization opportunities

## Current Architecture Overview

### Infrastructure Components
- **Container Apps Environment** with Log Analytics integration
- **Shared Container Registry** (Basic SKU) across all environments
- **Service Bus Standard** for event processing
- **Event Grid** for blob storage events
- **4 Container Apps**: Site Generator, Content Collector, Content Ranker, Content Generator
- **Scale-to-zero capability** for most workloads

### Current Resource Allocation
```
Site Generator:    min=1, max=3, 0.5 CPU, 1Gi RAM (always-on for public access)
Content Collector: min=0, max=2, 0.5 CPU, 1Gi RAM
Content Ranker:    min=0, max=2, 0.5 CPU, 1Gi RAM  
Content Generator: min=0, max=5, 0.5 CPU, 1Gi RAM
```

## Cost Optimization Opportunities

### 1. Container Resource Right-sizing (30-40% compute savings)

**Current Problem:** All containers use same resource allocation regardless of workload
**Recommended Allocation:**
- **Content Collector**: 0.25 CPU + 0.5Gi (API calls only)
- **Content Ranker**: 0.5 CPU + 1Gi (computation heavy) 
- **Content Generator**: 1.0 CPU + 2Gi (AI processing intensive)
- **Site Generator**: 0.25 CPU + 0.5Gi (static file generation)

### 2. Eliminate Service Bus Architecture (~$10-15/month savings)

**Current:** Event Grid → Service Bus → Container Apps
**Problem:** Over-engineered for batch processing pipeline

**Alternative Options:**
- **Option A - HTTP Webhooks:** Storage events → direct HTTP calls to Container Apps
- **Option B - Simple Polling:** Timer-based checks every 30 minutes  
- **Option C - Logic Apps:** Orchestrate pipeline for $2-3/month vs Service Bus costs

### 3. Environment Consolidation (50% infrastructure savings)

**Current:** Support for development, staging, production, + ephemeral PR environments
**Recommendation for Personal Project:**
- Single shared dev/staging environment
- Production-only deployment from main branch
- Skip ephemeral PR environments unless critical for testing

### 4. Alternative Architecture Patterns

#### Pattern A: Event-Driven HTTP (Recommended)
```
Timer → Content Collector (HTTP) → Blob Storage → 
Webhook → Content Ranker (HTTP) → Blob Storage → 
Webhook → Content Generator (HTTP) → Site Generator (HTTP)
```

**Benefits:**
- No Service Bus costs
- Simpler debugging
- Direct container-to-container communication
- Maintains event-driven benefits

#### Pattern B: Single Orchestrator Container
```
Single scheduled container (every 6 hours):
1. Collect content from Reddit
2. Rank and filter content
3. Generate articles via AI
4. Update static site
```

**Benefits:**
- Minimal infrastructure
- Predictable costs
- Perfect for batch processing
- Single point of monitoring

#### Pattern C: Azure Container Instances Jobs
```
Scheduled ACI Jobs for each pipeline stage:
- Pay only for execution time
- No always-on infrastructure
- Perfect for infrequent batch work
```

## Implementation Priority

### Phase 1: Quick Wins (Next Session)
1. **Right-size container resources** based on workload analysis
2. **Set all min_replicas = 0** except public-facing components
3. **Review Service Bus necessity** - can we use simpler triggers?

### Phase 2: Architecture Simplification  
1. **Eliminate Service Bus + Event Grid** if not essential
2. **Implement direct HTTP event chains** between containers
3. **Consolidate environments** to dev + production only

### Phase 3: Alternative Architecture (If Needed)
1. **Evaluate single-container orchestrator** approach
2. **Consider Azure Container Instances Jobs** for true batch processing
3. **Implement cost monitoring** and alerting

## Cost Benefits Analysis

### Current Monthly Estimate
- Container Apps Environment: ~$20-30
- Container Registry (Basic): ~$5  
- Service Bus (Standard): ~$10
- Event Grid: ~$2-5
- Always-on containers: ~$40-60
- **Total: ~$77-110/month**

### Optimized Monthly Estimate
- Container Apps Environment: ~$20-30
- Container Registry (Basic): ~$5
- Simplified events: ~$0-2  
- Scale-to-zero containers: ~$15-25
- **Total: ~$40-62/month (40-45% savings)**

## Decision Factors

### Stick with Current Architecture If:
- Need real-time event processing
- Require independent scaling of each component
- Plan to add more complex workflows
- Team development requires environment isolation

### Simplify Architecture If:
- Content processing is primarily batch-oriented (every few hours)
- Personal project with simple requirements
- Cost optimization is high priority
- Maintenance overhead should be minimal

## Next Steps

1. **Monitor current usage patterns** to validate optimization assumptions
2. **Run cost analysis** with Infracost on proposed changes
3. **Implement Phase 1 optimizations** in development environment
4. **Measure performance impact** of resource changes
5. **Document lessons learned** for future architecture decisions

## Files to Review/Modify

- `/infra/container_apps.tf` - Resource allocation and scaling configuration
- `/infra/main.tf` - Service Bus and Event Grid resources
- Container Apps deployment configurations
- Cost monitoring and alerting setup

---
**Note:** This analysis assumes content processing happens in batches (every few hours) rather than real-time streaming. Architecture choice should align with actual usage patterns and business requirements.

# AI Content Farm

**An intelligent content aggregation and curation platform** that collects trending topics from Reddit and transforms them into high-quality articles for personal reading and content marketing.

## 🎯 Current Status

**Clean Restart Approach** (August 2025):
- ✅ **Infrastructure Working**: Terraform deploying to Azure successfully
- ✅ **Authentication Ready**: OIDC and Key Vault configured
- ✅ **Python Logic Available**: Good content processing code to salvage
- 🔄 **Architecture Reset**: Building 3 simple containers instead of 8 complex ones
- 🎯 **Direct Azure Development**: Working live in non-production environment

**Previous Problem**: 8 over-engineered containers, expensive (~$77-110/month)
**New Approach**: 3 cost-effective containers with standard libraries

## 🏗️ New Simple Architecture

**Target: 3 Containers**
```
Reddit → Collector → Processor → Publisher → jablab.com
```

1. **Collector** (FastAPI)
   - Fetch Reddit trending topics every 6 hours
   - Save topics to Azure Blob Storage
   - Standard REST API with health checks

2. **Processor** (FastAPI)
   - Rank topics by engagement/relevance
   - Enrich with research and fact-checking
   - Generate article content using AI
   - Standard Python libraries (requests, openai, etc.)

3. **Publisher** (FastAPI)
   - Convert content to markdown
   - Build static site with standard generators
   - Deploy to blob storage for public access

**Key Principles**:
- Standard Python libraries wherever possible
- Simple FastAPI REST APIs
- Blob storage for all data exchange
- No complex event systems or service buses
- Cost target: ~$30-40/month (60% reduction)

## 🚀 Development Approach

**Working Directly in Azure**:
- No local development complexity
- Deploy and test in live environment
- Use standard Python libraries
- Keep infrastructure costs low
- Focus on working code over perfect architecture

### Deploy to Azure
```bash
# Deploy infrastructure and containers
make deploy-production # Deploy to Azure
```

### Access Your System
- Check Container Apps in Azure portal for URLs
- Test APIs directly with curl/Postman
- Monitor with Application Insights

## 🔧 Key Commands

```bash
# Deploy to Azure
make deploy-production

# Check infrastructure
terraform plan
terraform apply

# Monitor deployment
az containerapp list --output table
```

## � Documentation

**Three Documents Only**:
- `README.md` - This file (current state, how to use)
- `TODO.md` - What we're doing next, priorities  
- `.github/agent-instructions.md` - AI agent behavior guidelines

**Archive Location**: `docs/` folder for completed work

# AI Content Farm

**An intelligent content aggregation and curation platform** that collects trending topics from Reddit ### Immediate (Week 1):
1. **✅ Architecture Simplification** - COMPLETED
2. **🔄 End-to-End Testing** - Test full Reddit → Website pipeline
3. **🔄 Documentation Updates** - Update all references to new architecture
4. **✅ content-generator Cleanup** - COMPLETED - Removed deprecated containerransforms them into high-quality articles for personal reading and content marketing.

## 🎉 Current Status: Site Generation Verified & Operational!

**Achievement**: Phase 1-3 site generation implementations verified working in production (Oct 17, 2025)  
**Site**: https://aicontentprodstkwakpx.z33.web.core.windows.net/  
**Status**: ✅ All containers running, processing articles, publishing live content

### ✅ Storage Queue Migration Complete!
**Achievement**: Successfully migrated from Service Bus to Azure Storage Queues  
**Resolution**: Resolved Azure Container Apps managed identity conflicts with KEDA scaling  
**Result**: Full end-to-end automation working with managed identity authentication  
**Status**: All containers now use Storage Queues for KEDA-triggered processing

### ✅ Phase 3: Content Quality Verified Active!
**AI Title Generation**: Working with smart detection ($0.0017/article)  
**Smart Images**: Finding relevant Unsplash photos with keyword extraction  
**Content Rendering**: 800+ word articles publishing with proper attribution  
**Site Performance**: Pagination, responsive design, performance monitoring active

### What's Working ✅
- **✅ Simplified Architecture**: Clean 3-container design (collector → processor → generator)
- **✅ Enhanced content-processor**: Now handles both processing AND AI generation
- **✅ Storage Queue Integration**: Managed identity authentication with KEDA scaling
- **✅ API Standardization**: All containers use shared library pattern with consistent responses
- **✅ Test Coverage**: Content-collector: 123 passed, content-processor: 33 passed
- **✅ Queue Automation**: Collection → blob save → queue message → KEDA scale → processing
- **✅ Security**: OWASP-compliant error handling and input sanitization
- **✅ Infrastructure**: Azure Container Apps, Terraform, CI/CD pipeline

### Recent Achievements 🏆
- **Phase 3 Verification** (Oct 17): AI title generation and smart image selection verified active
- **Production Site**: Publishing 800+ word articles with relevant imagery
- **Performance Monitoring**: Client-side telemetry and Application Insights integration working
- **Storage Queue Migration**: Completed migration from Service Bus to Storage Queues
- **Authentication Resolution**: Managed identity now works with both blob storage and queues
- **Architecture Simplification**: Reduced from 4 containers to 3 (25% reduction in complexity)
- **Content-Generator Merger**: AI generation functionality successfully integrated into content-processor
- **Zero Regression**: All existing functionality preserved during integration
- **Enhanced Security**: Added OWASP-compliant error handling and input sanitization

## 🏗️ Current Clean Architecture

**Before (Complex)**: 4 containers with Service Bus authentication conflicts  
 **After (Clean)**: 3 containers with Storage Queues, KEDA cron scheduling, and managed identity  

**Status**: ✅ **COMPLETE** - Full automation working with 8-hour collection cycles

```
KEDA Cron (8hrs) → content-collector → [Storage Queue] → content-processor → site-generator → jablab.com
                         ↓                    ↑                    ↓
                    Blob Storage      KEDA Scaling           Blob Storage
                   (Raw Content)   (Managed Identity)    (Processed Content)
```

**Architecture Benefits** (✅ Implemented):
- **✅ KEDA Cron Scheduling**: Automated collection every 8 hours with zero-cost idle time
- **✅ Managed Identity**: No connection strings needed, secure authentication throughout
- **✅ KEDA Queue Scaling**: Native support for azure-queue scaler with managed identity
- **✅ Cost Effective**: Zero-replica scaling eliminates idle compute costs
- **✅ Simplified Architecture**: No authentication conflicts or connection string management

1. **content-collector** (FastAPI)
   - Automated collection every 8 hours via KEDA cron scaler
   - Zero-replica scaling (scales from 0 to 1 on schedule)
   - Template-based collection from approved sources (RSS, Mastodon, Web)
   - Save raw topics to Azure Blob Storage
   - Standard REST API with health checks

2. **content-processor** (FastAPI) **← ENHANCED!**
   - **Content Processing**: Read raw topics, enhance with AI, quality assessment
   - **AI Content Generation**: TLDR/blog/deepdive article generation with multiple writer personalities
   - **Batch Processing**: Asynchronous generation with status tracking
   - **KEDA Queue Scaling**: Automatically scales based on storage queue depth
   - **Dual API**: Both processing and generation endpoints available
   - Save processed/generated articles to blob storage

3. **site-generator** (FastAPI)
   - Read processed articles from blob storage
   - Generate static website with standard tools
   - **KEDA Queue Scaling**: Automatically scales when generation requests arrive
   - Deploy to Azure Static Web Apps

### 🚀 Enhanced Content-Processor Capabilities

**New Generation Endpoints:**
```
POST /generate/tldr                      # Generate TLDR articles (200-400 words)
POST /generate/blog                      # Generate blog posts (600-1000 words)  
POST /generate/deepdive                  # Generate deep analysis (1200+ words)
POST /generate/batch                     # Start batch generation
GET  /generation/status/{batch_id}       # Get batch status
```

**Existing Processing Endpoints:**
```
POST /process                            # Core content processing
POST /wake-up                            # Wake up work queue
GET  /process/status                     # Queue status
```

## 🚀 Quick Start

### Check System Status
```bash
# Verify content-processor integration
cd /workspaces/ai-content-farm
python -m pytest containers/content-processor/tests/ -v
# Expected: 10 passed, 3 skipped

# Test generation integration
./test-generation-integration.sh
# Expected: All ✅ confirmations
```

### Generate Content
```bash
# Start content-processor locally
cd containers/content-processor
python main.py

# Test generation (in another terminal)
curl -X POST "http://localhost:8000/generate/blog" \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI trends", "source_material": "Latest AI developments"}'
```

### Deploy to Azure
```bash
# Deploy the enhanced 3-container architecture
make deploy-production
```

## 📋 Technical Standards

### Standard API Pattern (All Containers)
```
GET  /health              # Health check
GET  /status              # Detailed status  
GET  /docs                # Auto-generated docs
POST /process             # Main business logic (or /generate for content-processor)
GET  /                    # Service info
```

### Standard Response Format
```json
{
  "status": "success|error",
  "message": "Human readable message",
  "data": { /* actual response data */ },
  "metadata": { /* service metadata */ }
}
```

## 🎯 Next Steps

### Immediate (Week 1):
1. **✅ Architecture Simplification** - COMPLETED
2. **� End-to-End Testing** - Test full Reddit → Website pipeline
3. **🔄 Documentation Updates** - Update all references to new architecture
4. **🔄 Remove content-generator** - Clean up deprecated container

### Future Enhancements:
1. **Real AI Integration** - Connect Azure OpenAI for actual content generation
2. **Advanced Batch Processing** - Parallel generation, queue management  
3. **Enhanced Content Types** - Add more generation formats and styles
4. **Cost Optimization** - Monitor Azure costs with simplified architecture

## � Container Lifecycle Management

**Environment-Based Shutdown Control**: All containers support flexible lifecycle management for debugging vs production efficiency.

**Current Setting** (Development/Debugging):
```bash
DISABLE_AUTO_SHUTDOWN=true  # Containers stay alive for investigation
```

**Production Setting** (Cost Efficiency):
```bash
DISABLE_AUTO_SHUTDOWN=false  # Containers shutdown after work completion
```

**Benefits**:
- **Development**: Containers stay alive for API testing and debugging
- **Production**: Automatic shutdown minimizes Azure compute costs
- **Consistent**: All three containers follow the same lifecycle pattern

**Documentation**: See [`docs/development/CONTAINER_LIFECYCLE_MANAGEMENT.md`](docs/development/CONTAINER_LIFECYCLE_MANAGEMENT.md) for detailed configuration and usage.

## �📁 Documentation

**Primary Documents**:
- `README.md` - This file (current architecture and usage)
- `CONTENT_GENERATOR_MERGER_SUCCESS.md` - Integration achievement summary
- `CONTENT_GENERATOR_DEPRECATION_PLAN.md` - Migration timeline and strategy
- `TODO.md` - Current priorities and next steps

**Detailed Documentation**: `docs/` folder for technical deep-dives

---

**Current Achievement**: ✅ Successfully simplified architecture from 4 to 3 containers while enhancing functionality. Content-processor now handles both processing AND AI generation with zero regression.

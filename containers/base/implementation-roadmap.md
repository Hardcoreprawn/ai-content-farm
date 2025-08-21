# Multi-Tier Container Implementation Roadmap
# Phased approach to reduce risk and validate benefits

## Phase 1: Foundation Migration (Week 1-2)
**Goal**: Standardize all containers on single Python base
**Risk**: Low (mainly cleanup)

### Steps:
1. **Update all Dockerfiles** to use `python:3.11-slim` (remove Azure Functions base)
2. **Test each container** individually to ensure no regressions
3. **Deploy to staging** and run full integration tests
4. **Merge and deploy** to production

### Expected Benefits:
- ✅ Consistent base across all containers
- ✅ Remove Azure Functions complexity
- ✅ Simpler dependency management

### Files to Update:
```bash
containers/content-collector/Dockerfile
containers/content-enricher/Dockerfile  
containers/content-processor/Dockerfile
containers/content-ranker/Dockerfile
# (4 containers still using Azure Functions base)
```

## Phase 2: Multi-Tier Base Creation (Week 3-4)
**Goal**: Implement layered base image strategy
**Risk**: Medium (new architecture)

### Steps:
1. **Build and test** `ai-content-farm-base` multi-tier image
2. **Migrate 1-2 containers** as proof of concept
3. **Validate dependency reduction** (should see ~80% fewer dependency PRs)
4. **Migrate remaining containers** once validated

### Expected Benefits:
- ✅ Reduce dependency PRs from ~38 to ~8-10
- ✅ Single point of security updates
- ✅ Faster builds (cached layers)

### Container Migration Order:
1. **content-generator** (simple, good test case)
2. **site-generator** (lightweight)
3. **content-enricher** (medium complexity)
4. **content-processor** (medium complexity)
5. **content-ranker** (medium complexity)
6. **markdown-generator** (medium complexity)  
7. **content-collector** (most complex - do last)
8. **collector-scheduler** (unique deps - special case)

## Phase 3: A/B Testing Infrastructure (Week 5-6)
**Goal**: Enable version comparison and safe deployments
**Risk**: Medium (new operational complexity)

### Steps:
1. **Implement traffic splitting** with nginx/load balancer
2. **Add monitoring** and metrics collection
3. **Create deployment pipeline** for multiple versions
4. **Test with non-critical service** first

### Expected Benefits:
- ✅ Safe deployment strategy
- ✅ Performance comparison capability
- ✅ Gradual rollout capability
- ✅ Easy rollback mechanism

## Phase 4: Automation & Optimization (Week 7-8)
**Goal**: Automate base image updates and optimize builds
**Risk**: Low (operational improvement)

### Steps:
1. **Automate base image builds** when common deps update
2. **Implement automated testing** of base image changes
3. **Add dependency scanning** at base image level
4. **Optimize build caching** and layer sharing

### Expected Benefits:
- ✅ Zero-touch dependency updates
- ✅ Automated security scanning
- ✅ Faster CI/CD pipeline
- ✅ Reduced operational overhead

## Success Metrics

### Before (Current State):
- 📊 **Dependency PRs**: ~38 per update cycle
- 📊 **Build time**: ~15-20 minutes total
- 📊 **Security scan time**: 8 separate scans
- 📊 **Deployment risk**: High (8 separate changes)

### After (Target State):
- 📊 **Dependency PRs**: ~8-10 per update cycle (-75%)
- 📊 **Build time**: ~8-10 minutes total (-50%)
- 📊 **Security scan time**: 3 base image scans (-65%)
- 📊 **Deployment risk**: Low (tested base + small changes)

## Migration Commands

### Phase 1 Quick Wins:
```bash
# Update Azure Functions containers to standard Python
find containers -name "Dockerfile" -exec sed -i 's|mcr.microsoft.com/azure-functions/python:4-python3.11-slim|python:3.11-slim|g' {} \;

# Test each container
for container in content-collector content-enricher content-processor content-ranker; do
  echo "Testing $container..."
  docker build -t $container-test containers/$container/
  docker run --rm $container-test python -c "import main; print('✅ $container OK')"
done
```

### Phase 2 Implementation:
```bash
# Build multi-tier base
docker build -f containers/base/Dockerfile.multitier -t ai-content-farm-base:latest .

# Test with content-generator
docker build -f containers/content-generator/Dockerfile.new -t content-generator-v2 .
docker run --rm content-generator-v2 python -c "import main; print('✅ Multi-tier working')"
```

## Risk Mitigation

### What Could Go Wrong:
1. **Dependency conflicts** between layers
2. **Build cache invalidation** causing slow builds  
3. **Layer bloat** making images larger
4. **Complex debugging** across multiple layers

### Mitigation Strategies:
1. **Gradual migration** (one container at a time)
2. **Comprehensive testing** at each phase
3. **Monitoring size** and performance metrics
4. **Clear rollback plan** for each phase
5. **Documentation** of layer responsibilities

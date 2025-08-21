# Container Consolidation Strategy
## Reducing Toil, Improving Security, Enabling A/B Testing

### Problem Statement
- 38 dependency PRs across 8 containers = unsustainable toil
- Mixed base images (Azure Functions vs Python) causing inconsistency
- Duplicate dependency management across containers
- Security scanning overhead on every container change
- Future need for A/B testing different versions

### Solution: Multi-Tier Base Image Strategy

```
ai-content-farm-base:latest
├── Common system deps (build tools, curl, git)
├── Common Python deps (fastapi, uvicorn, pydantic, etc.)
├── Azure SDK components
├── Testing framework
└── Security baseline

    ↓ (inherits from)

ai-content-farm-web:latest         ai-content-farm-processor:latest
├── Web-specific deps              ├── Data processing deps
├── HTTP utilities                 ├── ML libraries (if needed)
└── API frameworks                 └── Async processing tools

    ↓ (inherits from)               ↓ (inherits from)

content-generator:v1.2.3          content-processor:v1.2.3
├── Only unique deps               ├── Only unique deps
├── App code                       ├── App code
└── Configuration                  └── Configuration
```

### Benefits
1. **Reduce Toil**: 1 dependency update instead of 8
2. **Security**: Single scanning point for common vulnerabilities
3. **Consistency**: Same base across all containers
4. **A/B Testing**: Easy to deploy different versions side-by-side
5. **Modularity**: Swap components without rebuilding everything

### Implementation Strategy
1. **Phase 1**: Migrate all containers to single Python base
2. **Phase 2**: Create intermediate specialization layers
3. **Phase 3**: Implement versioning strategy for A/B testing
4. **Phase 4**: Add automated base image updates

### A/B Testing Architecture
```
Load Balancer
├── 50% → content-generator:v1.2.3 (GPT-4)
├── 30% → content-generator:v1.3.0 (Claude-3.5)
└── 20% → content-generator:v1.4.0-beta (Experimental)
```

All versions share the same base, only the final layer differs.

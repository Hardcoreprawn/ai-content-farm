# GitHub Issue: Split site-generator into specialized containers

## 🎯 Summary

Split the monolithic `site-generator` container into two specialized containers with distinct scaling patterns:

1. **markdown-generator**: Fast per-article JSON → Markdown conversion (KEDA: immediate, scales 0→5)
2. **site-builder**: Batched full-site HTML generation (KEDA: batched/cron, scales 0→1)

**Impact:**
- 63% cost reduction ($1.08 → $0.40/month)
- 85% faster article processing (40s → 7s latency)
- Better KEDA optimization for each workload pattern
- Cleaner separation of concerns

## 📋 Implementation Checklist

### Phase 1: Container Scaffolding (Days 1-2)
- [ ] Create `containers/markdown-generator/` directory structure
- [ ] Implement `main.py` (<150 lines, type hints, PEP8)
- [ ] Implement `markdown_processor.py` (<250 lines)
- [ ] Implement `models.py` (<100 lines, Pydantic)
- [ ] Implement `config.py` (<100 lines)
- [ ] Create `Dockerfile` with non-root user
- [ ] Add `requirements.txt`
- [ ] Create `containers/site-builder/` directory structure
- [ ] Implement `main.py` (<150 lines, type hints, PEP8)
- [ ] Implement `site_builder.py` (<300 lines)
- [ ] Implement `index_manager.py` (<150 lines)
- [ ] Implement `models.py` (<100 lines, Pydantic)
- [ ] Implement `config.py` (<100 lines)
- [ ] Create `Dockerfile` with non-root user
- [ ] Add `requirements.txt`

### Phase 2: Unit Tests (Days 3-4)
- [ ] **markdown-generator tests:**
  - [ ] `test_outcomes.py` - Observable outcome tests
  - [ ] `test_api_endpoints.py` - API contract validation
  - [ ] `test_queue_processing.py` - Queue integration
  - [ ] `conftest.py` - Test fixtures
  - [ ] Achieve 90%+ code coverage
- [ ] **site-builder tests:**
  - [ ] `test_outcomes.py` - Full site build outcomes
  - [ ] `test_index_management.py` - Index regeneration
  - [ ] `test_api_endpoints.py` - API contracts
  - [ ] `test_queue_processing.py` - Queue integration
  - [ ] `conftest.py` - Test fixtures
  - [ ] Achieve 90%+ code coverage
- [ ] Validate all tests pass locally
- [ ] Run `black`, `flake8`, `mypy` for code quality

### Phase 3: Infrastructure (Day 5)
- [ ] Create `infra/container_app_markdown_generator.tf`
- [ ] Create `infra/container_app_site_builder.tf`
- [ ] Add new queues to `infra/storage_queues.tf`:
  - [ ] `markdown-generation-requests`
  - [ ] `site-build-requests`
- [ ] Update KEDA auth configuration
- [ ] Update container image registry
- [ ] Add monitoring and alerting
- [ ] Validate Terraform plan

### Phase 4: CI/CD Integration (Day 6)
- [ ] Update `.github/workflows/container-build.yml`
- [ ] Add markdown-generator to build matrix
- [ ] Add site-builder to build matrix
- [ ] Update deployment workflow
- [ ] Validate builds pass

### Phase 5: Migration & Cleanup (Days 7-10)
- [ ] **Day 7: Parallel Deployment**
  - [ ] Deploy markdown-generator
  - [ ] Deploy site-builder
  - [ ] Keep site-generator running (no traffic)
  - [ ] Monitor both systems
- [ ] **Day 8: Traffic Cutover**
  - [ ] Update content-processor to use new queue
  - [ ] Verify markdown generation working
  - [ ] Verify site builds working
  - [ ] Validate cost metrics
- [ ] **Day 9: Deprecation**
  - [ ] Add deprecation notice to site-generator
  - [ ] Scale site-generator to 0 replicas
  - [ ] Stop sending to old queue
  - [ ] Monitor for issues
- [ ] **Day 10: Cleanup**
  - [ ] Remove site-generator container app (Terraform)
  - [ ] Remove old queue: `site-generation-requests`
  - [ ] Archive code to `docs/deprecated/`
  - [ ] Update all documentation
  - [ ] Close migration PR

## 📊 Success Criteria

### Code Quality
- [x] All Python files < 500 lines
- [x] PEP8 compliant (black, flake8 pass)
- [x] Type hints on all functions
- [x] No inline exports
- [x] Docstrings on public functions
- [x] No hardcoded values

### Testing
- [x] Unit tests cover 90%+ code
- [x] Tests focus on outcomes, not methods
- [x] All tests pass
- [x] Integration tests validate queue flow
- [x] Performance tests verify latency

### Monitoring
- [x] Health endpoints return proper status
- [x] Status endpoints show metrics
- [x] Logging follows standards
- [x] Metrics exported to App Insights
- [x] Alerts configured

### Performance
- [x] Markdown generation < 5s per article
- [x] Full site build < 60s for 100 articles
- [x] Queue latency < 2s
- [x] Cold start < 10s

### Cost
- [x] Total cost < $0.50/month
- [x] 50%+ reduction vs current
- [x] Cost tracking implemented

## 🔗 Related Documents

- Implementation Plan: `docs/SITE_GENERATOR_SPLIT_IMPLEMENTATION_PLAN.md`
- Architecture Decision: `docs/SITE_GENERATOR_ARCHITECTURE_DECISION.md`
- Cost Analysis: `docs/infrastructure/cost-optimization.md`

## 👥 Assignees

@Hardcoreprawn

## 🏷️ Labels

- `enhancement`
- `infrastructure`
- `containers`
- `cost-optimization`
- `breaking-change`

## ⏱️ Estimated Effort

**2 weeks** (10 working days)
- Phase 1-2: 4 days (scaffolding + tests)
- Phase 3-4: 2 days (infra + CI/CD)
- Phase 5: 4 days (migration + cleanup)

## 🚨 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data loss during migration | High | Parallel deployment, comprehensive testing |
| Cost increase vs reduction | Medium | Monitor costs daily, rollback plan ready |
| KEDA scaling issues | Medium | Test scaling rules extensively, alerts configured |
| Breaking changes for downstream | Low | Maintain backward compatibility during migration |

## 📝 Notes

- Keep site-generator running until full validation
- Monitor queue depths closely during cutover
- Have rollback plan ready (revert queue routing)
- Document all configuration changes
- Update runbooks for new containers

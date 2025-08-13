# Container Apps Migration - Remaining Services Implementation

**Created:** August 13, 2025  
**Status:** In Progress  
**Priority:** High  

## Overview
Complete the Container Apps migration by implementing ContentEnricher, Scheduler, and SSG services following the proven pattern established with SummaryWomble and ContentRanker.

## Issue Breakdown

### Issue #1: ContentEnricher Service Implementation
**Assignee:** GitHub Copilot Coding Agent  
**Priority:** High  
**Estimated Time:** 4 hours  

**Requirements:**
- Migrate Azure Functions ContentEnricher to FastAPI service
- Implement AI-powered content enhancement and summarization
- Add job-based processing with status tracking
- Port 8002, following established API patterns

**Deliverables:**
- `/containers/content-enricher/` complete service
- Docker integration with hot reload
- API documentation at `/docs`
- Unit and integration tests

### Issue #2: Scheduler Service Implementation  
**Assignee:** GitHub Copilot Coding Agent  
**Priority:** High  
**Estimated Time:** 6 hours  

**Requirements:**
- Replace timer-based Azure Functions with HTTP orchestration
- Implement workflow management and job queuing
- Add Redis integration for job management
- Service-to-service communication patterns

**Deliverables:**
- `/containers/scheduler/` complete service
- Workflow orchestration endpoints
- Redis job queue integration
- Service communication layer

### Issue #3: Static Site Generator (SSG) Service
**Assignee:** GitHub Copilot Coding Agent  
**Priority:** Medium  
**Estimated Time:** 8 hours  

**Requirements:**
- Markdown generation from processed content
- Headless CMS integration (Strapi/Contentful)
- Template-based content generation
- Static site deployment automation

**Deliverables:**
- `/containers/ssg/` complete service
- Markdown generation engine
- CMS publisher integration
- Template management system

### Issue #4: Docker Compose Integration
**Assignee:** GitHub Copilot Coding Agent  
**Priority:** High  
**Estimated Time:** 2 hours  

**Requirements:**
- Update docker-compose.yml for all services
- Add Redis service for job queuing
- Proper service dependencies and networking
- Health checks for all services

**Deliverables:**
- Updated docker-compose.yml
- Redis integration
- Service dependency management
- Health check endpoints

### Issue #5: Documentation Updates
**Assignee:** GitHub Copilot Coding Agent  
**Priority:** Medium  
**Estimated Time:** 3 hours  

**Requirements:**
- Update architecture documentation
- Create API reference documentation
- Archive Azure Functions documentation
- Update deployment guides

**Deliverables:**
- Updated `/docs/system-design.md`
- Complete API reference
- Archived legacy documentation
- Container Apps deployment guide

## Implementation Strategy

### Parallel Implementation
All services can be implemented in parallel since they follow the established pattern:

1. **Core Services** (ContentEnricher, Scheduler) - Can be developed simultaneously
2. **SSG Service** - Can be developed in parallel with core services
3. **Docker Integration** - Should be done after services are created
4. **Documentation** - Can be done in parallel with development

### Success Metrics
- [ ] All services build and start successfully
- [ ] Complete end-to-end content pipeline working
- [ ] All health checks passing
- [ ] API documentation complete
- [ ] Local development environment fully functional

## Timeline
- **Day 1**: Create ContentEnricher and Scheduler services
- **Day 2**: Create SSG service and Docker integration
- **Day 3**: Documentation updates and testing
- **Total**: 3 days for complete pipeline

## Dependencies
- ✅ SummaryWomble pattern established
- ✅ ContentRanker pattern established  
- ✅ Docker Compose foundation ready
- ✅ Blob storage abstraction patterns
- ⏳ GitHub Copilot coding agent availability

## Notes
Since GitHub Copilot coding agent is currently unavailable, implementing manually with proper issue tracking and following established patterns from SummaryWomble and ContentRanker implementations.

# Scheduler Implementation Roadmap

## Implementation Phases

### 🚀 Phase 1: MVP Scheduler (Week 1)
**Goal**: Basic working scheduler calling content-collector on fixed intervals

#### Tasks
- [ ] **Infrastructure Setup**
  - [ ] Add Logic App Terraform resources (`infra/scheduler.tf`)
  - [ ] Configure managed identity and RBAC permissions
  - [ ] Create Azure Table Storage for topic configuration
  - [ ] Deploy initial infrastructure

- [ ] **Basic Logic App Workflow**
  - [ ] Simple recurrence trigger (every 4 hours)
  - [ ] Managed Identity authentication to content-collector
  - [ ] Single topic collection (Technology)
  - [ ] Basic error handling and logging

- [ ] **Topic Configuration**
  - [ ] Create initial topic configuration in Azure Table Storage
  - [ ] Technology topic with 3-4 subreddits
  - [ ] Basic collection parameters (limit, min_score, etc.)

- [ ] **Testing & Validation**
  - [ ] Test Logic App triggers content-collector successfully
  - [ ] Verify managed identity authentication works
  - [ ] Confirm content flows through to content-processor
  - [ ] Monitor costs and execution frequency

#### Success Criteria
- Logic App executes every 4 hours without errors
- Content-collector receives valid requests with authentication
- Content flows through to blob storage and content-processor
- Total additional monthly cost < $2

---

### 🎯 Phase 2: Multi-Topic Intelligence (Week 2-3)
**Goal**: Expand to multiple topics with dynamic configuration

#### Tasks
- [ ] **Topic Management System**
  - [ ] Implement 5-6 topic configurations (Technology, Programming, Science, Bees, etc.)
  - [ ] Dynamic subreddit mapping per topic
  - [ ] Topic-specific collection criteria
  - [ ] Schedule variation by topic priority

- [ ] **Enhanced Logic App Workflow**
  - [ ] For-each loop to process multiple topics
  - [ ] Dynamic request building based on topic config
  - [ ] Parallel execution for independent topics
  - [ ] Improved error handling per topic

- [ ] **Basic Feedback Collection**
  - [ ] Capture collection success/failure rates
  - [ ] Store basic analytics (items collected, processing success)
  - [ ] Simple schedule optimization (reduce frequency for failing topics)

- [ ] **Monitoring & Alerting**
  - [ ] Logic App execution monitoring
  - [ ] Collection success rate tracking
  - [ ] Cost monitoring and alerting

#### Success Criteria
- 5+ topics collecting successfully on different schedules
- Topic-specific content successfully flows to content-processor
- Basic analytics show collection patterns and success rates
- Schedule optimization reduces failed collections by 50%

---

### ⚡ Phase 3: Advanced Orchestration (Week 4+)
**Goal**: Intelligent scheduling with source discovery and optimization

#### Tasks
- [ ] **Source Discovery Engine**
  - [ ] Analyze successful content to identify high-value sources
  - [ ] Cross-reference topics to find overlapping subreddits
  - [ ] Automatically suggest new sources based on content quality
  - [ ] A/B test new sources before adding to regular schedule

- [ ] **Adaptive Scheduling**
  - [ ] Machine learning-based frequency optimization
  - [ ] Time-of-day optimization based on content availability
  - [ ] Seasonal adjustments for topic relevance
  - [ ] Load balancing to avoid rate limiting

- [ ] **Cross-Platform Preparation**
  - [ ] Extend topic configuration for multiple source types
  - [ ] Prepare framework for Bluesky/Mastodon integration
  - [ ] RSS feed integration via scheduler
  - [ ] Web scraping schedule coordination

- [ ] **Advanced Analytics**
  - [ ] Content performance correlation (collection → website traffic)
  - [ ] ROI analysis (collection cost vs content value)
  - [ ] Predictive scheduling based on historical patterns
  - [ ] Source quality scoring and ranking

#### Success Criteria
- Scheduler automatically discovers 2+ new valuable sources monthly
- Content quality scores improve by 20% through better source selection
- Collection costs reduce by 30% through optimized scheduling
- Cross-posting intelligence identifies content overlap > 80% accuracy

---

## Technical Implementation Details

### Terraform Resources Needed
```hcl
# In infra/scheduler.tf
resource "azurerm_logic_app_workflow" "content_scheduler"
resource "azurerm_storage_table" "topic_configurations"  
resource "azurerm_storage_table" "execution_history"
resource "azurerm_role_assignment" "scheduler_container_apps"
resource "azurerm_role_assignment" "scheduler_storage"
```

### Logic App Workflow JSON Structure
```json
{
  "triggers": {
    "Recurrence": { "frequency": "Hour", "interval": 4 }
  },
  "actions": {
    "Get_Topic_Configs": { "type": "AzureTableStorage" },
    "For_Each_Topic": {
      "foreach": "@body('Get_Topic_Configs')",
      "actions": {
        "Build_Collection_Request": { "type": "Compose" },
        "Call_Content_Collector": { "type": "Http" },
        "Record_Results": { "type": "AzureTableStorage" }
      }
    }
  }
}
```

### Topic Configuration Schema
```json
{
  "PartitionKey": "topics",
  "RowKey": "technology",
  "DisplayName": "Technology",
  "Schedule": { "frequency_hours": 4, "priority": "high" },
  "Sources": {
    "reddit": {
      "subreddits": ["technology", "programming", "MachineLearning"],
      "limit": 20,
      "sort": "hot"
    }
  },
  "Criteria": { "min_score": 50, "min_comments": 10 },
  "Analytics": { "success_rate": 0.85, "last_run": "2025-09-09T10:00:00Z" }
}
```

## File Structure & Organization

### New Files to Create
```
infra/
├── scheduler.tf              # Main scheduler infrastructure
└── scheduler_storage.tf      # Topic configuration storage

docs/
├── SCHEDULER_DESIGN.md       # ✅ Created - High-level design
├── SCHEDULER_IMPLEMENTATION.md # ✅ Created - Implementation plan
└── scheduler/
    ├── topic-configuration.md # Topic management guide
    ├── logic-app-workflow.md  # Logic App workflow documentation
    └── analytics-integration.md # Feedback system integration

scripts/
└── scheduler/
    ├── deploy-scheduler.sh    # Deployment automation
    ├── configure-topics.sh    # Topic configuration setup
    └── test-scheduler.sh      # End-to-end testing

tests/
└── scheduler/
    ├── test_topic_config.py   # Topic configuration validation
    ├── test_logic_app.py      # Logic App workflow testing
    └── test_integration.py    # Scheduler → Content-collector integration
```

### Integration Points
```
Scheduler → Content-Collector → Content-Processor → Site-Generator → Website
    ↓              ↓                  ↓
Topic Config   Collection         Analytics
Storage        Metadata           Feedback
```

## Risk Mitigation

### Technical Risks
- **Logic App Reliability**: Implement comprehensive error handling and retry logic
- **Authentication Failures**: Test managed identity integration thoroughly
- **Rate Limiting**: Implement intelligent request spacing and backoff
- **Cost Overruns**: Set up budget alerts and automatic scaling controls

### Business Risks
- **Low Content Quality**: Start with proven subreddits, gradually expand
- **Topic Overlap**: Monitor cross-posting to avoid duplicate content
- **Seasonal Variations**: Plan for topic popularity fluctuations
- **Platform Changes**: Build modular source adapters for API changes

## Success Metrics per Phase

### Phase 1 Metrics
- [ ] Logic App executes 180+ times/month with >95% success rate
- [ ] Content-collector receives authenticated requests successfully
- [ ] Monthly scheduler costs < $2
- [ ] End-to-end content flow works (Reddit → Website)

### Phase 2 Metrics
- [ ] 5+ topics collecting on independent schedules
- [ ] Topic-specific content quality scores available
- [ ] Basic analytics show collection patterns
- [ ] Schedule optimization reduces failed collections

### Phase 3 Metrics
- [ ] 2+ new sources discovered monthly through analytics
- [ ] Content quality improvement >20% vs baseline
- [ ] Collection cost reduction >30% through optimization
- [ ] Cross-posting detection accuracy >80%

## GitHub Issues to Create

### Phase 1 Issues
1. **Create Scheduler Infrastructure** (`infrastructure` label)
   - Add Logic App Terraform resources
   - Configure managed identity and RBAC
   - Create topic configuration storage

2. **Implement Basic Logic App Workflow** (`scheduler` label)
   - Create Logic App workflow JSON
   - Implement authentication to content-collector
   - Add basic error handling

3. **Setup Topic Configuration System** (`configuration` label)
   - Define topic configuration schema
   - Create initial technology topic
   - Test topic-based collection

4. **End-to-End Scheduler Testing** (`testing` label)
   - Test complete scheduler flow
   - Validate authentication and collection
   - Monitor costs and performance

### Phase 2 Issues
5. **Multi-Topic Configuration** (`enhancement` label)
6. **Advanced Logic App Workflow** (`enhancement` label) 
7. **Basic Analytics Collection** (`analytics` label)
8. **Schedule Optimization** (`optimization` label)

## Next Actions

1. **👀 Review Design**: Confirm this approach aligns with your vision
2. **🎯 Prioritize Phases**: Decide if Phase 1 approach is correct
3. **📋 Create Issues**: Generate GitHub issues for Phase 1 tasks
4. **🏗️ Start Implementation**: Begin with Terraform infrastructure
5. **🧪 Test MVP**: Validate basic scheduler functionality
6. **📊 Monitor & Iterate**: Use analytics to guide Phase 2 development

---

*This roadmap provides a structured approach to building a cost-effective, intelligent content collection scheduler that grows with your platform's needs while maintaining your $30-40/month budget.*

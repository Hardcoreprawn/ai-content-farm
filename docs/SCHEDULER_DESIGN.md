# Azure Logic App Scheduler Design

## Overview
A cost-effective, dynamic scheduling system using Azure Logic Apps to orchestrate content collection across multiple topics and sources. The scheduler will authenticate with Azure Managed Identity and call the content-collector service to initiate targeted collection campaigns.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Logic App     │    │ Content Collector│    │ Content Topics  │
│   Scheduler     │───▶│    (HTTPS)       │───▶│   Storage       │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌──────────────────┐
│   Schedule      │    │    Collection    │
│   Configuration │    │    Feedback      │
│   Storage       │    │    Analytics     │
└─────────────────┘    └──────────────────┘
```

## Core Components

### 1. Logic App Scheduler
- **Recurrence Trigger**: 4-6 hour intervals (configurable)
- **Topic-Based Execution**: Different schedules for different topic categories
- **Dynamic Parameter Building**: Constructs collection requests based on topic configuration
- **Retry Logic**: Handles content-collector failures gracefully
- **Cost Tracking**: Monitors execution costs and adjusts frequency

### 2. Topic Configuration System
- **Topic Definitions**: Technology, Programming, Bees, Science, etc.
- **Source Mapping**: Maps topics to relevant subreddits and RSS feeds
- **Schedule Preferences**: Different frequencies for different topics
- **Quality Thresholds**: Topic-specific filtering criteria

### 3. Collection Orchestration
- **Batch Planning**: Groups related sources into efficient collection batches
- **Load Distribution**: Spreads requests across time to avoid rate limiting
- **Success Tracking**: Monitors collection success rates per topic/source
- **Adaptive Scheduling**: Adjusts frequency based on content quality/quantity

### 4. Feedback Mechanism
- **Collection Analytics**: Success rates, content quality scores, engagement metrics
- **Source Discovery**: Identifies new high-value subreddits based on successful collections
- **Schedule Optimization**: Automatically adjusts timing and frequency
- **Cross-Posting Intelligence**: Finds content overlap between sources

## Implementation Plan

### Phase 1: Basic Scheduler (Week 1)
- [ ] Create Logic App with simple recurrence trigger
- [ ] Implement Managed Identity authentication
- [ ] Basic topic configuration in Azure Table Storage
- [ ] Single collection endpoint calls

### Phase 2: Topic Intelligence (Week 2-3)
- [ ] Multi-topic configuration system
- [ ] Dynamic subreddit mapping per topic
- [ ] Basic feedback collection from content-processor
- [ ] Schedule optimization based on success rates

### Phase 3: Advanced Orchestration (Week 4+)
- [ ] Cross-source correlation and discovery
- [ ] Adaptive frequency adjustment
- [ ] Cost optimization algorithms
- [ ] Integration with content-processor analytics

## Technical Specifications

### Logic App Workflow Structure
```json
{
  "definition": {
    "triggers": {
      "Recurrence": {
        "type": "Recurrence",
        "recurrence": {
          "frequency": "Hour",
          "interval": 4,
          "timeZone": "UTC"
        }
      }
    },
    "actions": {
      "Get_Topic_Configurations": {},
      "For_Each_Topic": {
        "type": "Foreach",
        "foreach": "@body('Get_Topic_Configurations')",
        "actions": {
          "Build_Collection_Request": {},
          "Call_Content_Collector": {},
          "Record_Collection_Results": {}
        }
      }
    }
  }
}
```

### Topic Configuration Schema
```json
{
  "topic_id": "technology",
  "display_name": "Technology",
  "schedule": {
    "frequency_hours": 4,
    "priority": "high",
    "active_hours": "0-23"
  },
  "sources": {
    "reddit": {
      "subreddits": ["technology", "programming", "MachineLearning"],
      "sort_type": "hot",
      "limit": 20
    },
    "rss": {
      "feeds": ["https://feeds.wired.com/wired/index"]
    }
  },
  "collection_criteria": {
    "min_score": 50,
    "min_comments": 10,
    "keywords": ["AI", "machine learning", "automation"]
  },
  "analytics": {
    "last_run": "2025-09-09T10:00:00Z",
    "success_rate": 0.85,
    "avg_quality_score": 7.2,
    "content_generated": 45
  }
}
```

### Authentication & Security
- **Managed Identity**: Logic App uses system-assigned identity
- **RBAC**: Minimal permissions to call content-collector and access storage
- **Key Vault Integration**: Sensitive configuration stored securely
- **Network Security**: Logic App calls Container Apps via secure internal networking

### Cost Optimization
- **Execution Monitoring**: Track Logic App runs vs budget
- **Dynamic Frequency**: Reduce frequency during low-value periods
- **Batch Optimization**: Group related collections to minimize runs
- **Success-Based Scaling**: Scale up successful topics, scale down low-performing ones

## Integration Points

### Content Collector API Integration
```bash
# Topic-based collection call
POST https://content-collector.azurecontainerapps.io/collect
Authorization: Bearer <managed-identity-token>
Content-Type: application/json

{
  "sources": [
    {
      "type": "reddit",
      "subreddits": ["technology", "programming"],
      "limit": 20,
      "criteria": {
        "min_score": 50,
        "min_comments": 10,
        "include_keywords": ["AI", "automation"]
      }
    }
  ],
  "collection_metadata": {
    "topic": "technology",
    "scheduled_by": "logic-app-scheduler",
    "batch_id": "tech_2025090910"
  }
}
```

### Feedback Collection Integration
```bash
# Get collection analytics
GET https://content-processor.azurecontainerapps.io/analytics/collection/{batch_id}
Authorization: Bearer <managed-identity-token>

Response:
{
  "batch_id": "tech_2025090910",
  "items_collected": 15,
  "items_processed": 12,
  "quality_scores": [8.2, 7.5, 9.1, ...],
  "generation_success_rate": 0.8,
  "top_performing_sources": ["r/MachineLearning", "r/programming"]
}
```

## Storage Requirements

### Azure Table Storage for Configuration
- **Topics Table**: Topic definitions and schedules
- **SourceMappings Table**: Dynamic source-to-topic mappings  
- **ExecutionHistory Table**: Schedule execution tracking
- **AnalyticsCache Table**: Recent performance metrics

### Azure Blob Storage for Logs
- **schedule-logs** container: Logic App execution logs
- **analytics-cache** container: Collection performance data

## Monitoring & Observability

### Logic App Metrics
- Execution frequency and duration
- Success/failure rates per topic
- Cost per execution and monthly totals
- Authentication success rates

### Collection Metrics
- Topics collected per day/week
- Content quality trends by topic
- Source discovery and success rates
- Cross-posting correlation analysis

### Alerting
- Failed Logic App executions
- Monthly cost threshold breaches
- Low content quality alerts
- Authentication failures

## Future Enhancements

### Machine Learning Integration
- **Topic Trend Prediction**: Predict optimal collection timing
- **Source Quality Scoring**: Automatically rank and weight sources
- **Content Demand Forecasting**: Adjust collection based on reader interest

### Multi-Platform Expansion
- **Bluesky Integration**: Extend scheduler to include Bluesky sources
- **Mastodon Integration**: Add federated social media collection
- **Web Scraping**: Include general web sources in scheduling

### Advanced Analytics
- **Content Performance Correlation**: Link scheduled collections to website traffic
- **ROI Analysis**: Calculate content value vs collection costs
- **Seasonal Optimization**: Adjust schedules based on topic seasonality

## Cost Estimates

### Logic App Costs (4-6 hour schedule)
- **Executions per month**: ~180-270 (4-6 topic collections every 4-6 hours)
- **Cost per execution**: ~$0.000025
- **Monthly cost**: ~$0.005-0.007 (well within free tier)

### Supporting Infrastructure
- **Azure Table Storage**: ~$1/month for configuration data
- **Additional Blob Storage**: ~$0.50/month for logs
- **Total additional cost**: ~$1.50/month

## Success Metrics

### Technical Success
- Logic App reliability > 99%
- Content collection success rate > 90%
- Authentication success rate > 99.9%
- Monthly costs < $2

### Business Success  
- Content quality improvement (measured by engagement)
- Source discovery rate (new valuable sources found)
- Content generation efficiency (topics to articles ratio)
- Cross-posting intelligence (content overlap detection)

## Next Steps

1. **Review and Approve Design**: Confirm approach aligns with vision
2. **Create GitHub Issues**: Break down implementation into trackable tasks
3. **Terraform Implementation**: Add Logic App resources to infrastructure
4. **MVP Development**: Start with basic topic-based scheduling
5. **Feedback Integration**: Connect scheduler to content analytics
6. **Optimization**: Implement adaptive scheduling and source discovery

# Topic Configuration Management

## Overview
The scheduler uses topic-based configuration to organize content collection from different sources. Each topic defines its own schedule, sources, collection criteria, and analytics tracking.

## Configuration Storage
- **Primary Storage**: Azure Key Vault secret named `scheduler-config`
- **Backup Storage**: Azure Table Storage for historical data and analytics
- **Format**: JSON structure with nested topic definitions

## Topic Configuration Schema

### Root Structure
```json
{
  "content_collector_url": "https://content-collector.azurecontainerapps.io",
  "content_processor_url": "https://content-processor.azurecontainerapps.io", 
  "initial_topics": {
    "topic_id": { ... topic definition ... }
  }
}
```

### Topic Definition Schema
```json
{
  "display_name": "Human-readable topic name",
  "schedule": {
    "frequency_hours": 4,           // How often to collect (hours)
    "priority": "high|medium|low",  // Topic priority for resource allocation
    "active_hours": "0-23"          // Hours when collection is active (UTC)
  },
  "sources": {
    "reddit": {
      "subreddits": ["subreddit1", "subreddit2"],
      "limit": 20,                  // Max posts per subreddit
      "sort": "hot|new|top|rising"  // Sort method
    },
    "rss": {
      "feeds": ["https://example.com/feed.xml"]  // Future: RSS feed URLs
    }
  },
  "criteria": {
    "min_score": 50,                // Minimum upvotes/score
    "min_comments": 10,             // Minimum comment count
    "include_keywords": ["AI", "tech"],  // Keywords to prioritize
    "exclude_keywords": ["meme"]    // Keywords to filter out
  },
  "analytics": {
    "last_run": "2025-09-09T10:00:00Z",  // Last collection timestamp
    "success_rate": 0.85,           // Success rate (0-1)
    "avg_quality_score": 7.2,       // Average content quality (1-10)
    "content_generated": 45         // Total content items generated
  }
}
```

## Predefined Topics

### Technology Topic
- **Focus**: General technology trends, AI, automation
- **Schedule**: Every 4 hours (high priority)
- **Sources**: r/technology, r/programming, r/MachineLearning, r/artificial
- **Criteria**: min_score: 50, min_comments: 10

### Programming Topic  
- **Focus**: Software development, frameworks, languages
- **Schedule**: Every 6 hours (medium priority)
- **Sources**: r/programming, r/webdev, r/javascript, r/python
- **Criteria**: min_score: 30, min_comments: 5

### Science Topic
- **Focus**: Scientific research, discoveries, future technology
- **Schedule**: Every 8 hours (medium priority)
- **Sources**: r/science, r/Futurology, r/datascience
- **Criteria**: min_score: 40, min_comments: 8

## Configuration Management

### Initial Setup
Use the provided script to initialize topics:
```bash
./scripts/scheduler/configure-topics.sh
```

This script:
- Creates the scheduler-config secret in Key Vault
- Initializes Azure Table Storage tables
- Sets up predefined topics with current Container App URLs
- Validates the configuration format

### Manual Configuration
To manually update topic configuration:

1. **Get current configuration**:
```bash
az keyvault secret show \
  --vault-name <key-vault-name> \
  --name scheduler-config \
  --query "value" -o tsv
```

2. **Update configuration**:
```bash
# Edit the JSON and save to file
az keyvault secret set \
  --vault-name <key-vault-name> \
  --name scheduler-config \
  --file updated-config.json
```

### Configuration Validation
The Logic App validates configuration on each run:
- JSON structure validation
- Required field presence
- URL accessibility
- Subreddit name format

## Analytics Integration

### Collection Metrics
Each topic tracks:
- **Success Rate**: Percentage of successful collections
- **Quality Score**: Average content quality from content-processor
- **Content Generated**: Total articles/posts generated
- **Source Performance**: Success rates per subreddit

### Performance Optimization
The scheduler automatically:
- Adjusts frequency based on success rates
- Prioritizes high-performing sources
- Reduces collection from failing sources
- Discovers new sources based on content overlap

## Topic Lifecycle Management

### Adding New Topics
1. Define topic configuration following the schema
2. Update the Key Vault secret with new topic
3. Test collection manually before scheduling
4. Monitor performance and adjust criteria

### Modifying Existing Topics
1. Update topic definition in Key Vault
2. Changes take effect on next Logic App run
3. Monitor analytics for impact of changes
4. Revert if performance degrades

### Removing Topics
1. Remove topic from Key Vault configuration
2. Archive historical data in Table Storage
3. Update documentation and monitoring

## Best Practices

### Topic Design
- **Specific Focus**: Keep topics focused on specific domains
- **Balanced Frequency**: Higher frequency for high-value topics
- **Quality Criteria**: Set appropriate thresholds for content quality
- **Diverse Sources**: Include multiple subreddits per topic

### Performance Monitoring
- **Weekly Reviews**: Check analytics for topic performance
- **Source Evaluation**: Identify high/low performing subreddits  
- **Frequency Tuning**: Adjust collection frequency based on content volume
- **Quality Tracking**: Monitor content generation success rates

### Troubleshooting

#### Common Issues
- **Authentication Failures**: Check managed identity permissions
- **Source Access Errors**: Verify subreddit names and accessibility
- **Low Content Quality**: Adjust criteria or source selection
- **High Costs**: Reduce frequency or limit collection size

#### Debugging
1. Check Logic App execution history in Azure Portal
2. Review execution logs in Azure Table Storage
3. Test individual topics manually
4. Validate configuration JSON format

## Security Considerations

### Access Control
- Key Vault access limited to Logic App managed identity
- Table Storage secured with RBAC
- Configuration changes logged and audited

### Data Protection
- No sensitive data stored in topic configuration
- Collection results stored securely in blob storage
- Analytics data anonymized and aggregated

## Future Enhancements

### Planned Features
- **Machine Learning**: Predictive scheduling based on content trends
- **Multi-Platform**: Bluesky, Mastodon, RSS feed integration
- **Dynamic Discovery**: Automatic source discovery and evaluation
- **Seasonal Optimization**: Time-based frequency adjustments

### Extensibility
- **Custom Sources**: Plugin architecture for new content sources
- **Advanced Criteria**: ML-based content quality scoring
- **Real-time Triggers**: Event-based collection triggers
- **Cross-topic Intelligence**: Content overlap detection and optimization

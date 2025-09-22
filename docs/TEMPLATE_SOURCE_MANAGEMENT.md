# 🎛️ Collection Template Source Management

This system provides easy enable/disable functionality for content sources in collection templates, replacing the previous cumbersome approach of manual JSON editing and file renaming.

## 🔄 **What Changed**

### Before (Cumbersome)
- Manual JSON editing to rename sources to `_disabled_*`
- File renaming like `sustainable-reddit.json` → `.disabled`
- Required knowledge of JSON structure
- Error-prone manual editing

### After (Easy!)
- Simple `enabled: true/false` flags in templates
- CLI tool for quick source management
- REST API endpoints for programmatic control
- Backward compatibility with legacy `_disabled_*` format

## 🛠️ **Usage Methods**

### 1. Command Line Tool

The `scripts/manage_templates.py` script provides easy template management:

```bash
# List all sources with status
python scripts/manage_templates.py --list

# Enable all Reddit sources (after cooldown period)
python scripts/manage_templates.py --enable reddit

# Disable all RSS sources
python scripts/manage_templates.py --disable rss

# Enable specific source by index
python scripts/manage_templates.py --enable-source 0

# Disable specific source by index  
python scripts/manage_templates.py --disable-source 2
```

### 2. REST API Endpoints

New `/templates` endpoints for programmatic management:

#### List Template Sources
```http
GET /templates/sources
```

Response:
```json
{
  "status": "success",
  "data": {
    "sources": [
      {
        "index": 0,
        "type": "reddit", 
        "enabled": false,
        "description": "Reddit sources temporarily disabled...",
        "config_summary": "46 subreddits, limit: 25"
      },
      // ...
    ],
    "enabled_count": 5,
    "disabled_count": 3
  }
}
```

#### Toggle Sources by Type
```http
POST /templates/sources/toggle-type
Content-Type: application/json

{
  "source_type": "reddit",
  "enabled": true
}
```

#### Toggle Specific Source
```http
POST /templates/sources/toggle-index
Content-Type: application/json

{
  "source_index": 0,
  "enabled": true  
}
```

### 3. Manual JSON Editing (Still Supported)

Templates now support clean `enabled` flags:

```json
{
  "sources": [
    {
      "type": "reddit",
      "enabled": false,
      "_comment": "Disabled during cooldown",
      "subreddits": ["technology", "programming"],
      "limit": 25
    },
    {
      "type": "rss", 
      "enabled": true,
      "websites": ["https://techcrunch.com/feed/"],
      "limit": 20
    }
  ]
}
```

## 🏗️ **Technical Implementation**

### Collection Processing Logic
- Template loading automatically filters out disabled sources
- Supports both `enabled: false` and legacy `_disabled_*` formats
- Backward compatible with existing templates

### Source Filtering Logic
```python
# Filter out disabled sources
enabled_sources = []
for source_def in template["sources"]:
    # Skip if explicitly disabled
    if source_def.get("enabled", True) is False:
        continue
    
    # Skip legacy _disabled_* format  
    if any(key.startswith("_disabled_") for key in source_def.keys()):
        continue
        
    enabled_sources.append(source_def)
```

### Template Structure
Templates maintain full configuration for disabled sources, making re-enabling instant:

```json
{
  "type": "reddit",
  "enabled": false,
  "_comment": "Will re-enable after cooldown", 
  "subreddits": ["technology", "programming", "MachineLearning"],
  "limit": 25,
  "criteria": {"min_score": 5, "time_filter": "day"}
}
```

## 📋 **Current Source Status**

After Reddit compliance fixes and cooldown implementation:

- **Reddit Sources**: 3 disabled (awaiting 24-48h cooldown)
- **RSS Sources**: 2 enabled (tech news feeds)  
- **Mastodon Sources**: 2 enabled
- **Web Sources**: 1 enabled

## 🔮 **Future Enhancements**

### Planned Features
1. **Source Scheduling**: Enable/disable sources on schedule
2. **Template Validation**: Real-time validation of template changes
3. **Source Analytics**: Track which sources provide best content
4. **Automatic Failover**: Disable problematic sources automatically
5. **Template Versioning**: Track changes to template configurations

### Example Scheduling
```json
{
  "type": "reddit",
  "enabled": true,
  "schedule": {
    "enable_after": "2025-01-22T10:00:00Z",
    "disable_during_peak": true
  }
}
```

## 🎯 **Benefits**

1. **User-Friendly**: No more manual JSON editing
2. **Safe**: Preserves source configurations when disabled
3. **Flexible**: Multiple management interfaces (CLI, API, manual)
4. **Backward Compatible**: Works with existing templates
5. **Instant**: Enable/disable without redeployment
6. **Scriptable**: Easy integration with automation tools

## 🚀 **Getting Started**

1. **List current sources**: `python scripts/manage_templates.py --list`
2. **Make changes**: Use CLI tool or API endpoints
3. **Verify**: Changes take effect on next collection run
4. **Monitor**: Check collection logs for source activity

The new system makes source management as easy as flipping a switch! 🎛️

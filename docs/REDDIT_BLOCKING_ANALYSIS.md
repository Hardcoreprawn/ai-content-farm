# Reddit API Blocking Analysis & Resolution Plan

## 🔍 Current Issue Summary

**Status**: Reddit is actively blocking our collection requests with HTTP 403 responses  
**Error Message**: "You've been blocked by network security. To continue, log in to your Reddit account or use your developer token"  
**Impact**: Complete blockage of Reddit content collection (0 items collected despite "success" status)

## 📊 Policy Analysis

### Reddit's Official Rate Limits & Rules

Based on [Reddit Data API Wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki):

#### ✅ **Current Compliance**
- **Rate Limit**: 100 QPM (Queries Per Minute) per OAuth client ID
- **Our Configuration**: 30 requests per 60-second window = 30 QPM ✅ Well under limit
- **User Agent Required**: ✅ We have user agent (though potentially problematic)

#### ❌ **Potential Violations**

1. **User Agent Format**: 
   - **Reddit Requirement**: `<platform>:<app ID>:<version string> (by /u/<reddit username>)`
   - **Our Current**: `"ai-content-farm-collector/1.0"`
   - **Missing**: Platform, app ID, username contact info

2. **Authentication Method**:
   - **Reddit Requirement**: "Clients must authenticate with a registered OAuth token"
   - **Our Current**: Using public JSON API (unauthenticated) AND PRAW (authenticated)
   - **Issue**: Mixed authentication patterns, possible credential problems

3. **Generic User Agent Blocking**:
   - Reddit blocks "many default User-Agents" and encourages "unique and descriptive user-agent strings"
   - Our agent may be too generic

## 🔧 Our Current Implementation Issues

### 1. **User Agent Problems**
```python
# Found in multiple files:
headers = {"User-Agent": "ai-content-farm-collector/1.0"}
```
**Issues:**
- Doesn't follow Reddit's required format
- No contact information 
- Too generic - likely flagged for blocking

### 2. **Mixed Authentication Strategy**
- **RedditPublicCollector**: Uses unauthenticated JSON API
- **RedditPRAWCollector**: Uses OAuth credentials
- **Factory Logic**: Falls back to public if credentials invalid
- **Problem**: Inconsistent auth can trigger security blocks

### 3. **Rate Limiting Configuration**
```python
reddit_params = StrategyParameters(
    max_requests_per_window=30,  # 30 requests per minute
    window_duration=60,          # Well under 100 QPM limit
    base_delay=2.0,             # Conservative delays
)
```
**Status**: Rate limiting is actually quite conservative and should be fine

### 4. **Azure Container IP Issues**
- Azure Container Apps may use IP ranges that Reddit has flagged
- No IP rotation or proxy mechanisms
- Possible geographic/cloud provider blocking

## 🚨 Root Cause Assessment

### **Primary Suspects** (Ranked by Likelihood)

1. **🔴 User Agent Violation** (95% likely)
   - Non-compliant format triggers automated blocking
   - Lacks required contact information
   - Reddit explicitly blocks generic agents

2. **🟡 Authentication Issues** (70% likely)
   - Mixed auth strategies confusing Reddit's systems
   - Possible credential validation problems
   - OAuth token issues

3. **🟡 Azure IP Blocking** (50% likely)
   - Cloud provider IP ranges commonly blocked
   - No user reputation associated with IPs

4. **🟢 Rate Limiting** (5% likely)
   - Our rates are well below Reddit's limits
   - But may have triggered historical blocks

## 🛠️ Resolution Strategy

### **Phase 1: User Agent Compliance** (Immediate - High Impact)

**Action**: Fix user agent to comply with Reddit requirements

**Implementation**:
```python
# New compliant user agent format
user_agent = "azure:ai-content-farm:v2.0.1 (by /u/hardcoreprawn)"
```

**Changes Required**:
- Update all Reddit collectors to use compliant format
- Include platform (azure), app ID, version, contact username
- Ensure consistency across PRAW and public API calls

### **Phase 2: Authentication Standardization** (Priority - Medium Impact)

**Action**: Consolidate to single authentication method

**Options**:
1. **OAuth Only** (Recommended)
   - Use PRAW with proper credentials for all requests
   - Better rate limits and legitimacy
   - Requires valid Reddit app registration

2. **Public API Only** 
   - Remove OAuth entirely, use only public endpoints
   - Simpler but more restricted

### **Phase 3: Advanced Blocking Mitigation** (If needed)

**IP/Infrastructure**:
- Consider user agent rotation (within compliant format)
- Implement request jittering to appear more human
- Add retry logic with exponential backoff for 403s

**Monitoring**:
- Enhanced logging of Reddit responses
- Track blocking patterns and recovery times
- Implement blocking detection and auto-adjustment

## 📋 Implementation Plan

### **Step 1: Fix User Agent** (30 minutes)
```bash
# Update these files:
- containers/content-collector/collectors/reddit.py (3 locations)
- containers/content-collector/collectors/mastodon.py (1 location)
- libs/config_base.py (default value)
```

### **Step 2: Test Authentication** (1 hour)
- Verify Reddit app credentials are valid
- Test OAuth flow independently
- Ensure Azure Key Vault secrets are correct

### **Step 3: Deploy & Monitor** (2 hours)
- Deploy updated container
- Monitor logs for 403 responses
- Test collection functionality

### **Step 4: Escalation Path** (If still blocked)
- Contact Reddit via their support form
- Request review of blocking (mention academic/personal use)
- Consider registering new Reddit app with proper credentials

## 🎯 Success Metrics

- **Immediate**: No more HTTP 403 responses from Reddit
- **Short-term**: Reddit collection count > 0 in API responses
- **Long-term**: Stable collection over 24+ hours without blocks

## 📞 Reddit Support Information

If technical fixes fail:
- **Contact Form**: [Reddit Developer Support](https://reddithelp.com/hc/en-us/requests/new?ticket_form_id=14868593862164)
- **Community**: r/redditdev for technical support
- **Terms Reference**: Developer Terms & Data API Terms compliance
- **Use Case**: Academic/personal content curation (non-commercial)

---

**Next Action**: Start with Phase 1 (User Agent fix) as it's the most likely cause and quickest to implement.

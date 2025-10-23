# Reddit OAuth Implementation TODO

## Context

Reddit's API policy changed in 2023 to require OAuth authentication for ALL API access, including read-only operations. The current `collect_reddit()` function uses unauthenticated public JSON endpoints which will be blocked by Reddit.

**Status**: Reddit collection disabled pending OAuth implementation  
**Deadline**: No rush - Mastodon sources working well for production

## Background

### Why OAuth is Required
- Reddit API policy (2023+): "Traffic not using OAuth or login credentials will be blocked"
- Rate limits: 100 QPM with OAuth vs blocked without
- Previous blocking incident: September 2025 (network-level ban for 24-48 hours)
- Reference: https://www.reddit.com/wiki/api

### What Needs to Happen
Reddit requires:
1. OAuth2 client credentials (client_id, client_secret)
2. Access token acquisition and automatic refresh
3. Proper User-Agent header format: `<platform>:<app ID>:<version> (by /u/<username>)`
4. Use of `https://oauth.reddit.com` endpoints (not www.reddit.com)

## Implementation Options

### Option 1: PRAW Library (Recommended)
**Pros**:
- ✅ Handles OAuth token management automatically
- ✅ Auto-refresh tokens when expired
- ✅ Proper User-Agent handling built-in
- ✅ Reddit API compliance by design
- ✅ We used this successfully before

**Cons**:
- ❌ Adds dependency (but lightweight)
- ❌ Less control over HTTP details

**Implementation**:
```python
import praw

async def collect_reddit_oauth(subreddits, **kwargs):
    """Reddit collection with PRAW OAuth."""
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )
    
    for subreddit_name in subreddits:
        subreddit = reddit.subreddit(subreddit_name)
        for post in subreddit.hot(limit=25):
            yield standardize_reddit_item(post)
```

### Option 2: Direct OAuth Implementation
**Pros**:
- ✅ Full control over HTTP requests
- ✅ Can maintain current async/await patterns
- ✅ No additional dependencies

**Cons**:
- ❌ Must implement token refresh logic
- ❌ More code to maintain
- ❌ Higher risk of API compliance issues

**Implementation**:
```python
async def get_reddit_oauth_token():
    """Acquire Reddit OAuth access token."""
    auth = aiohttp.BasicAuth(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
    data = {"grant_type": "client_credentials"}
    headers = {"User-Agent": REDDIT_USER_AGENT}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=auth,
            data=data,
            headers=headers
        ) as resp:
            token_data = await resp.json()
            return token_data["access_token"]

async def collect_reddit_oauth(subreddits, **kwargs):
    """Reddit collection with manual OAuth."""
    token = await get_reddit_oauth_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": REDDIT_USER_AGENT
    }
    
    for subreddit in subreddits:
        url = f"https://oauth.reddit.com/r/{subreddit}/hot"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                # Process posts...
```

## Recommended Approach

**Use PRAW (Option 1)** for initial implementation:
1. Proven library with Reddit API compliance
2. Handles token refresh automatically
3. We've used it successfully before (check git history)
4. Can always optimize later if needed

## Implementation Checklist

### Phase 1: Setup
- [ ] Review previous PRAW implementation in git history
- [ ] Verify Reddit OAuth credentials exist in Azure Key Vault
  - `REDDIT_CLIENT_ID`
  - `REDDIT_CLIENT_SECRET`
  - `REDDIT_USER_AGENT` (format: `azure:content-womble:v2.0.2 (by /u/hardcorepr4wn)`)
- [ ] Test credentials with Reddit API sandbox

### Phase 2: Implementation
- [ ] Add PRAW to `requirements.txt`
- [ ] Create `collect_reddit_oauth()` function
- [ ] Implement async wrapper for PRAW (it's not natively async)
- [ ] Add proper error handling (401, 403, 429 responses)
- [ ] Implement rate limit respect (100 QPM)

### Phase 3: Integration
- [ ] Update `collectors/collect.py` to use OAuth version
- [ ] Update `collectors/standardize.py` for PRAW objects
- [ ] Add configuration in collection templates
- [ ] Update tests (mock PRAW objects)

### Phase 4: Testing
- [ ] Test with single subreddit
- [ ] Test with multiple subreddits
- [ ] Test rate limit handling
- [ ] Test token refresh (long-running collection)
- [ ] Test error recovery (network issues, API errors)

### Phase 5: Deployment
- [ ] Enable Reddit in collection templates (start with 1-2 subreddits)
- [ ] Monitor for 24 hours
- [ ] Check for API blocks or rate limit issues
- [ ] Gradually expand to more subreddits

## Testing Strategy

```python
# Mock PRAW for unit tests
@pytest.fixture
def mock_reddit():
    """Mock PRAW Reddit instance."""
    reddit = Mock()
    subreddit = Mock()
    post = Mock()
    
    post.id = "abc123"
    post.title = "Test Post"
    post.selftext = "Test content"
    post.score = 100
    # ... etc
    
    subreddit.hot = Mock(return_value=[post])
    reddit.subreddit = Mock(return_value=subreddit)
    
    return reddit
```

## Resources

- Reddit API Documentation: https://www.reddit.com/wiki/api
- Reddit OAuth2 Guide: https://github.com/reddit-archive/reddit/wiki/OAuth2
- PRAW Documentation: https://praw.readthedocs.io/
- Reddit Developer Terms: https://www.redditinc.com/policies/developer-terms
- Previous implementation: `git log --grep="PRAW"`

## Notes

- Reddit requires compliance or they will ban at network level (we experienced this in September 2025)
- Always respect rate limits: 100 QPM with OAuth
- Update User-Agent version when making changes
- Reddit monitors for scraping behavior - be respectful
- Consider Reddit API terms about data retention (delete user data within 48 hours if deleted on Reddit)

## Timeline Estimate

- **Option 1 (PRAW)**: 4-6 hours
  - Setup: 1 hour
  - Implementation: 2 hours
  - Testing: 1-2 hours
  - Deployment/monitoring: 1 hour

- **Option 2 (Direct OAuth)**: 8-12 hours
  - Token management: 3-4 hours
  - Implementation: 3-4 hours
  - Testing: 2-3 hours
  - Deployment/monitoring: 1 hour

**Recommendation**: Start with PRAW, optimize later if needed.

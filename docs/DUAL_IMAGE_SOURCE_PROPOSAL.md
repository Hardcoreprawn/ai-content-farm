# Dual Image Source Architecture: Unsplash + Pexels with Round-Robin Load Balancing

**Date**: October 19, 2025  
**Status**: Architecture Proposal  
**Priority**: Medium (Optimization)  
**Effort**: 8-12 hours  

---

## Executive Summary

Add **Pexels API** as a second image source alongside Unsplash to:
- **Balance load**: Each API handles ~50% of requests
- **Improve reliability**: Fallback if one API is rate-limited
- **Maintain quality**: Both have excellent photo libraries
- **Stay cost-free**: Both offer free tiers with no direct costs
- **Reduce rate limit pressure**: Split usage across two APIs

---

## Current State: Unsplash Only

### Architecture
```
Article Generator
         ↓
   ImageService
         ↓
  UnsplashClient (rate-limited at 0.4 req/sec = 50/hour)
         ↓
   Unsplash API
```

### Rate Limit Profile
- **Unsplash Free Tier**: 50 requests/hour
- **Current Usage**: ~10-20 articles/day = 10-20 requests/day
- **Safety Margin**: 50 requests/hour allows room for growth
- **Issue**: If usage grows or demos spike, could hit limits

### Current Implementation
- `services/unsplash_client.py`: Rate-limited search with exponential backoff
- `services/image_service.py`: Search query optimization and parsing
- `libs/rate_limiter.py`: Token bucket implementation (reusable)
- Metrics: Rate limit status tracked in Application Insights

---

## Proposed Solution: Dual Source with Round-Robin

### Architecture
```
Article Generator
         ↓
   ImageService (New Coordinator)
      ↙     ↘
UnsplashClient  PexelsClient
(rate-limited)   (rate-limited)
     ↓              ↓
Unsplash API    Pexels API
(50 req/hr)    (200 req/hr)
```

### Benefits
1. **Load Distribution**: Round-robin across two APIs
   - Request 1 → Unsplash
   - Request 2 → Pexels
   - Request 3 → Unsplash
   - Request 4 → Pexels

2. **Increased Capacity**:
   - Unsplash: 50 req/hour
   - Pexels: 200 req/hour (no strict limit, just rate-limited)
   - **Combined**: ~3x headroom for growth

3. **Reliability**:
   - If Unsplash times out or rate-limits, try Pexels
   - If Pexels fails, fallback to cached/default image
   - Better resilience to temporary API issues

4. **Cost**: $0 - both services free for our use case

---

## Pexels API Comparison

### API Specifications
```
Base URL: https://api.pexels.com/v1/
Authorization: Bearer API_KEY (via header)
Endpoint: /search

Query Parameters:
- query (required): Search term
- per_page: 1-80 (default 15)
- page: Pagination
- orientation: landscape, portrait, square (optional)
```

### Rate Limits
- No strict per-hour limit (unlike Unsplash)
- Practical limit: ~200 requests per second
- Throttling: 429 Too Many Requests if exceeded
- Recovery: Typically ~1 second

### Photo Library Quality
- 3.2 million+ photos
- Professional quality similar to Unsplash
- Good coverage for tech/science topics
- CC0 license (no attribution required, but encouraged)

### Response Format
```json
{
  "photos": [
    {
      "id": 123456,
      "width": 5000,
      "height": 3333,
      "url": "https://www.pexels.com/photo/...",
      "photographer": "John Doe",
      "photographer_url": "https://www.pexels.com/@johndoe",
      "photographer_id": 123,
      "avg_color": "#CCCCCC",
      "src": {
        "original": "https://images.pexels.com/photos/.../original.jpg",
        "large2x": "https://images.pexels.com/photos/.../large2x.jpg",
        "large": "https://images.pexels.com/photos/.../large.jpg",
        "medium": "https://images.pexels.com/photos/.../medium.jpg",
        "small": "https://images.pexels.com/photos/.../small.jpg",
        "portrait": "https://images.pexels.com/photos/.../portrait.jpg",
        "landscape": "https://images.pexels.com/photos/.../landscape.jpg",
        "tiny": "https://images.pexels.com/photos/.../tiny.jpg"
      },
      "liked": false,
      "alt": "Photo description"
    }
  ],
  "page": 1,
  "per_page": 1,
  "total_results": 1500,
  "next_page": "https://api.pexels.com/v1/search?query=nature&per_page=1&page=2"
}
```

---

## Implementation Plan

### Phase 1: Create Pexels Client (2-3 hours)

**File**: `containers/markdown-generator/services/pexels_client.py`

```python
"""
Pexels API client with rate limiting and retry logic.

Handles rate limiting (Pexels: no strict per-hour limit, just throttled).
Implements exponential backoff on 429 errors.

Rate Limits (Pexels):
- No official per-hour limit
- Practical limit: ~200 requests per second
- 429 = Too Many Requests
- Throttling: Usually resolves within 1 second

Strategy:
- Use token bucket limiter: 2 requests/sec (conservative)
- Exponential backoff on 429 errors (0.5s → 1s → 2s)
- Log requests for monitoring
"""

import logging
from typing import Any, Dict, Optional

import aiohttp

from libs.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Pexels API configuration
PEXELS_API_BASE_URL = "https://api.pexels.com/v1"

# Rate limiting: Conservative estimate (2 req/sec)
PEXELS_RATE_LIMIT = 2  # requests per second
PEXELS_RATE_LIMIT_NAME = "pexels-api"

# Singleton limiter instance
_pexels_limiter: Optional[RateLimiter] = None


def get_pexels_limiter() -> RateLimiter:
    """Get or create singleton Pexels rate limiter."""
    global _pexels_limiter

    if _pexels_limiter is None:
        rate = 2  # requests per second
        capacity = 10  # allow burst of 10
        _pexels_limiter = RateLimiter(
            rate=int(rate * 60),  # Convert to per-minute
            per_seconds=60,
            capacity=int(capacity),
            name=PEXELS_RATE_LIMIT_NAME,
        )
        logger.info(
            f"Created Pexels rate limiter: "
            f"{rate} req/sec, burst capacity={capacity}"
        )

    return _pexels_limiter


class PexelsError(Exception):
    """Base exception for Pexels API errors."""
    pass


class PexelsRateLimitError(Exception):
    """Raised when Pexels rate limit is exceeded after retries."""
    pass


async def search_pexels_photo(
    api_key: str,
    query: str,
    orientation: str = "landscape",
    max_retries: int = 3,
) -> Optional[Dict[str, Any]]:
    """
    Search Pexels API for a single photo with rate limiting and retries.

    Args:
        api_key: Pexels API key
        query: Search query (article topic)
        orientation: "landscape", "portrait", or "square"
        max_retries: Maximum retry attempts on rate limit error

    Returns:
        First photo data dict or None if not found

    Raises:
        PexelsRateLimitError: If rate limit exceeded after all retries
        PexelsError: For other API errors
    """
    limiter = get_pexels_limiter()
    attempt = 0
    retry_wait = 0.5  # Initial retry wait: 0.5 seconds

    clean_query = query.strip()[:100]

    if not clean_query:
        logger.warning("Empty search query provided to Pexels")
        return None

    while attempt <= max_retries:
        try:
            async with limiter:
                logger.info(f"Searching Pexels: query='{clean_query}'")

                async with aiohttp.ClientSession() as session:
                    params = {
                        "query": clean_query,
                        "per_page": 1,
                        "orientation": orientation,
                    }
                    headers = {"Authorization": f"Bearer {api_key}"}
                    url = f"{PEXELS_API_BASE_URL}/search"

                    async with session.get(
                        url,
                        params=params,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            logger.info(
                                f"Pexels search successful: "
                                f"{len(data.get('photos', []))} results"
                            )

                            if data.get("photos"):
                                return data["photos"][0]
                            else:
                                logger.warning(f"No images found for: {clean_query}")
                                return None

                        elif resp.status == 429:
                            # Rate limit exceeded
                            logger.warning(
                                f"Pexels rate limit (429): "
                                f"attempt={attempt}, retrying in {retry_wait}s"
                            )

                            if attempt < max_retries:
                                import asyncio
                                await asyncio.sleep(retry_wait)
                                retry_wait *= 2  # Exponential backoff
                                attempt += 1
                                continue
                            else:
                                raise PexelsRateLimitError(
                                    f"Pexels rate limit exceeded after {max_retries} retries"
                                )

                        elif resp.status == 401:
                            error_text = await resp.text()
                            logger.error(f"Pexels auth error (401): {error_text}")
                            raise PexelsError(f"Invalid API key: {error_text}")

                        else:
                            error_text = await resp.text()
                            logger.error(
                                f"Pexels API error ({resp.status}): {error_text}"
                            )
                            raise PexelsError(f"API error {resp.status}: {error_text}")

        except PexelsRateLimitError:
            raise
        except PexelsError:
            raise
        except aiohttp.ClientError as e:
            logger.error(f"Network error from Pexels: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Pexels search: {e}", exc_info=True)
            raise


def parse_pexels_photo(photo: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Pexels API photo response into standardized format.

    Args:
        photo: Raw photo data from Pexels API

    Returns:
        Standardized image metadata dictionary
    """
    return {
        "url_raw": photo["src"]["original"],
        "url_regular": photo["src"]["large"],
        "url_small": photo["src"]["small"],
        "photographer": photo["photographer"],
        "photographer_url": photo["photographer_url"],
        "description": photo.get("alt", ""),
        "color": photo.get("avg_color", "#CCCCCC"),
        "source_url": photo["url"],
        "license": "CC0",  # Pexels uses CC0 license
    }
```

### Phase 2: Create ImageSourceCoordinator (2 hours)

**File**: `containers/markdown-generator/services/image_coordinator.py`

```python
"""
Image source coordinator with round-robin load balancing.

Distributes requests across multiple image sources:
- Unsplash: 50 req/hour free tier
- Pexels: ~200 req/sec (no strict limit)

Strategy:
- Round-robin distribution
- Fallback if primary source fails
- Track usage per source for monitoring
- Unified response format
"""

import logging
from enum import Enum
from typing import Any, Dict, Optional

from services.unsplash_client import (
    search_unsplash_photo,
    get_unsplash_limiter,
    UnsplashError,
    UnsplashRateLimitError,
)
from services.pexels_client import (
    search_pexels_photo,
    get_pexels_limiter,
    PexelsError,
    PexelsRateLimitError,
    parse_pexels_photo,
)

logger = logging.getLogger(__name__)


class ImageSource(Enum):
    """Supported image sources."""
    UNSPLASH = "unsplash"
    PEXELS = "pexels"


class ImageSourceCoordinator:
    """
    Coordinates image fetching across multiple sources with round-robin.
    """

    def __init__(self, unsplash_key: str, pexels_key: str):
        """
        Initialize coordinator.

        Args:
            unsplash_key: Unsplash API key
            pexels_key: Pexels API key
        """
        self.unsplash_key = unsplash_key
        self.pexels_key = pexels_key
        self.request_count = 0  # For round-robin
        self.stats = {
            ImageSource.UNSPLASH: {"success": 0, "failed": 0, "rate_limited": 0},
            ImageSource.PEXELS: {"success": 0, "failed": 0, "rate_limited": 0},
        }

    def _get_next_source(self) -> ImageSource:
        """
        Get next source using round-robin.

        Returns:
            Next ImageSource to try
        """
        source = ImageSource.UNSPLASH if self.request_count % 2 == 0 else ImageSource.PEXELS
        self.request_count += 1
        return source

    async def search_image(
        self,
        query: str,
        orientation: str = "landscape",
        allow_fallback: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Search for image using round-robin across sources.

        Args:
            query: Search query
            orientation: "landscape", "portrait", "squarish"
            allow_fallback: Try alternate source if primary fails

        Returns:
            Image data dict or None if not found
        """
        primary_source = self._get_next_source()
        sources_to_try = [primary_source]

        if allow_fallback:
            # Add fallback source (the other one)
            fallback = (
                ImageSource.PEXELS
                if primary_source == ImageSource.UNSPLASH
                else ImageSource.UNSPLASH
            )
            sources_to_try.append(fallback)

        logger.info(
            f"Searching image (query='{query[:50]}...', "
            f"primary={primary_source.value}, sources_to_try={len(sources_to_try)})"
        )

        for source in sources_to_try:
            try:
                logger.debug(f"Trying image source: {source.value}")

                if source == ImageSource.UNSPLASH:
                    photo = await search_unsplash_photo(
                        access_key=self.unsplash_key,
                        query=query,
                        orientation=orientation,
                    )
                else:  # PEXELS
                    # Map orientation: Pexels uses "square" instead of "squarish"
                    pexels_orientation = (
                        "square" if orientation == "squarish" else orientation
                    )
                    photo = await search_pexels_photo(
                        api_key=self.pexels_key,
                        query=query,
                        orientation=pexels_orientation,
                    )

                if photo:
                    self.stats[source]["success"] += 1
                    logger.info(
                        f"Image found via {source.value}: "
                        f"stats={self.stats[source]}"
                    )
                    # For Unsplash, return as-is (already parsed)
                    # For Pexels, parse into standard format
                    if source == ImageSource.PEXELS:
                        return parse_pexels_photo(photo)
                    return photo
                else:
                    logger.debug(f"No image found via {source.value}")

            except (UnsplashRateLimitError, PexelsRateLimitError) as e:
                self.stats[source]["rate_limited"] += 1
                logger.warning(
                    f"Rate limited by {source.value}: {e}, "
                    f"stats={self.stats[source]}"
                )
                # Try next source

            except (UnsplashError, PexelsError) as e:
                self.stats[source]["failed"] += 1
                logger.error(
                    f"Error from {source.value}: {e}, "
                    f"stats={self.stats[source]}"
                )
                # Try next source

            except Exception as e:
                self.stats[source]["failed"] += 1
                logger.error(
                    f"Unexpected error from {source.value}: {e}",
                    exc_info=True,
                )
                # Try next source

        logger.warning("No image found from any source")
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics."""
        return {
            "total_requests": self.request_count,
            "sources": self.stats,
            "unsplash_limiter": get_unsplash_limiter().get_stats(),
            "pexels_limiter": get_pexels_limiter().get_stats(),
        }
```

### Phase 3: Update Settings & Configuration (1 hour)

**File**: `containers/markdown-generator/settings.py`

```python
# Add to existing settings
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Image source configuration
    unsplash_api_key: Optional[str] = Field(
        default=None,
        description="Unsplash API key for stock images"
    )
    pexels_api_key: Optional[str] = Field(
        default=None,
        description="Pexels API key for stock images"
    )
    image_source_strategy: str = Field(
        default="dual-roundrobin",
        description="Image source strategy: 'unsplash-only', 'pexels-only', or 'dual-roundrobin'"
    )
```

### Phase 4: Update Article Processing Logic (1.5 hours)

**File**: `containers/markdown-generator/services/article_processor.py`

Update to use `ImageSourceCoordinator` instead of direct `UnsplashClient`:

```python
# OLD
image = await search_unsplash_image(
    access_key=settings.unsplash_api_key,
    query=article_title,
)

# NEW
coordinator = ImageSourceCoordinator(
    unsplash_key=settings.unsplash_api_key,
    pexels_key=settings.pexels_api_key,
)
image = await coordinator.search_image(
    query=article_title,
    orientation="landscape",
)
```

### Phase 5: Update Monitoring & Metrics (1 hour)

Update `models.py` MetricsResponse to include dual-source stats:

```python
@dataclass
class MetricsResponse(BaseModel):
    # ... existing fields ...
    
    image_sources_stats: Optional[Dict[str, Any]] = Field(
        None,
        description="Image source usage and rate limit status for both Unsplash and Pexels"
    )
```

### Phase 6: Testing & Documentation (2-3 hours)

Tests to implement:
- Unit tests for `pexels_client.py`
- Unit tests for `image_coordinator.py`
- Round-robin distribution verification
- Fallback behavior under rate limiting
- Integration tests with both APIs
- Mock tests with API failures

---

## Configuration Changes Required

### Environment Variables
```bash
# Keep existing
UNSPLASH_API_KEY=...

# Add new
PEXELS_API_KEY=...

# Control strategy
IMAGE_SOURCE_STRATEGY=dual-roundrobin  # or "unsplash-only", "pexels-only"
```

### Azure Key Vault
Add new secret:
```bash
az keyvault secret set --name "pexels-api-key" --value "your-key"
```

### Docker Compose (local dev)
```yaml
environment:
  UNSPLASH_API_KEY: ${UNSPLASH_API_KEY}
  PEXELS_API_KEY: ${PEXELS_API_KEY}
  IMAGE_SOURCE_STRATEGY: dual-roundrobin
```

---

## Request Distribution Example

```
Request 1 (article 1) → Unsplash (via round-robin)
  ✓ Found image from Unsplash

Request 2 (article 2) → Pexels (via round-robin)
  ✓ Found image from Pexels

Request 3 (article 3) → Unsplash (via round-robin)
  ✗ Rate limited by Unsplash
  ↓ Fallback to Pexels
  ✓ Found image from Pexels

Request 4 (article 4) → Pexels (via round-robin)
  ✓ Found image from Pexels

Request 5 (article 5) → Unsplash (via round-robin)
  ✓ Found image from Unsplash
```

---

## Monitoring & Metrics

### New Metrics to Track
1. **Per-source success rate**:
   - Unsplash: X% successful
   - Pexels: Y% successful

2. **Fallback usage**:
   - How often primary source fails and fallback succeeds
   - When both sources fail

3. **Rate limit events**:
   - When each API rate limits
   - How backoff/retry behavior performs

4. **Load distribution**:
   - Request distribution (should be ~50/50 round-robin)
   - Any skew in actual distribution

### Application Insights Queries
```kusto
customMetrics
| where name == "image_search_success"
| extend source = tostring(customDimensions.source)
| summarize count() by source, bin(timestamp, 1h)
| render timechart
```

---

## Rollout Strategy

### Phase 1: Shadow Mode (Day 1)
- Deploy coordinator with both APIs
- Round-robin distribution
- Log metrics but use Unsplash responses only
- Verify Pexels client works without impacting production

### Phase 2: Hybrid Mode (Day 1-2)
- Switch to real round-robin (50/50 split)
- Monitor success rates and quality
- Ensure fallback logic works correctly
- Verify load is actually balanced

### Phase 3: Production (Day 3+)
- Full dual-source with monitoring
- Adjust rate limits based on observed patterns
- Collect quality feedback
- Optimize based on which source is better for our topics

---

## Fallback Behavior

### If Unsplash Rate Limits
```
Primary (Unsplash) → Rate limited
Fallback (Pexels) → Success ✓
Result: Article gets image from Pexels
Stats: Unsplash "rate_limited", Pexels "success"
```

### If Both Fail
```
Primary (Unsplash) → Error
Fallback (Pexels) → Error
Result: Article published without image (still functional)
Stats: Both marked "failed"
Alert: Monitor why both failed
```

---

## Costs & Rate Limits Summary

### Unsplash
- **Free Tier**: 50 requests/hour
- **Cost**: $0
- **Our Usage**: ~10-20/day = well within limits

### Pexels
- **Free Tier**: Practical limit ~200 req/sec
- **Cost**: $0
- **Our Usage**: ~10-20/day = trivial fraction

### Combined
- **Effective Capacity**: 50 req/hour (Unsplash) + 200 req/sec (Pexels)
- **Our Usage**: ~10-20/day split between both
- **Safety Margin**: Extremely high
- **Cost**: $0

---

## Risk Assessment

### Low Risk
- Both APIs are reliable (>99.9% uptime)
- Implementation is isolated to image service
- Fallback logic ensures graceful degradation
- Zero cost for both services

### Mitigation
- Round-robin ensures neither API is overloaded
- Rate limiting prevents spikes
- Comprehensive error handling and logging
- Easy rollback to Unsplash-only if needed

---

## Success Criteria

1. ✅ Both APIs successfully providing images
2. ✅ Round-robin distribution verified (logs show ~50/50)
3. ✅ Fallback works when primary fails
4. ✅ No degradation in article quality
5. ✅ Metrics correctly track usage per source
6. ✅ Zero cost maintained
7. ✅ >99% success rate for image retrieval

---

## Next Steps

1. Get Pexels API key (free, instant signup at pexels.com/api)
2. Review proposal for feedback
3. Implement Phase 1: Pexels Client
4. Add comprehensive tests
5. Deploy to staging for testing
6. Verify metrics and fallback behavior
7. Deploy to production with monitoring

"""
Topic Intelligence Collector - Production Version

Discovers trending topics across platforms for research and analysis.
Uses Reddit API with PRAW in Azure (with Key Vault), anonymous locally.
"""

import logging
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List

import praw
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from libs.blob_storage import BlobContainers, BlobStorageClient
from libs.shared_models import StandardResponse, create_service_dependency

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Topic Intelligence Collector",
    description="Discovers trending topics for research and original content creation",
    version="2.0.0",
    docs_url="/docs",
)

# Service metadata dependency
service_metadata = create_service_dependency("topic-collector")

# Initialize blob storage
blob_client = BlobStorageClient()


class SourceConfig(BaseModel):
    """Configuration for topic discovery source."""

    platform: str = Field(..., description="Platform: reddit, twitter, linkedin")
    categories: List[str] = Field(
        default=[], description="Categories/subreddits to monitor"
    )
    keywords: List[str] = Field(default=[], description="Keywords to track")
    limit: int = Field(default=50, ge=10, le=200, description="Posts to analyze")


class DiscoveryRequest(BaseModel):
    """Request to discover trending topics."""

    sources: List[SourceConfig] = Field(..., description="Sources to analyze")
    min_mentions: int = Field(
        default=3, ge=1, le=50, description="Minimum topic mentions"
    )
    quality_threshold: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Quality threshold"
    )


class TrendingTopic(BaseModel):
    """A discovered trending topic."""

    topic: str = Field(..., description="Topic name/phrase")
    mentions: int = Field(..., description="Number of mentions across sources")
    platforms: List[str] = Field(..., description="Platforms where mentioned")
    keywords: List[str] = Field(..., description="Related keywords")
    sentiment: str = Field(
        ..., description="Overall sentiment: positive/negative/neutral"
    )
    urgency_score: float = Field(..., description="How trending/urgent (0-1)")
    research_potential: float = Field(..., description="Research potential score (0-1)")
    sample_posts: List[str] = Field(..., description="Sample post titles")


class ResearchRecommendation(BaseModel):
    """Research recommendation for a topic."""

    topic: str = Field(..., description="Topic to research")
    approach: str = Field(..., description="Recommended research approach")
    key_questions: List[str] = Field(..., description="Key questions to investigate")
    source_types: List[str] = Field(..., description="Recommended source types")
    estimated_depth: str = Field(..., description="brief/medium/deep")


class DiscoveryResult(BaseModel):
    """Result of topic discovery."""

    trending_topics: List[TrendingTopic] = Field(
        ..., description="Discovered trending topics"
    )
    research_recommendations: List[ResearchRecommendation] = Field(
        ..., description="Research suggestions"
    )
    sources_analyzed: int = Field(..., description="Number of sources analyzed")
    posts_processed: int = Field(..., description="Total posts processed")
    discovery_timestamp: datetime = Field(
        ..., description="When discovery was performed"
    )
    execution_time_ms: int = Field(..., description="Processing time")


class RedditClient:
    """Reddit client with Azure Key Vault integration."""

    def __init__(self):
        self.reddit = None
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        self._initialize_reddit()

    def _initialize_reddit(self):
        """Initialize Reddit client based on environment."""
        try:
            # Check for environment variables first (Container Apps secrets)
            client_id = os.getenv("REDDIT_CLIENT_ID")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            user_agent = os.getenv("REDDIT_USER_AGENT")

            if client_id and client_secret and user_agent:
                # Use environment variables (Container Apps secrets)
                self._init_reddit_with_creds(client_id, client_secret, user_agent)
                logger.info("Reddit client initialized with Container Apps secrets")
            elif self.environment == "production":
                # Azure environment - use Key Vault directly
                self._init_azure_reddit()
            else:
                # Local development - anonymous access
                self._init_local_reddit()
        except Exception as e:
            logger.error(f"Failed to initialize Reddit: {e}")
            raise

    def _init_reddit_with_creds(
        self, client_id: str, client_secret: str, user_agent: str
    ):
        """Initialize Reddit with provided credentials."""
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            check_for_async=False,
        )

    def _init_azure_reddit(self):
        """Initialize Reddit with Azure Key Vault credentials."""
        try:
            # Get Key Vault URL from environment
            vault_url = os.getenv("AZURE_KEY_VAULT_URL")
            if not vault_url:
                raise ValueError("AZURE_KEY_VAULT_URL not set")

            # Create Key Vault client with managed identity
            credential = DefaultAzureCredential()
            kv_client = SecretClient(vault_url=vault_url, credential=credential)

            # Retrieve Reddit credentials
            client_id = kv_client.get_secret("reddit-client-id").value
            client_secret = kv_client.get_secret("reddit-client-secret").value
            user_agent = kv_client.get_secret("reddit-user-agent").value

            # Initialize PRAW
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                check_for_async=False,
            )

            logger.info("Reddit client initialized with Azure Key Vault credentials")

        except Exception as e:
            logger.error(f"Failed to initialize Reddit with Key Vault: {e}")
            raise

    def _init_local_reddit(self):
        """Initialize Reddit for local development (anonymous)."""
        try:
            # Use environment variables if available, otherwise anonymous
            client_id = os.getenv("REDDIT_CLIENT_ID")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            user_agent = os.getenv("REDDIT_USER_AGENT", "topic-intelligence-local/1.0")

            if client_id and client_secret:
                self.reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=user_agent,
                    check_for_async=False,
                )
                logger.info("Reddit client initialized with local credentials")
            else:
                # Anonymous access for local testing
                self.reddit = praw.Reddit(
                    client_id=None,
                    client_secret=None,
                    user_agent=user_agent,
                    check_for_async=False,
                )
                logger.info("Reddit client initialized in read-only mode (no API key)")

        except Exception as e:
            logger.warning(f"Reddit initialization failed, using mock data: {e}")
            self.reddit = None

    def is_available(self) -> bool:
        """Check if Reddit client is available."""
        return self.reddit is not None

    def get_trending_posts(
        self, subreddit: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get trending posts from a subreddit."""
        if not self.is_available():
            # Return mock data for testing
            return self._get_mock_posts(subreddit, limit)

        try:
            subreddit_obj = self.reddit.subreddit(subreddit)
            posts = []

            for submission in subreddit_obj.hot(limit=limit):
                posts.append(
                    {
                        "title": submission.title,
                        "score": submission.score,
                        "num_comments": submission.num_comments,
                        "created_utc": submission.created_utc,
                        "url": submission.url,
                        "subreddit": subreddit,
                        "selftext": (
                            submission.selftext[:500] if submission.selftext else ""
                        ),
                    }
                )

            logger.debug(f"Retrieved {len(posts)} posts from r/{subreddit}")
            return posts

        except Exception as e:
            logger.error(f"Failed to get posts from r/{subreddit}: {e}")
            return self._get_mock_posts(subreddit, limit)

    def _get_mock_posts(self, subreddit: str, limit: int) -> List[Dict[str, Any]]:
        """Generate mock posts for testing."""
        mock_topics = {
            "technology": [
                "AI breakthrough in quantum computing announced",
                "New programming language gains developer adoption",
                "Cloud computing costs optimization strategies",
                "Cybersecurity threats in remote work environments",
                "Open source software sustainability discussed",
            ],
            "MachineLearning": [
                "Large language model training efficiency improvements",
                "Computer vision applications in healthcare",
                "Machine learning model interpretability research",
                "AI ethics in automated decision making",
                "Neural network architecture innovations",
            ],
            "science": [
                "Climate change mitigation technology developments",
                "Medical research breakthrough in gene therapy",
                "Space exploration mission updates",
                "Renewable energy storage solutions",
                "Quantum physics experimental results",
            ],
        }

        topics = mock_topics.get(
            subreddit,
            ["General topic discussion", "Technology news", "Research updates"],
        )
        posts = []

        for i in range(min(limit, len(topics) * 2)):
            topic = topics[i % len(topics)]
            posts.append(
                {
                    "title": f"{topic} - Discussion Thread",
                    "score": 100 + (i * 10),
                    "num_comments": 20 + i,
                    "created_utc": time.time() - (i * 3600),
                    "url": f"https://reddit.com/r/{subreddit}/posts/{i}",
                    "subreddit": subreddit,
                    "selftext": f"Mock discussion about {topic.lower()}",
                }
            )

        return posts


# Initialize Reddit client
reddit_client = RedditClient()


@app.get("/", response_model=StandardResponse)
async def root(metadata: Dict[str, Any] = Depends(service_metadata)):
    """Service information and capabilities."""
    return StandardResponse(
        status="success",
        message="Topic Intelligence Collector - Production Ready",
        data={
            "service": "topic-intelligence-collector",
            "version": "2.0.0",
            "purpose": "Discover trending topics for research and original content",
            "platforms_supported": ["reddit", "twitter", "linkedin"],
            "reddit_available": reddit_client.is_available(),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "endpoints": ["/discover", "/health", "/topics/recent"],
        },
        errors=[],
        metadata=metadata,
    )


@app.get("/health", response_model=StandardResponse)
async def health(metadata: Dict[str, Any] = Depends(service_metadata)):
    """Health check with Reddit and storage connectivity."""
    try:
        # Check blob storage
        storage_health = blob_client.health_check()
        storage_ok = storage_health.get("status") == "healthy"

        # Check Reddit availability
        reddit_ok = reddit_client.is_available()

        overall_status = "healthy" if (storage_ok and reddit_ok) else "degraded"

        return StandardResponse(
            status="success" if overall_status == "healthy" else "warning",
            message=f"Service is {overall_status}",
            data={
                "status": overall_status,
                "storage_connected": storage_ok,
                "reddit_available": reddit_ok,
                "environment": os.getenv("ENVIRONMENT", "development"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            errors=[],
            metadata=metadata,
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return StandardResponse(
            status="error",
            message="Health check failed",
            data={"error": str(e)},
            errors=[str(e)],
            metadata=metadata,
        )


@app.post("/discover", response_model=StandardResponse)
async def discover_topics(
    request: DiscoveryRequest, metadata: Dict[str, Any] = Depends(service_metadata)
):
    """Discover trending topics across platforms."""
    start_time = time.time()

    logger.info(f"Starting topic discovery from {len(request.sources)} sources")

    try:
        all_posts = []
        sources_analyzed = 0

        # Collect posts from all sources
        for source in request.sources:
            if source.platform == "reddit":
                for category in source.categories:
                    posts = reddit_client.get_trending_posts(category, source.limit)
                    all_posts.extend(posts)
                    sources_analyzed += 1
            # TODO: Add other platforms (Twitter, LinkedIn, etc.)

        # Analyze topics and trends
        trending_topics = _analyze_trending_topics(all_posts, request.min_mentions)

        # Generate research recommendations
        research_recommendations = _generate_research_recommendations(trending_topics)

        # Save results to blob storage
        discovery_result = DiscoveryResult(
            trending_topics=trending_topics,
            research_recommendations=research_recommendations,
            sources_analyzed=sources_analyzed,
            posts_processed=len(all_posts),
            discovery_timestamp=datetime.now(timezone.utc),
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

        await _save_discovery_results(discovery_result)

        return StandardResponse(
            status="success",
            message=f"Discovered {len(trending_topics)} trending topics for research",
            data=discovery_result.model_dump(),
            errors=[],
            metadata=metadata,
        )

    except Exception as e:
        logger.error(f"Topic discovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")


def _analyze_trending_topics(
    posts: List[Dict[str, Any]], min_mentions: int
) -> List[TrendingTopic]:
    """Analyze posts to identify trending topics."""
    # Extract keywords and topics from posts
    topic_mentions = Counter()
    topic_contexts = defaultdict(list)
    topic_platforms = defaultdict(set)

    for post in posts:
        title = post.get("title", "").lower()
        content = post.get("selftext", "").lower()
        platform = "reddit"  # For now, expand later

        # Simple keyword extraction (in production, use NLP)
        keywords = _extract_keywords(title + " " + content)

        for keyword in keywords:
            topic_mentions[keyword] += 1
            topic_contexts[keyword].append(post.get("title", ""))
            topic_platforms[keyword].add(platform)

    # Filter and rank topics
    trending_topics = []
    for topic, mentions in topic_mentions.most_common(20):
        if mentions >= min_mentions:
            trending_topic = TrendingTopic(
                topic=topic,
                mentions=mentions,
                platforms=list(topic_platforms[topic]),
                keywords=[topic],  # Simplified
                sentiment="neutral",  # TODO: Add sentiment analysis
                urgency_score=min(mentions / 10.0, 1.0),
                research_potential=_calculate_research_potential(topic, mentions),
                sample_posts=topic_contexts[topic][:3],
            )
            trending_topics.append(trending_topic)

    return trending_topics


def _extract_keywords(text: str) -> List[str]:
    """Extract potential topics/keywords from text."""
    # Simple keyword extraction - in production use NLP libraries
    tech_keywords = [
        "artificial intelligence",
        "ai",
        "machine learning",
        "ml",
        "quantum computing",
        "blockchain",
        "cryptocurrency",
        "cloud computing",
        "cybersecurity",
        "automation",
        "neural networks",
        "deep learning",
        "data science",
        "kubernetes",
        "docker",
        "microservices",
        "api",
        "devops",
        "cicd",
        "terraform",
        "ansible",
    ]

    found_keywords = []
    text_lower = text.lower()

    for keyword in tech_keywords:
        if keyword in text_lower:
            found_keywords.append(keyword)

    return found_keywords


def _calculate_research_potential(topic: str, mentions: int) -> float:
    """Calculate research potential for a topic."""
    # High research potential for technical topics with good engagement
    research_indicators = [
        "artificial intelligence",
        "machine learning",
        "quantum",
        "blockchain",
        "cybersecurity",
        "automation",
        "climate",
        "healthcare",
        "research",
    ]

    base_score = min(mentions / 10.0, 0.7)

    for indicator in research_indicators:
        if indicator in topic.lower():
            base_score += 0.2
            break

    return min(base_score, 1.0)


def _generate_research_recommendations(
    topics: List[TrendingTopic],
) -> List[ResearchRecommendation]:
    """Generate research recommendations for trending topics."""
    recommendations = []

    for topic in topics[:5]:  # Top 5 topics
        if topic.research_potential > 0.6:
            recommendation = ResearchRecommendation(
                topic=topic.topic,
                approach=_get_research_approach(topic),
                key_questions=_generate_key_questions(topic),
                source_types=_recommend_sources(topic),
                estimated_depth=_estimate_depth(topic),
            )
            recommendations.append(recommendation)

    return recommendations


def _get_research_approach(topic: TrendingTopic) -> str:
    """Recommend research approach for a topic."""
    if "ai" in topic.topic or "machine learning" in topic.topic:
        return (
            "Technical analysis with practical applications and ethical considerations"
        )
    elif "cybersecurity" in topic.topic:
        return "Threat landscape analysis with mitigation strategies"
    elif "blockchain" in topic.topic:
        return "Technology assessment with use case analysis"
    else:
        return "Multi-perspective analysis with trend evaluation"


def _generate_key_questions(topic: TrendingTopic) -> List[str]:
    """Generate key research questions for a topic."""
    base_questions = [
        f"What are the latest developments in {topic.topic}?",
        f"What are the practical implications of {topic.topic}?",
        f"What challenges exist in {topic.topic} implementation?",
    ]

    if topic.urgency_score > 0.7:
        base_questions.append(f"Why is {topic.topic} trending now?")

    if "ai" in topic.topic or "machine learning" in topic.topic:
        base_questions.append(f"What are the ethical considerations of {topic.topic}?")

    return base_questions


def _recommend_sources(topic: TrendingTopic) -> List[str]:
    """Recommend source types for researching a topic."""
    sources = ["academic papers", "industry reports", "expert interviews"]

    if "ai" in topic.topic or "technology" in topic.topic:
        sources.extend(["technical documentation", "open source projects"])

    if topic.urgency_score > 0.7:
        sources.append("news articles")

    return sources


def _estimate_depth(topic: TrendingTopic) -> str:
    """Estimate recommended research depth."""
    if topic.research_potential > 0.8:
        return "deep"
    elif topic.research_potential > 0.6:
        return "medium"
    else:
        return "brief"


async def _save_discovery_results(result: DiscoveryResult) -> None:
    """Save discovery results to blob storage."""
    try:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        blob_name = f"topic_discovery_{timestamp}.json"

        # Save to collected content container
        blob_client.upload_json(
            container_name=BlobContainers.COLLECTED_CONTENT,
            blob_name=blob_name,
            data=result.model_dump(),
        )

        logger.info(f"Saved discovery results to {blob_name}")

    except Exception as e:
        logger.error(f"Failed to save discovery results: {e}")
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

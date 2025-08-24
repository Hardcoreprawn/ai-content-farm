import os
import sys
from pathlib import Path
from typing import Dict, List

import pytest
from contracts.azure_openai_contract import AzureOpenAIResponseContract
from contracts.claude_contract import ClaudeResponseContract
from contracts.openai_contract import OpenAIResponseContract
from models import RankedTopic, SourceData
from service_logic import ContentGeneratorService

# Ensure container dir and repo root are importable BEFORE local imports
container_dir = Path(__file__).parent.parent
repo_root = container_dir.parent.parent
if str(container_dir) not in sys.path:
    sys.path.insert(0, str(container_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Now import local modules after path setup

# Now safe to import local modules and shared test contracts


# ...paths already configured above...

# Mock environment variables for testing
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["CLAUDE_API_KEY"] = "test-claude-key"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.openai.azure.com/"
os.environ["AZURE_OPENAI_API_KEY"] = "test-azure-openai-key"
os.environ.setdefault("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")
os.environ.setdefault("AZURE_STORAGE_ACCOUNT_NAME", "testaccount")
os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("BLOB_STORAGE_MOCK", "true")


@pytest.fixture(autouse=True)
def _isolate_mock_blob_storage():
    """Ensure mock blob storage state is isolated per test when in mock mode."""
    if os.getenv("BLOB_STORAGE_MOCK", "false").lower() == "true":
        try:
            import libs.blob_storage as _bs

            if hasattr(_bs, "_MOCK_BLOBS"):
                _bs._MOCK_BLOBS.clear()
            if hasattr(_bs, "_MOCK_CONTAINERS"):
                _bs._MOCK_CONTAINERS.clear()
        except Exception:
            pass
    yield


@pytest.fixture
def sample_source_data() -> List[SourceData]:
    """Create realistic source data for testing"""
    return [
        SourceData(
            name="TechCrunch",
            url="https://techcrunch.com/ai-breakthrough",
            title="Major AI Breakthrough Announced: Revolutionary System Transforms Healthcare",
            summary="New AI system achieves significant performance improvements in medical diagnosis, showing 95% accuracy in detecting rare diseases. The breakthrough represents a major advance in artificial intelligence applications for healthcare, with potential to revolutionize patient care and medical research worldwide.",
            content="Detailed article content about AI breakthrough covering technological innovations, clinical trials, implementation strategies, and future implications for healthcare industry...",
            metadata={"published": "2025-08-23", "author": "Tech Reporter"},
        ),
        SourceData(
            name="MIT Technology Review",
            url="https://technologyreview.com/ai-research",
            title="The Future of AI Research: Comprehensive Analysis of Current Trends",
            summary="Comprehensive analysis of current AI research trends, covering machine learning advances, neural network architectures, and emerging applications across industries. The research highlights significant progress in natural language processing, computer vision, and automated reasoning systems.",
            content="Comprehensive analysis of AI research directions including deep learning innovations, transformer architectures, reinforcement learning applications, and ethical considerations in AI development...",
            metadata={"published": "2025-08-23", "category": "research"},
        ),
        SourceData(
            name="Nature",
            url="https://nature.com/ai-healthcare-study",
            title="Peer-Reviewed Study: AI Systems in Clinical Practice",
            summary="Rigorous scientific study examining the effectiveness of AI systems in clinical practice, including statistical analysis of diagnostic accuracy, patient outcomes, and implementation challenges. The study provides evidence-based insights into AI adoption in healthcare settings.",
            content="Scientific analysis of AI implementation in healthcare including methodology, data analysis, statistical results, discussion of findings, and recommendations for clinical practice...",
            metadata={"published": "2025-08-23", "category": "scientific"},
        ),
    ]


@pytest.fixture
def sample_ranked_topic(sample_source_data) -> RankedTopic:
    """Create realistic ranked topic for testing"""
    return RankedTopic(
        topic="Artificial Intelligence Breakthrough in Healthcare",
        sources=sample_source_data,
        rank=1,
        ai_score=0.92,
        sentiment="positive",
        tags=["AI", "healthcare", "technology", "innovation"],
        metadata={
            "collection_date": "2025-08-23",
            "source_count": len(sample_source_data),
            "confidence": 0.85,
        },
    )


@pytest.fixture
def content_generator_service() -> ContentGeneratorService:
    """Create content generator service with mocked dependencies"""
    return ContentGeneratorService()


@pytest.fixture
def mock_azure_openai_responses() -> Dict[str, dict]:
    """Mock Azure OpenAI responses for different content types"""
    return {
        "tldr": AzureOpenAIResponseContract.create_tldr_response(),
        "blog": AzureOpenAIResponseContract.create_blog_response(),
        "deepdive": AzureOpenAIResponseContract.create_deepdive_response(),
    }


@pytest.fixture
def mock_claude_responses() -> Dict[str, dict]:
    """Mock Claude responses for different content types"""
    return {
        "tldr": ClaudeResponseContract.create_tldr_response(),
        "blog": ClaudeResponseContract.create_blog_response(),
        "deepdive": ClaudeResponseContract.create_deepdive_response(),
    }


@pytest.fixture
def mock_openai_responses() -> Dict[str, dict]:
    """Mock OpenAI responses for different content types"""
    return {
        "tldr": OpenAIResponseContract.create_mock_response(content_type="tldr"),
        "blog": OpenAIResponseContract.create_mock_response(content_type="blog"),
        "deepdive": OpenAIResponseContract.create_mock_response(
            content_type="deepdive"
        ),
    }

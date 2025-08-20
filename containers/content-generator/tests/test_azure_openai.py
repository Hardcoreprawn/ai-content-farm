#!/usr/bin/env python3
"""
Test Azure OpenAI integration
"""

import asyncio
import os
import sys

# Add root to path to access shared libs
sys.path.insert(0, "/workspaces/ai-content-farm")

from config import config
from models import RankedTopic
from service_logic import ContentGenerator

from libs.blob_storage import BlobStorageClient


async def test_azure_openai():
    """Test Azure OpenAI integration"""
    print("🧪 Testing Azure OpenAI Integration")
    print("=" * 50)

    # Check configuration
    print(f"Azure OpenAI Endpoint: {config.AZURE_OPENAI_ENDPOINT or 'Not set'}")
    print(
        f"Azure OpenAI Deployment: {config.AZURE_OPENAI_DEPLOYMENT_NAME or 'Not set'}"
    )
    print(f"API Key configured: {'Yes' if config.AZURE_OPENAI_API_KEY else 'No'}")

    if not config.AZURE_OPENAI_ENDPOINT or not config.AZURE_OPENAI_API_KEY:
        print("\n⚠️  Azure OpenAI not configured - using mock implementation")
        print("To test with real Azure OpenAI, set:")
        print("  - AZURE_OPENAI_ENDPOINT")
        print("  - AZURE_OPENAI_API_KEY")
        print("  - AZURE_OPENAI_DEPLOYMENT_NAME")

    # Initialize services
    blob_client = BlobStorageClient()
    content_generator = ContentGenerator(blob_client)

    # Create test topic
    test_topic = RankedTopic(
        topic="AI Infrastructure Investment in the UK",
        score=0.92,
        source_count=3,
        source_urls=[
            "https://techcrunch.com/uk-ai-investment",
            "https://reuters.com/technology/uk-ai-funding",
            "https://bbc.co.uk/news/technology-ai",
        ],
        keywords=["AI", "Investment", "Infrastructure", "UK"],
        category="Technology",
        priority="high",
    )

    print(f"\n📝 Test Topic: {test_topic.topic}")
    print(f"   Score: {test_topic.score}")
    print(f"   Sources: {test_topic.source_count}")

    # Test content generation
    try:
        print("\n🚀 Generating content...")
        result = await content_generator.generate_content_from_ranked_topics(
            ranked_topics=[test_topic],
            content_type="blog",
            writer_personality="professional",
            auto_notify=False,
        )

        if result and result.get("success"):
            content = result["generated_content"]
            print(f"✅ Success!")
            print(f"📖 Title: {content['title']}")
            print(f"📊 Word Count: {content['word_count']}")
            print(f"⏱️  Generation Time: {result['generation_time_seconds']:.2f}s")
            print(f"🔗 Sources Used: {len(content['sources_used'])}")

            # Show first few lines of content
            content_lines = content["content"].split("\n")[:5]
            print(f"\n📄 Content Preview:")
            for line in content_lines:
                if line.strip():
                    print(f"   {line}")
        else:
            error_msg = (
                result.get("error_message", "Unknown error")
                if result
                else "No result returned"
            )
            print(f"❌ Failed: {error_msg}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_azure_openai())

#!/usr/bin/env python3
"""Test script for Azure OpenAI integration."""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the container directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent))

from models import RankedTopic
from service_logic import ContentGenerator

from libs.blob_storage import BlobStorageClient


class MockBlobClient:
    """Mock blob client for testing."""

    async def upload_blob(self, container: str, blob_name: str, data: str) -> str:
        print(f"Mock upload to {container}/{blob_name}")
        return f"https://mock.blob.core.windows.net/{container}/{blob_name}"

    async def list_blobs_in_container(self, container: str):
        return []


async def test_azure_openai_integration():
    """Test Azure OpenAI integration with real or mock responses."""

    print("Testing Azure OpenAI Integration")
    print("=" * 50)

    # Check configuration
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-35-turbo")

    print(f"Azure OpenAI Endpoint: {'Set' if endpoint else 'Not Set'}")
    print(f"Azure OpenAI API Key: {'Set' if api_key else 'Not Set'}")
    print(f"Deployment Name: {deployment}")
    print()

    # Create content generator
    blob_client = MockBlobClient()
    generator = ContentGenerator(blob_client)

    # Check if Azure OpenAI client was initialized
    if generator.ai_client:
        print("✅ Azure OpenAI client initialized successfully")
    else:
        print("⚠️  Azure OpenAI client not initialized - will use mock responses")
    print()

    # Create test ranked topics
    test_topics = [
        RankedTopic(
            topic="Artificial Intelligence in Healthcare",
            score=95.0,
            source_count=3,
            source_urls=[
                "https://example.com/ai-healthcare-1",
                "https://example.com/ai-healthcare-2",
            ],
            keywords=["AI", "healthcare", "machine learning", "medical diagnosis"],
            category="technology",
            priority="high",
        ),
        RankedTopic(
            topic="Sustainable Energy Solutions",
            score=90.0,
            source_count=2,
            source_urls=["https://example.com/sustainable-energy-1"],
            keywords=["renewable energy", "solar", "wind power", "sustainability"],
            category="environment",
            priority="normal",
        ),
    ]

    print("Generating content for test topics...")
    print("-" * 30)

    try:
        # Generate content for each topic and content type
        results = []

        for topic in test_topics:
            for content_type in ["article", "tldr"]:
                for writer_personality in ["professional", "casual"]:
                    print(
                        f"Generating {content_type} content with {writer_personality} style for: {topic.topic}"
                    )

                    result = await generator.generate_content_from_ranked_topics(
                        ranked_topics=[topic],
                        content_type=content_type,
                        writer_personality=writer_personality,
                        auto_notify=False,
                    )

                    if result:
                        results.append(result)

        print(f"✅ Successfully generated {len(results)} pieces of content")

        # Display results
        for i, result in enumerate(results, 1):
            print(f"\n📄 Content {i}:")
            if isinstance(result, dict) and "generated_content" in result:
                content = result["generated_content"]
                print(f"   Topic: {content.get('topic', 'N/A')}")
                print(f"   Type: {content.get('content_type', 'N/A')}")
                print(f"   Writer: {content.get('writer_personality', 'N/A')}")
                print(f"   Title: {content.get('title', 'N/A')}")
                print(f"   Word Count: {content.get('word_count', 'N/A')}")
                print(f"   Generated: {content.get('generated_at', 'N/A')}")
                if "content" in content:
                    preview = (
                        content["content"][:100] + "..."
                        if len(content["content"]) > 100
                        else content["content"]
                    )
                    print(f"   Content Preview: {preview}")
            else:
                print(f"   Result: {str(result)[:200]}...")

        print(f"\n✅ Test completed successfully!")
        print(f"Generation count: {generator.get_generation_count()}")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_azure_openai_integration())

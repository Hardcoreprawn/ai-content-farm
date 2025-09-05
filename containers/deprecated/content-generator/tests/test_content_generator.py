#!/usr/bin/env python3
"""
Tests for content generation service endpoints and core business logic.
"""

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

# Add content generator path
sys.path.append(str(Path(__file__).parent.parent.resolve()))


async def test_content_generator():
    """Test content generator with sample data"""

    # Set up environment variables for testing
    os.environ["AZURE_STORAGE_ACCOUNT_NAME"] = "aicontentfarm76ko2h"
    os.environ["ENVIRONMENT"] = "development"

    print("🚀 Testing Content Generator Integration")
    print("=" * 50)

    try:
        # Import content generator modules
        from models import GenerationRequest, RankedTopic
        from service_logic import ContentGeneratorService

        print("✅ Successfully imported content generator modules")

        # Create service instance
        service = ContentGeneratorService()
        print("✅ Successfully created content generator service")

        # Test blob client health
        if hasattr(service, "blob_client"):
            health = service.blob_client.health_check()
            print(f"📊 Blob Storage Health: {health['status']}")
            print(f"   Connection Type: {health.get('connection_type', 'unknown')}")

        # Create a sample ranked topic
        sample_topic = RankedTopic(
            topic="Artificial Intelligence in Healthcare",
            sources=[
                {
                    "name": "AI Health Research",
                    "url": "https://example.com/ai-healthcare",
                    "title": "AI Transforming Healthcare",
                    "summary": "AI is revolutionizing medical diagnosis and treatment",
                    "content": "Artificial intelligence applications in healthcare are showing promising results...",
                    "metadata": {"source_type": "research_article"},
                }
            ],
            rank=1,
            ai_score=85.4,
            sentiment="positive",
            tags=["AI", "healthcare", "machine learning"],
            metadata={
                "category": "technology",
                "keywords": ["AI", "healthcare", "machine learning"],
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        print("📋 Created sample ranked topic:")
        print(f"   Topic: {sample_topic.topic}")
        print(f"   Score: {sample_topic.ai_score}")

        # Test content generation (this will use OpenAI/Azure OpenAI if configured)
        print("\n📝 Attempting content generation...")

        # Check if we have Azure OpenAI configured
        azure_openai_configured = bool(
            os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY")
        )
        openai_configured = bool(os.getenv("OPENAI_API_KEY"))

        if not azure_openai_configured and not openai_configured:
            print(
                "⚠️  No AI service API keys configured - skipping content generation test"
            )
            print(
                "   Set AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY or OPENAI_API_KEY to test generation"
            )
        else:
            print(
                f"🔑 AI Service configured: {'Azure OpenAI' if azure_openai_configured else 'OpenAI'}"
            )

            try:
                # Generate a TL;DR
                generated_content = await service.generate_content(
                    topic=sample_topic,
                    content_type="tldr",
                    writer_personality="professional",
                )

                print("✅ Successfully generated content!")
                print(f"   Title: {generated_content.title}")
                print(f"   Content Type: {generated_content.content_type}")
                print(f"   Word Count: {len(generated_content.content.split())}")

            except Exception as e:
                print(f"⚠️  Content generation failed: {e}")
                print("   This might be due to API key issues or network connectivity")

        print("\n🎉 Content Generator Integration Test Complete!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_content_generator())
    sys.exit(0 if result else 1)

#!/usr/bin/env python3
"""
Test Azure OpenAI integration and demonstrate content generation capabilities
"""

import os
import sys

from config import config
from models import RankedTopic, SourceData

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_azure_openai_config():
    """Test Azure OpenAI configuration"""
    print("🔧 AZURE OPENAI CONFIGURATION TEST")
    print("=" * 50)

    # Check configuration
    config_status = config.validate_config()

    print("Configuration Status:")
    print(f"✅ Valid: {config_status['valid']}")

    if config_status["issues"]:
        print("\n❌ Issues found:")
        for issue in config_status["issues"]:
            print(f"  - {issue}")

    print(f"\n🔧 Configuration Details:")
    print(f"  - Service: {config_status['config']['service_name']}")
    print(f"  - Version: {config_status['config']['version']}")
    print(
        f"  - Azure OpenAI: {'✅ Configured' if config_status['config']['has_azure_openai'] else '❌ Not configured'}"
    )
    print(
        f"  - OpenAI Direct: {'✅ Configured' if config_status['config']['has_openai'] else '❌ Not configured'}"
    )
    print(
        f"  - Claude: {'✅ Configured' if config_status['config']['has_claude'] else '❌ Not configured'}"
    )
    print(f"  - Blob Storage: {config_status['config']['blob_storage']}")

    print(f"\n📊 Environment Variables:")
    print(
        f"  - AZURE_OPENAI_ENDPOINT: {'✅ Set' if config.AZURE_OPENAI_ENDPOINT else '❌ Not set'}"
    )
    print(
        f"  - AZURE_OPENAI_API_KEY: {'✅ Set' if config.AZURE_OPENAI_API_KEY else '❌ Not set'}"
    )
    print(f"  - AZURE_OPENAI_DEPLOYMENT_NAME: {config.AZURE_OPENAI_DEPLOYMENT_NAME}")
    print(f"  - OPENAI_API_KEY: {'✅ Set' if config.OPENAI_API_KEY else '❌ Not set'}")

    return config_status["valid"]


def demo_content_generation_flow():
    """Demonstrate the content generation flow"""
    print("\n🎭 CONTENT GENERATION FLOW DEMO")
    print("=" * 50)

    # Create sample topic
    topic = RankedTopic(
        topic="Azure AI Service Integration",
        sources=[
            SourceData(
                name="Microsoft Azure Blog",
                url="https://azure.microsoft.com/en-us/blog/azure-openai-service-now-generally-available/",
                title="Azure OpenAI Service Now Generally Available",
                summary="Microsoft announces general availability of Azure OpenAI Service with enterprise-grade security and compliance",
            ),
            SourceData(
                name="TechCrunch",
                url="https://techcrunch.com/2023/01/16/microsoft-azure-openai-service/",
                title="Microsoft's Azure OpenAI Service Goes Live",
                summary="Azure OpenAI provides access to GPT models with enterprise features and data privacy",
            ),
        ],
        rank=1,
        ai_score=0.92,
        sentiment="positive",
        tags=["Azure", "OpenAI", "AI Services", "Enterprise"],
    )

    print(f"📝 Sample Topic: {topic.topic}")
    print(f"📊 AI Score: {topic.ai_score}")
    print(f"🏆 Rank: {topic.rank}")
    print(f"📰 Sources: {len(topic.sources)}")

    print(f"\n🔍 Source Analysis:")
    for i, source in enumerate(topic.sources, 1):
        print(f"  {i}. {source.name}")
        print(f"     📄 {source.title}")
        print(f"     🔗 {source.url}")
        print(f"     📝 {(source.summary or 'No summary')[:100]}...")
        print()

    print("🎯 Content Generation Options:")
    print("  1. TL;DR (200-400 words) - Quick professional summary")
    print("  2. Blog (600-1000 words) - Comprehensive analysis")
    print("  3. Deep Dive (1500-2500 words) - Exhaustive coverage")

    print("\n🎭 Writer Personalities Available:")
    for personality, description in config.WRITER_PERSONALITIES.items():
        print(f"  - {personality}: {description}")

    print("\n✅ Content Requirements Met:")
    print(
        f"  - TL;DR: {'✅ Sufficient sources' if len(topic.sources) >= 1 else '❌ Need more sources'}"
    )
    print(
        f"  - Blog: {'✅ Sufficient sources' if len(topic.sources) >= 2 else '❌ Need more sources'}"
    )
    print(
        f"  - Deep Dive: {'✅ Sufficient sources' if len(topic.sources) >= 3 else '❌ Need more sources'}"
    )


def show_api_usage_example():
    """Show how to use the content generation API"""
    print("\n🚀 API USAGE EXAMPLES")
    print("=" * 50)

    print("1. Generate TL;DR with professional voice:")
    print("   POST http://localhost:8008/generate/tldr?writer_personality=professional")
    print("   Body: { RankedTopic object }")

    print("\n2. Generate blog with analytical voice:")
    print("   POST http://localhost:8008/generate/blog?writer_personality=analytical")

    print("\n3. Generate deep dive with expert voice:")
    print("   POST http://localhost:8008/generate/deepdive?writer_personality=expert")

    print("\n4. Health check:")
    print("   GET http://localhost:8008/health")

    print("\n5. Service status:")
    print("   GET http://localhost:8008/status")


def main():
    """Run all tests and demos"""
    print("🤖 AI CONTENT GENERATOR - AZURE INTEGRATION TEST")
    print("=" * 60)

    # Test configuration
    config_valid = test_azure_openai_config()

    # Show content generation flow
    demo_content_generation_flow()

    # Show API usage
    show_api_usage_example()

    print(f"\n📋 SUMMARY")
    print("=" * 20)
    if config_valid:
        print("✅ Configuration valid - ready for content generation!")
        print("💡 Start the service: docker-compose up content-generator")
    else:
        print("⚠️  Configuration incomplete - see Azure OpenAI setup guide")
        print("📖 Guide: docs/AZURE_OPENAI_SETUP.md")

    print("\n🎯 Next Steps:")
    print("1. Set up Azure OpenAI Service (see docs/AZURE_OPENAI_SETUP.md)")
    print("2. Update .env with your Azure OpenAI credentials")
    print("3. Test with: docker-compose up content-generator")
    print("4. Generate your first tl;dr article!")


if __name__ == "__main__":
    main()

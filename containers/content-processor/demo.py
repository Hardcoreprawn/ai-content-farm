#!/usr/bin/env python3
"""
Content Processor Demo

Demonstrates the full capabilities of the enhanced content processor
with real OpenAI integration, multiple processing types, and comprehensive features.
"""

import json
import time

from fastapi.testclient import TestClient
from main import app


def run_demo():
    """Run a comprehensive demo of the content processor capabilities."""

    print("🚀 CONTENT PROCESSOR DEMO - Phase 3 Complete!")
    print("=" * 60)

    client = TestClient(app)

    print("\n📋 AVAILABLE PROCESSING TYPES")
    print("-" * 30)
    response = client.get("/process/types")
    types_data = response.json()["data"]

    for proc_type, info in types_data["available_types"].items():
        print(f"• {proc_type.upper()}: {info['description']}")
        print(
            f"  Model: {info['typical_model']} | Cost: {info['estimated_cost_range']}"
        )

    print(f"\n🎨 SUPPORTED VOICES: {', '.join(types_data['supported_voices'])}")
    print(f"👥 TARGET AUDIENCES: {', '.join(types_data['supported_audiences'])}")

    # Demo different processing types
    test_cases = [
        {
            "name": "📰 ARTICLE GENERATION",
            "content": "The future of artificial intelligence in healthcare",
            "processing_type": "article_generation",
            "options": {
                "voice": "professional",
                "target_audience": "general",
                "max_length": 800,
            },
        },
        {
            "name": "🔍 CONTENT ANALYSIS",
            "content": "Artificial intelligence is revolutionizing healthcare through machine learning algorithms that can diagnose diseases, predict patient outcomes, and personalize treatment plans. This technology offers unprecedented opportunities for improving patient care.",
            "processing_type": "content_analysis",
            "options": {"voice": "academic", "target_audience": "technical"},
        },
        {
            "name": "⭐ QUALITY ASSESSMENT",
            "content": "AI in healthcare is good. It helps doctors. Machine learning can detect diseases early. This improves patient outcomes and reduces costs.",
            "processing_type": "quality_assessment",
            "options": {"voice": "professional", "target_audience": "general"},
        },
        {
            "name": "🌟 TOPIC EXPANSION",
            "content": "Quantum computing applications",
            "processing_type": "topic_expansion",
            "options": {
                "voice": "technical",
                "target_audience": "academic",
                "max_length": 600,
            },
        },
    ]

    results = []
    total_cost = 0.0

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{test_case['name']} ({i}/{len(test_cases)})")
        print("-" * 40)

        start_time = time.time()
        response = client.post(
            "/process",
            json={
                "content": test_case["content"],
                "processing_type": test_case["processing_type"],
                "options": test_case["options"],
            },
        )
        processing_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()["data"]
            metadata = result["processing_metadata"]

            print(f"✅ SUCCESS!")
            print(f"📊 Quality Score: {result['quality_score']:.2f}/1.00")
            print(f"🤖 Model Used: {metadata['model_used']}")
            print(f"🌍 Region: {metadata['region']}")
            print(f"💰 Cost: ${metadata['estimated_cost']:.4f}")
            print(f"⏱️  Processing Time: {metadata['processing_time']:.2f}s")
            print(f"📝 Content Length: {len(result['processed_content'])} chars")
            print(
                f"🎭 Voice: {metadata['voice']} | 👥 Audience: {metadata['target_audience']}"
            )

            if test_case["processing_type"] == "quality_assessment":
                # Extract quality score from the content for quality assessment
                content_lines = result["processed_content"].split("\n")
                score_line = [
                    line
                    for line in content_lines
                    if "Score:" in line and "/1.00" in line
                ]
                if score_line:
                    print(f"📈 Assessed Score: {score_line[0].split('Score: ')[1]}")

            total_cost += metadata["estimated_cost"]
            results.append(
                {
                    "type": test_case["processing_type"],
                    "quality": result["quality_score"],
                    "cost": metadata["estimated_cost"],
                    "model": metadata["model_used"],
                    "region": metadata["region"],
                }
            )

            # Show a sample of the generated content
            content_preview = result["processed_content"][:200]
            if len(result["processed_content"]) > 200:
                content_preview += "..."
            print(f"📄 Preview: {content_preview}")

        else:
            print(f"❌ FAILED: {response.status_code}")
            print(f"Error: {response.json()}")

    # Show final statistics
    print(f"\n📈 PROCESSING STATISTICS")
    print("-" * 30)
    response = client.get("/process/status")
    stats = response.json()["data"]

    print(f"📊 Total Processed: {stats['total_processed']}")
    print(f"✅ Success Rate: {stats['success_rate']:.1%}")
    print(f"💰 Total Session Cost: ${total_cost:.4f}")
    print(f"🌍 Region Usage: {stats['region_usage']}")
    print(f"🧪 Mock Mode: {stats.get('mock_mode', False)}")

    # Show model distribution
    model_usage = {}
    for result in results:
        model = result["model"]
        if model not in model_usage:
            model_usage[model] = []
        model_usage[model].append(result["type"])

    print(f"\n🤖 MODEL USAGE DISTRIBUTION")
    print("-" * 30)
    for model, types in model_usage.items():
        print(f"• {model}: {', '.join(types)}")

    print(f"\n🎯 QUALITY SCORES BY TYPE")
    print("-" * 30)
    for result in results:
        print(f"• {result['type']}: {result['quality']:.2f} (${result['cost']:.4f})")

    print(f"\n🚀 DEMO COMPLETE!")
    print("=" * 60)
    print("✨ Content Processor Phase 3: External API Integration - COMPLETE!")
    print("🔥 Features: Multi-region OpenAI, Smart model selection, Cost tracking,")
    print("   Quality assessment, Voice consistency, Retry logic, Mock fallback")
    print("🎯 Ready for Phase 4: Azure Function Integration!")


if __name__ == "__main__":
    run_demo()
